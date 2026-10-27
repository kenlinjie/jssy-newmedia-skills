#!/usr/bin/env python3
"""Resumable local long-audio transcription with Qwen3-ASR on Apple Silicon."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import gc
import hashlib
from importlib import metadata
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import unicodedata
import wave
from typing import Any


RUNTIME_VERSION = "0.4.6"
VENV_PYTHON = Path.home() / ".local/share/codex-local-asr/venv/bin/python"
MODEL_ROOT = Path.home() / "Library/Caches/codex-local-asr/models"
DEFAULT_ASR_MODEL = MODEL_ROOT / "Qwen3-ASR-0.6B-8bit"
DEFAULT_ALIGNER_MODEL = MODEL_ROOT / "Qwen3-ForcedAligner-0.6B-8bit"


@dataclass(frozen=True)
class Chunk:
    index: int
    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Transcribe long local audio/video with Qwen3-ASR, resumable per-chunk "
            "checkpoints, and optional word-level forced alignment."
        )
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--language", default="Chinese")
    parser.add_argument("--asr-model", type=Path, default=DEFAULT_ASR_MODEL)
    parser.add_argument("--aligner-model", type=Path, default=DEFAULT_ALIGNER_MODEL)
    alignment = parser.add_mutually_exclusive_group()
    alignment.add_argument(
        "--align",
        action="store_true",
        help=(
            "Add word-level timestamps in a second phase after unloading the ASR "
            "model. Coarse chunk timing is the lightweight default."
        ),
    )
    alignment.add_argument(
        "--no-align",
        action="store_true",
        help="Deprecated compatibility flag; coarse timing is already the default.",
    )
    parser.add_argument("--chunk-seconds", type=float, default=240.0)
    parser.add_argument("--overlap-seconds", type=float, default=4.0)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--start-seconds", type=float, default=0.0)
    parser.add_argument("--duration-seconds", type=float)
    parser.add_argument("--context-file", type=Path)
    parser.add_argument(
        "--term",
        action="append",
        default=[],
        help="Domain term or proper noun to bias recognition; may be repeated.",
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Validate runtime, models, source, and output boundary without transcribing.",
    )
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def ensure_runtime() -> None:
    current_prefix = Path(sys.prefix).resolve()
    expected_prefix = VENV_PYTHON.parent.parent.resolve()
    if current_prefix != expected_prefix:
        if not VENV_PYTHON.is_file():
            raise SystemExit(
                f"Local ASR runtime is missing: {VENV_PYTHON}. "
                "Run scripts/bootstrap_runtime.sh with network and local-write approval."
            )
        os.execv(
            str(VENV_PYTHON),
            [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]],
        )


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def probe_source(source: Path) -> dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise SystemExit("ffprobe is not installed")
    result = run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "format=duration,size:stream=codec_name,sample_rate,channels",
            "-of",
            "json",
            str(source),
        ]
    )
    payload = json.loads(result.stdout)
    streams = payload.get("streams") or []
    if not streams:
        raise SystemExit(f"No readable audio stream found: {source}")
    duration = float(payload["format"]["duration"])
    if not math.isfinite(duration) or duration <= 0:
        raise SystemExit(f"Invalid media duration: {duration}")
    return {
        "duration_seconds": duration,
        "size_bytes": source.stat().st_size,
        "stream": streams[0],
    }


def verify_model_directory(path: Path, label: str) -> dict[str, Any]:
    required = [path / "config.json", path / "model.safetensors"]
    missing = [str(item) for item in required if not item.is_file()]
    if missing:
        raise SystemExit(f"{label} model is incomplete; missing: {', '.join(missing)}")
    source_meta = path / "MODEL_SOURCE.json"
    metadata_payload = None
    if source_meta.is_file():
        metadata_payload = json.loads(source_meta.read_text(encoding="utf-8"))
        expected_bytes = metadata_payload.get("weight_bytes")
        expected_sha256 = metadata_payload.get("weight_sha256")
        actual_bytes = (path / "model.safetensors").stat().st_size
        if expected_bytes is not None and actual_bytes != int(expected_bytes):
            raise SystemExit(
                f"{label} model size mismatch: {actual_bytes}/{expected_bytes}"
            )
        if expected_sha256:
            actual_sha256 = hash_file(path / "model.safetensors")
            if actual_sha256 != expected_sha256:
                raise SystemExit(
                    f"{label} model SHA-256 mismatch: "
                    f"{actual_sha256}/{expected_sha256}"
                )
    return {
        "path": str(path.resolve()),
        "weight_bytes": (path / "model.safetensors").stat().st_size,
        "source": metadata_payload,
    }


def load_context(args: argparse.Namespace) -> str:
    pieces: list[str] = []
    if args.context_file:
        if not args.context_file.is_file():
            raise SystemExit(f"Context file does not exist: {args.context_file}")
        context_text = args.context_file.read_text(encoding="utf-8").strip()
        if len(context_text) > 50_000:
            raise SystemExit("Context file exceeds the 50,000-character safety limit")
        if context_text:
            pieces.append(context_text)
    terms = [term.strip() for term in args.term if term.strip()]
    if terms:
        pieces.append("专有名词：" + "、".join(terms))
    if not pieces:
        return ""
    combined = "\n".join(pieces)
    if len(combined) > 8_000:
        combined = combined[:8_000]
    return (
        "只转写音频中实际说出的内容，不补写未听到的内容。"
        "优先准确识别以下会议上下文和专有名词：\n" + combined
    )


def plan_chunks(
    start: float, end: float, chunk_seconds: float, overlap_seconds: float
) -> list[Chunk]:
    if chunk_seconds <= 1:
        raise SystemExit("--chunk-seconds must be greater than 1")
    if overlap_seconds < 0 or overlap_seconds >= chunk_seconds:
        raise SystemExit("--overlap-seconds must be >= 0 and < chunk-seconds")
    step = chunk_seconds - overlap_seconds
    chunks: list[Chunk] = []
    cursor = start
    index = 0
    while cursor < end - 0.001:
        chunk_end = min(cursor + chunk_seconds, end)
        chunks.append(Chunk(index=index, start=cursor, end=chunk_end))
        if chunk_end >= end:
            break
        cursor += step
        index += 1
    return chunks


def extract_chunk(source: Path, chunk: Chunk, wav_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg is not installed")
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    if wav_path.exists():
        wav_path.unlink()
    run(
        [
            ffmpeg,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{chunk.start:.3f}",
            "-t",
            f"{chunk.duration:.3f}",
            "-i",
            str(source),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(wav_path),
        ]
    )
    if not wav_path.is_file() or wav_path.stat().st_size <= 44:
        raise RuntimeError(f"ffmpeg produced no usable WAV: {wav_path}")
    with wave.open(str(wav_path), "rb") as handle:
        if handle.getnchannels() != 1 or handle.getframerate() != 16000:
            raise RuntimeError(f"Unexpected WAV format: {wav_path}")
        actual_duration = handle.getnframes() / handle.getframerate()
    if abs(actual_duration - chunk.duration) > 0.25:
        raise RuntimeError(
            f"Chunk duration mismatch: planned={chunk.duration:.3f}, "
            f"actual={actual_duration:.3f}"
        )


def chunk_result_is_reusable(
    path: Path, fingerprint: str, source_sha256: str
) -> bool:
    if not path.is_file():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        payload.get("status") == "complete"
        and payload.get("fingerprint") == fingerprint
        and payload.get("source_sha256") == source_sha256
        and bool(str(payload.get("text", "")).strip())
    )


def alignment_fingerprint(
    aligner_info: dict[str, Any], text: str, language: str
) -> str:
    return digest_json(
        {
            "aligner": aligner_info,
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "language": language,
        }
    )


def chunk_alignment_is_reusable(
    payload: dict[str, Any], expected_fingerprint: str
) -> bool:
    return (
        bool(payload.get("alignment"))
        and payload.get("alignment_fingerprint") == expected_fingerprint
    )


def serialize_alignment(alignment: Any) -> list[dict[str, Any]]:
    items = getattr(alignment, "items", alignment)
    return [
        {
            "text": str(item.text),
            "start": float(item.start_time),
            "end": float(item.end_time),
        }
        for item in items
        if str(item.text).strip()
    ]


def ownership_bounds(chunks: list[Chunk], index: int) -> tuple[float, float]:
    chunk = chunks[index]
    if index == 0:
        left = chunk.start
    else:
        previous = chunks[index - 1]
        left = (previous.end + chunk.start) / 2
    if index == len(chunks) - 1:
        right = chunk.end
    else:
        following = chunks[index + 1]
        right = (chunk.end + following.start) / 2
    return left, right


def is_cjk(character: str) -> bool:
    if not character:
        return False
    code = ord(character)
    return (
        0x3400 <= code <= 0x4DBF
        or 0x4E00 <= code <= 0x9FFF
        or 0xF900 <= code <= 0xFAFF
        or 0x3040 <= code <= 0x30FF
        or 0xAC00 <= code <= 0xD7AF
    )


def join_token(existing: str, token: str) -> str:
    token = token.strip()
    if not existing:
        return token
    if not token:
        return existing
    no_space_before = "，。！？；：、,.!?;:%)]}》」』”’"
    no_space_after = "([{《「『“‘"
    if (
        token[0] in no_space_before
        or existing[-1] in no_space_after
        or is_cjk(token[0])
        or is_cjk(existing[-1])
        or unicodedata.category(token[0]).startswith("P")
    ):
        return existing + token
    return existing + " " + token


def group_words(words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    current_text = ""
    current_start = 0.0
    current_end = 0.0
    current_chunks: set[int] = set()
    terminal = ("。", "！", "？", "!", "?", "；", ";")

    def flush() -> None:
        nonlocal current_text, current_start, current_end, current_chunks
        if current_text.strip():
            segments.append(
                {
                    "start": round(current_start, 3),
                    "end": round(max(current_end, current_start), 3),
                    "text": current_text.strip(),
                    "source_chunks": sorted(current_chunks),
                }
            )
        current_text = ""
        current_start = 0.0
        current_end = 0.0
        current_chunks = set()

    for word in words:
        text = str(word["text"]).strip()
        if not text:
            continue
        if not current_text:
            current_start = float(word["start"])
        current_text = join_token(current_text, text)
        current_end = float(word["end"])
        current_chunks.add(int(word["chunk_index"]))
        elapsed = current_end - current_start
        if current_text.endswith(terminal) or elapsed >= 30 or len(current_text) >= 160:
            flush()
    flush()
    return segments


def format_clock(seconds: float, decimal: str = ".") -> str:
    milliseconds = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{decimal}{millis:03d}"


def merge_results(
    chunks: list[Chunk],
    results_dir: Path,
    source_name: str,
    source_sha256: str,
    source_duration: float,
    fingerprint: str,
    language: str,
    model_info: dict[str, Any],
    aligner_info: dict[str, Any] | None,
    alignment_requested: bool,
) -> tuple[dict[str, Any], list[str]]:
    words: list[dict[str, Any]] = []
    coarse_segments: list[dict[str, Any]] = []
    warnings: list[str] = []
    chunk_payloads: list[dict[str, Any]] = []

    for chunk in chunks:
        path = results_dir / f"chunk-{chunk.index:05d}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        chunk_payloads.append(payload)
        left, right = ownership_bounds(chunks, chunk.index)
        aligned = (payload.get("alignment") or []) if alignment_requested else []
        if aligned:
            for item in aligned:
                global_start = chunk.start + float(item["start"])
                global_end = chunk.start + float(item["end"])
                midpoint = (global_start + global_end) / 2
                if midpoint < left or midpoint >= right:
                    continue
                words.append(
                    {
                        "start": round(max(chunk.start, global_start), 3),
                        "end": round(min(chunk.end, max(global_end, global_start)), 3),
                        "text": str(item["text"]),
                        "chunk_index": chunk.index,
                    }
                )
        else:
            if alignment_requested:
                warnings.append(
                    f"chunk-{chunk.index:05d} has no requested word alignment; "
                    "using coarse timing"
                )
            coarse_segments.append(
                {
                    "start": round(left, 3),
                    "end": round(right, 3),
                    "text": str(payload["text"]).strip(),
                    "source_chunks": [chunk.index],
                }
            )

    words.sort(key=lambda item: (item["start"], item["end"], item["chunk_index"]))
    if words:
        segments = group_words(words)
        if coarse_segments:
            segments.extend(coarse_segments)
            segments.sort(key=lambda item: item["start"])
    else:
        segments = coarse_segments

    transcript_text = "\n".join(segment["text"] for segment in segments).strip()
    timing_mode = (
        "word" if words and not coarse_segments else "mixed" if words else "coarse"
    )
    payload = {
        "schema_version": 1,
        "status": "complete" if not warnings else "partial",
        "source": {
            "name": source_name,
            "sha256": source_sha256,
            "duration_seconds": source_duration,
            "scope_start": chunks[0].start,
            "scope_end": chunks[-1].end,
        },
        "runtime": {"mlx_audio": RUNTIME_VERSION},
        "model": model_info,
        "aligner": aligner_info,
        "timing_mode": timing_mode,
        "alignment_requested": alignment_requested,
        "language": language,
        "fingerprint": fingerprint,
        "chunk_count": len(chunks),
        "segments": segments,
        "words": words,
        "text": transcript_text,
        "warnings": warnings,
        "generated_at": utc_now(),
        "chunk_metrics": [
            {
                "index": int(item["chunk"]["index"]),
                "asr_elapsed_seconds": item.get(
                    "asr_elapsed_seconds", item.get("elapsed_seconds")
                ),
                "alignment_elapsed_seconds": item.get(
                    "alignment_elapsed_seconds"
                ),
                "asr_total_time": item.get("asr_total_time"),
                "generation_tokens": item.get("generation_tokens"),
                "alignment_items": len(item.get("alignment") or []),
            }
            for item in chunk_payloads
        ],
    }
    return payload, warnings


def write_reader_outputs(output_dir: Path, transcript: dict[str, Any]) -> None:
    segments = transcript["segments"]
    txt_lines = [
        f"[{format_clock(float(segment['start']))}] {segment['text']}"
        for segment in segments
    ]
    atomic_text(output_dir / "transcript.txt", "\n".join(txt_lines) + "\n")

    srt_lines: list[str] = []
    for index, segment in enumerate(segments, start=1):
        srt_lines.extend(
            [
                str(index),
                f"{format_clock(float(segment['start']), ',')} --> "
                f"{format_clock(float(segment['end']), ',')}",
                str(segment["text"]),
                "",
            ]
        )
    atomic_text(output_dir / "transcript.srt", "\n".join(srt_lines))

    source = transcript["source"]
    model = transcript["model"]
    markdown = [
        f"# {source['name']} 本地转写",
        "",
        f"- 状态：`{transcript['status']}`",
        f"- 模型：`{Path(model['path']).name}`",
        f"- 源文件 SHA-256：`{source['sha256']}`",
        f"- 源时长：`{format_clock(float(source['duration_seconds']))}`",
        f"- 分块数：{transcript['chunk_count']}",
        f"- 时间戳模式：`{transcript['timing_mode']}`",
        "",
        "## 逐字稿",
        "",
    ]
    for segment in segments:
        markdown.append(
            f"[{format_clock(float(segment['start']))}–"
            f"{format_clock(float(segment['end']))}] {segment['text']}"
        )
        markdown.append("")
    if transcript["warnings"]:
        markdown.extend(["## 完整性说明", ""])
        markdown.extend(f"- {warning}" for warning in transcript["warnings"])
        markdown.append("")
    atomic_text(output_dir / "transcript.md", "\n".join(markdown))
    atomic_json(output_dir / "transcript.json", transcript)


def validate_existing_output_boundary(output_dir: Path, fingerprint: str) -> None:
    if not output_dir.exists():
        return
    if not output_dir.is_dir():
        raise SystemExit(f"Output path exists and is not a directory: {output_dir}")
    manifest_path = output_dir / "manifest.json"
    entries = list(output_dir.iterdir())
    if entries and not manifest_path.is_file():
        raise SystemExit(
            f"Refusing to use a non-empty output directory without manifest.json: "
            f"{output_dir}"
        )
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("fingerprint") != fingerprint:
            raise SystemExit(
                "Existing output parameters do not match this run. "
                "Choose a new --output-dir; no files were overwritten."
            )


def main() -> int:
    args = parse_args()
    ensure_runtime()
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    source = args.source.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    asr_model_path = args.asr_model.expanduser().resolve()
    aligner_model_path = args.aligner_model.expanduser().resolve()

    if not source.is_file() or not os.access(source, os.R_OK):
        raise SystemExit(f"Source is not a readable file: {source}")
    probe = probe_source(source)
    if args.start_seconds < 0 or args.start_seconds >= probe["duration_seconds"]:
        raise SystemExit("--start-seconds must fall within the source duration")
    scope_end = probe["duration_seconds"]
    if args.duration_seconds is not None:
        if args.duration_seconds <= 0:
            raise SystemExit("--duration-seconds must be positive")
        scope_end = min(scope_end, args.start_seconds + args.duration_seconds)

    runtime_version = metadata.version("mlx-audio")
    if runtime_version != RUNTIME_VERSION:
        raise SystemExit(
            f"Expected mlx-audio {RUNTIME_VERSION}, found {runtime_version}. "
            "Refusing unvalidated runtime drift."
        )
    import mlx.core as mx

    if not mx.metal.is_available():
        raise SystemExit(
            "MLX cannot access a Metal device. Run this command outside a headless "
            "or sandboxed process with local GPU access."
        )

    alignment_requested = bool(args.align)
    model_info = verify_model_directory(asr_model_path, "ASR")
    aligner_info = None
    if alignment_requested:
        aligner_info = verify_model_directory(aligner_model_path, "aligner")
    context = load_context(args)
    chunks = plan_chunks(
        args.start_seconds,
        scope_end,
        args.chunk_seconds,
        args.overlap_seconds,
    )
    source_sha256 = hash_file(source)
    transcription_configuration = {
        "schema_version": 2,
        "source": str(source),
        "source_sha256": source_sha256,
        "source_size": source.stat().st_size,
        "scope_start": args.start_seconds,
        "scope_end": scope_end,
        "language": args.language,
        "asr_model": model_info,
        "mlx_audio_version": runtime_version,
        "chunk_seconds": args.chunk_seconds,
        "overlap_seconds": args.overlap_seconds,
        "max_tokens": args.max_tokens,
        "context_sha256": hashlib.sha256(context.encode("utf-8")).hexdigest(),
    }
    fingerprint = digest_json(transcription_configuration)
    configuration = {
        **transcription_configuration,
        "alignment_requested": alignment_requested,
        "aligner_model": aligner_info,
    }
    validate_existing_output_boundary(output_dir, fingerprint)

    preflight_payload = {
        "status": "ready",
        "source": str(source),
        "probe": probe,
        "scope": {"start": args.start_seconds, "end": scope_end},
        "source_sha256": source_sha256,
        "runtime": {"python": sys.version.split()[0], "mlx_audio": runtime_version},
        "model": model_info,
        "aligner": aligner_info,
        "alignment_requested": alignment_requested,
        "timing_mode": "word" if alignment_requested else "coarse",
        "chunk_count": len(chunks),
        "fingerprint": fingerprint,
    }
    if args.preflight:
        print(json.dumps(preflight_payload, ensure_ascii=False, indent=2))
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    chunks_dir = output_dir / "chunks"
    results_dir = output_dir / "chunk-results"
    chunks_dir.mkdir(exist_ok=True)
    results_dir.mkdir(exist_ok=True)
    if context:
        atomic_text(output_dir / "context.txt", context + "\n")

    manifest_path = output_dir / "manifest.json"
    manifest = {
        **preflight_payload,
        "status": "transcribing",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "configuration": configuration,
        "completed_chunks": [],
        "aligned_chunks": [],
        "failed_chunk": None,
    }
    if manifest_path.is_file():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["created_at"] = previous.get("created_at", manifest["created_at"])
    atomic_json(manifest_path, manifest)

    from mlx_audio.stt import load

    asr_model = None
    completed_chunks: list[int] = []

    for chunk in chunks:
        result_path = results_dir / f"chunk-{chunk.index:05d}.json"
        if chunk_result_is_reusable(result_path, fingerprint, source_sha256):
            completed_chunks.append(chunk.index)
            print(
                f"[{chunk.index + 1}/{len(chunks)}] reuse checkpoint "
                f"{result_path.name}",
                flush=True,
            )
            continue

        wav_path = chunks_dir / f"chunk-{chunk.index:05d}.wav"
        started = time.monotonic()
        try:
            if asr_model is None:
                print(f"Loading ASR model: {asr_model_path}", flush=True)
                asr_model = load(str(asr_model_path))
            print(
                f"[{chunk.index + 1}/{len(chunks)}] extract "
                f"{format_clock(chunk.start)}–{format_clock(chunk.end)}",
                flush=True,
            )
            extract_chunk(source, chunk, wav_path)
            result = asr_model.generate(
                str(wav_path),
                max_tokens=args.max_tokens,
                batch_size=1,
                temperature=0.0,
                language=args.language,
                chunk_duration=args.chunk_seconds + 1,
                system_prompt=context or None,
                verbose=args.verbose,
            )
            text = str(result.text).strip()
            if not text:
                raise RuntimeError("ASR returned empty text")

            chunk_payload = {
                "schema_version": 2,
                "status": "complete",
                "fingerprint": fingerprint,
                "source_sha256": source_sha256,
                "chunk": asdict(chunk),
                "text": text,
                "alignment": [],
                "alignment_fingerprint": None,
                "language": args.language,
                "asr_elapsed_seconds": round(time.monotonic() - started, 3),
                "asr_total_time": getattr(result, "total_time", None),
                "prompt_tokens": getattr(result, "prompt_tokens", None),
                "generation_tokens": getattr(result, "generation_tokens", None),
                "completed_at": utc_now(),
            }
            atomic_json(result_path, chunk_payload)
            completed_chunks.append(chunk.index)
            wav_path.unlink(missing_ok=True)
            mx.clear_cache()
            manifest.update(
                {
                    "status": "transcribing",
                    "completed_chunks": completed_chunks,
                    "failed_chunk": None,
                    "updated_at": utc_now(),
                }
            )
            atomic_json(manifest_path, manifest)
            print(
                f"[{chunk.index + 1}/{len(chunks)}] checkpoint saved "
                f"({chunk_payload['asr_elapsed_seconds']:.1f}s)",
                flush=True,
            )
        except Exception as exc:
            error_payload = {
                "status": "error",
                "fingerprint": fingerprint,
                "source_sha256": source_sha256,
                "chunk": asdict(chunk),
                "error_type": type(exc).__name__,
                "error": str(exc),
                "failed_at": utc_now(),
            }
            atomic_json(results_dir / f"chunk-{chunk.index:05d}.error.json", error_payload)
            manifest.update(
                {
                    "status": "partial",
                    "completed_chunks": completed_chunks,
                    "failed_chunk": chunk.index,
                    "error": error_payload,
                    "updated_at": utc_now(),
                }
            )
            atomic_json(manifest_path, manifest)
            raise

    if asr_model is not None:
        print("Unloading ASR model before optional alignment", flush=True)
        result = None
        del asr_model
        gc.collect()
        mx.clear_cache()

    aligned_chunks: list[int] = []
    if alignment_requested:
        if aligner_info is None:
            raise RuntimeError("Alignment was requested without verified aligner metadata")
        manifest.update(
            {
                "status": "aligning",
                "completed_chunks": completed_chunks,
                "aligned_chunks": aligned_chunks,
                "failed_chunk": None,
                "updated_at": utc_now(),
            }
        )
        atomic_json(manifest_path, manifest)
        aligner_model = None

        for chunk in chunks:
            result_path = results_dir / f"chunk-{chunk.index:05d}.json"
            payload = json.loads(result_path.read_text(encoding="utf-8"))
            text = str(payload["text"]).strip()
            expected_alignment_fingerprint = alignment_fingerprint(
                aligner_info, text, args.language
            )
            if chunk_alignment_is_reusable(
                payload, expected_alignment_fingerprint
            ):
                aligned_chunks.append(chunk.index)
                print(
                    f"[{chunk.index + 1}/{len(chunks)}] reuse alignment "
                    f"{result_path.name}",
                    flush=True,
                )
                continue

            wav_path = chunks_dir / f"chunk-{chunk.index:05d}.wav"
            started = time.monotonic()
            try:
                if aligner_model is None:
                    print(
                        f"Loading forced aligner after ASR unload: "
                        f"{aligner_model_path}",
                        flush=True,
                    )
                    aligner_model = load(str(aligner_model_path))
                print(
                    f"[{chunk.index + 1}/{len(chunks)}] align "
                    f"{format_clock(chunk.start)}–{format_clock(chunk.end)}",
                    flush=True,
                )
                extract_chunk(source, chunk, wav_path)
                alignment = aligner_model.generate(
                    str(wav_path), text=text, language=args.language
                )
                alignment_items = serialize_alignment(alignment)
                if not alignment_items:
                    raise RuntimeError("Forced aligner returned no timestamp items")
                payload.update(
                    {
                        "alignment": alignment_items,
                        "alignment_fingerprint": expected_alignment_fingerprint,
                        "alignment_model": aligner_info,
                        "alignment_elapsed_seconds": round(
                            time.monotonic() - started, 3
                        ),
                        "alignment_completed_at": utc_now(),
                    }
                )
                atomic_json(result_path, payload)
                aligned_chunks.append(chunk.index)
                wav_path.unlink(missing_ok=True)
                mx.clear_cache()
                manifest.update(
                    {
                        "status": "aligning",
                        "completed_chunks": completed_chunks,
                        "aligned_chunks": aligned_chunks,
                        "failed_chunk": None,
                        "updated_at": utc_now(),
                    }
                )
                atomic_json(manifest_path, manifest)
                print(
                    f"[{chunk.index + 1}/{len(chunks)}] alignment saved "
                    f"({payload['alignment_elapsed_seconds']:.1f}s)",
                    flush=True,
                )
            except Exception as exc:
                error_payload = {
                    "status": "error",
                    "phase": "alignment",
                    "fingerprint": fingerprint,
                    "source_sha256": source_sha256,
                    "chunk": asdict(chunk),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "failed_at": utc_now(),
                }
                atomic_json(
                    results_dir / f"chunk-{chunk.index:05d}.alignment.error.json",
                    error_payload,
                )
                manifest.update(
                    {
                        "status": "partial",
                        "completed_chunks": completed_chunks,
                        "aligned_chunks": aligned_chunks,
                        "failed_chunk": chunk.index,
                        "error": error_payload,
                        "updated_at": utc_now(),
                    }
                )
                atomic_json(manifest_path, manifest)
                raise

        if aligner_model is not None:
            print("Unloading forced aligner", flush=True)
            alignment = None
            del aligner_model
            gc.collect()
            mx.clear_cache()

    transcript, warnings = merge_results(
        chunks=chunks,
        results_dir=results_dir,
        source_name=source.name,
        source_sha256=source_sha256,
        source_duration=probe["duration_seconds"],
        fingerprint=fingerprint,
        language=args.language,
        model_info=model_info,
        aligner_info=aligner_info,
        alignment_requested=alignment_requested,
    )
    write_reader_outputs(output_dir, transcript)

    source_sha256_readback = hash_file(source)
    source_unchanged = source_sha256_readback == source_sha256
    if not source_unchanged:
        transcript["status"] = "partial"
        warnings.append("Source SHA-256 changed during transcription")
        write_reader_outputs(output_dir, transcript)

    output_files = [
        output_dir / "transcript.json",
        output_dir / "transcript.md",
        output_dir / "transcript.txt",
        output_dir / "transcript.srt",
    ]
    verification = {
        "status": (
            "passed"
            if source_unchanged and not warnings and len(completed_chunks) == len(chunks)
            else "partial"
        ),
        "source_sha256_initial": source_sha256,
        "source_sha256_readback": source_sha256_readback,
        "source_unchanged": source_unchanged,
        "chunks_expected": len(chunks),
        "chunks_completed": len(completed_chunks),
        "alignment_requested": alignment_requested,
        "chunks_aligned": len(aligned_chunks),
        "timing_mode": transcript["timing_mode"],
        "segment_count": len(transcript["segments"]),
        "word_count": len(transcript["words"]),
        "warnings": warnings,
        "outputs": {
            path.name: {
                "bytes": path.stat().st_size,
                "sha256": hash_file(path),
            }
            for path in output_files
        },
        "verified_at": utc_now(),
    }
    atomic_json(output_dir / "verification.json", verification)
    manifest.update(
        {
            "status": "complete" if verification["status"] == "passed" else "partial",
            "completed_chunks": completed_chunks,
            "aligned_chunks": aligned_chunks,
            "failed_chunk": None,
            "verification": verification,
            "updated_at": utc_now(),
        }
    )
    atomic_json(manifest_path, manifest)
    print(json.dumps(verification, ensure_ascii=False, indent=2), flush=True)
    return 0 if verification["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Lightweight, on-device transcription through macOS SpeechAnalyzer."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
SWIFT_SOURCE = SCRIPT_DIR / "apple_speech_transcriber.swift"
RUNTIME_ROOT = Path.home() / ".local/share/codex-local-asr/bin"
HELPER_BINARY = RUNTIME_ROOT / "apple-speech-transcriber"
ENGINE_VERSION = "apple-speech-transcriber-v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(value)
    temporary.replace(path)


def mark_manifest_failure(
    manifest_path: Path, manifest: dict[str, Any], exc: Exception
) -> None:
    manifest.update(
        {
            "status": "partial",
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
                "failed_at": utc_now(),
            },
            "updated_at": utc_now(),
        }
    )
    atomic_json(manifest_path, manifest)


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic"
        raise RuntimeError(
            f"Command failed with exit {result.returncode}: {command[0]}: {detail}"
        )
    return result


def format_clock(seconds: float, decimal: str = ".") -> str:
    milliseconds = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{decimal}{millis:03d}"


def probe_source(source: Path) -> dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise SystemExit("ffprobe is not installed")
    payload = json.loads(
        run(
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
        ).stdout
    )
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


def ensure_helper() -> None:
    if not SWIFT_SOURCE.is_file():
        raise SystemExit(f"Swift helper source is missing: {SWIFT_SOURCE}")
    if (
        HELPER_BINARY.is_file()
        and HELPER_BINARY.stat().st_mtime_ns >= SWIFT_SOURCE.stat().st_mtime_ns
    ):
        return
    xcrun = shutil.which("xcrun")
    if not xcrun:
        raise SystemExit("xcrun is not installed")
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    temporary = HELPER_BINARY.with_name(HELPER_BINARY.name + ".tmp")
    temporary.unlink(missing_ok=True)
    try:
        run(
            [
                xcrun,
                "swiftc",
                "-parse-as-library",
                str(SWIFT_SOURCE),
                "-o",
                str(temporary),
            ]
        )
        temporary.replace(HELPER_BINARY)
    finally:
        temporary.unlink(missing_ok=True)


def check_support(locale: str) -> dict[str, Any]:
    ensure_helper()
    payload = json.loads(run([str(HELPER_BINARY), "--check", locale]).stdout)
    if not payload.get("available"):
        raise SystemExit("Apple SpeechTranscriber is unavailable on this Mac")
    if not payload.get("supported"):
        raise SystemExit(f"Apple SpeechTranscriber does not support locale: {locale}")
    if not payload.get("installed"):
        raise SystemExit(
            f"Apple SpeechTranscriber locale is supported but not installed: {locale}. "
            "This Skill does not download system assets automatically."
        )
    return payload


def validate_output_boundary(output_dir: Path, fingerprint: str) -> bool:
    if not output_dir.exists():
        return False
    if not output_dir.is_dir():
        raise SystemExit(f"Output path exists and is not a directory: {output_dir}")
    entries = list(output_dir.iterdir())
    if not entries:
        return False
    manifest_path = output_dir / "manifest.json"
    verification_path = output_dir / "verification.json"
    if not manifest_path.is_file() or not verification_path.is_file():
        raise SystemExit(
            "Refusing to use a non-empty Apple output directory without manifest "
            "and verification files"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    verification = json.loads(verification_path.read_text(encoding="utf-8"))
    if manifest.get("fingerprint") != fingerprint:
        raise SystemExit(
            "Existing Apple output parameters do not match this run; choose a new "
            "--output-dir"
        )
    if manifest.get("status") != "complete" or verification.get("status") != "passed":
        raise SystemExit(
            "Existing Apple output is incomplete; preserve it and choose a new "
            "--output-dir"
        )
    for name, expected in verification.get("outputs", {}).items():
        path = output_dir / name
        if not path.is_file() or hash_file(path) != expected.get("sha256"):
            raise SystemExit(f"Existing Apple output failed hash readback: {path}")
    return True


def extract_audio(source: Path, destination: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg is not installed")
    run(
        [
            ffmpeg,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(destination),
        ]
    )


def write_outputs(output_dir: Path, transcript: dict[str, Any]) -> None:
    segments = transcript["segments"]
    atomic_text(
        output_dir / "transcript.txt",
        "\n".join(
            f"[{format_clock(float(item['start']))}] {item['text']}"
            for item in segments
        )
        + "\n",
    )
    srt_lines: list[str] = []
    for index, item in enumerate(segments, start=1):
        srt_lines.extend(
            [
                str(index),
                f"{format_clock(float(item['start']), ',')} --> "
                f"{format_clock(float(item['end']), ',')}",
                str(item["text"]),
                "",
            ]
        )
    atomic_text(output_dir / "transcript.srt", "\n".join(srt_lines))
    source = transcript["source"]
    markdown = [
        f"# {source['name']} Apple 本地转写",
        "",
        "- 状态：`complete`",
        "- 引擎：`Apple SpeechTranscriber`",
        f"- 语言：`{transcript['locale']}`",
        "- 时间戳模式：`apple-audio-time-range`",
        f"- 源文件 SHA-256：`{source['sha256']}`",
        "",
        "## 逐字稿",
        "",
    ]
    for item in segments:
        markdown.extend(
            [
                f"[{format_clock(float(item['start']))}–"
                f"{format_clock(float(item['end']))}] {item['text']}",
                "",
            ]
        )
    atomic_text(output_dir / "transcript.md", "\n".join(markdown))
    atomic_json(output_dir / "transcript.json", transcript)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe ordinary local media with macOS SpeechAnalyzer."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--locale", default="zh_CN")
    parser.add_argument("--preflight", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    if not source.is_file() or not os.access(source, os.R_OK):
        raise SystemExit(f"Source is not a readable file: {source}")
    probe = probe_source(source)
    support = check_support(args.locale)
    source_sha256 = hash_file(source)
    configuration = {
        "schema_version": 1,
        "engine": ENGINE_VERSION,
        "helper_sha256": hash_file(SWIFT_SOURCE),
        "source": str(source),
        "source_sha256": source_sha256,
        "source_size": source.stat().st_size,
        "locale": support["locale"],
    }
    fingerprint = canonical_digest(configuration)
    reused = validate_output_boundary(output_dir, fingerprint)
    preflight = {
        "status": "ready",
        "source": str(source),
        "probe": probe,
        "support": support,
        "fingerprint": fingerprint,
        "reusable_complete_output": reused,
    }
    if args.preflight:
        print(json.dumps(preflight, ensure_ascii=False, indent=2))
        return 0
    if reused:
        print(f"Reusing verified Apple transcript: {output_dir}")
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    manifest = {
        **preflight,
        "status": "in_progress",
        "configuration": configuration,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    atomic_json(manifest_path, manifest)

    try:
        with tempfile.TemporaryDirectory(prefix="codex-apple-asr-") as temporary:
            wav_path = Path(temporary) / "source_16k_mono.wav"
            extract_audio(source, wav_path)
            result = json.loads(
                run([str(HELPER_BINARY), str(wav_path), support["locale"]]).stdout
            )

        segments = [
            {
                "start": round(float(item["start"]), 3),
                "end": round(float(item["end"]), 3),
                "text": str(item["text"]).strip(),
            }
            for item in result["segments"]
            if str(item["text"]).strip()
        ]
        if not segments:
            raise RuntimeError("Apple SpeechTranscriber returned no usable segments")
    except Exception as exc:
        mark_manifest_failure(manifest_path, manifest, exc)
        raise
    transcript = {
        "schema_version": 1,
        "status": "complete",
        "engine": {
            "name": "Apple SpeechTranscriber",
            "version": ENGINE_VERSION,
            "system_owned_model": True,
        },
        "source": {
            "name": source.name,
            "sha256": source_sha256,
            "duration_seconds": probe["duration_seconds"],
        },
        "locale": result["locale"],
        "timing_mode": "apple-audio-time-range",
        "segments": segments,
        "text": "\n".join(item["text"] for item in segments),
        "limitations": [
            "No speaker identity",
            "Use the Qwen route for formal or terminology-heavy transcripts",
        ],
        "generated_at": utc_now(),
    }
    try:
        write_outputs(output_dir, transcript)
    except Exception as exc:
        mark_manifest_failure(manifest_path, manifest, exc)
        raise

    source_sha256_readback = hash_file(source)
    output_files = [
        output_dir / "transcript.json",
        output_dir / "transcript.md",
        output_dir / "transcript.txt",
        output_dir / "transcript.srt",
    ]
    verification = {
        "status": "passed" if source_sha256_readback == source_sha256 else "partial",
        "source_sha256_initial": source_sha256,
        "source_sha256_readback": source_sha256_readback,
        "source_unchanged": source_sha256_readback == source_sha256,
        "segment_count": len(segments),
        "timing_mode": transcript["timing_mode"],
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
            "verification": verification,
            "updated_at": utc_now(),
        }
    )
    atomic_json(manifest_path, manifest)
    print(json.dumps(verification, ensure_ascii=False, indent=2))
    return 0 if verification["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())

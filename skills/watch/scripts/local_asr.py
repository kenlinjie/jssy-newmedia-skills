#!/usr/bin/env python3
"""Bridge /watch to the verified lightweight Qwen3-ASR pipeline.

The ASR runtime stays in the existing local-sota-transcription skill.
This adapter only builds the command, validates its completion gates, and
normalizes the timestamped transcript for watch.py.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable


DEFAULT_PYTHON = Path.home() / ".local/share/codex-local-asr/venv/bin/python"
DEFAULT_SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "local-sota-transcription/scripts/transcribe_long_audio.py"
)
DEFAULT_ASR_MODEL = (
    Path.home()
    / "Library/Caches/codex-local-asr/models/Qwen3-ASR-0.6B-8bit"
)
DEFAULT_ALIGNER_MODEL = (
    Path.home()
    / "Library/Caches/codex-local-asr/models/Qwen3-ForcedAligner-0.6B-8bit"
)


class LocalASRError(RuntimeError):
    """Raised when local ASR is unavailable or fails its verification gate."""


def _configured_path(env_name: str, default: Path) -> Path:
    value = os.environ.get(env_name)
    # Keep the venv's symlinked interpreter path intact; resolving it would
    # misleadingly display the framework Python even though the venv is used.
    path = Path(value).expanduser() if value else default.expanduser()
    return Path(os.path.abspath(path))


def resolved_paths() -> dict[str, Path]:
    return {
        "python": _configured_path("WATCH_LOCAL_ASR_PYTHON", DEFAULT_PYTHON),
        "script": _configured_path("WATCH_LOCAL_ASR_SCRIPT", DEFAULT_SCRIPT),
        "asr_model": _configured_path("WATCH_LOCAL_ASR_MODEL", DEFAULT_ASR_MODEL),
        "aligner_model": _configured_path(
            "WATCH_LOCAL_ASR_ALIGNER", DEFAULT_ALIGNER_MODEL
        ),
    }


def local_asr_status() -> dict[str, object]:
    paths = resolved_paths()
    checks = {
        "python": paths["python"].is_file() and os.access(paths["python"], os.X_OK),
        "script": paths["script"].is_file(),
        "asr_model": (paths["asr_model"] / "model.safetensors").is_file(),
        "aligner_model": (paths["aligner_model"] / "model.safetensors").is_file(),
    }
    return {
        "available": all(checks.values()),
        "checks": checks,
        "paths": {name: str(path) for name, path in paths.items()},
    }


def build_command(
    source: str | Path,
    output_dir: str | Path,
    *,
    language: str = "Chinese",
    start_seconds: float | None = None,
    end_seconds: float | None = None,
    context_file: str | Path | None = None,
    terms: Iterable[str] = (),
    preflight: bool = False,
) -> list[str]:
    paths = resolved_paths()
    command = [
        str(paths["python"]),
        str(paths["script"]),
        str(Path(source).expanduser().resolve()),
        "--output-dir",
        str(Path(output_dir).expanduser().resolve()),
        "--language",
        language,
        "--asr-model",
        str(paths["asr_model"]),
        "--aligner-model",
        str(paths["aligner_model"]),
        "--align",
    ]
    scope_start = start_seconds if start_seconds is not None else 0.0
    if start_seconds is not None:
        command.extend(["--start-seconds", f"{start_seconds:.3f}"])
    if end_seconds is not None:
        duration = end_seconds - scope_start
        if duration <= 0:
            raise LocalASRError("local ASR end time must be greater than start time")
        command.extend(["--duration-seconds", f"{duration:.3f}"])
    if context_file is not None:
        command.extend(
            ["--context-file", str(Path(context_file).expanduser().resolve())]
        )
    for term in terms:
        cleaned = term.strip()
        if cleaned:
            command.extend(["--term", cleaned])
    if preflight:
        command.append("--preflight")
    return command


def _read_json(path: Path, label: str) -> dict:
    if not path.is_file():
        raise LocalASRError(f"local ASR did not produce {label}: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LocalASRError(f"cannot read local ASR {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise LocalASRError(f"local ASR {label} has an invalid top-level shape")
    return payload


def load_verified_result(output_dir: str | Path) -> tuple[list[dict], dict]:
    output = Path(output_dir).expanduser().resolve()
    manifest = _read_json(output / "manifest.json", "manifest")
    verification = _read_json(output / "verification.json", "verification")
    transcript = _read_json(output / "transcript.json", "transcript")

    if manifest.get("status") != "complete":
        raise LocalASRError(
            f"local ASR manifest is {manifest.get('status')!r}, not 'complete'"
        )
    if verification.get("status") != "passed":
        raise LocalASRError(
            f"local ASR verification is {verification.get('status')!r}, not 'passed'"
        )
    if transcript.get("status") != "complete":
        raise LocalASRError(
            f"local ASR transcript is {transcript.get('status')!r}, not 'complete'"
        )
    timing_mode = transcript.get("timing_mode")
    if timing_mode != "word" or verification.get("timing_mode") != "word":
        raise LocalASRError(
            "watch requires complete word timing; rerun the same local ASR output "
            "with --align"
        )
    if verification.get("alignment_requested") is not True:
        raise LocalASRError("watch local ASR verification did not request alignment")
    chunks_expected = verification.get("chunks_expected")
    chunks_aligned = verification.get("chunks_aligned")
    if (
        not isinstance(chunks_expected, int)
        or chunks_expected <= 0
        or chunks_aligned != chunks_expected
    ):
        raise LocalASRError(
            "watch local ASR alignment coverage is incomplete: "
            f"{chunks_aligned}/{chunks_expected} chunks"
        )
    words = transcript.get("words") or []
    if not isinstance(words, list) or not words:
        raise LocalASRError("watch local ASR word-timing output is empty")

    segments: list[dict] = []
    for raw in transcript.get("segments") or []:
        text = str(raw.get("text") or "").strip()
        if not text:
            continue
        segments.append(
            {
                "start": round(float(raw.get("start") or 0.0), 3),
                "end": round(float(raw.get("end") or 0.0), 3),
                "text": text,
            }
        )
    if not segments:
        raise LocalASRError("verified local ASR result contains no transcript segments")

    metadata = {
        "output_dir": str(output),
        "manifest": str(output / "manifest.json"),
        "verification": str(output / "verification.json"),
        "transcript_json": str(output / "transcript.json"),
        "source_sha256": (transcript.get("source") or {}).get("sha256"),
        "chunk_count": transcript.get("chunk_count"),
        "word_count": len(words),
        "timing_mode": timing_mode,
        "chunks_aligned": chunks_aligned,
        "language": transcript.get("language"),
    }
    return segments, metadata


def transcribe_local(
    source: str | Path,
    output_dir: str | Path,
    *,
    language: str = "Chinese",
    start_seconds: float | None = None,
    end_seconds: float | None = None,
    context_file: str | Path | None = None,
    terms: Iterable[str] = (),
) -> tuple[list[dict], dict]:
    status = local_asr_status()
    if not status["available"]:
        missing = [name for name, ok in status["checks"].items() if not ok]
        raise LocalASRError(f"local ASR is incomplete; missing: {', '.join(missing)}")

    command = build_command(
        source,
        output_dir,
        language=language,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        context_file=context_file,
        terms=terms,
    )
    print(
        f"[watch] lightweight Qwen3-ASR ({language}) with sequential alignment…",
        file=sys.stderr,
    )
    result = subprocess.run(command, stdout=sys.stderr, stderr=sys.stderr)
    if result.returncode != 0:
        raise LocalASRError(
            f"local ASR exited {result.returncode}; keep {Path(output_dir).resolve()} for recovery"
        )
    return load_verified_result(output_dir)


if __name__ == "__main__":
    print(json.dumps(local_asr_status(), ensure_ascii=False, indent=2))

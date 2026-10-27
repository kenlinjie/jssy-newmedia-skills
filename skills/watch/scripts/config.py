#!/usr/bin/env python3
"""Shared /watch configuration helpers."""
from __future__ import annotations

import os
from pathlib import Path


CONFIG_DIR = Path.home() / ".config" / "watch"
CONFIG_FILE = CONFIG_DIR / ".env"

DEFAULT_DETAIL = "balanced"
DEFAULT_ASR = "local"
DEFAULT_ASR_LANGUAGE = "Chinese"
DEFAULT_SUBTITLE_LANGUAGES = "zh.*,en.*"

DETAILS = {"transcript", "efficient", "balanced", "token-burner"}
ASR_MODES = {"local", "api", "off"}


def read_env_file(path: Path | None = None) -> dict[str, str]:
    if path is None:
        path = CONFIG_FILE
    values: dict[str, str] = {}
    if not path.exists():
        return values
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return values
    for line in lines:
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, _, value = raw.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] in ('"', "'") and value[-1] == value[0]:
            value = value[1:-1]
        else:
            # Strip an inline comment (a '#' preceded by whitespace) from an
            # unquoted value. Without this, `WATCH_DETAIL=balanced  # note`
            # parses as "balanced  # note", fails validation, and silently
            # falls back to the default. Keeps '#' inside quotes / API keys.
            for i, ch in enumerate(value):
                if ch == "#" and i > 0 and value[i - 1] in " \t":
                    value = value[:i].rstrip()
                    break
        values[key.strip()] = value
    return values


def get_config() -> dict[str, object]:
    file_values = read_env_file()

    detail = (
        os.environ.get("WATCH_DETAIL")
        or file_values.get("WATCH_DETAIL")
        or DEFAULT_DETAIL
    )
    if detail not in DETAILS:
        detail = DEFAULT_DETAIL

    asr = os.environ.get("WATCH_ASR") or file_values.get("WATCH_ASR") or DEFAULT_ASR
    if asr not in ASR_MODES:
        asr = DEFAULT_ASR

    asr_language = (
        os.environ.get("WATCH_ASR_LANGUAGE")
        or file_values.get("WATCH_ASR_LANGUAGE")
        or DEFAULT_ASR_LANGUAGE
    )
    subtitle_languages = (
        os.environ.get("WATCH_SUBTITLE_LANGUAGES")
        or file_values.get("WATCH_SUBTITLE_LANGUAGES")
        or DEFAULT_SUBTITLE_LANGUAGES
    )

    return {
        "detail": detail,
        "asr": asr,
        "asr_language": asr_language,
        "subtitle_languages": subtitle_languages,
        "config_file": str(CONFIG_FILE),
    }


def frame_cap(detail: str) -> int | None:
    if detail == "efficient":
        return 50
    if detail == "balanced":
        return 100
    if detail == "token-burner":
        return None
    if detail == "transcript":
        return None
    return 100

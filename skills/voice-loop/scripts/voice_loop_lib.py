#!/usr/bin/env python3
"""Shared helpers for Voice Loop's standard-library-only scripts."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

SCHEMA_VERSION = "1.0"
VALID_MODES = {"writing", "spoken", "both"}
VALID_RULE_STATUSES = {"candidate", "approved", "retired"}
VALID_CATEGORIES = {"style", "fact", "content", "format", "mixed"}
VALID_KINDS = {
    "self-writing",
    "self-spoken",
    "human-final",
    "correction",
    "benchmark",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    if slug:
        return slug
    return "profile-" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]


def normalize_rule_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def write_json(path: Path, value: Dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def read_jsonl(path: Path) -> Tuple[List[Dict[str, Any]], List[str]]:
    records: List[Dict[str, Any]] = []
    errors: List[str] = []
    if not path.exists():
        return records, errors
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"{path}:{line_number}: invalid JSON: {exc.msg}")
                continue
            if not isinstance(record, dict):
                errors.append(f"{path}:{line_number}: expected a JSON object")
                continue
            records.append(record)
    return records, errors


def write_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> None:
    lines = [json.dumps(record, ensure_ascii=False, separators=(",", ":")) for record in records]
    atomic_write_text(path, ("\n".join(lines) + "\n") if lines else "")


def update_profile_timestamp(profile_dir: Path, timestamp: str) -> None:
    profile_path = profile_dir / "profile.json"
    profile = load_json(profile_path)
    profile["updated_at"] = timestamp
    write_json(profile_path, profile)


def independent_sources(rule: Dict[str, Any]) -> int:
    sources = {
        str(item.get("source", "")).strip()
        for item in rule.get("evidence", [])
        if isinstance(item, dict) and str(item.get("source", "")).strip()
    }
    return len(sources)

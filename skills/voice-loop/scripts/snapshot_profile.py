#!/usr/bin/env python3
"""Create an immutable, corpus-free snapshot of an audited Voice Loop profile."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from audit_profile import audit_profile
from voice_loop_lib import read_jsonl, sha256_file, utc_now, write_json, write_jsonl

SAFE_LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
COPY_FILES = (
    "profile.json",
    "facts.md",
    "rules.json",
    "corpus/manifest.jsonl",
    "eval/cases.jsonl",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile_dir", type=Path)
    parser.add_argument("--label", required=True, help="Immutable version label, e.g. v0.2.0")
    parser.add_argument("--note", required=True, help="What changed and which regression passed")
    return parser.parse_args()


def correction_index(profile_dir: Path) -> List[Dict[str, Any]]:
    records, errors = read_jsonl(profile_dir / "corrections.jsonl")
    if errors:
        raise ValueError("; ".join(errors))
    keep = (
        "correction_id",
        "recorded_at",
        "mode",
        "scope",
        "category",
        "source",
        "reason",
        "draft_sha256",
        "final_sha256",
        "candidate_rules",
    )
    return [{key: record.get(key) for key in keep} for record in records]


def main() -> int:
    args = parse_args()
    profile_dir = args.profile_dir.expanduser()
    if not SAFE_LABEL.fullmatch(args.label):
        print(
            "error: label must be 1–64 characters using letters, numbers, dot, underscore, or hyphen",
            file=sys.stderr,
        )
        return 2
    if not args.note.strip():
        print("error: note cannot be blank", file=sys.stderr)
        return 2

    findings, summary = audit_profile(profile_dir)
    errors = [item for item in findings if item["level"] == "error"]
    if errors:
        print("error: profile audit failed; snapshot not created", file=sys.stderr)
        for item in errors:
            print(f"  {item['code']}: {item['message']}", file=sys.stderr)
        return 2

    versions_dir = profile_dir / "versions"
    target = versions_dir / args.label
    if target.exists():
        print(f"error: refusing to overwrite snapshot: {target}", file=sys.stderr)
        return 2

    versions_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix=f".{args.label}.", dir=str(versions_dir)))
    try:
        for relative in COPY_FILES:
            source = profile_dir / relative
            destination = temp_dir / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        write_jsonl(temp_dir / "corrections-index.jsonl", correction_index(profile_dir))

        files: Dict[str, Dict[str, Any]] = {}
        for path in sorted(item for item in temp_dir.rglob("*") if item.is_file()):
            relative = path.relative_to(temp_dir).as_posix()
            files[relative] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
        manifest = {
            "schema_version": "1.0",
            "label": args.label,
            "created_at": utc_now(),
            "note": args.note.strip(),
            "profile_summary": summary,
            "audit_warnings": [
                item for item in findings if item["level"] == "warning"
            ],
            "files": files,
            "excluded": [
                "corpus/raw/**",
                "corpus/approved/**",
                "corpus/benchmark/**",
                "corrections.jsonl full text",
                "eval/results/**",
            ],
        }
        write_json(temp_dir / "manifest.json", manifest)
        os.replace(temp_dir, target)
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise

    print(f"created snapshot: {target}")
    print("corpus text excluded; corrections stored as hash-only index")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

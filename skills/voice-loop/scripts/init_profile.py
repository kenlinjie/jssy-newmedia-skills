#!/usr/bin/env python3
"""Initialize a private Voice Loop profile without overwriting existing data."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from voice_loop_lib import SCHEMA_VERSION, slugify, utc_now, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile_dir", type=Path, help="New profile directory")
    parser.add_argument("--name", required=True, help="Human-facing profile name")
    parser.add_argument("--language", default="zh-CN", help="Primary locale")
    parser.add_argument(
        "--modes",
        default="writing,spoken",
        help="Comma-separated list containing writing and/or spoken",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = args.profile_dir.expanduser()
    modes = [item.strip() for item in args.modes.split(",") if item.strip()]
    invalid_modes = sorted(set(modes) - {"writing", "spoken"})
    if not modes or invalid_modes:
        print(f"error: invalid modes: {', '.join(invalid_modes) or '(empty)'}", file=sys.stderr)
        return 2
    if target.exists():
        print(f"error: refusing to overwrite existing path: {target}", file=sys.stderr)
        return 2

    timestamp = utc_now()
    target.mkdir(parents=True)
    for relative in (
        "corpus/raw",
        "corpus/approved",
        "corpus/benchmark",
        "eval/results",
        "versions",
    ):
        directory = target / relative
        directory.mkdir(parents=True)
        (directory / ".gitkeep").write_text("", encoding="utf-8")

    profile = {
        "schema_version": SCHEMA_VERSION,
        "profile_id": slugify(args.name),
        "display_name": args.name,
        "language": args.language,
        "modes": modes,
        "status": "learning",
        "purpose": {
            "audiences": [],
            "channels": [],
            "goals": [],
            "non_goals": [],
        },
        "data_policy": {
            "authorized_only": True,
            "benchmark_is_identity_evidence": False,
            "git_private_by_default": True,
        },
        "promotion_policy": {
            "minimum_independent_evidence": 3,
            "requires_human_approval": True,
        },
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    rules = {
        "schema_version": SCHEMA_VERSION,
        "profile_id": profile["profile_id"],
        "rules": [],
    }
    write_json(target / "profile.json", profile)
    write_json(target / "rules.json", rules)
    (target / "facts.md").write_text(
        "# Facts\n\n"
        "## Verified facts\n\n"
        "<!-- Add only user-confirmed facts. -->\n\n"
        "## Needs verification\n\n"
        "<!-- These claims may not be stated as fact. -->\n\n"
        "## Forbidden assumptions\n\n"
        "<!-- Add claims the model must never infer. -->\n",
        encoding="utf-8",
    )
    for relative in ("corrections.jsonl", "corpus/manifest.jsonl", "eval/cases.jsonl"):
        (target / relative).write_text("", encoding="utf-8")
    (target / ".gitignore").write_text(
        "# Voice Loop profiles contain personal data. Keep all contents private by default.\n"
        "*\n"
        "!.gitignore\n",
        encoding="utf-8",
    )

    print(f"created profile: {target}")
    print(f"profile_id: {profile['profile_id']}")
    print("next: complete profile.json, facts.md, and corpus/manifest.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

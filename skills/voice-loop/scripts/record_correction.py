#!/usr/bin/env python3
"""Record an AI-draft to human-final correction and candidate rule evidence."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Any, Dict, List

from voice_loop_lib import (
    VALID_CATEGORIES,
    load_json,
    normalize_rule_text,
    read_jsonl,
    sha256_text,
    update_profile_timestamp,
    utc_now,
    write_json,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile_dir", type=Path)
    parser.add_argument("--draft-file", type=Path, required=True)
    parser.add_argument("--final-file", type=Path, required=True)
    parser.add_argument("--mode", choices=("writing", "spoken"), required=True)
    parser.add_argument("--category", choices=sorted(VALID_CATEGORIES), required=True)
    parser.add_argument("--source", required=True, help="Independent document or episode ID")
    parser.add_argument("--reason", required=True, help="Human-given or observed edit reason")
    parser.add_argument("--scope", default="global")
    parser.add_argument(
        "--candidate-rule",
        action="append",
        default=[],
        help="Repeat to attach one or more style candidates",
    )
    return parser.parse_args()


def make_rule_id(text: str, mode: str, scope: str) -> str:
    payload = f"{mode}\0{scope}\0{text.casefold()}".encode("utf-8")
    return "r_" + hashlib.sha256(payload).hexdigest()[:10]


def main() -> int:
    args = parse_args()
    profile_dir = args.profile_dir.expanduser()
    required = (profile_dir / "profile.json", profile_dir / "rules.json")
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        print(f"error: missing profile files: {', '.join(missing)}", file=sys.stderr)
        return 2
    if not args.draft_file.is_file() or not args.final_file.is_file():
        print("error: draft and final files must both exist", file=sys.stderr)
        return 2
    if not args.source.strip() or not args.reason.strip() or not args.scope.strip():
        print("error: source, reason, and scope cannot be blank", file=sys.stderr)
        return 2
    if args.candidate_rule and args.category not in {"style", "mixed"}:
        print("error: candidate rules are allowed only for style or mixed corrections", file=sys.stderr)
        return 2

    profile = load_json(profile_dir / "profile.json")
    if args.mode not in profile.get("modes", []):
        print(f"error: mode {args.mode!r} is not enabled in profile.json", file=sys.stderr)
        return 2
    rules_doc = load_json(profile_dir / "rules.json")
    rules = rules_doc.get("rules")
    if not isinstance(rules, list):
        print("error: rules.json field 'rules' must be an array", file=sys.stderr)
        return 2
    corrections, correction_errors = read_jsonl(profile_dir / "corrections.jsonl")
    if correction_errors:
        print("error: fix corrections.jsonl before appending:", file=sys.stderr)
        for error in correction_errors:
            print(f"  {error}", file=sys.stderr)
        return 2

    draft = args.draft_file.read_text(encoding="utf-8-sig")
    final = args.final_file.read_text(encoding="utf-8-sig")
    if draft == final:
        print("error: draft and final are identical", file=sys.stderr)
        return 2
    timestamp = utc_now()
    id_payload = f"{timestamp}\0{args.source}\0{draft}\0{final}".encode("utf-8")
    correction_id = "corr_" + hashlib.sha256(id_payload).hexdigest()[:16]
    record: Dict[str, Any] = {
        "correction_id": correction_id,
        "recorded_at": timestamp,
        "mode": args.mode,
        "scope": args.scope.strip(),
        "category": args.category,
        "source": args.source.strip(),
        "reason": args.reason.strip(),
        "draft": draft,
        "final": final,
        "draft_sha256": sha256_text(draft),
        "final_sha256": sha256_text(final),
        "candidate_rules": [],
    }

    normalized_candidates = [normalize_rule_text(item) for item in args.candidate_rule]
    normalized_candidates = [item for item in normalized_candidates if item]
    seen_candidates = set()
    for candidate_text in normalized_candidates:
        key = (candidate_text.casefold(), args.mode, args.scope.strip())
        if key in seen_candidates:
            continue
        seen_candidates.add(key)
        matching = next(
            (
                rule
                for rule in rules
                if isinstance(rule, dict)
                and normalize_rule_text(str(rule.get("text", ""))).casefold() == key[0]
                and rule.get("mode") == key[1]
                and rule.get("scope") == key[2]
            ),
            None,
        )
        if matching and matching.get("status") == "retired":
            print(
                f"error: matching rule {matching.get('rule_id')} is retired; review it manually",
                file=sys.stderr,
            )
            return 2
        if matching is None:
            matching = {
                "rule_id": make_rule_id(candidate_text, args.mode, args.scope.strip()),
                "text": candidate_text,
                "mode": args.mode,
                "scope": args.scope.strip(),
                "status": "candidate",
                "evidence": [],
                "approval": None,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
            rules.append(matching)
        evidence: List[Dict[str, Any]] = matching.setdefault("evidence", [])
        if not any(item.get("correction_id") == correction_id for item in evidence):
            evidence.append(
                {
                    "correction_id": correction_id,
                    "source": args.source.strip(),
                    "note": args.reason.strip(),
                    "added_at": timestamp,
                }
            )
            matching["updated_at"] = timestamp
        record["candidate_rules"].append(matching["rule_id"])

    corrections.append(record)
    rules_doc["rules"] = rules
    write_json(profile_dir / "rules.json", rules_doc)
    write_jsonl(profile_dir / "corrections.jsonl", corrections)
    update_profile_timestamp(profile_dir, timestamp)
    print(f"recorded correction: {correction_id}")
    if record["candidate_rules"]:
        print("candidate rules: " + ", ".join(record["candidate_rules"]))
    else:
        print("candidate rules: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

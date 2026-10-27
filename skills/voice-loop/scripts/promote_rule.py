#!/usr/bin/env python3
"""Promote a candidate Voice Loop rule after explicit human approval."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from voice_loop_lib import (
    independent_sources,
    load_json,
    update_profile_timestamp,
    utc_now,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile_dir", type=Path)
    parser.add_argument("rule_id")
    parser.add_argument("--approved-by", required=True, help="Human approver")
    parser.add_argument("--approval-note", required=True)
    parser.add_argument(
        "--allow-low-evidence",
        action="store_true",
        help="Use only after explicit human approval with fewer sources than policy requires",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    profile_dir = args.profile_dir.expanduser()
    if not args.approved_by.strip() or not args.approval_note.strip():
        print("error: approved-by and approval-note cannot be blank", file=sys.stderr)
        return 2
    profile = load_json(profile_dir / "profile.json")
    rules_doc = load_json(profile_dir / "rules.json")
    rules = rules_doc.get("rules", [])
    rule = next(
        (item for item in rules if isinstance(item, dict) and item.get("rule_id") == args.rule_id),
        None,
    )
    if rule is None:
        print(f"error: rule not found: {args.rule_id}", file=sys.stderr)
        return 2
    if rule.get("status") == "retired":
        print("error: retired rules must be reviewed and recreated manually", file=sys.stderr)
        return 2
    if rule.get("status") == "approved":
        print(f"already approved: {args.rule_id}")
        return 0

    policy = profile.get("promotion_policy", {})
    try:
        minimum = int(policy.get("minimum_independent_evidence", 3))
        if minimum < 1:
            raise ValueError
    except (TypeError, ValueError):
        print(
            "error: promotion_policy.minimum_independent_evidence must be a positive integer",
            file=sys.stderr,
        )
        return 2
    source_count = independent_sources(rule)
    if source_count < minimum and not args.allow_low_evidence:
        print(
            f"error: {source_count} independent source(s); policy requires {minimum}. "
            "Use --allow-low-evidence only after explicit human approval.",
            file=sys.stderr,
        )
        return 2

    timestamp = utc_now()
    rule["status"] = "approved"
    rule["approval"] = {
        "approved_by": args.approved_by.strip(),
        "approved_at": timestamp,
        "note": args.approval_note.strip(),
        "independent_evidence": source_count,
        "low_evidence_override": source_count < minimum,
    }
    rule["updated_at"] = timestamp
    write_json(profile_dir / "rules.json", rules_doc)
    update_profile_timestamp(profile_dir, timestamp)
    print(f"approved: {args.rule_id}")
    print(f"independent evidence: {source_count}/{minimum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

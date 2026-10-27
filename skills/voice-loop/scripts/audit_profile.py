#!/usr/bin/env python3
"""Audit a Voice Loop profile's structure, evidence gates, and privacy defaults."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from voice_loop_lib import (
    SCHEMA_VERSION,
    VALID_KINDS,
    VALID_MODES,
    VALID_RULE_STATUSES,
    independent_sources,
    load_json,
    read_jsonl,
)

Finding = Dict[str, str]


def add(findings: List[Finding], level: str, code: str, message: str) -> None:
    findings.append({"level": level, "code": code, "message": message})


def visible_fact_lines(text: str) -> List[str]:
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip()
        and not line.lstrip().startswith("#")
        and not line.lstrip().startswith("<!--")
        and not line.rstrip().endswith("-->")
    ]


def count_content_files(directory: Path) -> int:
    if not directory.is_dir():
        return 0
    return sum(1 for path in directory.rglob("*") if path.is_file() and path.name != ".gitkeep")


def audit_profile(profile_dir: Path) -> Tuple[List[Finding], Dict[str, Any]]:
    findings: List[Finding] = []
    required_files = (
        "profile.json",
        "facts.md",
        "rules.json",
        "corrections.jsonl",
        "corpus/manifest.jsonl",
        "eval/cases.jsonl",
        ".gitignore",
    )
    required_dirs = (
        "corpus/raw",
        "corpus/approved",
        "corpus/benchmark",
        "eval/results",
        "versions",
    )
    for relative in required_files:
        if not (profile_dir / relative).is_file():
            add(findings, "error", "missing-file", f"missing required file: {relative}")
    for relative in required_dirs:
        if not (profile_dir / relative).is_dir():
            add(findings, "error", "missing-dir", f"missing required directory: {relative}")
    if any(item["level"] == "error" for item in findings):
        return findings, {"profile": str(profile_dir)}

    try:
        profile = load_json(profile_dir / "profile.json")
        rules_doc = load_json(profile_dir / "rules.json")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        add(findings, "error", "invalid-json", str(exc))
        return findings, {"profile": str(profile_dir)}

    if profile.get("schema_version") != SCHEMA_VERSION:
        add(findings, "error", "profile-schema", "profile.json schema_version must be 1.0")
    if rules_doc.get("schema_version") != SCHEMA_VERSION:
        add(findings, "error", "rules-schema", "rules.json schema_version must be 1.0")
    if profile.get("profile_id") != rules_doc.get("profile_id"):
        add(findings, "error", "profile-id", "profile_id differs between profile.json and rules.json")
    modes = profile.get("modes")
    if not isinstance(modes, list) or not modes or set(modes) - {"writing", "spoken"}:
        add(findings, "error", "profile-modes", "profile modes must contain writing and/or spoken")
    if profile.get("status") not in {"learning", "active", "paused"}:
        add(findings, "error", "profile-status", "profile status must be learning, active, or paused")
    data_policy = profile.get("data_policy")
    if not isinstance(data_policy, dict):
        add(findings, "error", "data-policy", "data_policy must be an object")
        data_policy = {}
    if data_policy.get("authorized_only") is not True:
        add(findings, "error", "authorization-policy", "authorized_only must remain true")
    if data_policy.get("benchmark_is_identity_evidence") is not False:
        add(
            findings,
            "error",
            "benchmark-policy",
            "benchmark_is_identity_evidence must remain false",
        )
    policy = profile.get("promotion_policy", {})
    if not isinstance(policy, dict):
        add(findings, "error", "promotion-policy", "promotion_policy must be an object")
        policy = {}
    try:
        minimum = int(policy.get("minimum_independent_evidence", 3))
        if minimum < 1:
            raise ValueError
    except (TypeError, ValueError):
        add(
            findings,
            "error",
            "evidence-policy",
            "minimum_independent_evidence must be a positive integer",
        )
        minimum = 3
    if policy.get("requires_human_approval") is not True:
        add(findings, "error", "human-gate", "requires_human_approval must remain true")

    ignore_lines = {
        line.strip()
        for line in (profile_dir / ".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    if "*" not in ignore_lines:
        add(
            findings,
            "warning",
            "privacy-ignore",
            "profile .gitignore does not ignore all contents by default",
        )

    facts_text = (profile_dir / "facts.md").read_text(encoding="utf-8")
    if not visible_fact_lines(facts_text):
        add(findings, "warning", "facts-empty", "facts.md has no confirmed or blocked facts yet")

    manifest, manifest_errors = read_jsonl(profile_dir / "corpus/manifest.jsonl")
    corrections, correction_errors = read_jsonl(profile_dir / "corrections.jsonl")
    eval_cases, eval_errors = read_jsonl(profile_dir / "eval/cases.jsonl")
    for error in manifest_errors + correction_errors + eval_errors:
        add(findings, "error", "invalid-jsonl", error)

    sample_ids = set()
    for index, item in enumerate(manifest, 1):
        prefix = f"manifest record {index}"
        sample_id = str(item.get("sample_id", "")).strip()
        if not sample_id:
            add(findings, "error", "sample-id", f"{prefix} has no sample_id")
        elif sample_id in sample_ids:
            add(findings, "error", "sample-id", f"duplicate sample_id: {sample_id}")
        sample_ids.add(sample_id)
        kind = item.get("kind")
        if kind not in VALID_KINDS:
            add(findings, "error", "sample-kind", f"{prefix} has invalid kind: {kind!r}")
        mode = item.get("mode")
        if mode not in {"writing", "spoken"}:
            add(findings, "error", "sample-mode", f"{prefix} has invalid mode: {mode!r}")
        if item.get("identity_evidence") is True and item.get("authorized") is not True:
            add(
                findings,
                "error",
                "unauthorized-identity",
                f"{prefix} is identity evidence but is not authorized",
            )
        if kind == "benchmark" and item.get("identity_evidence") is not False:
            add(
                findings,
                "error",
                "benchmark-identity",
                f"{prefix} benchmark must set identity_evidence to false",
            )
        relative_path = str(item.get("path", "")).strip()
        if not relative_path:
            add(findings, "error", "sample-path", f"{prefix} has no path")
        elif Path(relative_path).is_absolute():
            add(findings, "warning", "absolute-path", f"{prefix} should prefer a relative path")
        elif not (profile_dir / relative_path).is_file():
            add(findings, "error", "sample-path", f"{prefix} path does not exist: {relative_path}")

    rules = rules_doc.get("rules")
    if not isinstance(rules, list):
        add(findings, "error", "rules-array", "rules.json field 'rules' must be an array")
        rules = []
    rule_ids = set()
    for index, rule in enumerate(rules, 1):
        if not isinstance(rule, dict):
            add(findings, "error", "rule-object", f"rule {index} is not an object")
            continue
        rule_id = str(rule.get("rule_id", "")).strip()
        if not rule_id or rule_id in rule_ids:
            add(findings, "error", "rule-id", f"missing or duplicate rule_id at rule {index}")
        rule_ids.add(rule_id)
        if not str(rule.get("text", "")).strip():
            add(findings, "error", "rule-text", f"{rule_id or index} has no text")
        if rule.get("mode") not in VALID_MODES:
            add(findings, "error", "rule-mode", f"{rule_id or index} has invalid mode")
        if rule.get("status") not in VALID_RULE_STATUSES:
            add(findings, "error", "rule-status", f"{rule_id or index} has invalid status")
        evidence = rule.get("evidence")
        if not isinstance(evidence, list):
            add(findings, "error", "rule-evidence", f"{rule_id or index} evidence must be an array")
            evidence = []
        for evidence_item in evidence:
            if not isinstance(evidence_item, dict) or not str(evidence_item.get("source", "")).strip():
                add(findings, "error", "evidence-source", f"{rule_id or index} has evidence without source")
        if rule.get("status") == "approved":
            approval = rule.get("approval")
            if not isinstance(approval, dict) or not str(approval.get("approved_by", "")).strip():
                add(findings, "error", "approval-human", f"{rule_id} lacks human approval")
            else:
                source_count = independent_sources(rule)
                override = approval.get("low_evidence_override") is True
                if source_count < minimum and not override:
                    add(
                        findings,
                        "error",
                        "approval-evidence",
                        f"{rule_id} has {source_count}/{minimum} sources without override",
                    )

    for record in corrections:
        for rule_id in record.get("candidate_rules", []):
            if rule_id not in rule_ids:
                add(
                    findings,
                    "error",
                    "correction-rule",
                    f"correction {record.get('correction_id')} references missing rule {rule_id}",
                )

    approved_count = count_content_files(profile_dir / "corpus/approved")
    if approved_count < 8:
        add(
            findings,
            "warning",
            "low-coverage",
            f"approved corpus has {approved_count} file(s); 8–15 is recommended for a first profile",
        )
    if len(eval_cases) < 3:
        add(
            findings,
            "warning",
            "regression-cases",
            f"only {len(eval_cases)} regression case(s); at least 3 are recommended",
        )

    summary = {
        "profile": str(profile_dir),
        "approved_samples": approved_count,
        "manifest_records": len(manifest),
        "corrections": len(corrections),
        "rules": len(rules),
        "approved_rules": sum(
            1 for rule in rules if isinstance(rule, dict) and rule.get("status") == "approved"
        ),
        "regression_cases": len(eval_cases),
    }
    return findings, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile_dir", type=Path)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    findings, summary = audit_profile(args.profile_dir.expanduser())
    errors = sum(1 for item in findings if item["level"] == "error")
    warnings = sum(1 for item in findings if item["level"] == "warning")
    if args.json:
        print(json.dumps({"summary": summary, "findings": findings}, ensure_ascii=False, indent=2))
    else:
        for item in findings:
            print(f"[{item['level'].upper()}] {item['code']}: {item['message']}")
        print(f"SUMMARY errors={errors} warnings={warnings}")
        for key, value in summary.items():
            print(f"{key}: {value}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

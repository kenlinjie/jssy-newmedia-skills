from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]


def run_script(name: str, *args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *[str(arg) for arg in args]],
        text=True,
        capture_output=True,
        check=False,
    )


class VoiceLoopIntegrationTests(unittest.TestCase):
    def make_profile(self, root: Path, name: str = "测试说话人") -> Path:
        profile = root / "profile"
        result = run_script(
            "init_profile.py",
            profile,
            "--name",
            name,
            "--language",
            "zh-CN",
            "--modes",
            "writing,spoken",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return profile

    def test_init_is_non_destructive_and_auditable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            profile = self.make_profile(Path(temp))
            second = run_script("init_profile.py", profile, "--name", "again")
            self.assertNotEqual(second.returncode, 0)
            audit = run_script("audit_profile.py", profile)
            self.assertEqual(audit.returncode, 0, audit.stderr)
            self.assertIn("SUMMARY errors=0", audit.stdout)
            self.assertIn("low-coverage", audit.stdout)
            self.assertEqual(
                (profile / ".gitignore").read_text(encoding="utf-8").splitlines()[1],
                "*",
            )

    def test_clean_subtitles_preserves_wording(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "sample.srt"
            output = root / "cleaned.txt"
            source.write_text(
                "1\n00:00:00,000 --> 00:00:01,000\n先说结论，\n\n"
                "2\n00:00:01,100 --> 00:00:03,000\n这件事值得做。\n",
                encoding="utf-8",
            )
            result = run_script("clean_subtitles.py", source, "--output", output)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_text(encoding="utf-8"), "先说结论，这件事值得做。\n")

    def test_correction_evidence_promotion_and_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            profile = self.make_profile(root)
            candidate = "口播开头直接进入判断，不用泛化寒暄。"
            for index in range(3):
                draft = root / f"draft-{index}.txt"
                final = root / f"final-{index}.txt"
                draft.write_text("今天我们来聊聊这个问题。", encoding="utf-8")
                final.write_text(f"先说结论，第{index + 1}个判断成立。", encoding="utf-8")
                result = run_script(
                    "record_correction.py",
                    profile,
                    "--draft-file",
                    draft,
                    "--final-file",
                    final,
                    "--mode",
                    "spoken",
                    "--category",
                    "style",
                    "--source",
                    f"episode-{index + 1:03d}",
                    "--reason",
                    "人工删除泛化寒暄",
                    "--candidate-rule",
                    candidate,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

            rules = json.loads((profile / "rules.json").read_text(encoding="utf-8"))
            self.assertEqual(len(rules["rules"]), 1)
            rule_id = rules["rules"][0]["rule_id"]
            self.assertEqual(len(rules["rules"][0]["evidence"]), 3)

            promote = run_script(
                "promote_rule.py",
                profile,
                rule_id,
                "--approved-by",
                "profile owner",
                "--approval-note",
                "explicitly approved in review",
            )
            self.assertEqual(promote.returncode, 0, promote.stderr)
            audit = run_script("audit_profile.py", profile)
            self.assertEqual(audit.returncode, 0, audit.stdout + audit.stderr)

            snapshot = run_script(
                "snapshot_profile.py",
                profile,
                "--label",
                "v0.1.0",
                "--note",
                "approved one rule after three independent sources",
            )
            self.assertEqual(snapshot.returncode, 0, snapshot.stderr)
            version = profile / "versions" / "v0.1.0"
            self.assertTrue((version / "manifest.json").is_file())
            self.assertFalse((version / "corrections.jsonl").exists())
            indexed = (version / "corrections-index.jsonl").read_text(encoding="utf-8")
            self.assertNotIn('"draft":', indexed)
            self.assertNotIn('"final":', indexed)
            self.assertFalse((version / "corpus" / "approved").exists())

    def test_low_evidence_requires_explicit_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            profile = self.make_profile(root)
            draft = root / "draft.txt"
            final = root / "final.txt"
            draft.write_text("首先，我们需要。", encoding="utf-8")
            final.write_text("先说要点。", encoding="utf-8")
            record = run_script(
                "record_correction.py",
                profile,
                "--draft-file",
                draft,
                "--final-file",
                final,
                "--mode",
                "writing",
                "--category",
                "style",
                "--source",
                "article-001",
                "--reason",
                "删掉模板连接词",
                "--candidate-rule",
                "不使用“首先，我们需要”作为模板开头。",
            )
            self.assertEqual(record.returncode, 0, record.stderr)
            rules = json.loads((profile / "rules.json").read_text(encoding="utf-8"))
            rule_id = rules["rules"][0]["rule_id"]
            blocked = run_script(
                "promote_rule.py",
                profile,
                rule_id,
                "--approved-by",
                "profile owner",
                "--approval-note",
                "reviewed",
            )
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("policy requires", blocked.stderr)
            allowed = run_script(
                "promote_rule.py",
                profile,
                rule_id,
                "--approved-by",
                "profile owner",
                "--approval-note",
                "owner explicitly approves early",
                "--allow-low-evidence",
            )
            self.assertEqual(allowed.returncode, 0, allowed.stderr)

    def test_audit_rejects_unauthorized_identity_and_benchmark_leak(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            profile = self.make_profile(Path(temp))
            sample = profile / "corpus" / "approved" / "sample.txt"
            sample.write_text("synthetic sample", encoding="utf-8")
            records = [
                {
                    "sample_id": "sample-001",
                    "path": "corpus/approved/sample.txt",
                    "kind": "self-writing",
                    "mode": "writing",
                    "source": "doc-001",
                    "authorized": False,
                    "identity_evidence": True,
                },
                {
                    "sample_id": "sample-002",
                    "path": "corpus/approved/sample.txt",
                    "kind": "benchmark",
                    "mode": "writing",
                    "source": "benchmark-001",
                    "authorized": True,
                    "identity_evidence": True,
                },
            ]
            (profile / "corpus" / "manifest.jsonl").write_text(
                "".join(json.dumps(item) + "\n" for item in records),
                encoding="utf-8",
            )
            audit = run_script("audit_profile.py", profile)
            self.assertNotEqual(audit.returncode, 0)
            self.assertIn("unauthorized-identity", audit.stdout)
            self.assertIn("benchmark-identity", audit.stdout)


if __name__ == "__main__":
    unittest.main()

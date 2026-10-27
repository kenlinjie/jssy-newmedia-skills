import importlib.util
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from urllib.error import HTTPError, URLError
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "resolve_latest.py"
SPEC = importlib.util.spec_from_file_location("resolve_latest", SCRIPT)
resolver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(resolver)


def fake_release(**overrides):
    release = {
        "tag_name": "v4.2.1",
        "draft": False,
        "prerelease": False,
        "html_url": "https://github.com/obsidianmd/obsidian-releases/releases/tag/v4.2.1",
        "assets": [{"name": "example.dmg", "browser_download_url": "https://github.com/example/asset"}],
    }
    release.update(overrides)
    return release


class ReleaseTests(unittest.TestCase):
    def test_release_metadata_does_not_claim_installation(self):
        result = resolver.resolve_product("obsidian", fetch=lambda *a, **k: fake_release())
        self.assertEqual(result["target_version"], "v4.2.1")
        self.assertEqual(result["status"], "release_metadata")
        self.assertFalse(result["installation_verified"])
        self.assertIn("checked_at", result)

    def test_preview_draft_and_unknown_publication_status_fail(self):
        for changes in ({"prerelease": True}, {"draft": True}, {"draft": None}):
            with self.subTest(changes=changes):
                result = resolver.resolve_product("obsidian-git", fetch=lambda *a, **k: fake_release(**changes))
                self.assertEqual(result["status"], "error")
                self.assertIsNone(result["target_version"])

    def test_github_prerelease_tag_also_fails(self):
        result = resolver.resolve_product("obsidian", fetch=lambda *a, **k: fake_release(tag_name="v4.2.1-beta.1"))
        self.assertEqual(result["status"], "error")

    def test_network_and_rate_limit_failure_never_fall_back_to_old_version(self):
        failures = [URLError("offline"), HTTPError("https://api.github.com/", 403, "rate limited", {}, None)]
        for failure in failures:
            def fetch(*args, **kwargs):
                raise failure
            result = resolver.resolve_product("obsidian", fetch=fetch)
            self.assertEqual(result["status"], "error")
            self.assertIsNone(result["target_version"])
            self.assertFalse(result["installation_verified"])

    def test_npm_package_identity_and_stable_version_are_required(self):
        for data in (
            {"name": "unrelated-cli", "version": "1.2.3"},
            {"name": "@larksuite/cli", "version": "1.2.3-rc.1"},
            {"name": "@larksuite/cli"},
        ):
            result = resolver.resolve_product("feishu", fetch=lambda *a, **k: data)
            self.assertEqual(result["status"], "error")

    def test_scoped_npm_package_url_and_engine_constraints(self):
        calls = []
        def fetch(url, **kwargs):
            calls.append(url)
            return {"name": "@larksuite/cli", "version": "5.1.0", "engines": {"node": ">=22"}}
        result = resolver.resolve_product("feishu", fetch=fetch)
        self.assertEqual(calls, ["https://registry.npmjs.org/@larksuite%2Fcli/latest"])
        self.assertEqual(result["engines"], {"node": ">=22"})
        self.assertEqual(result["status"], "release_metadata")

    def test_node_selects_highest_stable_lts_not_current_or_first_item(self):
        data = [
            {"version": "v26.0.0", "lts": False},
            {"version": "v22.9.0", "lts": "Older"},
            {"version": "v24.2.0-rc.1", "lts": "Preview"},
            {"version": "v24.1.1", "lts": "Newer", "files": ["win-arm64-msi"]},
        ]
        result = resolver.resolve_product("node", fetch=lambda *a, **k: data)
        self.assertEqual(result["target_version"], "v24.1.1")
        self.assertEqual(result["files"], ["win-arm64-msi"])

    def test_missing_lts_is_an_error(self):
        result = resolver.resolve_product("node", fetch=lambda *a, **k: [{"version": "v26.0.0", "lts": False}])
        self.assertEqual(result["status"], "error")

    def test_page_products_do_not_guess_versions_or_use_network(self):
        def unexpected_request(*args, **kwargs):
            self.fail("page-only products should not request a guessed metadata endpoint")
        for product in ("egolite", "chatgpt", "cindy", "git"):
            result = resolver.resolve_product(product, fetch=unexpected_request)
            self.assertEqual(result["status"], "needs_official_page")
            self.assertIsNone(result["target_version"])
            self.assertFalse(result["installation_verified"])

    def test_unrecognized_response_shapes_are_errors(self):
        for product, data in (("obsidian", []), ("obsidian", fake_release(assets="bad")), ("dws", []), ("node", {})):
            with self.subTest(product=product):
                self.assertEqual(resolver.resolve_product(product, fetch=lambda *a, **k: data)["status"], "error")

    def test_exit_codes_keep_manual_checks_distinct_from_success(self):
        self.assertEqual(resolver.exit_code([{"status": "release_metadata"}]), 0)
        self.assertEqual(resolver.exit_code([{"status": "needs_official_page"}]), 2)
        self.assertEqual(resolver.exit_code([{"status": "error"}, {"status": "needs_official_page"}]), 1)

    def test_main_deduplicates_products_without_requesting_unselected_products(self):
        calls = []
        def resolve(product, **kwargs):
            calls.append(product)
            return {"product": product, "status": "needs_official_page"}
        with patch.object(resolver, "resolve_product", side_effect=resolve), redirect_stdout(io.StringIO()) as stdout:
            code = resolver.main(["--products", "egolite", "egolite", "git"])
        self.assertEqual(calls, ["egolite", "git"])
        self.assertEqual(code, 2)
        self.assertIn('"environment_setup_verified": false', stdout.getvalue())


if __name__ == "__main__":
    unittest.main()

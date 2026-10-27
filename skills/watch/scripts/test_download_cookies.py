from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.resolve()))

import download


class CookieDownloadTests(unittest.TestCase):
    def test_browser_cookie_args_are_inserted_before_url_separator(self) -> None:
        cmd = ["yt-dlp", "--skip-download", "--", "https://example.test/video"]
        actual = download._with_cookie_args(
            cmd,
            download._cookie_args(cookies_from_browser="chrome:Profile 1"),
        )
        self.assertEqual(
            actual,
            [
                "yt-dlp",
                "--skip-download",
                "--cookies-from-browser",
                "chrome:Profile 1",
                "--",
                "https://example.test/video",
            ],
        )

    def test_missing_browser_cookies_fall_back_to_public_metadata(self) -> None:
        calls: list[list[str]] = []
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)

            def fake_run(cmd: list[str], **_: object) -> SimpleNamespace:
                calls.append(cmd)
                if len(calls) == 2:
                    (out_dir / "video.info.json").write_text(
                        json.dumps({"title": "public metadata"}),
                        encoding="utf-8",
                    )
                return SimpleNamespace(returncode=1 if len(calls) == 1 else 0)

            with patch("download.shutil.which", return_value="/usr/bin/yt-dlp"), patch(
                "download.subprocess.run", side_effect=fake_run
            ):
                result = download.fetch_captions(
                    "https://example.test/video",
                    out_dir,
                    cookies_from_browser="chrome",
                )

        self.assertEqual(len(calls), 2)
        self.assertIn("--cookies-from-browser", calls[0])
        self.assertNotIn("--cookies-from-browser", calls[1])
        self.assertEqual(result["info"]["title"], "public metadata")

    def test_missing_browser_cookies_fall_back_to_public_media(self) -> None:
        calls: list[list[str]] = []
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)

            def fake_run(cmd: list[str], **_: object) -> SimpleNamespace:
                calls.append(cmd)
                if len(calls) == 2:
                    (out_dir / "video.mp4").write_bytes(b"video")
                return SimpleNamespace(returncode=1 if len(calls) == 1 else 0)

            with patch("download.shutil.which", return_value="/usr/bin/yt-dlp"), patch(
                "download.subprocess.run", side_effect=fake_run
            ):
                result = download.download_url(
                    "https://example.test/video",
                    out_dir,
                    cookies_from_browser="chrome",
                )

        self.assertEqual(len(calls), 2)
        self.assertIn("--cookies-from-browser", calls[0])
        self.assertNotIn("--cookies-from-browser", calls[1])
        self.assertTrue(result["video_path"].endswith("video.mp4"))

    def test_cookie_file_is_validated_and_forwarded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cookie_file = Path(tmp) / "cookies.txt"
            cookie_file.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
            args = download._cookie_args(cookies_file=cookie_file)
        self.assertEqual(args, ["--cookies", str(cookie_file.resolve())])


if __name__ == "__main__":
    unittest.main()

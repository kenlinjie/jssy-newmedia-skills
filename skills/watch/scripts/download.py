#!/usr/bin/env python3
"""Download a video via yt-dlp, or resolve a local file path.

Also fetches subtitles (manual first, then auto-generated) in VTT format so
transcribe.py can parse them without needing Whisper.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".mov", ".m4v", ".avi", ".flv", ".wmv"}
DEFAULT_SUBTITLE_LANGUAGES = "zh.*,en.*"


def is_url(source: str) -> bool:
    if source.startswith("-"):
        return False
    parsed = urlparse(source)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def resolve_local(path: str) -> dict:
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise SystemExit(f"File not found: {p}")
    if p.suffix.lower() not in VIDEO_EXTS:
        print(
            f"[watch] warning: {p.suffix} is not a known video extension, proceeding anyway",
            file=sys.stderr,
        )
    return {
        "video_path": str(p),
        "subtitle_path": None,
        "info": {"title": p.name, "url": str(p)},
        "downloaded": False,
    }


def _pick_subtitle(out_dir: Path) -> Path | None:
    candidates = sorted(out_dir.glob("video*.vtt"))
    if not candidates:
        return None
    # This installation serves a Chinese-first workflow. Prefer original or
    # Simplified Chinese tracks, then other Chinese tracks, then English.
    priorities = (
        (".zh-Hans.", ".zh-CN.", ".zh."),
        (".zh-Hant.", ".zh-TW.", ".zh-HK."),
        (".en-orig.", ".en-US.", ".en-GB.", ".en."),
    )
    for markers in priorities:
        preferred = [c for c in candidates if any(marker in c.name for marker in markers)]
        if preferred:
            return preferred[0]
    return candidates[0]


def _pick_video(out_dir: Path) -> Path | None:
    for ext in (".mp4", ".mkv", ".webm", ".mov", ".m4a", ".mp3", ".opus"):
        for candidate in out_dir.glob(f"video*{ext}"):
            return candidate
    for candidate in out_dir.glob("video.*"):
        if candidate.suffix.lower() in VIDEO_EXTS:
            return candidate
    return None


def _cookie_args(
    cookies_from_browser: str | None = None,
    cookies_file: str | Path | None = None,
) -> list[str]:
    """Build yt-dlp cookie arguments without exposing cookie contents."""
    if cookies_from_browser and cookies_file:
        raise SystemExit("Use only one of browser cookies or a cookies file")
    if cookies_from_browser:
        browser = cookies_from_browser.strip()
        if not browser or browser.startswith("-"):
            raise SystemExit("Invalid --cookies-from-browser value")
        return ["--cookies-from-browser", browser]
    if cookies_file:
        path = Path(cookies_file).expanduser().resolve()
        if not path.is_file():
            raise SystemExit(f"Cookies file not found: {path}")
        return ["--cookies", str(path)]
    return []


def _with_cookie_args(cmd: list[str], cookie_args: list[str]) -> list[str]:
    if not cookie_args:
        return cmd
    url_separator = cmd.index("--")
    return cmd[:url_separator] + cookie_args + cmd[url_separator:]


def fetch_captions(
    url: str,
    out_dir: Path,
    subtitle_languages: str = DEFAULT_SUBTITLE_LANGUAGES,
    cookies_from_browser: str | None = None,
    cookies_file: str | Path | None = None,
) -> dict:
    """Fetch metadata and best available VTT captions without downloading video."""
    if shutil.which("yt-dlp") is None:
        raise SystemExit("yt-dlp is not installed. Install with: brew install yt-dlp")

    out_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(out_dir / "video.%(ext)s")
    cmd = [
        "yt-dlp",
        "--skip-download",
        "--write-info-json",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs", subtitle_languages,
        "--sub-format", "vtt",
        "--convert-subs", "vtt",
        "--no-playlist",
        "--ignore-errors",
        "-o", output_template,
        "--",
        url,
    ]
    auth_args = _cookie_args(cookies_from_browser, cookies_file)
    result = subprocess.run(
        _with_cookie_args(cmd, auth_args),
        stdout=sys.stderr,
        stderr=sys.stderr,
    )
    subtitle = _pick_subtitle(out_dir)
    info_path = out_dir / "video.info.json"
    if auth_args and subtitle is None and not info_path.exists():
        print(
            "[watch] cookies unavailable or produced no metadata; retrying public access…",
            file=sys.stderr,
        )
        result = subprocess.run(cmd, stdout=sys.stderr, stderr=sys.stderr)
        subtitle = _pick_subtitle(out_dir)
    info = _read_info(info_path, url)
    return {
        "video_path": None,
        "subtitle_path": str(subtitle) if subtitle else None,
        "info": info or {"url": url},
        "downloaded": False,
    }


def _read_info(info_path: Path, url: str) -> dict:
    info: dict = {}
    if info_path.exists():
        try:
            raw = json.loads(info_path.read_text(encoding="utf-8"))
            info = {
                "title": raw.get("title"),
                "uploader": raw.get("uploader") or raw.get("channel"),
                "duration": raw.get("duration"),
                "url": raw.get("webpage_url") or url,
            }
        except Exception as exc:
            print(f"[watch] info.json parse failed: {exc}", file=sys.stderr)
            info = {"url": url}
    return info


def download_url(
    url: str,
    out_dir: Path,
    audio_only: bool = False,
    subtitle_languages: str = DEFAULT_SUBTITLE_LANGUAGES,
    cookies_from_browser: str | None = None,
    cookies_file: str | Path | None = None,
) -> dict:
    if shutil.which("yt-dlp") is None:
        raise SystemExit("yt-dlp is not installed. Install with: brew install yt-dlp")

    out_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(out_dir / "video.%(ext)s")

    fmt = "ba/bestaudio" if audio_only else "bv*[height<=720]+ba/b[height<=720]/bv+ba/b"
    cmd = [
        "yt-dlp",
        "-N", "8",
        "-f", fmt,
        "--merge-output-format", "mp4",
        "--write-info-json",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs", subtitle_languages,
        "--sub-format", "vtt",
        "--convert-subs", "vtt",
        "--no-playlist",
        "--ignore-errors",
        "-o", output_template,
        "--",
        url,
    ]

    # yt-dlp may exit non-zero if a subtitle variant fails (e.g. 429) even when
    # the video itself downloaded fine. Treat "video file present" as success.
    auth_args = _cookie_args(cookies_from_browser, cookies_file)
    result = subprocess.run(
        _with_cookie_args(cmd, auth_args),
        stdout=sys.stderr,
        stderr=sys.stderr,
    )
    video = _pick_video(out_dir)
    if auth_args and video is None:
        print(
            "[watch] cookies unavailable or produced no media; retrying public access…",
            file=sys.stderr,
        )
        result = subprocess.run(cmd, stdout=sys.stderr, stderr=sys.stderr)
        video = _pick_video(out_dir)
    if video is None:
        raise SystemExit(
            f"yt-dlp did not produce a video file in {out_dir} (exit {result.returncode})"
        )

    subtitle = _pick_subtitle(out_dir)
    info = _read_info(out_dir / "video.info.json", url)

    return {
        "video_path": str(video),
        "subtitle_path": str(subtitle) if subtitle else None,
        "info": info or {"url": url},
        "downloaded": True,
    }


def download(
    source: str,
    out_dir: Path,
    audio_only: bool = False,
    subtitle_languages: str = DEFAULT_SUBTITLE_LANGUAGES,
    cookies_from_browser: str | None = None,
    cookies_file: str | Path | None = None,
) -> dict:
    if is_url(source):
        return download_url(
            source,
            out_dir,
            audio_only=audio_only,
            subtitle_languages=subtitle_languages,
            cookies_from_browser=cookies_from_browser,
            cookies_file=cookies_file,
        )
    return resolve_local(source)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: download.py <url-or-path> <out-dir>", file=sys.stderr)
        raise SystemExit(2)
    result = download(sys.argv[1], Path(sys.argv[2]))
    print(json.dumps(result, indent=2))

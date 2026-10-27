#!/usr/bin/env python3
"""Local-first setup / preflight for /watch.

Modes:
  setup.py --check      Silent preflight. Exit 0 if ready, 2/3/4 on failure.
  setup.py --json       Machine-readable status for Codex to parse.
  setup.py              Installer. Auto-installs binaries and scaffolds local defaults.

Design:
- Silent on success: --check exits 0 with no output when everything's ready so
  that /watch doesn't spam "setup is complete" on every turn.
- Idempotent: re-running the installer is safe — it never clobbers existing
  keys and only appends missing ones.
- Local Qwen3-ASR is the default fallback. Cloud Whisper remains opt-in.
- Never sudo. On macOS, auto-install via brew. Elsewhere, print exact commands.
- Never write an API key to disk automatically.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from config import get_config  # noqa: E402
from local_asr import local_asr_status  # noqa: E402


REQUIRED_BINARIES = ["ffmpeg", "ffprobe", "yt-dlp"]
CONFIG_DIR = Path.home() / ".config" / "watch"
CONFIG_FILE = CONFIG_DIR / ".env"
ENV_TEMPLATE = """# Local-first /watch configuration
WATCH_DETAIL=balanced
WATCH_ASR=local
WATCH_ASR_LANGUAGE=Chinese
WATCH_SUBTITLE_LANGUAGES=zh.*,en.*

# Cloud Whisper is disabled unless WATCH_ASR=api or --asr api is explicit.
GROQ_API_KEY=
OPENAI_API_KEY=
"""


def _which(name: str) -> str | None:
    return shutil.which(name)


def _check_binaries() -> list[str]:
    return [b for b in REQUIRED_BINARIES if not _which(b)]


_PERM_WARNED: set[str] = set()


def _check_file_permissions(path: Path) -> None:
    """Warn to stderr (once per path per process) if a secrets file is
    world/group readable."""
    key = str(path)
    if key in _PERM_WARNED:
        return
    try:
        mode = path.stat().st_mode
        if mode & 0o044:
            _PERM_WARNED.add(key)
            sys.stderr.write(
                f"[watch] WARNING: {path} is readable by other users. "
                f"Run: chmod 600 {path}\n"
            )
            sys.stderr.flush()
    except OSError:
        pass


def _read_env_key(name: str) -> str | None:
    value = os.environ.get(name)
    if value and value.strip():
        return value.strip()
    if not CONFIG_FILE.exists():
        return None
    _check_file_permissions(CONFIG_FILE)
    try:
        for line in CONFIG_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, raw = line.partition("=")
            if key.strip() != name:
                continue
            raw = raw.strip()
            if len(raw) >= 2 and raw[0] in ('"', "'") and raw[-1] == raw[0]:
                raw = raw[1:-1]
            return raw or None
    except OSError:
        return None
    return None


def _have_api_key() -> tuple[bool, str | None]:
    if _read_env_key("GROQ_API_KEY"):
        return True, "groq"
    if _read_env_key("OPENAI_API_KEY"):
        return True, "openai"
    return False, None


def is_first_run() -> bool:
    """True if the installer hasn't completed successfully yet."""
    return _read_env_key("SETUP_COMPLETE") != "true"


def _scaffold_env() -> bool:
    """Create ~/.config/watch/.env with placeholders if missing."""
    if CONFIG_FILE.exists():
        return False
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(ENV_TEMPLATE, encoding="utf-8")
    try:
        CONFIG_FILE.chmod(0o600)
    except OSError:
        pass
    return True


def _ensure_config_defaults() -> None:
    """Append only missing non-secret defaults; preserve every existing value."""
    _scaffold_env()
    existing = CONFIG_FILE.read_text(encoding="utf-8")
    present = {
        line.partition("=")[0].strip()
        for line in existing.splitlines()
        if line.strip() and not line.lstrip().startswith("#") and "=" in line
    }
    defaults = {
        "WATCH_DETAIL": "balanced",
        "WATCH_ASR": "local",
        "WATCH_ASR_LANGUAGE": "Chinese",
        "WATCH_SUBTITLE_LANGUAGES": "zh.*,en.*",
        "GROQ_API_KEY": "",
        "OPENAI_API_KEY": "",
    }
    missing = [f"{key}={value}" for key, value in defaults.items() if key not in present]
    if missing:
        suffix = "" if not existing or existing.endswith("\n") else "\n"
        CONFIG_FILE.write_text(existing + suffix + "\n".join(missing) + "\n", encoding="utf-8")
    try:
        CONFIG_FILE.chmod(0o600)
    except OSError:
        pass


def _write_setup_complete() -> None:
    """Idempotently append SETUP_COMPLETE=true to .env.

    Used only after a successful local setup. Future sessions
    detect this marker to skip wizard-style UI and stay silent.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    existing = ""
    if CONFIG_FILE.exists():
        existing = CONFIG_FILE.read_text(encoding="utf-8")
        lines = existing.splitlines()
        for index, line in enumerate(lines):
            if line.strip().startswith("SETUP_COMPLETE="):
                if line.strip() != "SETUP_COMPLETE=true":
                    lines[index] = "SETUP_COMPLETE=true"
                    CONFIG_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
                return
        if existing and not existing.endswith("\n"):
            existing += "\n"
        CONFIG_FILE.write_text(existing + "SETUP_COMPLETE=true\n", encoding="utf-8")
    else:
        CONFIG_FILE.write_text(ENV_TEMPLATE + "\nSETUP_COMPLETE=true\n", encoding="utf-8")
    try:
        CONFIG_FILE.chmod(0o600)
    except OSError:
        pass


def _brew_pkg(missing: list[str]) -> list[str]:
    pkgs: list[str] = []
    for bin_name in missing:
        if bin_name in ("ffmpeg", "ffprobe"):
            if "ffmpeg" not in pkgs:
                pkgs.append("ffmpeg")
        elif bin_name == "yt-dlp":
            if "yt-dlp" not in pkgs:
                pkgs.append("yt-dlp")
        else:
            pkgs.append(bin_name)
    return pkgs


def _install_macos(missing: list[str]) -> tuple[bool, str]:
    if _which("brew") is None:
        return False, (
            "Homebrew is not installed. Install it from https://brew.sh, then re-run setup. "
            "Or install manually: `brew install " + " ".join(_brew_pkg(missing)) + "`"
        )
    pkgs = _brew_pkg(missing)
    if not pkgs:
        return True, "nothing to install"
    cmd = ["brew", "install", *pkgs]
    print(f"[setup] running: {' '.join(cmd)}", file=sys.stderr)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        return False, f"brew install failed with exit code {result.returncode}"
    return True, f"installed via brew: {', '.join(pkgs)}"


def _install_hint_linux(missing: list[str]) -> str:
    pkgs = _brew_pkg(missing)
    hints = []
    if "ffmpeg" in pkgs:
        hints.append("apt: `sudo apt install ffmpeg` or dnf: `sudo dnf install ffmpeg`")
    if "yt-dlp" in pkgs:
        hints.append("`pipx install yt-dlp` (recommended) or `pip install --user yt-dlp`")
    return "\n  ".join(hints) if hints else "nothing to install"


def _install_hint_windows(missing: list[str]) -> str:
    pkgs = _brew_pkg(missing)
    hints = []
    if "ffmpeg" in pkgs:
        hints.append("winget: `winget install Gyan.FFmpeg`")
    if "yt-dlp" in pkgs:
        hints.append("winget: `winget install yt-dlp.yt-dlp` or pip: `pip install --user yt-dlp`")
    return "\n  ".join(hints) if hints else "nothing to install"


def _status() -> dict:
    """Return a structured local-first preflight snapshot."""
    missing = _check_binaries()
    has_key, backend = _have_api_key()
    setup_complete = not is_first_run()
    cfg = get_config()
    asr_mode = str(cfg["asr"])
    local = local_asr_status()
    if asr_mode == "local":
        asr_ready = bool(local["available"])
        asr_problem = "needs_local_asr" if not asr_ready else None
    elif asr_mode == "api":
        asr_ready = has_key
        asr_problem = "needs_api_key" if not asr_ready else None
    else:
        asr_ready = True
        asr_problem = None

    can_proceed = not missing and asr_ready
    if can_proceed:
        status = "ready"
    elif missing and asr_problem:
        status = f"needs_install_and_{asr_problem.removeprefix('needs_')}"
    elif missing:
        status = "needs_install"
    else:
        status = asr_problem or "not_ready"

    return {
        "status": status,
        "can_proceed": can_proceed,
        "first_run": not setup_complete,
        "setup_complete": setup_complete,
        "missing_binaries": missing,
        "whisper_backend": backend,
        "has_api_key": has_key,
        "asr_mode": asr_mode,
        "asr_language": cfg["asr_language"],
        "local_asr": local,
        "config_file": str(CONFIG_FILE),
        "watch_detail": cfg["detail"],
        "platform": platform.system(),
    }


def cmd_check() -> int:
    """Silent-on-success preflight.

    Exit 0 with no output when the selected local/API/off route can run.
    """
    s = _status()
    if s["can_proceed"]:
        return 0

    parts = []
    if s["missing_binaries"]:
        parts.append(f"missing binaries: {', '.join(s['missing_binaries'])}")
    if s["asr_mode"] == "local" and not s["local_asr"]["available"]:
        failed = [name for name, ok in s["local_asr"]["checks"].items() if not ok]
        parts.append(f"local ASR incomplete: {', '.join(failed)}")
    if s["asr_mode"] == "api" and not s["has_api_key"]:
        parts.append("cloud ASR selected but no matching API key is configured")
    installer = Path(__file__).resolve()
    sys.stderr.write(
        f"[watch] setup incomplete ({'; '.join(parts)}). "
        f"Run: python3 {installer}\n"
    )
    sys.stderr.flush()

    if s["missing_binaries"] and len(parts) > 1:
        return 4
    if s["missing_binaries"]:
        return 2
    return 3


def cmd_json() -> int:
    json.dump(_status(), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_install() -> int:
    missing = _check_binaries()
    installed_deps = False
    if missing:
        system = platform.system()
        if system == "Darwin":
            ok, msg = _install_macos(missing)
            print(f"[setup] {msg}", file=sys.stderr)
            if not ok:
                return 2
            still_missing = _check_binaries()
            if still_missing:
                print(f"[setup] still missing after install: {', '.join(still_missing)}", file=sys.stderr)
                return 2
            installed_deps = True
        elif system == "Linux":
            print("[setup] dependencies missing on Linux — please install:", file=sys.stderr)
            print("  " + _install_hint_linux(missing), file=sys.stderr)
            return 2
        elif system == "Windows":
            print("[setup] dependencies missing on Windows — please install:", file=sys.stderr)
            print("  " + _install_hint_windows(missing), file=sys.stderr)
            return 2
        else:
            print(f"[setup] unsupported platform ({system}) for auto-install. Install manually:", file=sys.stderr)
            print(f"  missing: {', '.join(missing)}", file=sys.stderr)
            return 2

    created = _scaffold_env()
    _ensure_config_defaults()
    if created:
        print(f"[setup] created config: {CONFIG_FILE}")
    else:
        print(f"[setup] config exists: {CONFIG_FILE}")

    current = _status()
    if current["can_proceed"]:
        _write_setup_complete()
        print(f"[setup] ready. ASR fallback: {current['asr_mode']}")
        if installed_deps:
            print("[setup] installed dependencies; /watch is fully set up.")
        return 0

    if current["asr_mode"] == "local":
        failed = [name for name, ok in current["local_asr"]["checks"].items() if not ok]
        print(f"[setup] local ASR incomplete: {', '.join(failed)}", file=sys.stderr)
    else:
        print(
            "[setup] WATCH_ASR=api requires GROQ_API_KEY or OPENAI_API_KEY; "
            "switch back to WATCH_ASR=local to stay offline.",
            file=sys.stderr,
        )
    return 3


def main() -> int:
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--check":
            return cmd_check()
        if arg == "--json":
            return cmd_json()
    return cmd_install()


if __name__ == "__main__":
    raise SystemExit(main())

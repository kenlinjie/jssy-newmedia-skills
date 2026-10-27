#!/bin/bash

set -euo pipefail

UV_BIN="${UV_BIN:-$(command -v uv || true)}"
VENV_DIR="$HOME/.local/share/codex-local-asr/venv"
PYTHON_BIN="$VENV_DIR/bin/python"

die() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

[[ "$(uname -s)" == "Darwin" ]] || die "this runtime is only supported on macOS"
[[ "$(uname -m)" == "arm64" ]] || die "this runtime requires Apple Silicon"
[[ -x "$UV_BIN" ]] || die "uv is not executable at $UV_BIN"

if [[ -e "$VENV_DIR" && ! -x "$PYTHON_BIN" ]]; then
  die "runtime directory exists but is incomplete; preserve and inspect it before retrying"
fi

if [[ -x "$PYTHON_BIN" ]]; then
  "$PYTHON_BIN" -c '
from importlib.metadata import version
expected = {"mlx-audio": "0.4.6", "httpx": "0.28.1", "socksio": "1.0.0"}
actual = {name: version(name) for name in expected}
if actual != expected:
    raise SystemExit(f"runtime exists with unexpected versions: {actual}")
print(f"Local ASR runtime already verified: {actual}")
'
  exit 0
fi

"$UV_BIN" venv --python 3.11 "$VENV_DIR"
"$UV_BIN" pip install \
  --python "$PYTHON_BIN" \
  "mlx-audio==0.4.6" \
  "httpx[socks]==0.28.1"

"$PYTHON_BIN" -c '
from importlib.metadata import version
expected = {"mlx-audio": "0.4.6", "httpx": "0.28.1", "socksio": "1.0.0"}
actual = {name: version(name) for name in expected}
if actual != expected:
    raise SystemExit(f"installed runtime failed version verification: {actual}")
print(f"Installed local ASR runtime: {actual}")
'

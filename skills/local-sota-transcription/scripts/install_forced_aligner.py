#!/usr/bin/env python3
from pathlib import Path
from huggingface_hub import snapshot_download
import json, os
from datetime import datetime, timezone

REPO_ID = "mlx-community/Qwen3-ForcedAligner-0.6B-8bit"
REVISION = "0e1a68e91d815300c7c9754b2a7639378b23db15"
WEIGHT_BYTES = 1271924386
WEIGHT_SHA256 = "be19ef8ac4326d032e7673342930b14c2df30bd68c1632493b0f563e30829f91"
MODEL_ROOT = Path.home() / "Library/Caches/codex-local-asr/models"
VERSIONED_NAME = f"Qwen3-ForcedAligner-0.6B-8bit-{REVISION[:7]}"
ALIAS_NAME = "Qwen3-ForcedAligner-0.6B-8bit"

MODEL_ROOT.mkdir(parents=True, exist_ok=True)
target = MODEL_ROOT / VERSIONED_NAME
alias = MODEL_ROOT / ALIAS_NAME

if not target.exists():
    print(f"Downloading {REPO_ID} to {target}...")
    snapshot_download(repo_id=REPO_ID, revision=REVISION, local_dir=target, max_workers=4)
    meta = {
        "repo": REPO_ID,
        "revision": REVISION,
        "weight_file": "model.safetensors",
        "weight_bytes": WEIGHT_BYTES,
        "weight_sha256": WEIGHT_SHA256,
        "downloaded_at": datetime.now(timezone.utc).isoformat()
    }
    (target / "MODEL_SOURCE.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

if alias.is_symlink() or not alias.exists():
    alias.unlink(missing_ok=True)
    alias.symlink_to(target)
print("ForcedAligner ready:", alias.resolve())

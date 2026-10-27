#!/usr/bin/env python3
"""Install the pinned lightweight Qwen3-ASR model without touching fallbacks."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

from huggingface_hub import snapshot_download


REPO_ID = "mlx-community/Qwen3-ASR-0.6B-8bit"
REVISION = "89e96d92ba34aca20b3e29fb10cc284097d1219f"
WEIGHT_BYTES = 1_006_229_426
WEIGHT_SHA256 = "b5bfe4abc1b4c6e58b633096682ec2b6297298add1527119936107d211adf0e8"
MODEL_ROOT = Path.home() / "Library/Caches/codex-local-asr/models"
VERSIONED_NAME = f"Qwen3-ASR-0.6B-8bit-{REVISION[:7]}"
ALIAS_NAME = "Qwen3-ASR-0.6B-8bit"


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_model(path: Path) -> None:
    required = [path / "config.json", path / "model.safetensors"]
    missing = [str(item) for item in required if not item.is_file()]
    if missing:
        raise SystemExit(f"Model is incomplete; missing: {', '.join(missing)}")
    weight = path / "model.safetensors"
    if weight.stat().st_size != WEIGHT_BYTES:
        raise SystemExit(
            f"Model size mismatch: {weight.stat().st_size}/{WEIGHT_BYTES}"
        )
    actual_hash = hash_file(weight)
    if actual_hash != WEIGHT_SHA256:
        raise SystemExit(f"Model SHA-256 mismatch: {actual_hash}/{WEIGHT_SHA256}")


def write_source_metadata(path: Path) -> None:
    payload = {
        "repo": REPO_ID,
        "revision": REVISION,
        "weight_file": "model.safetensors",
        "weight_bytes": WEIGHT_BYTES,
        "weight_sha256": WEIGHT_SHA256,
        "conversion_runtime": {"package": "mlx-audio", "version": "0.3.1"},
        "validated_runtime": {"package": "mlx-audio", "version": "0.4.6"},
        "license": "apache-2.0",
        "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    destination = path / "MODEL_SOURCE.json"
    temporary = destination.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)


def point_alias(alias: Path, target: Path) -> None:
    if alias.exists() and not alias.is_symlink():
        raise SystemExit(f"Refusing to replace non-symlink model alias: {alias}")
    if alias.is_symlink() and alias.resolve() == target.resolve():
        return
    temporary = alias.with_name(alias.name + ".tmp")
    temporary.unlink(missing_ok=True)
    temporary.symlink_to(target)
    temporary.replace(alias)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install or verify the pinned Qwen3-ASR-0.6B-8bit model."
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify the pinned version and alias without downloading anything.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    MODEL_ROOT.mkdir(parents=True, exist_ok=True)
    target = MODEL_ROOT / VERSIONED_NAME
    alias = MODEL_ROOT / ALIAS_NAME

    if target.exists():
        verify_model(target)
        point_alias(alias, target)
        print(f"Pinned lightweight ASR model verified: {target}")
        return 0
    if args.verify_only:
        raise SystemExit(f"Pinned lightweight ASR model is not installed: {target}")

    staging = Path(tempfile.mkdtemp(prefix=f".{VERSIONED_NAME}-", dir=MODEL_ROOT))
    try:
        snapshot_download(
            repo_id=REPO_ID,
            revision=REVISION,
            local_dir=staging,
            max_workers=4,
        )
        verify_model(staging)
        write_source_metadata(staging)
        os.replace(staging, target)
        point_alias(alias, target)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise

    verify_model(target)
    print(f"Installed pinned lightweight ASR model: {target}")
    print(f"Alias: {alias} -> {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

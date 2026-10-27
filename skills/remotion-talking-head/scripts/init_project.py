#!/usr/bin/env python3
"""Initialize a non-destructive Remotion talking-head project package."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


DIRECTORIES = (
    "00-source",
    "01-analysis/frames",
    "02-style-review/frames",
    "03-remotion",
    "04-renders/preview",
    "04-renders/final",
    "05-qa/final-keyframes",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def probe_media(path: Path) -> dict:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return {"status": "ffprobe-unavailable"}

    command = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=format_name,duration,size:stream=index,codec_type,codec_name,width,height,r_frame_rate,pix_fmt,color_range,color_space,color_transfer,color_primaries,sample_rate,channels",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return {"status": "probe-failed", "error": result.stderr.strip()}
    return {"status": "ok", "data": json.loads(result.stdout)}


def write_json_if_absent(path: Path, payload: dict) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {path}")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_template_if_absent(template: Path, destination: Path, replacements: dict[str, str]) -> None:
    if destination.exists():
        return
    content = template.read_text(encoding="utf-8")
    for key, value in replacements.items():
        content = content.replace("{{" + key + "}}", value)
    destination.write_text(content, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="Absolute output project directory")
    parser.add_argument("--name", required=True, help="Human-readable project name")
    parser.add_argument("--source", required=True, help="Absolute source media path")
    parser.add_argument("--platform", default="unspecified", help="Target platform")
    parser.add_argument("--aspect", default="auto", help="Target aspect ratio, for example 9:16")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Create missing directories/templates without replacing an existing manifest",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    source = Path(args.source).expanduser().resolve()

    if not source.is_file():
        print(f"Source media does not exist: {source}", file=sys.stderr)
        return 2
    if not root.is_absolute():
        print("--root must resolve to an absolute path", file=sys.stderr)
        return 2

    manifest_path = root / "project.json"
    if manifest_path.exists() and not args.resume:
        print(f"Project already initialized: {manifest_path}", file=sys.stderr)
        return 3

    root.mkdir(parents=True, exist_ok=True)
    for relative in DIRECTORIES:
        (root / relative).mkdir(parents=True, exist_ok=True)

    source_hash = sha256_file(source)
    now = datetime.now(timezone.utc).isoformat()
    media_info = probe_media(source)

    source_manifest_path = root / "00-source" / "source-manifest.json"
    if source_manifest_path.exists():
        existing = json.loads(source_manifest_path.read_text(encoding="utf-8"))
        if existing.get("sha256") != source_hash:
            print("Existing source manifest points to different content", file=sys.stderr)
            return 4
    else:
        write_json_if_absent(
            source_manifest_path,
            {
                "originalPath": str(source),
                "sha256": source_hash,
                "bytes": source.stat().st_size,
                "recordedAt": now,
                "sourcePolicy": "read-only; do not overwrite, move, rename, or delete",
                "media": media_info,
            },
        )

    if not manifest_path.exists():
        write_json_if_absent(
            manifest_path,
            {
                "schemaVersion": 1,
                "projectName": args.name,
                "createdAt": now,
                "status": "style_review_pending",
                "target": {"platform": args.platform, "aspect": args.aspect},
                "source": {"path": str(source), "sha256": source_hash},
                "styleReview": {
                    "required": True,
                    "onlinePopularOptions": 3,
                    "originalImagegenOptions": 2,
                    "selected": None,
                },
                "paths": {
                    "analysis": "01-analysis",
                    "styleReview": "02-style-review",
                    "remotion": "03-remotion",
                    "renders": "04-renders",
                    "qa": "05-qa",
                },
                "deliverables": {
                    "finalMp4": None,
                    "compositionId": None,
                    "qaStatus": "pending",
                },
            },
        )

    skill_root = Path(__file__).resolve().parent.parent
    replacements = {
        "PROJECT_NAME": args.name,
        "SOURCE_PATH": str(source),
        "PLATFORM": args.platform,
        "ASPECT": args.aspect,
    }
    write_template_if_absent(
        skill_root / "assets" / "CONTENT_MAP_TEMPLATE.md",
        root / "01-analysis" / "CONTENT_MAP.md",
        replacements,
    )
    write_template_if_absent(
        skill_root / "assets" / "STYLE_REVIEW_TEMPLATE.md",
        root / "02-style-review" / "STYLE_REVIEW.md",
        replacements,
    )
    write_template_if_absent(
        skill_root / "assets" / "QA_REPORT_TEMPLATE.md",
        root / "05-qa" / "QA_REPORT.md",
        replacements,
    )

    print(json.dumps({"projectRoot": str(root), "status": "style_review_pending", "sourceSha256": source_hash}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

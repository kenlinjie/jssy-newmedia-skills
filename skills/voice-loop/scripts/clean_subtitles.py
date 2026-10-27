#!/usr/bin/env python3
"""Remove SRT/VTT transport noise while preserving spoken wording."""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path
from typing import List

TIMESTAMP = re.compile(
    r"^\s*(?:\d{1,2}:)?\d{1,2}:\d{2}[,.]\d{3}\s*-->\s*"
    r"(?:\d{1,2}:)?\d{1,2}:\d{2}[,.]\d{3}"
)
TAG = re.compile(r"<[^>]+>|\{\\[^}]+\}")
SPEAKER = re.compile(r"^\s*(?:[-–—]\s*)?(?:[\w\u3400-\u9fff]{1,24}:\s+)")
TERMINAL = re.compile(r"(?<=[。！？!?…])")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="SRT, VTT, or subtitle-like text")
    parser.add_argument("--output", type=Path, help="Write cleaned text here; defaults to stdout")
    parser.add_argument(
        "--strip-speaker-labels",
        action="store_true",
        help="Remove leading 'Speaker:' labels (kept by default)",
    )
    parser.add_argument(
        "--paragraph-chars",
        type=int,
        default=300,
        help="Soft paragraph target, split only at sentence punctuation",
    )
    return parser.parse_args()


def clean_line(line: str, strip_speaker: bool) -> str:
    value = html.unescape(TAG.sub("", line)).replace("\ufeff", "").strip()
    if strip_speaker:
        value = SPEAKER.sub("", value).strip()
    return re.sub(r"[ \t]+", " ", value)


def extract_cues(text: str, strip_speaker: bool) -> List[str]:
    cues: List[str] = []
    buffer: List[str] = []
    skipping_block = False

    def flush() -> None:
        nonlocal buffer
        if buffer:
            cue = join_fragments(buffer)
            if cue:
                if cues and cue == cues[-1]:
                    buffer = []
                    return
                if cues and cue.startswith(cues[-1]) and len(cue) > len(cues[-1]):
                    cues[-1] = cue
                elif cues and cues[-1].startswith(cue):
                    pass
                else:
                    cues.append(cue)
        buffer = []

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        upper = stripped.upper()
        if skipping_block:
            if not stripped:
                skipping_block = False
            continue
        if upper.startswith(("NOTE", "STYLE", "REGION")):
            flush()
            skipping_block = True
            continue
        if not stripped:
            flush()
            continue
        if upper == "WEBVTT" or upper.startswith(("KIND:", "LANGUAGE:")):
            continue
        if TIMESTAMP.match(stripped):
            flush()
            continue
        if stripped.isdigit() and not buffer:
            continue
        value = clean_line(stripped, strip_speaker)
        if value:
            buffer.append(value)
    flush()
    return cues


def is_cjk(char: str) -> bool:
    return any(
        start <= ord(char) <= end
        for start, end in (
            (0x3400, 0x4DBF),
            (0x4E00, 0x9FFF),
            (0x3040, 0x30FF),
            (0xAC00, 0xD7AF),
        )
    )


def join_fragments(parts: List[str]) -> str:
    result = ""
    no_space_before = set("，。！？；：、,.!?;:)]}》」』”’…")
    no_space_after = set("([{《「『“‘")
    for part in parts:
        if not result:
            result = part
            continue
        if (
            part[0] in no_space_before
            or result[-1] in no_space_after
            or is_cjk(part[0])
            or is_cjk(result[-1])
        ):
            result += part
        else:
            result += " " + part
    return re.sub(r"\s+", " ", result).strip()


def make_paragraphs(text: str, target: int) -> str:
    if target <= 0:
        return text
    units = [unit for unit in TERMINAL.split(text) if unit]
    paragraphs: List[str] = []
    current = ""
    for unit in units:
        if current and len(current) >= target:
            paragraphs.append(current.strip())
            current = unit
        else:
            current += unit
    if current.strip():
        paragraphs.append(current.strip())
    return "\n\n".join(paragraphs)


def main() -> int:
    args = parse_args()
    if not args.input.is_file():
        print(f"error: input file not found: {args.input}", file=sys.stderr)
        return 2
    text = args.input.read_text(encoding="utf-8-sig")
    cues = extract_cues(text, args.strip_speaker_labels)
    cleaned = make_paragraphs(join_fragments(cues), args.paragraph_chars).strip() + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(cleaned, encoding="utf-8")
        print(f"wrote: {args.output}")
    else:
        sys.stdout.write(cleaned)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

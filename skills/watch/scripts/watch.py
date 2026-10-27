#!/usr/bin/env python3
"""/watch entry point: download video, extract frames, parse transcript.

Prints a markdown report to stdout listing frame paths and transcript. Codex
then opens each frame with its local image viewer.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

from config import frame_cap, get_config  # noqa: E402
from download import download, fetch_captions, is_url  # noqa: E402
from frames import MAX_FPS, auto_fps, auto_fps_focus, extract_at_timestamps, extract_keyframes, extract_scene_or_uniform, format_time, get_metadata, merge_frames, parse_time, parse_timestamps  # noqa: E402
from local_asr import LocalASRError, transcribe_local  # noqa: E402
from transcribe import filter_range, format_transcript, parse_vtt  # noqa: E402
from whisper import load_api_key, transcribe_video  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="watch",
        description="Download a video, extract auto-scaled frames, and surface the transcript.",
    )
    ap.add_argument("source", help="Video URL or local file path")
    ap.add_argument("--max-frames", type=int, default=None, help="Override frame cap")
    ap.add_argument("--resolution", type=int, default=512, help="Frame width in pixels (default 512)")
    ap.add_argument("--fps", type=float, default=None, help="Override auto-fps")
    ap.add_argument(
        "--detail",
        choices=["transcript", "efficient", "balanced", "token-burner"],
        default=None,
        help="Fidelity/speed dial: transcript (no frames), efficient (fast keyframes, cap 50), "
             "balanced (scene, cap 100), token-burner (scene, uncapped).",
    )
    ap.add_argument(
        "--timestamps",
        type=str,
        default=None,
        help="Comma-separated absolute timestamps (SS, MM:SS, HH:MM:SS) to grab a frame at, "
             "e.g. transcript-flagged 'look here' moments. Added on top of the detail frames "
             "(reserved against the cap); with --detail transcript these become the only frames.",
    )
    ap.add_argument("--start", type=str, default=None, help="Range start (SS, MM:SS, or HH:MM:SS)")
    ap.add_argument("--end", type=str, default=None, help="Range end (SS, MM:SS, or HH:MM:SS)")
    ap.add_argument("--out-dir", type=str, default=None, help="Working directory (default: tmp)")
    ap.add_argument(
        "--asr",
        choices=["local", "api", "off"],
        default=None,
        help="Fallback when native captions are missing. Default: local Qwen3-ASR.",
    )
    ap.add_argument(
        "--language",
        type=str,
        default=None,
        help="Language name for local Qwen3-ASR (default from WATCH_ASR_LANGUAGE).",
    )
    ap.add_argument(
        "--context-file",
        type=str,
        default=None,
        help="UTF-8 context/terminology file for local Qwen3-ASR.",
    )
    ap.add_argument(
        "--term",
        action="append",
        default=[],
        help="Proper noun or domain term for local Qwen3-ASR; may be repeated.",
    )
    ap.add_argument(
        "--no-whisper",
        action="store_true",
        help="Compatibility alias for --asr off.",
    )
    ap.add_argument(
        "--whisper",
        choices=["groq", "openai"],
        default=None,
        help="Explicitly use a cloud Whisper backend (implies --asr api).",
    )
    ap.add_argument(
        "--no-dedup",
        action="store_true",
        help="Disable near-duplicate frame removal. Keeps visually identical "
             "frames (static screen recordings, held slides) instead of collapsing them.",
    )
    cookie_group = ap.add_mutually_exclusive_group()
    cookie_group.add_argument(
        "--cookies-from-browser",
        metavar="BROWSER",
        default=None,
        help="Read cookies through yt-dlp from BROWSER (default: chrome; override with "
             "WATCH_COOKIES_FROM_BROWSER). Falls back to public access when unavailable.",
    )
    cookie_group.add_argument(
        "--cookies-file",
        metavar="FILE",
        default=None,
        help="Read a Netscape-format cookies file instead of browser cookies.",
    )
    cookie_group.add_argument(
        "--no-cookies",
        action="store_true",
        help="Disable cookie access and use public access only.",
    )
    args = ap.parse_args()

    config = get_config()
    detail = args.detail or str(config["detail"])
    asr_mode = args.asr or str(config["asr"])
    if args.no_whisper:
        asr_mode = "off"
    if args.whisper:
        asr_mode = "api"
    asr_language = args.language or str(config["asr_language"])
    subtitle_languages = str(config["subtitle_languages"])
    configured_cap = frame_cap(detail)
    if args.max_frames is not None:
        max_frames = args.max_frames
    else:
        max_frames = configured_cap
    if max_frames is not None and max_frames < 1:
        raise SystemExit("--max-frames must be greater than zero")
    budget_cap = max_frames if max_frames is not None else 100
    cue_timestamps = parse_timestamps(args.timestamps)
    cookies_from_browser: str | None = None
    cookies_file: str | None = None
    if not args.no_cookies:
        if args.cookies_file:
            cookies_file = args.cookies_file
        else:
            cookies_from_browser = (
                args.cookies_from_browser
                or os.environ.get("WATCH_COOKIES_FROM_BROWSER")
                or "chrome"
            )

    if args.out_dir:
        work = Path(args.out_dir).expanduser().resolve()
    else:
        work = Path(tempfile.mkdtemp(prefix="watch-"))
    work.mkdir(parents=True, exist_ok=True)
    print(f"[watch] working dir: {work}", file=sys.stderr)

    url_source = is_url(args.source)
    dl: dict = {"subtitle_path": None, "info": {}, "downloaded": False}
    transcript_segments: list[dict] = []
    transcript_text: str | None = None
    transcript_source: str | None = None
    local_asr_meta: dict | None = None
    asr_failure: str | None = None
    video_path: str | None = None

    if url_source:
        if cookies_file:
            print(
                "[watch] cookie mode: explicit file; public fallback is enabled",
                file=sys.stderr,
            )
        elif cookies_from_browser:
            print(
                "[watch] cookie mode: browser; public fallback is enabled",
                file=sys.stderr,
            )
        else:
            print("[watch] cookie mode: disabled", file=sys.stderr)
        print("[watch] checking metadata/captions via yt-dlp…", file=sys.stderr)
        dl = fetch_captions(
            args.source,
            work / "download",
            subtitle_languages=subtitle_languages,
            cookies_from_browser=cookies_from_browser,
            cookies_file=cookies_file,
        )
        if dl.get("subtitle_path"):
            try:
                transcript_segments = parse_vtt(dl["subtitle_path"])
                transcript_text = format_transcript(transcript_segments)
                transcript_source = "captions"
            except Exception as exc:
                print(f"[watch] subtitle parse failed: {exc}", file=sys.stderr)
                transcript_segments = []

    # --timestamps needs the video for frame grabs, so it overrides the
    # transcript-mode download skip (and forces a full, not audio-only, fetch).
    audio_only = detail == "transcript" and not cue_timestamps
    if detail == "transcript" and transcript_segments and not cue_timestamps:
        video_path = None
    else:
        if url_source:
            print(
                "[watch] downloading audio via yt-dlp…" if audio_only
                else "[watch] downloading video via yt-dlp…",
                file=sys.stderr,
            )
            dl = download(
                args.source,
                work / "download",
                audio_only=audio_only,
                subtitle_languages=subtitle_languages,
                cookies_from_browser=cookies_from_browser,
                cookies_file=cookies_file,
            )
        else:
            print("[watch] using local file…", file=sys.stderr)
            dl = download(
                args.source,
                work / "download",
                subtitle_languages=subtitle_languages,
                cookies_from_browser=cookies_from_browser,
                cookies_file=cookies_file,
            )
        video_path = dl["video_path"]

    meta = get_metadata(video_path) if video_path else {
        "duration_seconds": float((dl.get("info") or {}).get("duration") or 0),
        "width": None,
        "height": None,
        "codec": None,
        "has_audio": False,
    }
    full_duration = meta["duration_seconds"]

    start_sec = parse_time(args.start)
    end_sec = parse_time(args.end)

    if start_sec is not None and start_sec < 0:
        raise SystemExit("--start must be non-negative")
    if end_sec is not None and start_sec is not None and end_sec <= start_sec:
        raise SystemExit("--end must be greater than --start")
    if full_duration > 0 and start_sec is not None and start_sec >= full_duration:
        raise SystemExit(f"--start {start_sec:.1f}s is past end of video ({full_duration:.1f}s)")

    effective_start = start_sec if start_sec is not None else 0.0
    effective_end = end_sec if end_sec is not None else full_duration
    effective_duration = max(0.0, effective_end - effective_start)
    focused = start_sec is not None or end_sec is not None

    if focused:
        fps, target = auto_fps_focus(effective_duration, max_frames=budget_cap)
    else:
        fps, target = auto_fps(effective_duration, max_frames=budget_cap)
    if args.fps is not None:
        fps = min(args.fps, MAX_FPS)
        target = max(1, int(round(fps * effective_duration)))

    if transcript_segments and focused:
        transcript_segments = filter_range(transcript_segments, start_sec, end_sec)
        transcript_text = format_transcript(transcript_segments)

    scope = (
        f"{format_time(effective_start)}-{format_time(effective_end)} ({effective_duration:.1f}s)"
        if focused else f"full {effective_duration:.1f}s"
    )
    frames: list[dict] = []
    frame_meta: dict = {"engine": "none", "candidate_count": 0, "selected_count": 0, "fallback": False}
    cue_frames: list[dict] = []
    cue_meta: dict = {}

    # Transcript cues are pinned: extracted first and counted against the cap so
    # the detail engine never evicts the moments the user explicitly asked for.
    if cue_timestamps and video_path:
        cue_frames, cue_meta = extract_at_timestamps(
            video_path,
            work / "frames",
            cue_timestamps,
            resolution=args.resolution,
            max_frames=max_frames,
            start_seconds=start_sec,
            end_seconds=end_sec,
        )
        if cue_meta.get("dropped_out_of_window"):
            print(
                f"[watch] {cue_meta['dropped_out_of_window']} cue timestamp(s) outside the "
                "focus range — dropped",
                file=sys.stderr,
            )

    detail_budget = max_frames if max_frames is None else max(0, max_frames - len(cue_frames))
    if detail != "transcript" and video_path and detail_budget != 0:
        cap_label = "unlimited" if detail_budget is None else str(detail_budget)
        engine_label = "keyframes" if detail == "efficient" else "scene-aware frames"
        print(
            f"[watch] extracting {engine_label} over {scope} "
            f"(target {target}, cap {cap_label})…",
            file=sys.stderr,
        )
        if detail == "efficient":
            frames, frame_meta = extract_keyframes(
                video_path,
                work / "frames",
                resolution=args.resolution,
                max_frames=detail_budget,
                start_seconds=start_sec,
                end_seconds=end_sec,
                dedup=not args.no_dedup,
            )
        else:  # balanced, token-burner
            frames, frame_meta = extract_scene_or_uniform(
                video_path,
                work / "frames",
                fps=fps,
                target_frames=target,
                resolution=args.resolution,
                max_frames=detail_budget,
                start_seconds=start_sec,
                end_seconds=end_sec,
                dedup=not args.no_dedup,
            )

    if cue_frames:
        frames = merge_frames(frames, cue_frames)

    if not transcript_segments and dl.get("subtitle_path"):
        try:
            all_segments = parse_vtt(dl["subtitle_path"])
            transcript_segments = filter_range(all_segments, start_sec, end_sec) if focused else all_segments
            transcript_text = format_transcript(transcript_segments)
            transcript_source = "captions"
        except Exception as exc:
            print(f"[watch] subtitle parse failed: {exc}", file=sys.stderr)

    if not transcript_segments and video_path and meta.get("has_audio"):
        if asr_mode == "local":
            try:
                all_segments, local_asr_meta = transcribe_local(
                    video_path,
                    work / "local-asr",
                    language=asr_language,
                    start_seconds=start_sec,
                    end_seconds=end_sec,
                    context_file=args.context_file,
                    terms=args.term,
                )
                transcript_segments = (
                    filter_range(all_segments, start_sec, end_sec)
                    if focused
                    else all_segments
                )
                transcript_text = format_transcript(transcript_segments)
                transcript_source = "local Qwen3-ASR (verified)"
            except LocalASRError as exc:
                asr_failure = str(exc)
                print(f"[watch] local ASR failed: {exc}", file=sys.stderr)
        elif asr_mode == "api":
            backend, api_key = load_api_key(args.whisper)
            if backend and api_key:
                try:
                    all_segments, used_backend = transcribe_video(
                        video_path,
                        work / "audio.mp3",
                        backend=backend,
                        api_key=api_key,
                    )
                    transcript_segments = (
                        filter_range(all_segments, start_sec, end_sec)
                        if focused
                        else all_segments
                    )
                    transcript_text = format_transcript(transcript_segments)
                    transcript_source = f"cloud Whisper ({used_backend})"
                except SystemExit as exc:
                    asr_failure = str(exc)
                    print(f"[watch] cloud Whisper failed: {exc}", file=sys.stderr)
            else:
                asr_failure = "cloud ASR requested but the selected API key is missing"
                print(f"[watch] {asr_failure}", file=sys.stderr)
        else:
            asr_failure = "ASR fallback disabled"
            print("[watch] captions missing; ASR fallback is off", file=sys.stderr)
    elif not transcript_segments and video_path and not meta.get("has_audio"):
        print("[watch] no audio stream found — proceeding without transcription", file=sys.stderr)

    info = dl.get("info") or {}

    print()
    print("# watch: video report")
    print()
    print(f"- **Source:** {args.source}")
    if info.get("title"):
        print(f"- **Title:** {info['title']}")
    if info.get("uploader"):
        print(f"- **Uploader:** {info['uploader']}")
    print(f"- **Duration:** {format_time(full_duration)} ({full_duration:.1f}s)")
    if focused:
        print(
            f"- **Focus range:** {format_time(effective_start)} → {format_time(effective_end)} "
            f"({effective_duration:.1f}s)"
        )
    if meta.get("width") and meta.get("height"):
        print(f"- **Resolution:** {meta['width']}x{meta['height']} ({meta.get('codec') or 'unknown codec'})")
    range_mode = "focused" if focused else "full"
    print(f"- **Detail:** {detail}")
    print(f"- **ASR fallback:** {asr_mode}" + (f" ({asr_language})" if asr_mode == "local" else ""))
    detail_count = frame_meta.get("selected_count", 0)
    if detail != "transcript":
        cap_label = "unlimited" if detail_budget is None else str(detail_budget)
        engine = frame_meta.get("engine", "scene")
        fallback = " with uniform fallback" if frame_meta.get("fallback") else ""
        deduped = frame_meta.get("deduped_count", 0)
        dedup_note = f", {deduped} near-duplicate{'s' if deduped != 1 else ''} dropped" if deduped else ""
        print(
            f"- **Frames:** {detail_count} selected from {frame_meta.get('candidate_count', detail_count)} "
            f"candidates ({engine}{fallback}{dedup_note}, {range_mode} range, budget {target}, cap {cap_label})"
        )
    elif not cue_frames:
        print("- **Frames:** skipped (transcript detail)")
    if cue_frames:
        dropped = cue_meta.get("dropped_out_of_window", 0)
        drop_note = f", {dropped} dropped outside range" if dropped else ""
        print(
            f"- **Cue frames:** {len(cue_frames)} at transcript-flagged timestamps "
            f"(transcript-cue{drop_note})"
        )
    if frames:
        print(f"- **Frame size:** max {args.resolution}px wide, max 1998px tall")
    if transcript_segments:
        in_range = " in range" if focused else ""
        print(
            f"- **Transcript:** {len(transcript_segments)} segments{in_range} "
            f"(via {transcript_source or 'captions'})"
        )
    else:
        print("- **Transcript:** none available")
    if local_asr_meta:
        print(
            f"- **Local ASR verification:** passed; {local_asr_meta.get('chunk_count')} chunk(s), "
            f"{local_asr_meta.get('word_count')} timed token(s), "
            f"timing={local_asr_meta.get('timing_mode')}"
        )
        print(f"- **Local ASR artifacts:** {local_asr_meta['output_dir']}")

    if detail == "token-burner" and len(frames) > 250:
        print()
        print(
            f"> **Warning:** token-burner detail selected {len(frames)} frames. "
            "This may use a large number of image tokens."
        )

    if not focused and full_duration > 600 and detail not in ("transcript", "token-burner"):
        mins = int(full_duration // 60)
        print()
        print(
            f"> **Warning:** This is a {mins}-minute video. Frame coverage is sparse at this length "
            f"under `{detail}` detail — its cap spreads thin across the full clip. For better results, "
            "re-run with `--start HH:MM:SS --end HH:MM:SS` to zoom into a section, or use "
            "`--detail token-burner` to keep every scene-change frame across the whole video."
        )

    print()
    print("## Frames")
    print()
    if frames:
        print(f"Frames live at: `{work / 'frames'}`")
        print()
        print(
            "**Open every frame path with Codex's local image viewer.** "
            "Frames are in chronological order; `t=MM:SS` is the absolute timestamp in the source video."
        )
        print()
        for frame in frames:
            print(
                f"- `{frame['path']}` "
                f"(t={format_time(frame['timestamp_seconds'])}, reason={frame.get('reason', 'selected')})"
            )
    else:
        print("_No frames extracted._")

    print()
    print("## Transcript")
    print()
    if transcript_text:
        label = transcript_source or "captions"
        if focused:
            print(f"_Source: {label}. Filtered to {format_time(effective_start)} → {format_time(effective_end)}:_")
        else:
            print(f"_Source: {label}._")
        print()
        print("```")
        print(transcript_text)
        print("```")
    elif detail == "transcript":
        reason = asr_failure or "captions and ASR produced no verified transcript"
        print(
            f"_No verified transcript at transcript detail: {reason}. "
            "Re-run with `--detail balanced` for visual evidence._"
        )
    elif focused and dl.get("subtitle_path"):
        print(f"_No transcript lines fell inside {format_time(effective_start)} → {format_time(effective_end)}._")
    else:
        reason = asr_failure or "captions and ASR produced no verified transcript"
        print(
            f"_No verified transcript — proceed with frames only. Reason: {reason}. "
            "Do not infer spoken claims from visuals alone._"
        )

    print()
    print("---")
    print(f"_Work dir: `{work}` — retained for follow-ups and evidence readback._")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/bin/bash

set -euo pipefail

FFMPEG_BIN="/opt/homebrew/bin/ffmpeg"
WHISPER_BIN="/opt/homebrew/bin/whisper-cli"
WHISPER_MODEL="$HOME/Library/Caches/codex-local-asr/models/whisper-cpp/ggml-large-v3-turbo-q5_0.bin"

usage() {
  printf 'Usage: %s SOURCE START_SECONDS DURATION_SECONDS OUTPUT_DIR\n' "$0" >&2
}

die() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

[[ "$#" -eq 4 ]] || {
  usage
  exit 64
}

SOURCE="$1"
START_SECONDS="$2"
DURATION_SECONDS="$3"
OUTPUT_DIR="$4"

[[ -f "$SOURCE" && -r "$SOURCE" ]] || die "source is not readable: $SOURCE"
[[ "$START_SECONDS" =~ ^[0-9]+([.][0-9]+)?$ ]] \
  || die "START_SECONDS must be a non-negative number"
[[ "$DURATION_SECONDS" =~ ^[0-9]+([.][0-9]+)?$ ]] \
  || die "DURATION_SECONDS must be a positive number"
[[ ! "$DURATION_SECONDS" =~ ^0+([.]0+)?$ ]] \
  || die "DURATION_SECONDS must be greater than zero"
[[ -x "$FFMPEG_BIN" ]] || die "ffmpeg is not executable"
[[ -x "$WHISPER_BIN" ]] || die "whisper-cli is not executable"
[[ -r "$WHISPER_MODEL" ]] || die "Whisper model is not readable"

if [[ -e "$OUTPUT_DIR" && ! -d "$OUTPUT_DIR" ]]; then
  die "OUTPUT_DIR exists and is not a directory"
fi
mkdir -p -- "$OUTPUT_DIR"

SOURCE_NAME="$(basename -- "$SOURCE")"
SOURCE_STEM="${SOURCE_NAME%.*}"
START_TAG="${START_SECONDS//./_}"
DURATION_TAG="${DURATION_SECONDS//./_}"
RESULT_DIR="$OUTPUT_DIR/${SOURCE_STEM}__start-${START_TAG}s__duration-${DURATION_TAG}s"

mkdir -- "$RESULT_DIR" \
  || die "result exists; refusing to overwrite: $RESULT_DIR"

WAV_PATH="$RESULT_DIR/snippet_16k_mono.wav"
PREFIX="$RESULT_DIR/transcript_zh"
LOG_PATH="$RESULT_DIR/whisper.log"

"$FFMPEG_BIN" \
  -nostdin \
  -hide_banner \
  -loglevel error \
  -y \
  -ss "$START_SECONDS" \
  -t "$DURATION_SECONDS" \
  -i "$SOURCE" \
  -vn \
  -ac 1 \
  -ar 16000 \
  -c:a pcm_s16le \
  "$WAV_PATH"

"$WHISPER_BIN" \
  --model "$WHISPER_MODEL" \
  --no-gpu \
  --language zh \
  --threads 4 \
  --beam-size 3 \
  --file "$WAV_PATH" \
  --output-txt \
  --output-srt \
  --output-json-full \
  --output-file "$PREFIX" \
  > "$LOG_PATH" 2>&1

[[ -s "${PREFIX}.txt" && -s "${PREFIX}.srt" && -s "${PREFIX}.json" ]] \
  || die "Whisper did not produce all expected outputs"

shasum -a 256 "$SOURCE" > "$RESULT_DIR/source.sha256"
printf 'Result directory: %s\n' "$RESULT_DIR"

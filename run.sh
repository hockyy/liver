#!/usr/bin/env bash
# Interactive launcher: pick a project app to run from the repo root.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found in PATH." >&2
  exit 1
fi
PY=(python3)

# --- Per-app runners (paths are relative to ROOT) ---

run_liver() { exec "${PY[@]}" "$ROOT/liver/liver.py"; }
run_liver_launcher() { exec "${PY[@]}" "$ROOT/liver/launcher.py"; }
run_trayue() { exec "${PY[@]}" "$ROOT/trayue/trayue.py"; }
run_taika() { exec "${PY[@]}" "$ROOT/taika/taika.py"; }
run_subana() { exec "${PY[@]}" "$ROOT/subana/subana.py"; }
run_streaming() { exec "${PY[@]}" "$ROOT/streaming/streamer.py"; }
run_singgo() { exec "${PY[@]}" "$ROOT/singgo/singgo.py"; }
run_picyue() { exec "${PY[@]}" "$ROOT/picyue/picyue.py"; }
run_gozi() { exec "${PY[@]}" "$ROOT/gozi/gozi.py"; }
run_dialogue() { exec "${PY[@]}" "$ROOT/dialogue/dialogue.py"; }
run_clipper() { exec "${PY[@]}" "$ROOT/clipper/clipper.py"; }
run_clipper_web() { exec "${PY[@]}" "$ROOT/clipper/server.py"; }
run_webper() { exec "${PY[@]}" "$ROOT/webper/webper.py"; }
run_towebp_gui() { exec "${PY[@]}" "$ROOT/towebp/gui.py"; }
run_tomp4() { exec "${PY[@]}" "$ROOT/tomp4/tomp4.py"; }

run_towebp_cli() {
  read -r -p "Path to MOV file: " mov
  if [[ -z "$mov" || ! -f "$mov" ]]; then
    echo "File not found or empty path." >&2
    exit 1
  fi
  exec "${PY[@]}" "$ROOT/towebp/convert.py" "$mov"
}

run_srt_preprocessor() {
  read -r -p "Path to SRT file: " srt
  if [[ -z "$srt" || ! -f "$srt" ]]; then
    echo "File not found or empty path." >&2
    exit 1
  fi
  exec "${PY[@]}" "$ROOT/clipper/srt_preprocessor.py" "$srt"
}

run_typora_webp() {
  read -r -p "Path to image file: " img
  if [[ -z "$img" || ! -f "$img" ]]; then
    echo "File not found or empty path." >&2
    exit 1
  fi
  exec "${PY[@]}" "$ROOT/webper/typora_webp_converter.py" "$img"
}

run_typora_avif() {
  read -r -p "Path to image file: " img
  if [[ -z "$img" || ! -f "$img" ]]; then
    echo "File not found or empty path." >&2
    exit 1
  fi
  exec "${PY[@]}" "$ROOT/webper/typora_avif_converter.py" "$img"
}

run_chroma() {
  read -r -p "Path to PNG (subject with transparency): " png
  if [[ -z "$png" || ! -f "$png" ]]; then
    echo "File not found or empty path." >&2
    exit 1
  fi
  exec "${PY[@]}" -c 'import sys; sys.path.insert(0, sys.argv[1]); from chroma import find_best_background_color_optimized; find_best_background_color_optimized(sys.argv[2])' \
    "$ROOT/chroma" "$png"
}

# Descriptions: keep order in sync with case statement below.
print_menu() {
  cat <<'EOF'
Runnable apps (this repo)
-------------------------

  1) liver
     Subtitle Transcriber PRO — PyQt5 GUI to transcribe audio/video and produce subtitles.

  2) liver-launcher
     Same transcriber; interactive choice of PyQt5 vs CustomTkinter GUI (CustomTkinter needs a gui module if present).

  3) trayue
     SRT Translator — PyQt5 app to translate subtitle files (e.g. Cantonese to English) in a table.

  4) taika
     Chinese flashcards — load vocabulary from GitHub gists, flip cards and practice.

  5) subana
     Subana — extract and export subtitle/cue data from JSON files (GUI).

  6) streaming
     Streaming Tools Launcher — PyQt5 dashboard to launch configured streamer apps, Steam, and URLs (edit streamer_config.json for paths).

  7) singgo
     LRC Generator — PyQt5: paste lyrics, load audio, play with ffplay, stamp times, export LRC.

  8) picyue
     PaddleOCR GUI — load an image and draw detected text boxes (PaddleOCR + Tkinter).

  9) gozi
     Lyrics to Ruby HTML — Cantonese text to HTML ruby/furigana-style markup with live web preview (PyQt5 WebEngine).

 10) dialogue
     Interactive Dialogue Creator — terminal: alternating two-speaker lines for chat-style copy/paste.

 11) clipper
     Stream Clip Editor — PyQt5: 9:16 vertical preview, queue ffmpeg cuts from a video.

 12) clipper-web
     SRT Clip Preprocessor (web) — FastAPI app at http://localhost:8000; AI-assisted clip ideas from subtitles (needs API keys / .env).

 13) srt-preprocessor (CLI)
     Same AI pipeline as clipper-web, command-line: analyzes an SRT for clip-worthy segments (OpenRouter etc. via .env).

 14) webper
     WebPer — batch image converter to WebP/AVIF with optional GPU resize, drag-and-drop queue (PyQt5).

 15) towebp-gui
     MOV to animated WebP (or video) — PyQt5 GUI wrapping ffmpeg conversion options.

 16) towebp-cli (needs MOV path)
     MOV to animated WebP — CLI wrapper around ffmpeg (you will be asked for the MOV path).

 17) tomp4
     MKV to MP4 — Tkinter GUI: remux to MP4, list audio tracks, extract MP3, preview with pygame + ffmpeg.

 18) typora-webp (needs image path)
     Typora helper — converts one image to WebP (max size), prints file:// URL for Typora integration.

 19) typora-avif (needs image path)
     Typora helper — converts one image to AVIF, prints file:// URL for Typora integration.

 20) chroma (needs PNG path)
     Chroma key helper — suggests an optimal solid background color to key out behind a transparent PNG subject (CLI output).

EOF
}

echo "Project: $ROOT"
echo ""
print_menu

read -r -p "Enter number to run (or q to quit): " choice
choice="${choice//[[:space:]]/}"

case "$choice" in
  q|Q) echo "Cancelled."; exit 0 ;;
  1)  run_liver ;;
  2)  run_liver_launcher ;;
  3)  run_trayue ;;
  4)  run_taika ;;
  5)  run_subana ;;
  6)  run_streaming ;;
  7)  run_singgo ;;
  8)  run_picyue ;;
  9)  run_gozi ;;
  10) run_dialogue ;;
  11) run_clipper ;;
  12) run_clipper_web ;;
  13) run_srt_preprocessor ;;
  14) run_webper ;;
  15) run_towebp_gui ;;
  16) run_towebp_cli ;;
  17) run_tomp4 ;;
  18) run_typora_webp ;;
  19) run_typora_avif ;;
  20) run_chroma ;;
  *)
    echo "Invalid choice: $choice" >&2
    exit 1
    ;;
esac

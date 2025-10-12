#!/usr/bin/env bash
set -euo pipefail
VT=1
FB=/dev/fb1
DELAY="${SLIDE_INTERVAL:-8}"
IMG_DIR="/home/pi/pidisplay/images"

# Preferred order (put clock earlier if you want it more often)
PREFERRED=("clock.png" "btc.png" "news.png" "weather.png")

# Switch to the correct TTY once
chvt "$VT" || true

while true; do
  # Rebuild the list each cycle so new files appear without restart
  IMAGES=()
  for name in "${PREFERRED[@]}"; do
    path="$IMG_DIR/$name"
    [[ -f "$path" ]] && IMAGES+=("$path")
  done

  # Fallback: if none found, try any PNGs in the folder
  if [[ ${#IMAGES[@]} -eq 0 ]]; then
    mapfile -t found < <(find "$IMG_DIR" -maxdepth 1 -type f -name '*.png' | sort)
    IMAGES=("${found[@]}")
  fi

  for img in "${IMAGES[@]}"; do
    killall -q fbi || true
    fbi -T "$VT" -d "$FB" -a -noverbose "$img" >/dev/null 2>&1 || true
    sleep "$DELAY"
  done

  # Nothing to show? wait a bit
  [[ ${#IMAGES[@]} -eq 0 ]] && sleep 2
done

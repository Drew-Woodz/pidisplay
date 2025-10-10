#!/usr/bin/env bash
set -euo pipefail
VT=1
FB=/dev/fb1
DELAY="${SLIDE_INTERVAL:-8}"
IMG_DIR="/home/pi/pidisplay/images"

# choose the set you want to rotate
IMAGES=("$IMG_DIR/btc.png" "$IMG_DIR/news.png")

chvt "$VT" || true

while true; do
  for img in "${IMAGES[@]}"; do
    # if missing, skip quietly
    [[ -f "$img" ]] || continue
    # kill any previous viewer, then show this image
    killall -q fbi || true
    fbi -T "$VT" -d "$FB" -a -noverbose "$img" >/dev/null 2>&1 || true
    sleep "$DELAY"
  done
  # if nothing to show, avoid hot-spinning
  if [[ "${#IMAGES[@]}" -eq 0 ]]; then sleep 2; fi
done
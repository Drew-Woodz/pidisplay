#!/usr/bin/env bash
# run_slideshow.sh
set -euo pipefail

VT=1
FB=/dev/fb1
DELAY="${SLIDE_INTERVAL:-8}"
IMG_DIR="/home/pi/pidisplay/images"

PREFERRED=("clock.png" "btc.png" "news.png" "weather.png")

# only try chvt if root; as pi, skip
if [ "$(id -u)" -eq 0 ] && command -v chvt >/dev/null; then
  chvt 1 || true
fi

while true; do
  IMAGES=()
  for name in "${PREFERRED[@]}"; do
    p="$IMG_DIR/$name"
    [[ -f "$p" ]] && IMAGES+=("$p")
  done
  if [[ ${#IMAGES[@]} -eq 0 ]]; then
    mapfile -t IMAGES < <(find "$IMG_DIR" -maxdepth 1 -type f -name '*.png' | sort)
  fi

  if [[ ${#IMAGES[@]} -eq 0 ]]; then
    sleep 2
    continue
  fi

  for img in "${IMAGES[@]}"; do
    # only kill our own fbi
    pkill -u "$USER" -x fbi 2>/dev/null || true
    # draw one image and keep all chatter out of VT1
    fbi -T "$VT" -d "$FB" -a -noverbose -blend 1 "$img" 2>&1 | systemd-cat -t pidisplay-fbi
    sleep "$DELAY"
  done
done
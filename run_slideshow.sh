#!/usr/bin/env bash
# /home/pi/pidisplay/run_slideshow.sh
set -euo pipefail

VT=1
FB=/dev/fb1
DELAY="${SLIDE_INTERVAL:-8}"
PL=/home/pi/pidisplay/playlist

mkdir -p "$PL"
ln -sf ../images/clock.png   "$PL/clockA.png"
ln -sf ../images/clock.png   "$PL/clockB.png"
ln -sf ../images/btc.png     "$PL/btcA.png"
ln -sf ../images/btc.png     "$PL/btcB.png"
ln -sf ../images/news.png    "$PL/newsA.png"
ln -sf ../images/news.png    "$PL/newsB.png"
ln -sf ../images/weather.png "$PL/weatherA.png"
ln -sf ../images/weather.png "$PL/weatherB.png"

exec /usr/bin/fbi -T "$VT" -d "$FB" -a -noverbose -cachemem 0 -t "$DELAY" \
  "$PL/clockA.png" "$PL/clockB.png" \
  "$PL/btcA.png"   "$PL/btcB.png"   \
  "$PL/newsA.png"  "$PL/newsB.png"  \
  "$PL/weatherA.png" "$PL/weatherB.png"

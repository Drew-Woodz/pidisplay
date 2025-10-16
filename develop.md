
---

# Executive summary

* We **ditched SDL/Pygame** for display output (fbcon isn’t built in this OS) and instead:

  * **Render PNG cards** with Python (Pillow + requests + feedparser).
  * **Display them via `fbi`** onto `/dev/fb1` (the SPI LCD framebuffer).
* The LCD **driver path is fbtft** (`fb_ili9486` + `ads7846` touch) and works on **Raspberry Pi OS (Legacy, 32-bit) Lite** (Pi Imager shows “Bookworm (Legacy)”—that’s fine).
* We **installed the Waveshare overlay** (`waveshare35a.dtbo`) manually and configured `/boot/firmware/config.txt`.
* The slideshow is a **long-running loop** (`run_slideshow.sh`) under **systemd**; **no `fbi -t` restarts**. That fixed blinking/blanking.
* We added **atomic image writes** (temp → `os.replace`) to avoid half-drawn frames; optional `fsync()` for extra safety.
* Time drift was OS timezone/NTP—fixed with `timedatectl`.

---

# Final working architecture

**renderer**

* `render_cards.py` (Python 3.11 in `~/venv`): pulls data (BTC/News), draws 480×320 PNGs to `~/pidisplay/images/`.
* Atomic writes so the viewer never catches partial images.

**viewer**

* `run_slideshow.sh`: simple loop that shows one PNG at a time with `fbi` on **VT1** + **/dev/fb1**.
* A **systemd service** ties it to boot, switches to VT1, and kills any previous `fbi` per slide.

**scheduler (optional)**

* `picards.timer` calls `picards.service` every 5 min to refresh PNGs.

---

# OS & driver takeaway

* **OS image**: “Raspberry Pi OS (Legacy, 32-bit) Lite”. Even though it says Bookworm, it ships the **staging fbtft** modules we need.
* **Overlay**: The stock image doesn’t ship `waveshare35a.dtbo`. We **copied it from the Waveshare repo** and placed it under `/boot/firmware/overlays/`.
* **config.txt** on this OS lives at `/boot/firmware/config.txt`.

  * Enable SPI, disable KMS (comment it), and load the Waveshare overlay with rotation + BGR swap.

---

# Clean-room rebuild checklist (the “do these in order” plan)

1. **Flash + first boot**

* Use Pi Imager: Pi Zero 2 W → Raspberry Pi OS (Legacy, 32-bit) Lite. Enable SSH + Wi-Fi.
* Boot and SSH in.

2. **Baseline packages & Python env**

```bash
sudo apt update
sudo apt install -y git python3-venv fbi fonts-dejavu-core
python3 -m venv ~/venv
source ~/venv/bin/activate
pip install --upgrade pip
pip install Pillow requests feedparser
```

3. **LCD overlay install**

```bash
git clone https://github.com/waveshare/LCD-show ~/LCD-show
sudo mkdir -p /boot/firmware/overlays
sudo install -m 644 ~/LCD-show/waveshare35a-overlay.dtb /boot/firmware/overlays/waveshare35a.dtbo
```

4. **Edit `/boot/firmware/config.txt`** (append to the end)

```ini
[all]
dtparam=spi=on
#dtoverlay=vc4-kms-v3d      # disable KMS on this build
#dtoverlay=vc4-fkms-v3d     # (keep FKMS/KMS off for fbtft)
dtoverlay=waveshare35a,rotate=90,bgr=1,speed=60000000,fps=60
```

Reboot, then verify:

```bash
ls -l /dev/fb*
# expect /dev/fb0 and /dev/fb1

dmesg | egrep -i 'fbtft|ili9|ads7846|spi' | tail -n 100
# expect fb_ili9486 + ADS7846 lines and “graphics fb1: fb_ili9486…”
```

5. **Project repo**

```bash
git clone git@github.com:Drew-Woodz/pidisplay.git ~/pidisplay   # or HTTPS if no SSH yet
```

6. **Renderer (cards)**

* `~/pidisplay/render_cards.py` (we used the BTC + News version you have).
* **Atomic save** in `save()`:

```python
def save(img, name):
    path = os.path.join(OUT, name)
    tmpp = path + ".tmp"
    img.save(tmpp, format="PNG", optimize=True)
    # optional extra safety:
    # with open(tmpp, "rb") as f: os.fsync(f.fileno())
    os.replace(tmpp, path)
    return path
```

* Test:

```bash
source ~/venv/bin/activate
python ~/pidisplay/render_cards.py
ls -l ~/pidisplay/images
```

7. **Viewer loop (no slideshow mode, no restarts)**
   `~/pidisplay/run_slideshow.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
VT=1
FB=/dev/fb1
DELAY="${SLIDE_INTERVAL:-8}"
IMG_DIR="/home/pi/pidisplay/images"
IMAGES=("$IMG_DIR/btc.png" "$IMG_DIR/news.png")

chvt "$VT" || true

while true; do
  for img in "${IMAGES[@]}"; do
    [[ -f "$img" ]] || continue
    killall -q fbi || true
    fbi -T "$VT" -d "$FB" -a -noverbose "$img" >/dev/null 2>&1 || true
    sleep "$DELAY"
  done
  [[ "${#IMAGES[@]}" -gt 0 ]] || sleep 2
done
```

```bash
chmod +x ~/pidisplay/run_slideshow.sh
```

8. **Systemd service (attach to tty1)**
   `/etc/systemd/system/pidisplay.service`:

```ini
[Unit]
Description=Pi LCD Slideshow (looped fbi on fb1)
After=network-online.target getty@tty1.service
Wants=network-online.target
Conflicts=getty@tty1.service

[Service]
Type=simple
WorkingDirectory=/home/pi/pidisplay

# Attach to a real console
StandardInput=tty
TTYPath=/dev/tty1
TTYReset=yes
TTYVHangup=yes
TTYVTDisallocate=yes

Environment=SLIDE_INTERVAL=8
ExecStartPre=/usr/bin/chvt 1
ExecStartPre=-/usr/bin/killall fbi
ExecStart=/home/pi/pidisplay/run_slideshow.sh
ExecStop=-/usr/bin/killall fbi
KillMode=process
TimeoutStopSec=2s

Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
```

Enable it:

```bash
sudo systemctl daemon-reload
sudo systemctl disable --now getty@tty1.service
sudo systemctl enable --now pidisplay.service
systemctl status pidisplay.service --no-pager
```

9. **Auto-refresh cards (every 5 min)**
   `/etc/systemd/system/picards.service`:

```ini
[Unit]
Description=Render Pi dashboard cards

[Service]
Type=oneshot
User=pi
WorkingDirectory=/home/pi/pidisplay
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/pi/venv/bin/python /home/pi/pidisplay/render_cards.py
```

`/etc/systemd/system/picards.timer`:

```ini
[Unit]
Description=Update Pi dashboard cards every 5 minutes

[Timer]
OnBootSec=30s
OnUnitActiveSec=5min
Persistent=true

[Install]
WantedBy=timers.target
```

Enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now picards.timer
systemctl list-timers --all | grep picards
```

10. **Time + timezone (fix “tomorrow”)**

```bash
sudo timedatectl set-timezone America/Chicago
sudo timedatectl set-ntp true
sudo systemctl restart systemd-timesyncd
timedatectl
```

---

# Common pitfalls we hit (and how we solved them)

* **White/black screen (no `/dev/fb1`)**
  → KMS enabled / overlay missing. Fix: install `waveshare35a.dtbo`, disable KMS, set SPI on, add dtoverlay line.

* **Pygame fbcon “not available”**
  → SDL fbcon wasn’t built for this OS. Don’t fight it; just render PNGs and use `fbi`.

* **VS Code terminal pasting mangled here-docs**
  → Write files in `$HOME` first, then `sudo mv` into `/etc/systemd/system/`.

* **`fbi -t` blink/blank/flicker**
  → `fbi` exits after the slideshow, systemd restarts it constantly. Fix: a **single, long-running loop** that swaps images and kills `fbi` per slide.

* **Half-rendered/garbled images**
  → PNG being read while being written. Fix: **atomic write** via temp + `os.replace` (and optional `fsync()`).

* **Wrong time/“tomorrow”**
  → Timezone/NTP. Fix with `timedatectl` steps above.

* **Color off (BGR vs RGB)**
  → Add `bgr=1` in dtoverlay.

* **“Couldn’t get a file descriptor referring to the console.”**
  → `fbi` needs a TTY. Fix: attach unit to `TTYPath=/dev/tty1`, disable `getty@tty1`, `chvt 1` first.

---

# Validation checklist (after each rebuild)

* `ls -l /dev/fb*` → **fb0** + **fb1** present.
* `dmesg | egrep -i 'fb_ili9486|ADS7846'` → driver lines present.
* `sudo fbi -T 1 -d /dev/fb1 -a /usr/share/raspberrypi-artwork/raspberry-pi-logo.png` → renders a test image.
* `python ~/pidisplay/render_cards.py` → writes `btc.png` & `news.png`.
* `sudo systemctl enable --now pidisplay.service` → cards rotate.
* `timedatectl` → correct timezone and NTP active.

---

# Repo hygiene

Add a `.gitignore` to keep noise out:

```
# Python
__pycache__/
*.pyc
venv/

# Rendered assets
images/*.png
images/*.tmp

# VS Code server (if it ever appears)
.vscode-server/
```

Commit service/loop/render scripts to the repo; the unit files live in `/etc/systemd/system/` but you can keep canonical copies under `~/pidisplay/systemd/` and copy them during setup.

---

# Open items / polish

* **Slide change blink:** `fbi` clears the framebuffer; acceptable for MVP. For totally smooth swaps, replace `fbi` with a tiny Python framebuffer blitter (map `/dev/fb1`, draw pixels directly) or try `fbi -blend 1` if supported.
* **News robustness:** switch to the “robust fetch” version (explicit requests + fallbacks) when you’re ready; your crash looked like a transient OOM or feed hiccup mid-patch.
* **Run as `pi` (not root):** add `User=pi` to the service and `sudo usermod -aG video pi` so `pi` can open `/dev/fb1`. Currently we run without `User=` (root), which is fine for a dedicated appliance.
* **More cards:** weather (Open-Meteo), system stats, calendar (ICS), watchlist, etc. Each is just another function that returns a PNG.

---

# What I’ll turn this into

Turn this report into a **single idempotent install script** that:

* Backs up and edits `/boot/firmware/config.txt` safely (only once).
* Installs the overlay and packages.
* Creates venv + pip deps.
* Drops `render_cards.py` + `run_slideshow.sh`.
* Installs/enables the two systemd units.
* Sets timezone + NTP.
* Verifies `/dev/fb1` and prints a green “ready” banner.

That plus the `.gitignore` will make reflashes painless and reproducible—and gift-able.

---

## Development Log — Entry 2 (Recovery & Expansion)

### The Great Detour

We briefly broke everything.

During an attempt to integrate a weather card, multiple approaches for drawing and displaying images became mixed: `fbi`-based rendering, ad-hoc framebuffer writes, and partial service edits.
The result was a blank screen and an inconsistent update pipeline — `fbi` running without a proper VT, timers stepping on each other, and atomic saves disabled in places. We spent a few rounds chasing “maybe this will fix it” symptoms before recognizing the real problem: **two competing display mechanisms** coexisting.

### Diagnosis and Recovery

We halted, stripped the system down, and verified the intended behavior:

1. **Only one viewer** — `run_slideshow.sh` looping with `fbi` on `/dev/fb1` attached to VT1.
2. **Only one renderer** — Python scripts outputting complete PNGs atomically.
3. **One update mechanism per card** — independent `systemd` timers for each card type.
4. **Atomic image replacement** — always write to `.tmp` and `os.replace()`.

After cleaning stray units, re-enabling VT1, and restoring the atomic write pattern, the display returned to normal operation.
**Lesson learned:** don’t mix framebuffer writers. The viewer owns `/dev/fb1`; everything else just updates image files.

### New Components and Improvements

#### 1. Weather & Geo Integration

* Added a new **weather card** powered by **Open-Meteo**, fetching current conditions and a short-term forecast.
* Added a lightweight **geo-location step** using `ip-api.com` to determine coordinates, city, and timezone automatically.
* Weather updates now occur via a dedicated `weather-update.timer` (~10 min cadence).

#### 2. BTC, News, and Independent Schedules

* BTC updates every ~30 s.
* News refreshes every 2 min.
* Each card has its own `render_cards.py --only <type>` call managed by its own service/timer pair.
* This separation keeps data fresh without redrawing slow cards unnecessarily.

#### 3. Clock Card

* Implemented a minimal **clock card** (`render_clock.py`) showing local time and date.
* Refreshes every 15 s via `clock-update.timer`.
* Seconds removed for cleaner visuals (refresh granularity makes them redundant).
* Integrated into the slideshow rotation for constant time reference.

#### 4. Viewer Refinements

* `run_slideshow.sh` rebuilt as a **dynamic loop** that scans the `images/` directory and displays known cards in a preferred order:

  ```
  clock → btc → news → weather
  ```
* Automatically re-reads available PNGs each cycle; new cards appear without restarting the viewer.
* Added fallback behavior if no images exist (prevents runaway loop errors).

#### 5. Rendering Architecture Refactor

* `render_cards.py` restructured with explicit functions `render_btc()`, `render_news()`, and `render_weather()`.
* Added CLI argument `--only` for selective card generation.
* Restored consistent font handling (`DejaVuSans`) and color constants for visual parity.
* Added `is_stale()` timestamp check for data age labeling (“STALE” footer).

#### 6. Reliability & Process

* All services now run as **oneshot** jobs triggered by timers, fully decoupled from the viewer.
* Verified `tty1` ownership, confirmed that the slideshow runs continuously at boot, and ensured that no unit restarts interfere with display stability.
* Time sync validated (`timedatectl set-ntp true`) to keep timestamps consistent across cards.

### Current System Summary

| Component              | Role                           | Trigger        | Output                               |
| ---------------------- | ------------------------------ | -------------- | ------------------------------------ |
| `btc-update.timer`     | Fetch BTC price and render     | every 30 s     | `images/btc.png`                     |
| `news-update.timer`    | Fetch RSS headlines and render | every 2 min    | `images/news.png`                    |
| `weather-update.timer` | Geo + weather update           | every 10 min   | `images/weather.png`                 |
| `clock-update.timer`   | Render time/date card          | every 15 s     | `images/clock.png`                   |
| `pidisplay.service`    | Continuous viewer loop         | boot / restart | Displays rotating PNGs on `/dev/fb1` |

### Lessons Learned

* Keep **renderer logic and viewer logic isolated** — the viewer only shows finished PNGs.
* Always use **atomic image replacement** to prevent corruption mid-display.
* Don’t re-invent the framebuffer path — `fbi` is sufficient and reliable when used correctly.
* Version-control all systemd unit templates in the repo; install them into `/etc/systemd/system` with `sudo cp` to ensure reproducibility.
* Document and re-verify every timer after adding a new card — mismatched schedules are easy to miss.
* Never trust a confident “this should fix it” without validating the entire signal path: fetch → JSON → render → PNG → viewer.

---

## Development Log — Entry 3 (Weather Card – Fahrenheit Conversion)

**Summary:**
Converted the weather card and its data fetcher from Celsius to Fahrenheit display and data handling.

**Details:**

* Edited `fetch_weather.py` to request Fahrenheit directly from Open-Meteo using:
  `params["temperature_unit"] = "fahrenheit"`.
* Replaced all instances of `temp_c` with `temp_f` in both `fetch_weather.py` and `render_cards.py` to align with the new API field names.
* Updated label formatting in `render_weather()` to display `°F`.
* Regenerated weather data and verified correct Fahrenheit readings on the device display.

**Result:**
Weather card now pulls and renders temperature values in Fahrenheit with no intermediate conversion math. Functionality confirmed live on device.

---

### Master Plan Created

A comprehensive **Master Plan** document (`master_plan.md`) was created to define upcoming milestones and overall architecture.
No structural or code changes from that plan have been implemented yet — it currently serves only as the **roadmap reference** for future development and documentation updates.

---

## Development Log — Entry 3 (News pipeline + UI, clock polish)

**What changed (high level)**
We implemented a **real news ingestion pipeline** with per-source fetchers → a merged `state/news.json` → clustered rendering in `render_cards.py`. We also added the **clock card**, moved its timestamping logic out of the news card footer, and polished the viewer loop.

### News ingestion (fetchers)

* New directory: `pidisplay/fetch_news/`

  * `fetch_fox.py`, `fetch_breitbart.py` (RSS parsers writing into `~/pidisplay/state/news.json`)
* Each fetcher:

  * Normalizes items to a shared schema and **appends/updates** into `news.json`.
  * Keeps a rolling window (~200 items) and drops items older than 24h.
* **Systemd units** (oneshot) + **timers**:

  * `news-fox.service` / `news-fox.timer` (3 min)
  * `news-breitbart.service` / `news-breitbart.timer` (3 min)
  * `news-render.service` / `news-render.timer` (2 min; redraw card)

**`state/news.json` schema (current)**

```json
{
  "items": [
    {
      "id": "source-native-id-or-hash",
      "title": "Headline text",
      "source": "fox|breitbart|ap|...",
      "ts": "2025-10-12T03:40:03Z",
      "tags": ["breaking"]               // optional
    }
  ],
  "updated": "2025-10-12T03:40:03Z"
}
```

### News rendering (cards)

* `render_cards.py` now **reads** `state/news.json` (no site scraping here).
* Added `_norm_key()` + **`cluster_news()`** to group same/near-same headlines.

  * Near-duplicate merge via token **Jaccard similarity** (threshold ~0.85).
  * Cluster representative = newest item; exposes `count` for consensus `(×N)`.
* New **stacked-cell UI** (fits **5 cells** at 480×320):

  * Light **source-tinted background**, **1px border**, **2–3 px radius**.
  * **24×24 icon** at right (`~/pidisplay/icons/<source>.png`).
  * Headline in **dark text** (on light cells), 2 lines max with ellipsis.
  * Tiny `(×N)` badge when multiple sources carry the story.
  * Timestamp moved to **top-right under header** (muted, small).
* Source style map:

  * `SOURCE_STYLES = {"fox": {...}, "breitbart": {...}, "ap": {...}, "_default": {...}}`
  * Easy to extend by dropping an icon and adding a style entry.

### Clock card

* `render_clock.py` renders `images/clock.png` every **15 s** (no seconds displayed, by design).
* `clock-update.service` / `clock-update.timer` manage the schedule.
* Included in slideshow order with other PNGs.

### Viewer loop (unchanged behavior, tidier)

* `run_slideshow.sh` loops on VT1 over **`/dev/fb1`** via `fbi`.
* Preferred order: `clock → btc → news → weather` (auto-detects missing files).
* Still uses **atomic write** pattern everywhere to avoid tearing.

### Ops notes / guardrails

* **One writer rules the screen**: only the `fbi` viewer touches `/dev/fb1`; all other processes just write PNGs.
* **Atomic PNG writes**: always `.tmp` → `os.replace()`.
* **Timers are independent** to respect cadence:

  * BTC ~30s, News render 2m, Weather 10m, Clock 15s.
* **Icons**: put **24×24 PNGs** in `~/pidisplay/icons/` with lowercase names (`fox.png`, `breitbart.png`, …). Missing icons get a neutral placeholder box.

### Quick verification

```bash
# Timers present and scheduled:
systemctl list-timers --all | egrep 'news-fox|news-breitbart|news-render|btc-update|weather-update|clock-update'

# Kick first runs:
sudo systemctl start news-fox.service news-breitbart.service news-render.service
sudo systemctl start btc-update.service weather-update.service clock-update.service

# Check image mtimes advance:
watch -n 5 'ls -l --time-style=+"%H:%M:%S" ~/pidisplay/images/*.png'
```

### Known limits / deferred items

* **BREAKING** label is deferred (kept simple for now).
* No touch/scroll yet; the card shows the **top 5** clusters only.
* We still rely on public RSS; if sources rate-limit or 403, the fetchers back off and keep last data.

**Result:**
News headlines now flow reliably from multiple sources into a single, clear card with icons and soft source colors; duplicates are collapsed; cadence is decoupled; the viewer remains rock-solid. The clock card keeps time fresh between slower updates.

---

# Development Log — Entry 4 (Weather icons, RGB565 dithering, hourly badges)

## Executive summary

* Added a **layered weather icon system** (sun/moon base + condition layers) for the hero icon on the weather card.
* Introduced **tiny 20×20 condition badges** in the hourly strip (no sun/moon there to avoid clutter).
* Enriched weather fetch with **`is_day`** and wired **day/night base selection**.
* Improved LCD fidelity with **ordered dithering to RGB565** prior to PNG save (better gradients on the 16-bpp SPI panel).
* Bumped hero art to a tunable size (**`HERO_SZ`**, currently 96) for better legibility.
* Split icon caches to avoid collisions (**`_icon_cache`** vs **`_icon_cache_rgba`**).
* Cleaned up minor code drift (duplicate functions) and verified render loop.

---

## What changed

### 1) Layered weather hero icon (65–100 px)

**Where:** `render_cards.py → render_weather()`

**How it works**

* **Base**: `sun.png` if `is_day == 1`, otherwise `moon_full.png` (moon phases coming later).
* **Layers** (stacked in order):
  *Sky obstruction* → *precipitation* → *thunder*
  chosen from `weather/layers/` via `wc_to_layers(weathercode)`.
* Position near the big temp; size governed by `HERO_SZ` (we set 96).

**Assets (committed)**

```
icons/weather/base/
  sun.png
  moon_{new,first_quarter,third_quarter,full,waning_crescent,waning_gibbous,
        waxing_crescent,waxing_gibbous}.png

icons/weather/layers/
  few_clouds.png, scattered_clouds.png, overcast.png, fog.png
  drizzle.png, rain.png, snow.png, thunder.png
```

### 2) Hourly mini condition badges (20×20)

**Where:** `render_cards.py → render_weather()` within the hourly loop

* New **tiny layers** placed between the time label and temperature:

```
icons/weather/layers/tiny_layers/
  tiny_few_clouds.png, tiny_scattered_clouds.png, tiny_overcast.png, tiny_fog.png
  tiny_drizzle.png, tiny_rain.png, tiny_snow.png, tiny_thunder.png
```

* Mapping via `wc_to_tiny_layer(weathercode)`.
* If the hour is “clear” (code 0), we **omit** the tiny icon (keeps the row clean).

### 3) Data enrichment: `is_day`

**Where:** `fetch_weather.py`

* Request unchanged; we now capture `current_weather.is_day` and store it under `now.is_day`.
* Renderer uses this to select **sun vs moon** for the hero base.

### 4) Pre-dither to RGB565 (LCD quality)

**Where:** `render_cards.py`

* Added an ordered **Bayer 8×8** dither step that quantizes to **RGB565** before saving PNGs.
* Controlled by `DITHER_565 = True`.
* Result: noticeably smoother gradients and less posterization on the 16-bpp ILI9486 panel.

### 5) Hero size & layout polish

* Introduced `HERO_SZ` (currently **96**; try 88–100 to taste).
* Slight icon placement nudge so the glyph sits nicely by the temp.

### 6) Caching & small refactors

* **Separate caches**: `_icon_cache` (news/source icons) and `_icon_cache_rgba` (weather PNGs).
* Removed duplicate implementations:

  * Keep the **dithered `atomic_save()`** (delete the later non-dithered one).
  * Keep the **Jaccard-based `cluster_news()`** (delete the older grouping helper).

---

## Validation

1. **Weather fetch**

   ```
   /home/pi/venv/bin/python ~/pidisplay/fetch_weather.py
   jq . ~/pidisplay/state/weather.json | head
   ```

   Ensure `now.is_day` and `hourly[].weathercode` present.

2. **Render weather**

   ```
   /home/pi/venv/bin/python ~/pidisplay/render_cards.py --only weather
   fbi -T 1 -d /dev/fb1 -a ~/pidisplay/images/weather.png
   ```

3. **Quality check**

   * Inspect hero edges and gradients on the panel (moon/sun should look less “crunchy”).
   * Verify tiny icons appear only when conditions warrant (e.g., rain hour shows a drop).

---

## Notes & decisions

* We **do not** show base icons (sun/moon) in the hourly strip to prevent clutter.
* File structure is now stable; icons are **committed** to the repo (we exempt only rendered assets).
* The dithering is image-wide; no change is needed in `fbi` flags.

---

## Known limitations / next ideas

* **Moon phase base**: use Open-Meteo’s moon phase or another source to pick among the eight moon sprites.
* **Sunrise/Sunset line**: add right-aligned “Sunset 6:57 PM” / “Sunrise 5:54 AM” and flip based on current time.
* **Day/Night tint**: optional subtle background tint before sunset; back to black after.
* **Icon art iterations**: we can add 2–3 “position” variants (pre-sunrise/sunset) for a slow parallax-like progression.
* **Per-panel gamma**: optional LUT pass if we still want to fine-tune contrast.

---



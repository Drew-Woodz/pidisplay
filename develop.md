
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

Tomorrow we can turn this report into a **single idempotent install script** that:

* Backs up and edits `/boot/firmware/config.txt` safely (only once).
* Installs the overlay and packages.
* Creates venv + pip deps.
* Drops `render_cards.py` + `run_slideshow.sh`.
* Installs/enables the two systemd units.
* Sets timezone + NTP.
* Verifies `/dev/fb1` and prints a green “ready” banner.

That plus the `.gitignore` will make reflashes painless and reproducible—and gift-able.

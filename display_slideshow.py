#!/usr/bin/env python3
# display_slideshow.py
# Direct-framebuffer blitter with live config reload

import os
import glob
import time
import logging
import subprocess
from pathlib import Path
from config import load as load_config
import watchdog.events
import watchdog.observers

# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------
FB                = "/dev/fb1"
W, H              = 480, 320
EXPECTED_SIZE     = W * H * 2                     # 307200 bytes
IMAGE_DIR         = os.path.expanduser("~/pidisplay/images")
INTERVAL          = float(os.environ.get("SLIDE_INTERVAL", "8"))
CONFIG_PATH       = Path(os.path.expanduser("~/pidisplay/config.yaml"))

# ----------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

# ----------------------------------------------------------------------
# Global state (re-loaded on config change)
# ----------------------------------------------------------------------
CONFIG          = load_config()
config_changed  = False          # set by watchdog handler

# ----------------------------------------------------------------------
# Watchdog handler – reload config when config.yaml changes
# ----------------------------------------------------------------------
class ConfigHandler(watchdog.events.FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith("config.yaml"):
            global CONFIG, config_changed
            CONFIG = load_config()
            config_changed = True
            logging.info("Config reloaded – will re-render cards")

# ----------------------------------------------------------------------
# Blit a .raw file to the framebuffer
# ----------------------------------------------------------------------
def blit(raw_path: str):
    try:
        if os.path.getsize(raw_path) != EXPECTED_SIZE:
            raise ValueError(f"Size mismatch: {raw_path}")
        with open(raw_path, "rb") as src, open(FB, "r+b", buffering=0) as dst:
            dst.seek(0)
            dst.write(src.read())
        logging.info(f"Blitted {os.path.basename(raw_path)}")
    except Exception as e:
        logging.error(f"Blit failed for {raw_path}: {e}")

# ----------------------------------------------------------------------
# Main loop
# ----------------------------------------------------------------------
def main():
    # Start watchdog
    observer = watchdog.observers.Observer()
    observer.schedule(ConfigHandler(), path=str(CONFIG_PATH.parent), recursive=False)
    observer.start()
    logging.info("Watching config.yaml for changes")

    global config_changed

    while True:
        # ------------------------------------------------------------------
        # 1. Gather all .raw files that match enabled cards
        # ------------------------------------------------------------------
        all_raw = sorted(glob.glob(os.path.join(IMAGE_DIR, "*.raw")))
        enabled_cards = {c for c, on in CONFIG["cards"]["enabled"].items() if on}
        raw_files = [
            f for f in all_raw
            if os.path.basename(f).split(".")[0] in enabled_cards
        ]

        # ------------------------------------------------------------------
        # 2. If config changed, re-render everything
        # ------------------------------------------------------------------
        if config_changed:
            try:
                subprocess.run(
                    ["/home/pi/venv/bin/python", "/home/pi/pidisplay/render.py"],
                    check=True
                )
                logging.info("All cards re-rendered after config change")
            except Exception as e:
                logging.error(f"Re-render failed: {e}")
            config_changed = False

        # ------------------------------------------------------------------
        # 3. Show each enabled card
        # ------------------------------------------------------------------
        if not raw_files:
            logging.warning("No .raw files for enabled cards – sleeping")
            time.sleep(INTERVAL)
            continue

        for path in raw_files:
            blit(path)
            time.sleep(INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Stopped by user")
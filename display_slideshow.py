#!/usr/bin/env python3
# display_slideshow.py
# Direct-framebuffer blitter with live config reload

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
import glob
import time
import logging
import subprocess
from pathlib import Path
from config import load as load_config
import watchdog.events
import watchdog.observers
import queue
import threading  # Added for Thread
import input_handler  # New: Import the input module
from PIL import Image  # For composites
import numpy as np  # For fast RGB565 conversion
from cards import base  # Fixed import

# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------
FB                = "/dev/fb1"
W, H              = 480, 320
EXPECTED_SIZE     = W * H * 2                     # 307200 bytes
IMAGE_DIR         = os.path.expanduser("~/pidisplay/images")
DEFAULT_INTERVAL  = 8  # Fallback if no per-card interval
CONFIG_PATH       = Path(os.path.expanduser("~/pidisplay/config.yaml"))

MENU_ICON_NORMAL = os.path.join(base.ICON_DIR, "menu", "menu.png")
MENU_ICON_PRESSED = os.path.join(base.ICON_DIR, "menu", "menu_pressed.png")
MENU_ICON_SIZE = 24
MENU_ICON_POS = (4, 7)  # Top-left, centered in 38px header

# Pre-load icons at start for speed
normal_icon = None
pressed_icon = None
try:
    normal_icon = Image.open(MENU_ICON_NORMAL).convert("RGBA").resize((MENU_ICON_SIZE, MENU_ICON_SIZE), Image.Resampling.LANCZOS)
    logging.info(f"Pre-loaded normal icon: size {normal_icon.size}")
except Exception as e:
    logging.error(f"Pre-load normal icon failed: {e}")

try:
    pressed_icon = Image.open(MENU_ICON_PRESSED).convert("RGBA").resize((MENU_ICON_SIZE, MENU_ICON_SIZE), Image.Resampling.LANCZOS)
    logging.info(f"Pre-loaded pressed icon: size {pressed_icon.size}")
except Exception as e:
    logging.error(f"Pre-load pressed icon failed: {e}")

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

# Input queue from thread
event_queue = queue.Queue()

# Slideshow state
paused = False
menu_active = False
current_index = 0

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

def composite_blit(raw_path, card, pressed=False):
    """Composite menu button over card PNG, convert to RGB565, blit temp raw"""
    png_path = os.path.join(IMAGE_DIR, f"{card}.png")
    if not os.path.exists(png_path):
        logging.warning(f"No PNG for {card} - blitting raw without overlay")
        blit(raw_path)
        return

    logging.info(f"Starting composite for {card}, pressed={pressed}")
    img = Image.open(png_path).convert("RGB")
    icon = pressed_icon if pressed else normal_icon
    if icon:
        img.paste(icon, MENU_ICON_POS, icon)  # Alpha overlay
        logging.info("Pasted icon successfully")
    else:
        logging.warning("No icon available - skipping paste")

    # Fast RGB565 with numpy (no byteswap for LE Pi)
    pixels = np.array(img, dtype=np.uint16)
    r = (pixels[:, :, 0] >> 3) & 0x1F
    g = (pixels[:, :, 1] >> 2) & 0x3F
    b = (pixels[:, :, 2] >> 3) & 0x1F
    packed = (r << 11) | (g << 5) | b
    data = packed.astype(np.uint16).tobytes('C')  # C order, no swap

    temp_raw = os.path.join(IMAGE_DIR, "temp_overlay.raw")
    tmp_temp = temp_raw + ".tmp"
    with open(tmp_temp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_temp, temp_raw)  # Atomic save
    logging.info("Wrote temp raw atomically")
    blit(temp_raw)
    try:
        os.remove(temp_raw)
        logging.info("Removed temp raw")
    except Exception as e:
        logging.error(f"Failed to remove temp raw: {e}")

# ----------------------------------------------------------------------
# Handle unified input event
# ----------------------------------------------------------------------
def handle_input_event(event, current_index, raw_files):
    global paused, menu_active
    logging.info(f"Handling event: {event}")
    # Get current path/card for press effect
    path = raw_files[current_index] if raw_files else ''
    card = os.path.basename(path).split(".")[0] if path else ''

    # Menu tap check first
    if event['type'] == 'tap' and event['cal_y'] < 38 and event['cal_x'] < (4 + MENU_ICON_SIZE + 4):
        logging.info("Menu tap detected - starting press effect")
        composite_blit(path, card, pressed=True)
        time.sleep(0.2)  # Shorter for snappier feedback
        composite_blit(path, card, pressed=False)
        menu_active = not menu_active
        return current_index  # Skip nav

    if event['type'] in ['tap', 'swipe_left', 'swipe_right']:
        if event['type'] == 'swipe_left' or event['zone'] == 'left':
            current_index = (current_index - 1) % len(raw_files)
            composite_blit(raw_files[current_index], os.path.basename(raw_files[current_index]).split(".")[0])  # Use composite for nav too
            return current_index
        elif event['type'] == 'swipe_right' or event['zone'] == 'right':
            current_index = (current_index + 1) % len(raw_files)
            composite_blit(raw_files[current_index], os.path.basename(raw_files[current_index]).split(".")[0])
            return current_index
    elif event['type'] == 'long_press' and event['zone'] == 'center':
        paused = not paused
        logging.info(f"Slideshow {'paused' if paused else 'resumed'} on long-press")
    elif event['type'] == 'two_finger_tap':
        menu_active = True
        menu_path = os.path.join(IMAGE_DIR, "menu.raw")
        if os.path.exists(menu_path):
            blit(menu_path)
            logging.info("Displayed menu overlay")
            # Drain queue for interactions (e.g., tap zones in menu)
            while menu_active:
                while not event_queue.empty():
                    close_event = event_queue.get()
                    if close_event['type'] == 'tap':
                        menu_active = False
                        logging.info("Closed menu overlay")
                        blit(raw_files[current_index])  # Restore
                        break
                time.sleep(0.1)
    elif event['type'] in ['swipe_up', 'swipe_down']:
        logging.info(f"Vertical swipe detected: {event['type']} - Ready for scroll/menu use")
    return current_index

# ----------------------------------------------------------------------
# Main loop
# ----------------------------------------------------------------------
def main():
    # Start input thread
    input_thread = threading.Thread(target=input_handler.input_handler, args=(event_queue,))
    input_thread.daemon = True
    input_thread.start()

    # Start watchdog
    observer = watchdog.observers.Observer()
    observer.schedule(ConfigHandler(), path=str(CONFIG_PATH.parent), recursive=False)
    observer.start()
    logging.info("Watching config.yaml for changes")

    global config_changed, current_index, paused, menu_active

    while True:
        # Gather .raw files
        enabled_cards = {c for c, on in CONFIG["cards"]["enabled"].items() if on}
        raw_files = [
            os.path.join(IMAGE_DIR, card + ".raw")
            for card in CONFIG["cards"]["order"]
            if card in enabled_cards and os.path.exists(os.path.join(IMAGE_DIR, card + ".raw"))
        ]

        # Re-render if config changed
        if config_changed:
            try:
                subprocess.run(["/home/pi/venv/bin/python", "/home/pi/pidisplay/render.py"], check=True)
                logging.info("All cards re-rendered after config change")
            except Exception as e:
                logging.error(f"Re-render failed: {e}")
            config_changed = False

        if not raw_files:
            logging.warning("No .raw files for enabled cards – sleeping")
            time.sleep(DEFAULT_INTERVAL)
            continue

        # Process all queued events (drain fully)
        while not event_queue.empty():
            event = event_queue.get()
            current_index = handle_input_event(event, current_index, raw_files)

        # Show current card with per-card interval (skip if paused/menu)
        if paused or menu_active:
            time.sleep(0.1)  # Yield
            continue

        path = raw_files[current_index]
        card = os.path.basename(path).split(".")[0]
        composite_blit(path, card)  # Always overlay button
        interval = CONFIG["intervals"].get(card, DEFAULT_INTERVAL)
        time.sleep(interval)
        current_index = (current_index + 1) % len(raw_files)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Stopped by user")
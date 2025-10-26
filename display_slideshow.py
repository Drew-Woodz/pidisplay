#!/usr/bin/env python3
# display_slideshow.py
import os
import glob
import time
import logging
from PIL import Image
import struct

FB = "/dev/fb1"
W, H = 480, 320
IMAGE_DIR = os.path.expanduser("~/pidisplay/playlist")
INTERVAL = float(os.environ.get("SLIDE_INTERVAL", "8"))

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

def rgb_to_rgb565(img):
    """Convert RGB to BGR565 with boosted R/B precision for ILI9486."""
    img = img.convert("RGB").resize((W, H), Image.Resampling.BICUBIC)
    pixels = img.load()
    data = bytearray()
    for y in range(H):
        for x in range(W):
            r, g, b = pixels[x, y]
            # Boost R/B slightly, scale to 5/6 bits
            b5 = min(((b * 32 + 127) // 255), 31) & 0x1F  # 5 bits
            g6 = min(((g * 64 + 127) // 255), 63) & 0x3F  # 6 bits
            r5 = min(((r * 32 + 127) // 255), 31) & 0x1F  # 5 bits
            pixel = (b5 << 11) | (g6 << 5) | r5  # BGR565
            data.extend(struct.pack("<H", pixel))
    return data

def blit(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
        with open(FB, "r+b", buffering=0) as f:
            f.seek(0)
            f.write(data)
        logging.info(f"Blitted {path}")
    except Exception as e:
        logging.error(f"Failed to blit {path}: {e}")

def main():
    while True:
        files = sorted(glob.glob(os.path.join(IMAGE_DIR, "*.png")))  # Still .png for now
        if not files:
            logging.warning(f"No images in {IMAGE_DIR}")
            time.sleep(INTERVAL)
            continue
        for path in files:
            blit(path)
            time.sleep(INTERVAL)

if __name__ == "__main__":
    try:
      main()
    except KeyboardInterrupt:
        logging.info("Stopped by user")
    except Exception as e:
        logging.error(f"Viewer crashed: {e}")
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
RAW_FMT = "RGB;16"  # Try RGB;16 first, was BGR;16
IMAGE_DIR = os.path.expanduser("~/pidisplay/playlist")
INTERVAL = float(os.environ.get("SLIDE_INTERVAL", "8"))

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

def rgb_to_rgb565(img):
    """Convert RGB image to RGB565 bytes manually if RAW_FMT fails."""
    img = img.convert("RGB").resize((W, H), Image.Resampling.BICUBIC)
    pixels = img.load()
    data = bytearray()
    for y in range(H):
        for x in range(W):
            r, g, b = pixels[x, y]
            # RGB565: 5 bits R, 6 bits G, 5 bits B
            r = (r >> 3) & 0x1F
            g = (g >> 2) & 0x3F
            b = (b >> 3) & 0x1F
            pixel = (r << 11) | (g << 5) | b
            data.extend(struct.pack("<H", pixel))
    return data

def blit(path):
    try:
        img = Image.open(path)
        try:
            # Try Pillow's raw format first
            img = img.convert("RGB").resize((W, H), Image.Resampling.BICUBIC)
            data = img.tobytes("raw", RAW_FMT)
            logging.info(f"Blitted {path} with {RAW_FMT}")
        except ValueError as e:
            # Fallback to manual RGB565 conversion
            logging.warning(f"Pillow raw format failed: {e}, using manual RGB565")
            data = rgb_to_rgb565(img)
        with open(FB, "r+b", buffering=0) as f:
            f.seek(0)
            f.write(data)
        logging.info(f"Blitted {path}")
    except Exception as e:
        logging.error(f"Failed to blit {path}: {e}")

def main():
    while True:
        files = sorted(glob.glob(os.path.join(IMAGE_DIR, "*.png")))
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
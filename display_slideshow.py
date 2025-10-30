#!/usr/bin/env python3
# display_slideshow.py
import os
import glob
import time
import logging

FB = "/dev/fb1"
W, H = 480, 320
IMAGE_DIR = os.path.expanduser("~/pidisplay/images")  # ← RAW FILES HERE
INTERVAL = float(os.environ.get("SLIDE_INTERVAL", "8"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

def blit(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
        if len(data) != 480*320*2:
            logging.error(f"Bad size: {path} ({len(data)} bytes)")
            return
        with open(FB, "r+b", buffering=0) as f:
            f.seek(0)
            f.write(data)
        logging.info(f"Blitted {path}")
    except Exception as e:
        logging.error(f"Failed: {e}")

def main():
    while True:
        files = sorted(glob.glob(os.path.join(IMAGE_DIR, "*.raw")))
        if not files:
            time.sleep(INTERVAL)
            continue
        for path in files:
            blit(path)
            time.sleep(INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Stopped")
#!/usr/bin/env python3
# display_slideshow.py  (custom blitter – no fbi, no VT)

import os, glob, time, logging, struct

FB = "/dev/fb1"
W, H = 480, 320
EXPECTED_SIZE = W * H * 2          # 307200 bytes
IMAGE_DIR = os.path.expanduser("~/pidisplay/images")
INTERVAL = float(os.environ.get("SLIDE_INTERVAL", "8"))

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s: %(message)s")

def blit(raw_path):
    try:
        # sanity-check size
        if os.path.getsize(raw_path) != EXPECTED_SIZE:
            raise ValueError(f"Bad size {raw_path}")
        with open(raw_path, "rb") as src, open(FB, "r+b", buffering=0) as dst:
            dst.seek(0)
            dst.write(src.read())
        logging.info(f"Blitted {os.path.basename(raw_path)}")
    except Exception as e:
        logging.error(f"Blit failed {raw_path}: {e}")

def main():
    while True:
        raw_files = sorted(glob.glob(os.path.join(IMAGE_DIR, "*.raw")))
        if not raw_files:
            logging.warning("No .raw files – sleeping")
            time.sleep(INTERVAL)
            continue

        for p in raw_files:
            blit(p)
            time.sleep(INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Stopped by user")
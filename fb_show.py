#!/usr/bin/env python3

# fb_show.py
import sys, os
from PIL import Image

FB = "/dev/fb1"
W, H = 480, 320
# fb1 is 16bpp RGB565 little-endian on your panel
RAW_FMT = "BGR;16"   # if colors look swapped, change to "RGB;16"

def blit(path):
    img = Image.open(path).convert("RGB").resize((W, H), Image.BICUBIC)
    data = img.tobytes("raw", RAW_FMT)
    with open(FB, "r+b", buffering=0) as f:
        f.seek(0)
        f.write(data)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} image.png"); sys.exit(2)
    blit(sys.argv[1])

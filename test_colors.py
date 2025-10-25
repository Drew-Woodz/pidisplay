#!/usr/bin/env python3
from PIL import Image
import os

FB = "/dev/fb1"
W, H = 480, 320

def blit_color(r, g, b):
    img = Image.new("RGB", (W, H), (r, g, b))
    data = img.tobytes("raw", "RGBX")  # 24-bit for now, we'll convert manually
    with open(FB, "r+b", buffering=0) as f:
        f.seek(0)
        f.write(data)

if __name__ == "__main__":
    colors = [
        (12, 12, 12),   # Dark grey (header)
        (235, 235, 235), # Light grey (text)
        (0, 200, 255),  # Cyan accent
        (0, 255, 0),    # Green (BTC arrow)
    ]
    for r, g, b in colors:
        print(f"Blitting RGB({r},{g},{b})...")
        blit_color(r, g, b)
        input("Check color on screen, press Enter to continue...")
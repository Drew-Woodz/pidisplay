#!/usr/bin/env python3
# test_colors2.py — FULL COLOR WHEEL PROBE
import os
import struct

FB = "/dev/fb1"
W, H = 480, 320
FB_SIZE = W * H * 2  # 307200 bytes

def fill_screen(r, g, b):
    r5 = (r >> 3) & 0x1F
    g6 = (g >> 2) & 0x3F
    b5 = (b >> 3) & 0x1F
    pixel = (r5 << 11) | (g6 << 5) | b5  # RGB565
    data = struct.pack("<H", pixel) * (480*320)
    with open("/dev/fb1", "r+b") as f:
        f.write(data)

# === FULL COLOR WHEEL ===
colors = [
    (255,   0,   0, "Red"),
    (  0, 255,   0, "Green"),
    (  0,   0, 255, "Blue"),
    (255, 255,   0, "Yellow"),
    (255,   0, 255, "Magenta"),
    (  0, 255, 255, "Cyan"),
    (255, 255, 255, "White"),
    (  0,   0,   0, "Black"),
    (128, 128, 128, "Medium Grey"),
    ( 64,  64,  64, "Dark Grey"),
    (192, 192, 192, "Light Grey"),
    (255, 165,   0, "Orange"),
    (128,   0, 128, "Purple"),
    (  0, 128,   0, "Dark Green"),
    (139,   0, 139, "Dark Magenta"),
    ( 30, 144, 255, "Dodger Blue"),
    (255, 192, 203, "Pink"),
    ( 12,  12,  12, "Your Header BG"),
    (  0, 200, 255, "Your Accent"),
]

if __name__ == "__main__":
    print("ULTIMATE COLOR PROBE")
    print("Stop slideshow: sudo systemctl stop pidisplay")
    input("Press Enter when ready...")
    for r, g, b, name in colors:
        print(f"\n→ Sending RGB({r:3},{g:3},{b:3}) → Expect: {name}")
        fill_screen(r, g, b)
        input("  → What color do you see? Press Enter...")
    print("\nDone. Report back.")
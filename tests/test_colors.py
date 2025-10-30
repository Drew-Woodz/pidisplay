#!/usr/bin/env python3
# test_colors.py — RGB565/BGR565 probe
import os
import struct

FB = "/dev/fb1"
W, H = 480, 320
FB_SIZE = W * H * 2  # 307200 bytes

def fill_screen(r, g, b, invert=False, order='BGR'):
    """Fill /dev/fb1 with solid color using BGR565 or RGB565."""
    data = bytearray()
    # Scale 0-255 → 5/6/5 bits
    r5 = ((r * 31 + 127) // 255) & 0x1F
    g6 = ((g * 63 + 127) // 255) & 0x3F
    b5 = ((b * 31 + 127) // 255) & 0x1F

    # Optional inversion
    if invert:
        r5 = 31 - r5
        g6 = 63 - g6
        b5 = 31 - b5

    # Pack in BGR or RGB order
    if order == 'BGR':
        pixel = (b5 << 11) | (g6 << 5) | r5
    else:  # RGB
        pixel = (r5 << 11) | (g6 << 5) | b5

    # Repeat pixel for entire screen
    pixel_bytes = struct.pack("<H", pixel)
    data.extend(pixel_bytes * (W * H))

    # Write
    with open(FB, "r+b", buffering=0) as f:
        f.seek(0)
        f.write(data)

# === TEST MATRIX ===
tests = [
    # (R, G, B, invert, order, name)
    (255, 0, 0, False, 'BGR', "Red (BGR565)"),
    (0, 255, 0, False, 'BGR', "Green (BGR565)"),
    (0, 0, 255, False, 'BGR', "Blue (BGR565)"),
    (255, 255, 255, False, 'BGR', "White"),
    (0, 0, 0, False, 'BGR', "Black"),
    (12, 12, 12, False, 'BGR', "Dark Grey (header)"),
    # Try RGB order
    (255, 0, 0, False, 'RGB', "Red (RGB565)"),
    (0, 255, 0, False, 'RGB', "Green (RGB565)"),
    (0, 0, 255, False, 'RGB', "Blue (RGB565)"),
]

if __name__ == "__main__":
    print("COLOR PROBE STARTING")
    print("Stop slideshow: sudo systemctl stop pidisplay")
    input("Press Enter when ready...")
    for r, g, b, inv, ord, name in tests:
        print(f"\n→ {name}: RGB({r},{g},{b}) | invert={inv} | order={ord}")
        fill_screen(r, g, b, invert=inv, order=ord)
        input("  → What color do you see? Press Enter to continue...")
    print("Done.")
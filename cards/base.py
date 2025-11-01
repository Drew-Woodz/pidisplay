# ~/pidisplay/cards/base.py
from PIL import Image, ImageDraw, ImageFont
from config import load
import os

CONFIG = load()

W, H = 480, 320
OUT = os.path.expanduser("~/pidisplay/images")

# Colors
BG = tuple(CONFIG["colors"]["bg"])
FG = tuple(CONFIG["colors"]["fg"])
ACCENT = tuple(CONFIG["colors"]["accent"])
MUTED = tuple(CONFIG["colors"]["muted"])
DAY_BG = tuple(CONFIG["colors"]["day_bg"])

# Fonts
TIMESTAMP_FONT_SIZE = CONFIG["fonts"]["timestamp_size"]
HEADER_FONT_SIZE = CONFIG["fonts"]["header_size"]
BIG_TEMP_SIZE = CONFIG["fonts"]["big_temp_size"]

def font(size):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except:
        return ImageFont.load_default()

def text_size(d, txt, size):
    l, t, r, b = d.textbbox((0,0), txt, font=font(size))
    return r - l, b - t

def atomic_save(img, name):
    png_path = os.path.join(OUT, f"{name}.png")
    raw_path = os.path.join(OUT, f"{name}.raw")
    tmp_png = png_path + ".tmp"
    tmp_raw = raw_path + ".tmp"

    # PNG
    img.save(tmp_png, "PNG", optimize=True)
    os.replace(tmp_png, png_path)

    # RAW RGB565
    data = bytearray()
    pixels = img.convert("RGB").load()
    for y in range(H):
        for x in range(W):
            r, g, b = pixels[x, y]
            r5 = (r >> 3) & 0x1F
            g6 = (g >> 2) & 0x3F
            b5 = (b >> 3) & 0x1F
            pixel = (r5 << 11) | (g6 << 5) | b5
            data.extend(pixel.to_bytes(2, "little"))
    with open(tmp_raw, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_raw, raw_path)

    return png_path
#!/usr/bin/env python3
import os, datetime
from PIL import Image, ImageDraw, ImageFont

W, H = 480, 320
OUTDIR = os.path.join(os.path.dirname(__file__), "images")
os.makedirs(OUTDIR, exist_ok=True)
OUT = os.path.join(OUTDIR, "clock.png")
TMP = OUT + ".tmp"

def load_font(size):
    # DejaVuSans is present from fonts-dejavu-core
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()

def text_wh(draw, txt, font):
    # Pillow 10+ uses textbbox
    left, top, right, bottom = draw.textbbox((0, 0), txt, font=font)
    return right - left, bottom - top

def main():
    now = datetime.datetime.now()
    time_str = now.strftime("%-I:%M %p")  # 12-hour clock
    date_str = now.strftime("%a, %b %d %Y")

    img = Image.new("RGB", (W, H), (10, 10, 12))
    d = ImageDraw.Draw(img)

    font_big = load_font(64)
    font_small = load_font(28)

    tw, th = text_wh(d, time_str, font_big)
    dw, dh = text_wh(d, date_str, font_small)

    d.text(((W - tw) // 2, H // 2 - th - 8), time_str, fill=(240, 240, 240), font=font_big)
    d.text(((W - dw) // 2, H // 2 + 6), date_str, fill=(180, 180, 180), font=font_small)

    img.save(TMP, format="PNG", optimize=True)
    os.replace(TMP, OUT)

if __name__ == "__main__":
    main()
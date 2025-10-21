#!/usr/bin/env python3
# render_clock.py
import os, json
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

W, H = 480, 320
OUTDIR = os.path.join(os.path.dirname(__file__), "images")
os.makedirs(OUTDIR, exist_ok=True)
OUT = os.path.join(OUTDIR, "clock.png")
TMP = OUT + ".tmp"

def load_font(size: int):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()

def text_wh(draw: ImageDraw.ImageDraw, txt: str, fnt: ImageFont.FreeTypeFont):
    l, t, r, b = draw.textbbox((0, 0), txt, font=fnt)
    return r - l, b - t

def _health_summary(path=os.path.expanduser("~/pidisplay/state/health.json")):
    try:
        j = json.load(open(path))
        st = j.get("status", {})
        keys = ["pidisplay.service", "clock-update.timer", "weather-update.timer"]
        parts = []
        for k in keys:
            ok = (st.get(k, {}).get("ok") is True)
            short = k.split(".")[0].replace("-update","").replace("-render","")
            parts.append(f"{short}:{'✓' if ok else '✗'}")
        return " ".join(parts)
    except Exception:
        return ""

def main():
    now = datetime.now()
    time_str = now.strftime("%-I:%M %p") if "%" in "%-I" else now.strftime("%I:%M %p").lstrip("0")
    date_str = now.strftime("%a, %b %d %Y")

    img = Image.new("RGB", (W, H), (10, 10, 12))
    d = ImageDraw.Draw(img)

    font_big   = load_font(64)
    font_small = load_font(28)
    font_tiny  = load_font(14)

    tw, th = text_wh(d, time_str, font_big)
    dw, dh = text_wh(d, date_str, font_small)

    d.text(((W - tw) // 2, H // 2 - th - 8), time_str, fill=(240,240,240), font=font_big)
    d.text(((W - dw) // 2, H // 2 + 6),     date_str, fill=(180,180,180), font=font_small)

    # Draw footer BEFORE saving
    summary = _health_summary()
    if summary:
        d.text((12, H - 22), summary, fill=(150,150,150), font=font_tiny)

    # Atomic save
    img.save(TMP, format="PNG", optimize=True)
    os.replace(TMP, OUT)

if __name__ == "__main__":
    main()

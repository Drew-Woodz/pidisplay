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

    # ----- PNG (for VS Code) -----
        png_tmp = TMP + ".png"
        img.save(png_tmp, format="PNG", optimize=True)
        os.replace(png_tmp, OUT)          # OUT = …/clock.png

        # ----- RAW RGB565 -----
        raw_path = OUT.replace(".png", ".raw")
        raw_tmp  = raw_path + ".tmp"

        img_resized = img.convert("RGB").resize((W, H), Image.BICUBIC)
        if DITHER_565:
            img_resized = dither_to_rgb565(img_resized)

        data = bytearray()
        pixels = img_resized.load()
        for y in range(H):
            for x in range(W):
                r, g, b = pixels[x, y]
                r5 = (r >> 3) & 0x1F
                g6 = (g >> 2) & 0x3F
                b5 = (b >> 3) & 0x1F
                pixel = (r5 << 11) | (g6 << 5) | b5
                data.extend(struct.pack("<H", pixel))

        with open(raw_tmp, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(raw_tmp, raw_path)

if __name__ == "__main__":
    main()

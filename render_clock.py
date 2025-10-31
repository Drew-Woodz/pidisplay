#!/usr/bin/env python3
# render_clock.py
from render_cards import BG, FG, ACCENT
import os, json, struct  # <-- added struct
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# === CONFIG ===
W, H = 480, 320
DITHER_565 = False  # <-- # set False to disable

OUTDIR = os.path.join(os.path.dirname(__file__), "images")
os.makedirs(OUTDIR, exist_ok=True)
OUT = os.path.join(OUTDIR, "clock.png")
TMP = OUT + ".tmp"

# === DITHER FUNCTION (from render_cards.py) ===
_BAYER8 = [
    [0,32,8,40,2,34,10,42],
    [48,16,56,24,50,18,58,26],
    [12,44,4,36,14,46,6,38],
    [60,28,52,20,62,30,54,22],
    [3,35,11,43,1,33,9,41],
    [51,19,59,27,49,17,57,25],
    [15,47,7,39,13,45,5,37],
    [63,31,55,23,61,29,53,21],
]

def _quant_dither_8bit(val, levels, t):
    q = int(val * levels / 256 + t)
    q = max(0, min(q, levels - 1))
    return int(round(q * 255 / (levels - 1)))

def dither_to_rgb565(img_rgb):
    if img_rgb.mode != "RGB":
        img_rgb = img_rgb.convert("RGB")
    w, h = img_rgb.size
    src = img_rgb.load()
    out = Image.new("RGB", (w, h))
    dst = out.load()
    for y in range(h):
        row = _BAYER8[y & 7]
        for x in range(w):
            t = (row[x & 7] / 64.0) - 0.5
            r, g, b = src[x, y]
            r = _quant_dither_8bit(r, 32, t)
            g = _quant_dither_8bit(g, 64, t)
            b = _quant_dither_8bit(b, 32, t)
            dst[x, y] = (r, g, b)
    return out

# === UTILS ===
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
            parts.append(f"{short}:{'Check' if ok else 'Cross'}")
        return " ".join(parts)
    except Exception:
        return ""

# === MAIN ===
def main():
    now = datetime.now()
    time_str = now.strftime("%-I:%M %p") if "%-I" in now.strftime("%-I") else now.strftime("%I:%M %p").lstrip("0")
    date_str = now.strftime("%a, %b %d %Y")

    # --- Create base image ---
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # --- Fonts ---
    font_time = load_font(72)
    font_date = load_font(24)
    font_health = load_font(16)

    # --- Draw time ---
    tw, th = text_wh(draw, time_str, font_time)
    draw.text(((W - tw) // 2, 60), time_str, fill=(255,255,255), font=font_time)

    # --- Draw date ---
    dw, dh = text_wh(draw, date_str, font_date)
    draw.text(((W - dw) // 2, 160), date_str, fill=(235, 235, 235), font=font_date)

    # --- Draw health ---
    health = _health_summary()
    if health:
        hw, hh = text_wh(draw, health, font_health)
        draw.text(((W - hw) // 2, 220), health, fill=(235, 235, 235), font=font_health)

    # ----- PNG (for VS Code) -----
    png_tmp = TMP + ".png"
    img.save(png_tmp, format="PNG", optimize=True)
    os.replace(png_tmp, OUT)

    # ----- RAW RGB565 -----
    raw_path = OUT.replace(".png", ".raw")
    raw_tmp = raw_path + ".tmp"

    img_resized = img.resize((W, H), Image.BICUBIC)  # already correct size
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
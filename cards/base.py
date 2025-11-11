# ~/pidisplay/cards/base.py
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import os
import json
import logging

print("base.py is being imported")

W, H = 480, 320
OUT = os.path.expanduser("~/pidisplay/images")
ICON_DIR = os.path.expanduser("~/pidisplay/icons")

ICON_WEATHER_BASE   = os.path.join(ICON_DIR, "weather", "base")
ICON_WEATHER_LAYERS = os.path.join(ICON_DIR, "weather", "layers")
ICON_WEATHER_TINY   = os.path.join(ICON_DIR, "weather", "layers", "tiny_layers")

SOURCE_STYLES = {
    "fox":       {"bg": (230,240,255), "bd": (170,200,255), "icon": "fox.png"},
    "breitbart": {"bg": (255,240,225), "bd": (255,205,160), "icon": "breitbart.png"},
    "ap":        {"bg": (238,238,238), "bd": (210,210,210), "icon": "ap.png"},
    "_default":  {"bg": (228,232,236), "bd": (196,204,212), "icon": None},
}

# ----------------------------------------------------------------------
# LAZY CONFIG
# ----------------------------------------------------------------------
def get_config():
    """Lazy-load config on first use – avoids circular imports"""
    from config import load
    return load()

# ----------------------------------------------------------------------
# HELPERS (use get_config() inside each)
# ----------------------------------------------------------------------
def font(size):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except:
        return ImageFont.load_default()

def text_size(d, txt, size):
    l, t, r, b = d.textbbox((0,0), txt, font=font(size))
    return r - l, b - t

def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {}

def draw_header(d, title):
    cfg = get_config()
    BG = tuple(cfg["colors"]["bg"])
    FG = tuple(cfg["colors"]["fg"])
    sz = cfg["fonts"]["header_size"]
    d.rectangle([0, 0, W, 38], fill=BG)
    d.text((36, 8), title, fill=FG, font=font(sz)) # shifted text left to accomidate menu icon

def fmt_clock(time_str):
    if not time_str:
        return ""
    try:
        if 'T' in time_str:  # Handle ISO like 2025-11-10T06:08:00
            time_part = time_str.split('T')[1][:5]  # HH:MM
            t = datetime.strptime(time_part, "%H:%M")
        else:
           t = datetime.strptime(time_str, "%H:%M")
        try:
            t.strftime("%-I")
            fmt = "%-I:%M %p"
        except ValueError:
            fmt = "%I:%M %p"
        return t.strftime(fmt).lstrip("0")
    except:
        return time_str

def pick_moon_icon(phase):
    """phase: float in [0,1] where 0=new, 0.5=full"""
    try:
        p = float(phase)
    except:
        p = 0.0
    idx = int((p * 8.0) + 0.5) % 8
    icons = [
        "moon_new.png",
        "moon_waxing_crescent.png",
        "moon_first_quarter.png",
        "moon_waxing_gibbous.png",
        "moon_full.png",
        "moon_waning_gibbous.png",
        "moon_third_quarter.png",
        "moon_waning_crescent.png",
    ]
    return icons[idx]

def wc_to_layers(code: int):
    """Return (sky_layer, precip_layer, thunder_layer) filenames"""
    try:
        code = int(code)
    except:
        code = -1
      
    sky = precip = thunder = None
    if code in (1,):
        sky = "few_clouds.png"
    elif code in (2,):
        sky = "scattered_clouds.png"
    elif code in (3,):
        sky = "overcast.png"
    elif code in (45, 48):
        sky = "fog.png"

    if code in (51, 53, 55):
        precip = "drizzle.png"
    elif code in (61, 63, 65, 80, 81, 82):
        precip = "rain.png"
    elif code in (71, 73, 75):
        precip = "snow.png"

    if code in (95, 96, 99):
        thunder = "thunder.png"

    return sky, precip, thunder

def wc_to_tiny_layer(code: int):
    if code in (1,):
        return "tiny_few_clouds.png"
    if code in (2,):
        return "tiny_scattered_clouds.png"
    if code in (3,):
        return "tiny_overcast.png"
    if code in (45, 48):
        return "tiny_fog.png"
    if code in (51, 53, 55):
        return "tiny_drizzle.png"
    if code in (61, 63, 65, 80, 81, 82):
        return "tiny_rain.png"
    if code in (71, 73, 75):
        return "tiny_snow.png"
    if code in (95, 96, 99):
        return "tiny_thunder.png"
    return None

def load_rgba(path, size=None):
    print(f"Attempting to load: {path} (exists: {os.path.exists(path)})")
    try:
        im = Image.open(path).convert("RGBA")
        if size:
            im = im.resize(size, Image.Resampling.LANCZOS)
        return im
    except Exception as e:
        print(f"Load failed for {path}: {e}")
        return None

def load_icon(path, size):
    try:
        im = Image.open(path).convert("RGBA")
        return im.resize((size, size), Image.Resampling.LANCZOS)
    except:
        return None

_icon_cache = {}
def load_icon(path, size):
    key = (path, size)
    if key in _icon_cache:
        return _icon_cache[key]
    try:
        img = Image.open(path).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
    except Exception:
        # fallback: simple placeholder if no icon
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        dr.rectangle([0, 0, size-1, size-1], outline=(60, 60, 60), width=1)
    _icon_cache[key] = img
    return img

def wrap_text_px(d, text, fnt, max_w, max_lines=2):
    words = text.split()
    lines = []
    cur = []
    for word in words:
        test = " ".join(cur + [word])
        w, _ = text_size(d, test, fnt.size)
        if w <= max_w:
            cur.append(word)
        else:
            if cur:
                lines.append(" ".join(cur))
                cur = [word]
            else:
                lines.append(word)
                cur = []
        if len(lines) >= max_lines:
            break
    if cur:
        lines.append(" ".join(cur))
    if len(lines) > max_lines:
        lines[-1] = lines[-1][:-3] + "..."
    return lines

def get_source_style(src: str):
    return SOURCE_STYLES.get((src or "").lower(), SOURCE_STYLES["_default"])

def is_stale(ts_iso, max_age_sec=180):
    """Return True if ts_iso is older than max_age_sec. Accepts '...Z' or offset."""
    try:
        from datetime import timezone
        ts = (ts_iso or "").replace("Z", "+00:00")
        t = datetime.fromisoformat(ts)
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return (now - t).total_seconds() > max_age_sec
    except:
        return True

def atomic_save(img, name):
    png_path = os.path.join(OUT, f"{name}.png")
    raw_path = os.path.join(OUT, f"{name}.raw")
    tmp_png = png_path + ".tmp"
    tmp_raw = raw_path + ".tmp"

    img.save(tmp_png, "PNG", optimize=True)
    os.replace(tmp_png, png_path)

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
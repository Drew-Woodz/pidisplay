#!/usr/bin/env python3
# render_cards.py
# Render BTC / News / Weather cards to fixed PNG filenames atomically.
import os, io, math, time, textwrap, argparse, json, struct
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# ---------- Paths & constants ----------
OUT = os.path.expanduser("~/pidisplay/images")
os.makedirs(OUT, exist_ok=True)

W, H = 480, 320
BG = (12, 12, 12)
FG = (235, 235, 235)
ACCENT = (0, 200, 255)
MUTED = (150, 150, 150)

# ---- LCD quality: pre-dither to RGB565 (optional) ----
DITHER_565 = True  # set False to disable

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
    """Ordered dither to N levels (levels=32 or 64). t in [-0.5,0.5)."""
    # Map 0..255 → 0..levels-1 with a tiny threshold nudge
    q = int(val * levels / 256 + t)
    if q < 0: q = 0
    if q >= levels: q = levels - 1
    # Map back to 0..255
    return int(round(q * 255 / (levels - 1)))

def dither_to_rgb565(img_rgb):
    """Return an RGB image whose pixels are quantized to RGB565 with Bayer 8×8."""
    if img_rgb.mode != "RGB":
        img_rgb = img_rgb.convert("RGB")
    w, h = img_rgb.size
    src = img_rgb.load()
    out = Image.new("RGB", (w, h))
    dst = out.load()
    for y in range(h):
        row = _BAYER8[y & 7]
        for x in range(w):
            t = (row[x & 7] / 64.0) - 0.5  # [-0.5, 0.5)
            r, g, b = src[x, y]
            r = _quant_dither_8bit(r, 32, t)  # 5 bits
            g = _quant_dither_8bit(g, 64, t)  # 6 bits
            b = _quant_dither_8bit(b, 32, t)  # 5 bits
            dst[x, y] = (r, g, b)
    return out

def atomic_save(img: Image.Image, name: str):
    path = os.path.join(OUT, name)
    tmpp = path + ".tmp"
    
    img = img.convert("RGB").resize((480, 320), Image.Resampling.BICUBIC)
    rgb565 = Image.new("RGB", (480, 320))
    draw = ImageDraw.Draw(rgb565)
    pixels = img.load()
    
    for y in range(320):
        for x in range(480):
            r, g, b = pixels[x, y]
            r5 = (r >> 3) & 0x1F
            g6 = (g >> 2) & 0x3F
            b5 = (b >> 3) & 0x1F
            pixel = (r5 << 11) | (g6 << 5) | b5
            r8 = (r5 * 255) // 31
            g8 = (g6 * 255) // 63
            b8 = (b5 * 255) // 31
            draw.point((x, y), (r8, g8, b8))
    
    rgb565.save(tmpp, format="PNG", optimize=True)
    os.replace(tmpp, path)
    return path

# ---------- News cell style (icons + tints) ----------
ICON_DIR = os.path.expanduser("~/pidisplay/icons")

# per-source soft tints + border; add more as you add fetchers
SOURCE_STYLES = {
    "fox":       {"bg": (230,240,255), "bd": (170,200,255), "icon": "fox.png"},
    "breitbart": {"bg": (255,240,225), "bd": (255,205,160), "icon": "breitbart.png"},
    "ap":        {"bg": (238,238,238), "bd": (210,210,210), "icon": "ap.png"},
    "_default":  {"bg": (228,232,236), "bd": (196,204,212), "icon": None},
}

def get_source_style(src: str):
    return SOURCE_STYLES.get((src or "").lower(), SOURCE_STYLES["_default"])

_icon_cache = {}
def load_icon(path, size):
    key = (path, size)
    if key in _icon_cache:
        return _icon_cache[key]
    try:
        img = Image.open(path).convert("RGBA").resize((size,size), Image.LANCZOS)
    except Exception:
        # fallback: simple placeholder if no icon
        img = Image.new("RGBA", (size,size), (0,0,0,0))
        dr = ImageDraw.Draw(img)
        dr.rectangle([0,0,size-1,size-1], outline=(60,60,60), width=1)
    _icon_cache[key] = img
    return img

def wrap_text_px(draw, text, font, max_width_px, max_lines=2):
    """Greedy wrap to pixel width; returns up to max_lines lines."""
    words = (text or "").split()
    lines, cur = [], ""
    for w in words:
        test = w if not cur else (cur + " " + w)
        wpx = draw.textbbox((0,0), test, font=font)[2]
        if wpx <= max_width_px:
            cur = test
        else:
            if cur:
                lines.append(cur)
                if len(lines) == max_lines:
                    return lines
            cur = w
    if cur and len(lines) < max_lines:
        lines.append(cur)
    return lines

# ---------- Helpers ----------
def _norm_key(title):
    import re
    return " ".join(re.sub(r"[^a-z0-9 ]+"," ", (title or "").lower()).split())

def font(size: int):
    # DejaVuSans is present on Lite when fonts-dejavu-core is installed
    return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)

def load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None

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
    except Exception:
        return True

def draw_header(d, title: str):
    d.rectangle([0, 0, W, 38], fill=(20, 20, 20))
    d.text((12, 8), title, fill=FG, font=font(22))

# --- Weather icon helpers ---
ICON_WEATHER_BASE = os.path.expanduser("~/pidisplay/icons/weather/base")
ICON_WEATHER_LAYERS = os.path.expanduser("~/pidisplay/icons/weather/layers")
ICON_WEATHER_TINY = os.path.join(ICON_WEATHER_LAYERS, "tiny_layers")
HERO_SZ = 96  # try 84–100; bigger reads nicer on this panel

_icon_cache_rgba = {}
def load_rgba(path, size=None):
    key = (path, size)
    if key in _icon_cache_rgba:
        return _icon_cache_rgba[key]
    try:
        im = Image.open(path).convert("RGBA")
        if size:
            im = im.resize(size, Image.LANCZOS)
    except Exception:
        im = None
    _icon_cache_rgba[key] = im
    return im

def wc_to_layers(code: int):
    """Return (sky_layer, precip_layer, thunder_layer) filenames (no paths)."""
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
        # 80-82 are showers; we already show a sky layer if you want (scattered_clouds), but precip dominates.
    elif code in (71, 73, 75):
        precip = "snow.png"

    if code in (95, 96, 99):
        thunder = "thunder.png"

    return sky, precip, thunder

def wc_to_tiny_layer(code: int):
    """Return 20x20 tiny layer filename (no sun/moon), or None."""
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

def _parse_local(ts_str):
    """Parse 'YYYY-MM-DDTHH:MM' or ISO with offset/Z to a datetime (naive or aware)."""
    if not ts_str:
        return None
    ts = ts_str.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None

def _fmt_clock(ts_str):
    """Format to '6:57 PM' without leading zero; fallback '—'."""
    dt = _parse_local(ts_str)
    if not dt:
        return "—"
    try:
        return dt.strftime("%-I:%M %p")  # Linux
    except ValueError:
        return dt.strftime("%I:%M %p").lstrip("0")  # macOS/Windows fallback

def pick_moon_icon(phase):
    """
    phase: float in [0,1] where 0=new, 0.25=first quarter, 0.5=full, 0.75=third.
    Rule: round to nearest phase (your +50% rule).
    """
    try:
        p = float(phase)
    except Exception:
        p = 0.0
    idx = int((p * 8.0) + 0.5) % 8
    return MOON_ICONS[idx]

# ---------- Renderers ----------
# ---------- BTC 
def render_btc():
    data = load_json(os.path.expanduser("~/pidisplay/state/btc.json"))
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    draw_header(d, "BTC-USD")

    if not data or "price" not in data:
        d.text((16, 60), "No BTC data", fill=(255, 120, 120), font=font(36))
        d.text((16, H-30), "OFFLINE", fill=(255, 120, 120), font=font(18))
        return atomic_save(img, "btc.png")

    price = float(data.get("price", 0.0))
    chg   = data.get("chg_24h", None)
    ts    = data.get("ts", "")

    # Big price
    price_str = f"${price:,.0f}"
    d.text((16, 60), price_str, fill=FG, font=font(52))

    # Change
    if chg is not None:
        sign = "▲" if chg >= 0 else "▼"
        color = (60, 220, 100) if chg >= 0 else (255, 90, 90)
        d.text((18, 130), f"{sign} {chg:+.2f}% (24h)", fill=color, font=font(26))

    # Footer: updated time or STALE (BTC fetch cadence ~30s; tolerate 3 min)
    stale = is_stale(ts, max_age_sec=180)
    footer = "STALE" if stale else "Updated"
    d.text((16, H-30), f"{footer} {datetime.now().strftime('%b %d %I:%M %p')}", fill=MUTED, font=font(18))
    return atomic_save(img, "btc.png")

# ----------------- # Weather Card # state/weather.json # ---------------------
# Weather code mappings (Open-Meteo)
WCMAP = {
    0:"Clear",1:"Mainly clear",2:"Partly cloudy",3:"Overcast",
    45:"Fog",48:"Fog",51:"Drizzle",53:"Drizzle",55:"Drizzle",
    61:"Rain",63:"Rain",65:"Rain",71:"Snow",73:"Snow",75:"Snow",
    80:"Showers",81:"Showers",82:"Showers",95:"Thunder",96:"Thunder",99:"Thunder"
}

# Moon phase icon list
MOON_ICONS = [
    "moon_new.png",
    "moon_waxing_crescent.png",
    "moon_first_quarter.png",
    "moon_waxing_gibbous.png",
    "moon_full.png",
    "moon_waning_gibbous.png",
    "moon_third_quarter.png",
    "moon_waning_crescent.png",
]

# --- Hourly strip layout knobs ---
HOURLY_COL_W = 72       # column width
HOURLY_Y     = 180      # top of the hourly block ("Coming Up" sits at Y-24)
TIME_DY      = 0        # y-offset for the time label relative to HOURLY_Y
TEMP_DY      = 18       # y-offset for the temperature
POP_DY       = 38       # y-offset for precip %
ICON_SZ_TINY = 20       # 20x20 tiny weather icon
ICON_DX      = 36       # icon x offset from the column anchor (x)
ICON_DY      = 16       # icon y offset from HOURLY_Y (place near the temp line)


def render_weather():
    data = load_json(os.path.expanduser("~/pidisplay/state/weather.json"))
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    title = "Weather"
    if data and data.get("loc", {}).get("city"):
        title += f" • {data['loc']['city']}"
    draw_header(d, title)

    if not data or "now" not in data:
        d.text((16, 60), "No weather data", fill=(255, 120, 120), font=font(32))
        d.text((16, H-30), "OFFLINE", fill=(255, 120, 120), font=font(18))
        return atomic_save(img, "weather.png")

    noww = data["now"]
    astro = data.get("astronomy", {}) or {}
    temp = noww.get("temp_f")
    wc   = noww.get("weathercode")
    desc = WCMAP.get(int(wc) if wc is not None else -1, "—")
    is_day = int(noww.get("is_day") or 0)

    # === Header right-side blurb: Sunrise/Sunset ===
    # Open-Meteo daily times are in the requested timezone (we asked for tz),
    # so just format them. At night, prefer tomorrow's sunrise when present.
    sunset_str = _fmt_clock(astro.get("sunset"))
    sunrise_next_str = _fmt_clock(astro.get("sunrise_next") or astro.get("sunrise"))
    blurb = f"Sunset {sunset_str}" if is_day == 1 else f"Sunrise {sunrise_next_str}"
    # draw in top-right, under the title bar
    blurb_w = d.textbbox((0,0), blurb, font=font(16))[2]
    d.text((W - blurb_w - 12, 8), blurb, fill=MUTED, font=font(16))

    # === Big temp + description ===
    main = f"{int(round(temp))}°F" if isinstance(temp, (int, float)) else "—°"
    d.text((16, 60), main, fill=FG, font=font(56))
    d.text((16, 126), desc, fill=(180, 220, 255), font=font(26))

    # === Hero icon (base sun/moon + layers) ===
    if is_day == 1:
        base_name = "sun.png"
    else:
        phase = astro.get("moon_phase")
        base_name = pick_moon_icon(phase)

    base_im = load_rgba(os.path.join(ICON_WEATHER_BASE, base_name), size=(HERO_SZ, HERO_SZ))

    sky_name, precip_name, thunder_name = wc_to_layers(int(wc) if wc is not None else -1)
    sky_im     = load_rgba(os.path.join(ICON_WEATHER_LAYERS, sky_name), size=(HERO_SZ, HERO_SZ)) if sky_name else None
    precip_im  = load_rgba(os.path.join(ICON_WEATHER_LAYERS, precip_name), size=(HERO_SZ, HERO_SZ)) if precip_name else None
    thunder_im = load_rgba(os.path.join(ICON_WEATHER_LAYERS, thunder_name), size=(HERO_SZ, HERO_SZ)) if thunder_name else None

    icon_x, icon_y = 200, 56
    for layer in (base_im, sky_im, precip_im, thunder_im):
        if layer is not None:
            img.paste(layer, (icon_x, icon_y), layer)

    # Mini 6-hour strip
    from datetime import datetime, timedelta
    y = 180
    d.text((16, y-24), "Coming Up", fill=(180, 180, 180), font=font(18))

    hourly_list = (data.get("hourly", []) or [])
    # quick lookup by ISO hour key, e.g. "2025-10-13T18:00"
    hour_map = {h.get("time"): h for h in hourly_list}

    now = datetime.now()
    start = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)

    labels, keys = [], []
    t = start
    for _ in range(6):
        try:
            lbl = t.strftime("%-I %p")
        except ValueError:
            lbl = t.strftime("%I %p").lstrip("0")
        labels.append(lbl)
        keys.append(t.strftime("%Y-%m-%dT%H:00"))
        t += timedelta(hours=1)

    x = 16
    for lbl, key in zip(labels, keys):
        h  = hour_map.get(key, {}) or {}
        tf = h.get("temp_f")
        pp = h.get("pop")
        hwc = h.get("weathercode")

        # time label
    x = 16
    for lbl, key in zip(labels, keys):
        h   = hour_map.get(key, {}) or {}
        tf  = h.get("temp_f")
        pp  = h.get("pop")
        hwc = h.get("weathercode")

        # 1) fixed anchors (left-aligned columns)
        time_xy = (x, HOURLY_Y + TIME_DY)
        temp_xy = (x, HOURLY_Y + TEMP_DY)
        pop_xy  = (x, HOURLY_Y + POP_DY)

        # time (never moves)
        d.text(time_xy, lbl, fill=MUTED, font=font(16))

        # temperature (never moves)
        temp_txt = f"{int(round(tf))}°" if isinstance(tf, (int, float)) else "—°"
        d.text(temp_xy, temp_txt, fill=FG, font=font(20))

        # tiny icon (overlay; does NOT change text positions)
        tiny_name = wc_to_tiny_layer(int(hwc) if hwc is not None else -1)
        if tiny_name:
            tiny_im = load_rgba(os.path.join(ICON_WEATHER_TINY, tiny_name), size=(ICON_SZ_TINY, ICON_SZ_TINY))
            if tiny_im is not None:
                ix = x + ICON_DX
                iy = HOURLY_Y + ICON_DY
                img.paste(tiny_im, (ix, iy), tiny_im)

        # precip %
        if isinstance(pp, (int, float)):
            d.text(pop_xy, f"{int(pp)}%", fill=(140, 200, 255), font=font(14))
        else:
            d.text(pop_xy, "—", fill=(100, 120, 140), font=font(14))

        # advance to next column
        x += HOURLY_COL_W
        if x > W - 64:
            break


    # Footer time: STALE if older than 30 min
    stale = is_stale(data.get("updated", ""), max_age_sec=1800)
    footer = "STALE" if stale else "Updated"
    d.text((16, H-30), f"{footer} {datetime.now().strftime('%b %d %I:%M %p')}", fill=MUTED, font=font(18))
    return atomic_save(img, "weather.png")

# ---------- News: clustering from state/news.json ----------

def _similar(a: str, b: str, thresh=0.85):
    ta = set(_norm_key(a).split())
    tb = set(_norm_key(b).split())
    if not ta or not tb: return False
    j = len(ta & tb) / len(ta | tb)
    return j >= thresh

def cluster_news(items, top_n=5):
    groups = []
    for it in sorted(items, key=lambda x: x.get("ts",""), reverse=True):
        placed = False
        for g in groups:
            # compare to representative title of group[0]
            if _similar(it.get("title",""), g[0].get("title","")):
                g.append(it); placed = True; break
        if not placed:
            groups.append([it])

    reps = []
    for g in groups:
        rep = max(g, key=lambda it: it.get("ts",""))
        rep = dict(rep)
        rep["count"] = len(g)
        reps.append(rep)
    reps.sort(key=lambda it: it.get("ts",""), reverse=True)
    return reps[:top_n]

def render_news():
    # read merged feed from per-source fetchers
    state = load_json(os.path.expanduser("~/pidisplay/state/news.json")) or {}
    items = state.get("items", []) or []
    clusters = cluster_news(items, top_n=5) if items else []

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    draw_header(d, "Top Headlines")

    if not clusters:
        d.text((16, 60), "No news yet", fill=(200, 120, 120), font=font(28))
        d.text((16, 96), "Waiting for sources…", fill=MUTED, font=font(20))
        d.text((16, H-30), datetime.now().strftime("%b %d %I:%M %p"), fill=MUTED, font=font(18))
        return atomic_save(img, "news.png")

    # Layout constants to fit 5 cells comfortably
    TOP_MARGIN = 6
    CELL_H = 53
    GAP = 2
    L_MARGIN, R_MARGIN = 12, 12
    PAD = 8
    ICON_SZ = 24
    BORDER = 1
    HEAD_FONT = font(19)  # smaller, denser

    y = 38 + TOP_MARGIN  # below header

    for it in clusters:
        src = (it.get("source") or "").lower()
        title = (it.get("title") or "").strip()
        count = int(it.get("count", 1))

        style = get_source_style(src)
        bg, bd = style["bg"], style["bd"]

        # Cell rect
        x0, x1 = L_MARGIN, W - R_MARGIN
        y0, y1 = y, y + CELL_H

        # Cell background + 1px border (rounded corners for a tiny lift)
        try:
            d.rounded_rectangle([x0, y0, x1, y1], radius=4, fill=bg, outline=bd, width=BORDER)
        except Exception:
            # older Pillow without rounded_rectangle
            d.rectangle([x0, y0, x1, y1], fill=bg, outline=bd, width=BORDER)

        # Icon on right
        icon_x = x1 - PAD - ICON_SZ
        icon_y = y0 + (CELL_H - ICON_SZ)//2
        icon_name = style.get("icon")
        icon_path = os.path.join(ICON_DIR, icon_name) if icon_name else None
        if icon_path and os.path.exists(icon_path):
            ico = load_icon(icon_path, ICON_SZ)
            img.paste(ico, (icon_x, icon_y), ico)

        # Consensus badge (×N) near the icon if >1
        if count > 1:
            badge_text = f"×{count}"
            bt_w = d.textbbox((0,0), badge_text, font=font(14))[2]
            bx0 = icon_x - 6 - bt_w - 6
            by0 = y0 + 6
            bx1 = bx0 + bt_w + 12
            by1 = by0 + 18
            # slightly darker strip from bg for the badge
            badge_bg = tuple(max(0, c - 18) for c in bg)
            try:
                d.rounded_rectangle([bx0, by0, bx1, by1], radius=3, fill=badge_bg, outline=bd, width=1)
            except Exception:
                d.rectangle([bx0, by0, bx1, by1], fill=badge_bg, outline=bd, width=1)
            d.text((bx0 + 6, by0 + 2), badge_text, fill=(20,20,20), font=font(14))

        # Headline text (dark over light)
        text_x = x0 + PAD
        text_y = y0 + 8
        max_text_right = icon_x - 8  # leave a bit of breathing room
        max_w = max_text_right - text_x
        lines = wrap_text_px(d, title, HEAD_FONT, max_w, max_lines=2)
        for j, ln in enumerate(lines):
            d.text((text_x, text_y + j*22), ln, fill=(20,20,20), font=HEAD_FONT)

        y += CELL_H + GAP
        if y > H - 40:
            break

    # Top-right timestamp just under the header
    stamp = datetime.now().strftime("%b %d %I:%M %p")
    sw = d.textbbox((0, 0), stamp, font=font(16))[2]
    d.text((W - sw - 12, 10), stamp, fill=MUTED, font=font(16))

    return atomic_save(img, "news.png")

# ---------- CLI ----------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="*", default=[], help="subset: btc news weather")
    args = parser.parse_args()
    only = set(x.lower() for x in args.only)

    def want(name): return (not only) or (name in only)

    try:
        if want("btc"):
            render_btc()
    except Exception as e:
        print("btc render error:", e)

    try:
        if want("news"):
            render_news()
    except Exception as e:
        print("news render error:", e)

    try:
        if want("weather"):
            render_weather()
    except Exception as e:
        print("weather render error:", e)

    print("rendered cards")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# Render BTC / News / Weather cards to fixed PNG filenames atomically.
import os, io, math, time, textwrap, argparse, json
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

def cluster_news(items, top_n=5):
    groups = {}
    for it in items:
        k = _norm_key(it.get("title"))
        if not k:
            continue
        groups.setdefault(k, []).append(it)
    reps = []
    for k, group in groups.items():
        rep = max(group, key=lambda it: it.get("ts",""))
        rep = dict(rep)
        rep["count"] = len(group)
        reps.append(rep)
    reps.sort(key=lambda it: it.get("ts",""), reverse=True)
    return reps[:top_n]

def font(size: int):
    # DejaVuSans is present on Lite when fonts-dejavu-core is installed
    return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)

def atomic_save(img: Image.Image, name: str):
    path = os.path.join(OUT, name)
    tmpp = path + ".tmp"
    img.save(tmpp, format="PNG", optimize=True)
    os.replace(tmpp, path)
    return path

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
    temp = noww.get("temp_f")
    wc   = noww.get("weathercode")
    desc = WCMAP.get(int(wc) if wc is not None else -1, "—")
    is_day = int(noww.get("is_day") or 0)

    # Big temp + description
    main = f"{int(round(temp))}°F" if isinstance(temp, (int, float)) else "—°"
    d.text((16, 60), main, fill=FG, font=font(56))
    d.text((16, 126), desc, fill=(180, 220, 255), font=font(26))

    # --- Hero icon (≈65x65), stacked: base + sky + precip + thunder ---
    base_name = "sun.png" if is_day == 1 else "moon_full.png"  # v1: simple day/night
    base_im = load_rgba(os.path.join(ICON_WEATHER_BASE, base_name), size=(65, 65))

    sky_name, precip_name, thunder_name = wc_to_layers(int(wc) if wc is not None else -1)
    sky_im     = load_rgba(os.path.join(ICON_WEATHER_LAYERS, sky_name), size=(65, 65)) if sky_name else None
    precip_im  = load_rgba(os.path.join(ICON_WEATHER_LAYERS, precip_name), size=(65, 65)) if precip_name else None
    thunder_im = load_rgba(os.path.join(ICON_WEATHER_LAYERS, thunder_name), size=(65, 65)) if thunder_name else None

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
        d.text((x, y), lbl, fill=MUTED, font=font(16))

        # tiny condition badge (20x20) between label and temp
        tiny_name = wc_to_tiny_layer(int(hwc) if hwc is not None else -1)
        tiny_im = load_rgba(os.path.join(ICON_WEATHER_TINY, tiny_name), size=(20, 20)) if tiny_name else None

        tx = x  # temp x starts at label x; shift if we draw an icon
        if tiny_im is not None:
            img.paste(tiny_im, (x, y+1), tiny_im)
            tx = x + 24  # make room for the tiny icon

        # temperature
        d.text((tx, y+18), f"{int(round(tf))}°" if isinstance(tf, (int, float)) else "—°", fill=FG, font=font(20))

        # precip %
        if isinstance(pp, (int, float)):
            d.text((x, y+38), f"{int(pp)}%", fill=(140, 200, 255), font=font(14))
        else:
            d.text((x, y+38), "—", fill=(100, 120, 140), font=font(14))

        x += 72
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

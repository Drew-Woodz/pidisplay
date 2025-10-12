#!/usr/bin/env python3
# Render BTC / News / Weather cards to fixed PNG filenames atomically.
import os, io, math, time, textwrap, argparse, json
from datetime import datetime
import requests, feedparser
from PIL import Image, ImageDraw, ImageFont

# ---------- Paths & constants ----------
OUT = os.path.expanduser("~/pidisplay/images")
os.makedirs(OUT, exist_ok=True)

W, H = 480, 320
BG = (12, 12, 12)
FG = (235, 235, 235)
ACCENT = (0, 200, 255)
MUTED = (150, 150, 150)

# ---------- Helpers ----------
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

# ---------- Renderers ----------
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
    temp = noww.get("temp_c")
    wc   = noww.get("weathercode")
    desc = WCMAP.get(int(wc) if wc is not None else -1, "—")

    # Big temp + description
    main = f"{int(round(temp))}°C" if temp is not None else "—°"
    d.text((16, 60), main, fill=FG, font=font(56))
    d.text((16, 126), desc, fill=(180, 220, 255), font=font(26))

    # Mini 6-hour strip
    y = 180
    d.text((16, y-24), "Next hours", fill=(180, 180, 180), font=font(18))
    hourly = (data.get("hourly", []) or [])[:6]
    x = 16
    for h in hourly:
        label = (h.get("time", "--")[11:16])  # HH:MM
        t = h.get("temp_c")
        pop = h.get("pop")
        d.text((x, y), label, fill=MUTED, font=font(16))
        d.text((x, y+18), f"{int(round(t))}°" if t is not None else "—°", fill=FG, font=font(20))
        if pop is not None:
            d.text((x, y+38), f"{int(pop)}%", fill=(140, 200, 255), font=font(14))
        x += 72
        if x > W - 64:
            break

    # Footer time: STALE if older than 30 min
    stale = is_stale(data.get("updated", ""), max_age_sec=1800)
    footer = "STALE" if stale else "Updated"
    d.text((16, H-30), f"{footer} {datetime.now().strftime('%b %d %I:%M %p')}", fill=MUTED, font=font(18))
    return atomic_save(img, "weather.png")

def render_news():
    # Fetch Reuters top RSS
    titles = []
    try:
        feed = feedparser.parse("https://feeds.reuters.com/reuters/topNews")
        for e in feed.entries[:5]:
            titles.append(e.title.strip())
    except Exception:
        titles = ["(news fetch failed)"]

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    draw_header(d, "Top Headlines")

    y = 52
    for i, t in enumerate(titles):
        wrapped = textwrap.wrap(t, width=40)
        bullet = f"{i+1}."
        d.text((16, y), bullet, fill=ACCENT, font=font(22))
        bx = 16 + 28
        for j, line in enumerate(wrapped[:2]):  # max 2 lines per headline
            d.text((bx, y + j*26), line, fill=FG, font=font(22))
        y += 58
        if y > H - 40:
            break

    d.text((16, H-30), datetime.now().strftime("%b %d %I:%M %p"), fill=MUTED, font=font(18))
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

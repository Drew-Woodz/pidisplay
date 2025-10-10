import os, io, math, time, textwrap
from datetime import datetime
import requests, feedparser
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.expanduser("~/pidisplay/images")
os.makedirs(OUT, exist_ok=True)

W, H = 480, 320
BG = (12, 12, 12)
FG = (235, 235, 235)
ACCENT = (0, 200, 255)
MUTED = (150,150,150)

# pick a font available on lite
def font(size): return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)

def draw_header(d, title):
    d.rectangle([0,0,W,38], fill=(20,20,20))
    d.text((12,8), title, fill=FG, font=font(22))

def save(img, name):
    path = os.path.join(OUT, name)
    tmpp = path + ".tmp"
    img.save(tmpp, format="PNG", optimize=True)
    os.replace(tmpp, path)
    return path

def render_btc():
    # Fetch BTC price
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price", params={"ids":"bitcoin","vs_currencies":"usd","include_24hr_change":"true"}, timeout=8)
        r.raise_for_status()
        data = r.json()["bitcoin"]
        price = float(data["usd"])
        chg = float(data.get("usd_24h_change", 0.0))
    except Exception as e:
        price, chg = float('nan'), float('nan')

    img = Image.new("RGB",(W,H),BG)
    d = ImageDraw.Draw(img)
    draw_header(d,"BTC-USD")

    # Big price
    price_str = "—" if math.isnan(price) else f"${price:,.0f}"
    d.text((16,60), price_str, fill=FG, font=font(52))

    # Change
    if not math.isnan(chg):
        sign = "▲" if chg>=0 else "▼"
        color = (60,220,100) if chg>=0 else (255,90,90)
        d.text((18,130), f"{sign} {chg:+.2f}% (24h)", fill=color, font=font(26))

    # Timestamp
    d.text((16, H-30), datetime.now().strftime("%b %d %I:%M %p"), fill=MUTED, font=font(18))

    return save(img,"btc.png")

def render_news():
    # Fetch Reuters top RSS
    titles = []
    try:
        feed = feedparser.parse("https://feeds.reuters.com/reuters/topNews")
        for e in feed.entries[:5]:
            titles.append(e.title.strip())
    except Exception:
        titles = ["(news fetch failed)"]

    img = Image.new("RGB",(W,H),BG)
    d = ImageDraw.Draw(img)
    draw_header(d,"Top Headlines")

    y = 52
    for i, t in enumerate(titles):
        wrapped = textwrap.wrap(t, width=40)
        bullet = f"{i+1}."
        d.text((16,y), bullet, fill=ACCENT, font=font(22))
        bx = 16 + 28
        for j, line in enumerate(wrapped[:2]):  # max 2 lines per headline
            d.text((bx, y + j*26), line, fill=FG, font=font(22))
        y += 58
        if y > H-40: break

    d.text((16, H-30), datetime.now().strftime("%b %d %I:%M %p"), fill=MUTED, font=font(18))
    return save(img,"news.png")

if __name__ == "__main__":
    p1 = render_btc()
    p2 = render_news()
    print("wrote", p1, "and", p2)
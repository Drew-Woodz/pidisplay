# ~/pidisplay/cards/btc.py
from .base import *
import json
from datetime import datetime

def render():
    cfg = get_config()
    try:
        data = json.load(open(os.path.expanduser("~/pidisplay/state/btc.json")))
    except:
        data = {}

    img = Image.new("RGB", (W, H), tuple(cfg["colors"]["bg"]))
    d = ImageDraw.Draw(img)

    draw_header(d, "Bitcoin")

    price: float = data.get("price", 0)
    price_str = f"${price:,.0f}" if isinstance(price, (int, float)) else "—"
    pw, _ = text_size(d, price_str, cfg["fonts"]["btc_price_size"])
    d.text(((W - pw) // 2, 60), price_str, fill=tuple(cfg["colors"]["accent"]), font=font(cfg["fonts"]["btc_price_size"]))

    change = data.get("change_24h")
    if isinstance(change, (int, float)):
        sign = "+" if change >= 0 else ""
        change_str = f"{sign}{change:.2f}%"
        color = (100, 255, 100) if change >= 0 else (255, 100, 100)
    else:
        change_str = "—"
        color = tuple(cfg["colors"]["muted"])
    cw, _ = text_size(d, change_str, cfg["fonts"]["btc_change_size"])
    d.text(((W - cw) // 2, 140), change_str, fill=color, font=font(cfg["fonts"]["btc_change_size"]))

    stamp = datetime.now().strftime("%b %d %I:%M %p")
    sw, _ = text_size(d, stamp, cfg["fonts"]["timestamp_size"])
    d.text((W - sw - cfg["padding"]["timestamp_x"], cfg["padding"]["timestamp_y"]),
           stamp, fill=tuple(cfg["colors"]["time_stamp"]), font=font(cfg["fonts"]["timestamp_size"]))

    return atomic_save(img, "btc")
# ~/pidisplay/cards/clock.py
from .base import *
from datetime import datetime

def render():
    cfg = get_config()
    img = Image.new("RGB", (W, H), tuple(cfg["colors"]["bg"]))
    d = ImageDraw.Draw(img)

    now = datetime.now()
    time_str = now.strftime("%-I:%M %p") if "%-I" in now.strftime("%-I") else now.strftime("%I:%M %p").lstrip("0")
    date_str = now.strftime("%a, %b %d %Y")

    tw, _ = text_size(d, time_str, cfg["fonts"]["clock_time_size"])
    d.text(((W - tw) // 2, 60), time_str, fill=tuple(cfg["colors"]["accent"]), font=font(cfg["fonts"]["clock_time_size"]))

    dw, _ = text_size(d, date_str, cfg["fonts"]["clock_date_size"])
    d.text(((W - dw) // 2, 160), date_str, fill=tuple(cfg["colors"]["fg"]), font=font(cfg["fonts"]["clock_date_size"]))

    return atomic_save(img, "clock")
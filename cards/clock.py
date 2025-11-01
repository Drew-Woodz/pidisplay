# ~/pidisplay/cards/clock.py
from .base import *
from datetime import datetime

def render():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    now = datetime.now()
    time_str = now.strftime("%-I:%M %p") if "%-I" in now.strftime("%-I") else now.strftime("%I:%M %p").lstrip("0")
    date_str = now.strftime("%a, %b %d %Y")

    # Time
    tw, _ = text_size(d, time_str, 92)
    d.text(((W - tw) // 2, 60), time_str, fill=ACCENT, font=font(92))

    # Date
    dw, _ = text_size(d, date_str, 36)
    d.text(((W - dw) // 2, 160), date_str, fill=FG, font=font(36))

    return atomic_save(img, "clock")

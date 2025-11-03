# ~/pidisplay/cards/news.py
from .base import *
import json
from datetime import datetime

def render():
    cfg = get_config()
    data = load_json(os.path.expanduser("~/pidisplay/state/news.json"))
    img = Image.new("RGB", (W, H), tuple(cfg["colors"]["bg"]))
    d = ImageDraw.Draw(img)

    title = "News"
    if data and data.get("loc", {}).get("city"):
        title += f" • {data['loc']['city']}"
    draw_header(d, title)

    if not data or "clusters" not in data:
        d.text((16, 60), "No news data", fill=(255, 120, 120), font=font(32))
        d.text((16, H-30), "OFFLINE", fill=(255, 120, 120), font=font(18))
        return atomic_save(img, "news")

    clusters = data["clusters"]

    # === Top-right timestamp ===
    stamp = datetime.now().strftime("%b %d %I:%M %p")
    sw, _ = text_size(d, stamp, TIMESTAMP_FONT_SIZE)
    d.text(
        (W - sw - cfg["padding"]["timestamp_x"], cfg["padding"]["timestamp_y"]),
        stamp,
        fill=tuple(cfg["colors"]["time_stamp"]),
        font=font(cfg["fonts"]["timestamp_size"])
    )

    y = 38 + 6  # below header
    for cluster in clusters:
        src = (cluster.get("source") or "").lower()
        title = (cluster.get("title") or "").strip()
        count = int(cluster.get("count", 1))

        style = get_source_style(src)
        bg, bd = style["bg"], style["bd"]

        # Cell
        x0, x1 = 12, W - 12
        y0, y1 = y, y + 53
        try:
            d.rounded_rectangle([x0, y0, x1, y1], radius=4, fill=bg, outline=bd, width=1)
        except:
            d.rectangle([x0, y0, x1, y1], fill=bg, outline=bd, width=1)

        # Icon
        icon_x = x1 - 8 - 24
        icon_y = y0 + (53 - 24)//2
        icon_name = style.get("icon")
        if icon_name:
            icon_path = os.path.join(ICON_DIR, icon_name)
            if os.path.exists(icon_path):
                ico = load_icon(icon_path, 24)
                img.paste(ico, (icon_x, icon_y), ico)

        # Badge
        if count > 1:
            badge = f"×{count}"
            bw = d.textbbox((0,0), badge, font=font(14))[2]
            bx0 = icon_x - 6 - bw - 6
            d.rounded_rectangle([bx0, y0 + 6, bx0 + bw + 12, y0 + 24], radius=3, fill=(max(0, bg[0]-18), max(0, bg[1]-18), max(0, bg[2]-18)))
            d.text((bx0 + 6, y0 + 6), badge, fill=(20,20,20), font=font(14))

        # Title
        lines = wrap_text_px(d, title, font(19), icon_x - 8 - 12, max_lines=2)
        for i, line in enumerate(lines):
            d.text((12 + 8, y0 + 8 + i*22), line, fill=(20,20,20), font=font(19))

        y += 53 + 2
        if y > H - 40:
            break

    return atomic_save(img, "news")
# ~/pidisplay/cards/weather.py
from .base import *
from datetime import datetime, timedelta
import json

# Weather code mappings (Open-Meteo)
WCMAP = {
    0:"Clear",1:"Mainly clear",2:"Partly cloudy",3:"Overcast",
    45:"Fog",48:"Fog",51:"Drizzle",53:"Drizzle",55:"Drizzle",
    61:"Rain",63:"Rain",65:"Rain",71:"Snow",73:"Snow",75:"Snow",
    80:"Showers",81:"Showers",82:"Showers",95:"Thunder",96:"Thunder",99:"Thunder"
}

def render():
    cfg = get_config()
    data = load_json(os.path.expanduser("~/pidisplay/state/weather.json"))

    if not data or "now" not in data:
        img = Image.new("RGB", (W, H), tuple(cfg["colors"]["bg"]))
        d = ImageDraw.Draw(img)
        d.text((16, 60), "No weather data", fill=(255, 120, 120), font=font(32))
        d.text((16, H-30), "OFFLINE", fill=(255, 120, 120), font=font(18))
        return atomic_save(img, "weather")

    noww = data["now"]
    is_day = int(noww.get("is_day", 1))
    img = Image.new("RGB", (W, H), tuple(cfg["colors"]["day_bg"]) if is_day else tuple(cfg["colors"]["bg"]))
    d = ImageDraw.Draw(img)

    # === Header ===
    title = "Weather"
    if data.get("loc", {}).get("city"):
        title += f" • {data['loc']['city']}"
    draw_header(d, title)

    # === Data ===
    temp = noww.get("temp_f")
    wc = noww.get("weathercode")
    desc = WCMAP.get(int(wc) if wc is not None else -1, "—")
    astro = data.get("astronomy", {}) or {}

    # === Sunrise / Sunset blurb — MOVED INSIDE render() ===
    sunset_str = fmt_clock(astro.get("sunset"))
    sunrise_next_str = fmt_clock(astro.get("sunrise_next") or astro.get("sunrise"))
    blurb = f"Sunset {sunset_str}" if is_day else f"Sunrise {sunrise_next_str}"

    font_size = cfg["fonts"]["timestamp_size"]
    x_pad = cfg["padding"]["timestamp_x"]
    y_pos = cfg["padding"]["timestamp_y"]
    color = tuple(cfg["colors"]["time_stamp"])
    bw, _ = text_size(d, blurb, font_size)
    d.text((W - bw - x_pad, y_pos), blurb, fill=color, font=font(font_size))

    # === Big temp + description ===
    main = f"{int(round(temp))}°F" if isinstance(temp, (int, float)) else "—°"
    d.text((16, 60), main, fill=tuple(cfg["colors"]["fg"]), font=font(cfg["fonts"]["big_temp_size"]))
    d.text((16, 126), desc, fill=(180, 220, 255), font=font(cfg["fonts"]["weather_desc_size"]))

    # === Hero icon ===
    base_name = "sun.png" if is_day else pick_moon_icon(astro.get("moon_phase"))
    base_im = load_rgba(os.path.join(ICON_WEATHER_BASE, base_name), size=cfg["padding"]["hero_sz"])

    sky_name, precip_name, thunder_name = wc_to_layers(int(wc) if wc is not None else -1)
    sky_im = load_rgba(os.path.join(ICON_WEATHER_LAYERS, sky_name), size=cfg["padding"]["hero_sz"]) if sky_name else None
    precip_im = load_rgba(os.path.join(ICON_WEATHER_LAYERS, precip_name), size=cfg["padding"]["hero_sz"]) if precip_name else None
    thunder_im = load_rgba(os.path.join(ICON_WEATHER_LAYERS, thunder_name), size=cfg["padding"]["hero_sz"]) if thunder_name else None

    icon_x = cfg["padding"]["hero_x"]
    icon_y = cfg["padding"]["hero_y"]
    for layer in (base_im, sky_im, precip_im, thunder_im):
        if layer:
            img.paste(layer, (icon_x, icon_y), layer)

    # === Hourly strip ===
    d.text((16, cfg["padding"]["coming_up_y"]), "Coming Up", fill=tuple(cfg["colors"]["accent"]), font=font(cfg["fonts"]["weather_coming_up_size"]))

    hourly_list = data.get("hourly", []) or []
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
        h = hour_map.get(key, {}) or {}
        tf = h.get("temp_f")
        pp = h.get("pop")
        hwc = h.get("weathercode")

        d.text((x, cfg["padding"]["hourly_y"] + cfg["padding"]["time_dy"]), lbl, fill=tuple(cfg["colors"]["muted"]), font=font(cfg["fonts"]["weather_hourly_time_size"]))
        d.text((x, cfg["padding"]["hourly_y"] + cfg["padding"]["temp_dy"]),
               f"{int(round(tf))}°" if isinstance(tf, (int, float)) else "—°",
               fill=tuple(cfg["colors"]["fg"]), font=font(cfg["fonts"]["weather_hourly_temp_size"]))

        tiny_name = wc_to_tiny_layer(int(hwc) if hwc is not None else -1)
        if tiny_name:
            tiny_im = load_rgba(os.path.join(ICON_WEATHER_TINY, tiny_name),
                                size=cfg["padding"]["icon_sz_tiny"])
            if tiny_im:
                img.paste(tiny_im, (x + cfg["padding"]["icon_dx"], cfg["padding"]["hourly_y"] + cfg["padding"]["icon_dy"]), tiny_im)

        pop_txt = f"{int(pp)}%" if isinstance(pp, (int, float)) else "—"
        pop_fill = (140, 200, 255) if isinstance(pp, (int, float)) else (100, 120, 140)
        d.text((x, cfg["padding"]["hourly_y"] + cfg["padding"]["pop_dy"]), pop_txt, fill=pop_fill, font=font(cfg["fonts"]["weather_hourly_pop_size"]))

        x += cfg["padding"]["hourly_col_w"]
        if x > W - 64:
            break

    # === Footer ===
    stale = is_stale(data.get("updated", ""), max_age_sec=1800)
    footer = "STALE" if stale else "Updated"
    footer_text = f"{footer} {datetime.now().strftime('%b %d %I:%M %p')}"

    fw, _ = text_size(d, footer_text, cfg["fonts"]["footer_size"])
    d.text((16, H - 30), footer_text, fill=tuple(cfg["colors"]["muted"]), font=font(cfg["fonts"]["footer_size"]))

    return atomic_save(img, "weather")
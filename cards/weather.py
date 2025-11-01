# ~/pidisplay/cards/weather.py
from .base import *
from datetime import datetime, timedelta
import json

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

def render():
    # ... [your full weather logic, using BG, DAY_BG, text_size, etc.]
    # At top:
    data = json.load(open(os.path.expanduser("~/pidisplay/state/weather.json")))
    is_day = int(data["now"].get("is_day", 1))
    img = Image.new("RGB", (W, H), DAY_BG if is_day else BG)
    # ... rest of your code ...
       data = load_json(os.path.expanduser("~/pidisplay/state/weather.json"))
    
    # === Day / Night background ===
    is_day = 1  # default fallback
    if data and "now" in data:
        is_day = int(data["now"].get("is_day") or 0)
    bg_color = BG_DAY if is_day else BG
    img = Image.new("RGB", (W, H), bg_color)
    d = ImageDraw.Draw(img)

    # === Header ===
    title = "Weather"
    if data and data.get("loc", {}).get("city"):
        title += f" • {data['loc']['city']}"
    draw_header(d, title)

    # === No data fallback ===
    if not data or "now" not in data:
        d.text((16, 60), "No weather data", fill=(255, 120, 120), font=font(32))
        d.text((16, H-30), "OFFLINE", fill=(255, 120, 120), font=font(18))
        return atomic_save(img, "weather.png")

    noww = data["now"]
    astro = data.get("astronomy", {}) or {}
    temp = noww.get("temp_f")
    wc   = noww.get("weathercode")
    desc = WCMAP.get(int(wc) if wc is not None else -1, "—")

    # === Sunrise / Sunset blurb (top-right, under header) ===
    sunset_str = _fmt_clock(astro.get("sunset"))
    sunrise_next_str = _fmt_clock(astro.get("sunrise_next") or astro.get("sunrise"))
    blurb = f"Sunset {sunset_str}" if is_day else f"Sunrise {sunrise_next_str}"

    bw, _ = text_size(d, blurb, font(TIMESTAMP_FONT_SIZE))
    d.text((W - bw - TIMESTAMP_X_PAD, TIMESTAMP_Y_PAD),
           blurb, fill=TIMESTAMP_COLOR, font=font(TIMESTAMP_FONT_SIZE))

    # === Big temp + description ===
    main = f"{int(round(temp))}°F" if isinstance(temp, (int, float)) else "—°"
    d.text((16, 60), main, fill=FG, font=font(56))
    d.text((16, 126), desc, fill=(180, 220, 255), font=font(26))

    # === Hero icon ===
    base_name = "sun.png" if is_day else pick_moon_icon(astro.get("moon_phase"))
    base_im = load_rgba(os.path.join(ICON_WEATHER_BASE, base_name), size=(HERO_SZ, HERO_SZ))

    sky_name, precip_name, thunder_name = wc_to_layers(int(wc) if wc is not None else -1)
    sky_im     = load_rgba(os.path.join(ICON_WEATHER_LAYERS, sky_name), size=(HERO_SZ, HERO_SZ)) if sky_name else None
    precip_im  = load_rgba(os.path.join(ICON_WEATHER_LAYERS, precip_name), size=(HERO_SZ, HERO_SZ)) if precip_name else None
    thunder_im = load_rgba(os.path.join(ICON_WEATHER_LAYERS, thunder_name), size=(HERO_SZ, HERO_SZ)) if thunder_name else None

    icon_x, icon_y = 170, 58
    for layer in (base_im, sky_im, precip_im, thunder_im):
        if layer:
            img.paste(layer, (icon_x, icon_y), layer)

    # === Hourly strip (6 columns) ===
    d.text((16, 180 - 24), "Coming Up", fill=ACCENT, font=font(18))

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

    # ← ONLY ONE LOOP
    x = 16
    for lbl, key in zip(labels, keys):
        h = hour_map.get(key, {}) or {}
        tf = h.get("temp_f")
        pp = h.get("pop")
        hwc = h.get("weathercode")

        # Fixed positions
        d.text((x, HOURLY_Y + TIME_DY), lbl, fill=MUTED, font=font(16))
        d.text((x, HOURLY_Y + TEMP_DY),
               f"{int(round(tf))}°" if isinstance(tf, (int, float)) else "—°",
               fill=FG, font=font(20))

        # Tiny icon
        tiny_name = wc_to_tiny_layer(int(hwc) if hwc is not None else -1)
        if tiny_name:
            tiny_im = load_rgba(os.path.join(ICON_WEATHER_TINY, tiny_name),
                                size=(ICON_SZ_TINY, ICON_SZ_TINY))
            if tiny_im:
                img.paste(tiny_im, (x + ICON_DX, HOURLY_Y + ICON_DY), tiny_im)

        # Precip %
        pop_txt = f"{int(pp)}%" if isinstance(pp, (int, float)) else "—"
        pop_fill = (140, 200, 255) if isinstance(pp, (int, float)) else (100, 120, 140)
        d.text((x, HOURLY_Y + POP_DY), pop_txt, fill=pop_fill, font=font(14))

        x += HOURLY_COL_W
        if x > W - 64:
            break

    # === Footer: Updated / STALE ===
    stale = is_stale(data.get("updated", ""), max_age_sec=1800)
    footer = "STALE" if stale else "Updated"
    footer_text = f"{footer} {datetime.now().strftime('%b %d %I:%M %p')}"
    fw, _ = text_size(d, footer_text, font(18))
    d.text((16, H - 30), footer_text, fill=MUTED, font=font(18))
    
    return atomic_save(img, "weather")
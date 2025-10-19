#!/usr/bin/env python3
# fetch_weather.py
import os, json, requests
from datetime import datetime, timezone, timedelta

STATE = os.path.expanduser("~/pidisplay/state")
os.makedirs(STATE, exist_ok=True)
GEO = os.path.join(STATE, "geo.json")
OUT = os.path.join(STATE, "weather.json")
TMP = OUT + ".tmp"
ASTRO_CACHE = os.path.join(STATE, "astro_cache.json")  # NEW

def load(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None

def save_atomic(obj, path):
    tmpp = path + ".tmp"
    with open(tmpp, "w") as f:
        json.dump(obj, f)
    os.replace(tmpp, path)

# Optional: simple mapping from WeatherAPI phase names → a fraction [0..1]
# (You already logged “(0.875)”, so keep or adjust this to match your current mapping.)
_PHASE_FRACTION = {
    "New Moon": 0.00,
    "Waxing Crescent": 0.125,
    "First Quarter": 0.25,
    "Waxing Gibbous": 0.375,
    "Full Moon": 0.50,
    "Waning Gibbous": 0.625,
    "Last Quarter": 0.75,
    "Third Quarter": 0.75,   # WeatherAPI sometimes uses this label
    "Waning Crescent": 0.875,
}

def main():
    geo = load(GEO) or {}
    lat = geo.get("lat")
    lon = geo.get("lon")
    tz  = geo.get("tz") or "UTC"

    if lat is None or lon is None:
        print("WARN: no geo; using (0,0) and UTC")
        lat, lon, tz = 0.0, 0.0, "UTC"

    # --- 1) Forecast (weather + hourly + sunrise/sunset) ---
    params_forecast = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation_probability,weathercode",
        "daily": "sunrise,sunset",
        "current_weather": "true",
        "timezone": tz,
        "temperature_unit": "fahrenheit",
    }

    # Load previous state so we can preserve moon_phase if the astronomy call fails
    prev = load(OUT) or {}
    prev_moon = ((prev.get("astronomy") or {}).get("moon_phase"))


    # --- 2) Astronomy (moon phase) — now with caching ---
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    today_str = today.isoformat()
    # Cache key sticks to ~1km with 3 decimal places; tweak if you like
    loc_key = f"{round(lat or 0.0, 3)},{round(lon or 0.0, 3)}"
    cache_key = f"{today_str}:{loc_key}"

    cache = load(ASTRO_CACHE) or {}
    cached = cache.get(cache_key)

    moon_phase_fraction = None  # 0..1 expected by your renderer
    moon_phase_name = None

    # Try cache first
    if cached and isinstance(cached, dict):
        moon_phase_fraction = cached.get("moon_phase")
        moon_phase_name = cached.get("moon_phase_name")

    # If not in cache, try WeatherAPI (and then store in cache)
    if moon_phase_fraction is None:
        api_key = os.getenv("WEATHERAPI_KEY")
        if not api_key:
            print("⚠️ WEATHERAPI_KEY not set; skipping moon phase.")
        else:
            try:
                # WeatherAPI astronomy endpoint:
                # https://api.weatherapi.com/v1/astronomy.json?key=KEY&q=LAT,LON&dt=YYYY-MM-DD
                url = "https://api.weatherapi.com/v1/astronomy.json"
                params = {"key": api_key, "q": f"{lat},{lon}", "dt": today_str}
                ra = requests.get(url, params=params, timeout=6)
                ra.raise_for_status()
                j = ra.json()

                astro = (((j or {}).get("astronomy") or {}).get("astro") or {})
                moon_phase_name = astro.get("moon_phase")
                # If you prefer illumination %, you can derive a rough fraction with int(illum)/100
                frac_from_map = _PHASE_FRACTION.get(moon_phase_name or "")
                if frac_from_map is not None:
                    moon_phase_fraction = frac_from_map
                else:
                    # Fallback: try illumination percentage → fraction
                    illum = astro.get("moon_illumination")
                    try:
                        moon_phase_fraction = max(0.0, min(1.0, float(illum) / 100.0))
                    except Exception:
                        moon_phase_fraction = None

                # Cache if we got *something*
                if moon_phase_fraction is not None:
                    cache[cache_key] = {
                        "moon_phase": moon_phase_fraction,
                        "moon_phase_name": moon_phase_name,
                        "fetched": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                        "source": "weatherapi",
                    }
                    save_atomic(cache, ASTRO_CACHE)

                    # Friendly log (like you showed earlier)
                    print(f"🌙 WeatherAPI moon phase: {moon_phase_name} ({moon_phase_fraction:.3f})")
            except Exception as e:
                print("⚠️ WeatherAPI astronomy fetch failed:", e)

    # ... after moon_phase = moon_list[0] if moon_list else None
    if moon_phase is None and prev_moon is not None:
        moon_phase = prev_moon


    try:
        # Forecast request (authoritative for sunrise/sunset and hourly)
        rf = requests.get("https://api.open-meteo.com/v1/forecast", params=params_forecast, timeout=6)
        rf.raise_for_status()
        j_forecast = rf.json()

        now = j_forecast.get("current_weather", {}) or {}
        hourly = j_forecast.get("hourly", {}) or {}
        daily_fc = j_forecast.get("daily", {}) or {}

        sunrise_list = daily_fc.get("sunrise", []) or []
        sunset_list  = daily_fc.get("sunset", [])  or []
        today_sunrise = sunrise_list[0] if sunrise_list else None
        today_sunset  = sunset_list[0]  if sunset_list  else None
        tomorrow_sunrise = sunrise_list[1] if len(sunrise_list) >= 2 else None

        out = {
            "loc": {"lat": lat, "lon": lon, "tz": tz, "city": geo.get("city")},
            "now": {
                "temp_f": now.get("temperature"),
                "windspeed": now.get("windspeed"),
                "weathercode": now.get("weathercode"),
                "is_day": now.get("is_day"),
                "ts": now.get("time"),
            },
            "astronomy": {
                "sunrise": today_sunrise,
                "sunset": today_sunset,
                "sunrise_next": tomorrow_sunrise,
                "moon_phase": moon_phase_fraction,     # <= cached or fresh
                "moon_phase_name": moon_phase_name,    # optional, handy for logs
            },
            "hourly": [],
            "updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "src": "open-meteo",
        }

        # Limit horizon to next 36 hours
        HORIZON = 36
        times   = (hourly.get("time", []) or [])[:HORIZON]
        temps_f = (hourly.get("temperature_2m", []) or [])[:HORIZON]
        pops    = (hourly.get("precipitation_probability", []) or [])[:HORIZON]
        wcs     = (hourly.get("weathercode", []) or [])[:HORIZON]

        for i, t in enumerate(times):
            out["hourly"].append({
                "time": t,
                "temp_f": temps_f[i] if i < len(temps_f) else None,
                "pop": pops[i] if i < len(pops) else None,
                "weathercode": wcs[i] if i < len(wcs) else None,
            })

        save_atomic(out, OUT)
        print("✅ weather updated for", tz, "@", lat, lon)

    except Exception as e:
        print("❌ weather fetch failed:", e)
        if not os.path.exists(OUT):
            save_atomic({"error": str(e), "updated": datetime.utcnow().isoformat()+"Z"}, OUT)

if __name__ == "__main__":
    main()

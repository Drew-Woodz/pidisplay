#!/usr/bin/env python3

# fetch_weather.py
import os, json, time, requests
from datetime import datetime, timezone

STATE = os.path.expanduser("~/pidisplay/state")
os.makedirs(STATE, exist_ok=True)
GEO = os.path.join(STATE, "geo.json")
OUT = os.path.join(STATE, "weather.json")
TMP = OUT + ".tmp"

def load(path):
    try:
        with open(path, "r") as f: return json.load(f)
    except: return None

def main():
    geo = load(GEO) or {}
    lat = geo.get("lat"); lon = geo.get("lon"); tz = geo.get("tz") or "UTC"
    if lat is None or lon is None:
        # fallback to 0,0 with marker
        print("WARN: no geo; using (0,0) and UTC")
        lat, lon, tz = 0.0, 0.0, "UTC"

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation_probability,weathercode",
        "current_weather": "true",
        "timezone": tz,
        "temperature_unit": "fahrenheit"
    }

    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=6)
        r.raise_for_status()
        j = r.json()

        now = j.get("current_weather", {})
        hourly = j.get("hourly", {})
        out = {
            "loc": {"lat":lat, "lon":lon, "tz":tz, "city": geo.get("city")},
            "now": {
                "temp_f": now.get("temperature"),
                "windspeed": now.get("windspeed"),
                "weathercode": now.get("weathercode"),
                "ts": now.get("time")
            },
            "hourly": [],  # next ~6 items for the card
            "updated": datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
            "src": "open-meteo"
        }
        times = hourly.get("time", [])[:6]
        temps = (hourly.get("temperature_2m", []) or [])[:6]
        pops  = (hourly.get("precipitation_probability", []) or [])[:6]
        wcs   = (hourly.get("weathercode", []) or [])[:6]
        for i, t in enumerate(times):
            out["hourly"].append({
                "time": t,
                "temp_f": temps[i] if i < len(temps) else None,
                "pop": pops[i] if i < len(pops) else None,
                "weathercode": wcs[i] if i < len(wcs) else None
            })

        with open(TMP, "w") as f: json.dump(out, f)
        os.replace(TMP, OUT)
        print("✅ weather updated for", tz, "@", lat, lon)
    except Exception as e:
        print("❌ weather fetch failed:", e)
        if not os.path.exists(OUT):
            with open(TMP, "w") as f:
                json.dump({"error": str(e), "updated": datetime.utcnow().isoformat()+"Z"}, f)
            os.replace(TMP, OUT)

if __name__ == "__main__":
    main()

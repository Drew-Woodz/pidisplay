#!/usr/bin/env python3

# fetch_geo.py
import os, json, time, requests, subprocess
from datetime import datetime

STATE_DIR = os.path.expanduser("~/pidisplay/state")
os.makedirs(STATE_DIR, exist_ok=True)
OUT = os.path.join(STATE_DIR, "geo.json")
TMP = OUT + ".tmp"

def set_timezone(tz):
    try:
        subprocess.run(["sudo","timedatectl","set-timezone",tz], check=True)
        subprocess.run(["sudo","timedatectl","set-ntp","true"], check=True)
    except Exception as e:
        print("WARN: failed to set timezone/ntp:", e)

def main():
    try:
        r = requests.get("http://ip-api.com/json", timeout=6)
        r.raise_for_status()
        j = r.json()
        data = {
            "lat": j.get("lat"),
            "lon": j.get("lon"),
            "city": j.get("city"),
            "region": j.get("regionName"),
            "country": j.get("country"),
            "tz": j.get("timezone"),
            "ts": datetime.utcnow().isoformat()+"Z",
            "src": "ip-api.com"
        }
        if data["tz"]:
            set_timezone(data["tz"])

        with open(TMP, "w") as f:
            json.dump(data, f)
        os.replace(TMP, OUT)
        print("✅ geo updated:", data)
    except Exception as e:
        print("❌ geo fetch failed:", e)
        # if we have no geo at all, write a minimal file
        if not os.path.exists(OUT):
            with open(TMP, "w") as f:
                json.dump({"error": str(e), "ts": datetime.utcnow().isoformat()+"Z"}, f)
            os.replace(TMP, OUT)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import json, os, subprocess
from datetime import datetime, timezone

STATE = os.path.expanduser("~/pidisplay/state")
os.makedirs(STATE, exist_ok=True)
OUT = os.path.join(STATE, "health.json")

# Units to watch: timers + services (add/remove as you like)
UNITS = [
    "pidisplay.service",
    "clock-update.timer",
    "weather-update.timer",
    "news-update.timer",
    "news-render.timer",
    "news-fox.timer",
    "news-breitbart.timer",
    "btc-update.timer",
]

def is_active(unit):
    # returns "active", "inactive", "failed", "activating", etc.
    try:
        out = subprocess.check_output(["systemctl", "is-active", unit], text=True).strip()
        return out
    except subprocess.CalledProcessError as e:
        return (e.output or "unknown").strip() or "unknown"

def last_result(unit):
    # useful for services: "success"/"failed"/"exit-code"
    try:
        out = subprocess.check_output(
            ["systemctl", "show", unit, "--property=Result", "--value"], text=True
        ).strip()
        return out or "n/a"
    except Exception:
        return "n/a"

status = {}
for u in UNITS:
    st = is_active(u)
    status[u] = {
        "active": st,
        "ok": (st == "active"),
        "result": last_result(u) if u.endswith(".service") else "n/a",
    }

doc = {
    "ts": datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
    "status": status,
}

tmp = OUT + ".tmp"
with open(tmp, "w") as f:
    json.dump(doc, f, indent=2)
os.replace(tmp, OUT)
print("health snapshot written:", OUT)

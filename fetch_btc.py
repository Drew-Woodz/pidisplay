#!/usr/bin/env python3

# fetch_btc.py
import os, json, time, requests
from datetime import datetime

STATE_DIR = os.path.expanduser("~/pidisplay/state")
os.makedirs(STATE_DIR, exist_ok=True)
OUT = os.path.join(STATE_DIR, "btc.json")
TMP = OUT + ".tmp"

def fetch_coinbase_btc():
    try:
        # Coinbase spot price
        spot = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=5).json()
        price = float(spot["data"]["amount"])

        # Historical (yesterday) price for 24h change calc
        hist = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/historic?period=day", timeout=5).json()
        data = hist["data"]["prices"]
        if len(data) >= 2:
            old_price = float(data[-1]["price"])
            chg_24h = (price - old_price) / old_price * 100
        else:
            chg_24h = 0.0

        result = {
            "symbol": "BTC-USD",
            "price": price,
            "chg_24h": round(chg_24h, 2),
            "ts": datetime.utcnow().isoformat() + "Z",
            "src": "coinbase"
        }

        with open(TMP, "w") as f:
            json.dump(result, f)
        os.replace(TMP, OUT)
        print("✅ BTC data updated:", result)
    except Exception as e:
        print("❌ BTC fetch failed:", e)
        # Keep last known file if available
        if not os.path.exists(OUT):
            with open(TMP, "w") as f:
                json.dump({"error": str(e), "ts": datetime.utcnow().isoformat()+"Z"}, f)
            os.replace(TMP, OUT)

if __name__ == "__main__":
    fetch_coinbase_btc()

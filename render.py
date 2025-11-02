# ~/pidisplay/render.py
#!/usr/bin/env python3
import argparse
from cards import clock, weather, btc, news

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="*", help="Render only these cards")
    args = parser.parse_args()

    cards = {
        "clock": clock,
        "weather": weather,
        "btc": btc,
        "news": news,
    }

    to_render = args.only or cards.keys()
    for name in to_render:
        if name in cards:
            try:
                cards[name]()
                print(f"Rendered {name}")
            except Exception as e:
                print(f"{name} error: {e}")

if __name__ == "__main__":
    main()
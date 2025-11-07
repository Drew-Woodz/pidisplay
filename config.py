# ~/pidisplay/config.py
import yaml
import os
from pathlib import Path

CONFIG_PATH = Path(os.path.expanduser("~/pidisplay/config.yaml"))

def load():
    if not CONFIG_PATH.exists():
        save_default()
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)

def save_default():
    default = {
        "cards": {"order": ["clock", "weather", "btc", "news"], "enabled": {}},
        "sources": {"news": {"breitbart": True, "fox": True}},  # New: Default sources enabled
        "intervals": {"clock": 5, "weather": 10, "btc": 8, "news": 12},  # Slide delays in viewer (seconds per card)
        "colors": {"bg": [12,12,12], "fg": [235,235,235], "accent": [0,100,255], "muted": [220,220,220], "day_bg": [55,175,255], "time_stamp": [200,200,200]},
        "fonts": {"timestamp_size": 20, "header_size": 19, "footer_size": 18, "big_temp_size": 56, "clock_time_size": 92, "clock_date_size": 36, "btc_price_size": 72, "btc_change_size": 32, "weather_desc_size": 26, "weather_coming_up_size": 18, "weather_hourly_time_size": 16, "weather_hourly_temp_size": 20, "weather_hourly_pop_size": 14, "news_title_size": 19, "news_badge_size": 14},
        "padding": {"timestamp_x": 12, "timestamp_y": 12, "hourly_y": 180, "hourly_col_w": 72, "time_dy": 0, "temp_dy": 18, "pop_dy": 38, "icon_dx": 36, "icon_dy": 16, "icon_sz_tiny": 20, "hero_sz": 100, "hero_x": 170, "hero_y": 58, "coming_up_y": 156, "footer_y": 290, "news_top_margin": 6, "news_cell_h": 53, "news_gap": 2, "news_l_margin": 12, "news_r_margin": 12, "news_pad": 8, "news_icon_sz": 24, "news_border": 1}
    }
    for card in default["cards"]["order"]:
        default["cards"]["enabled"][card] = True
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(default, f)
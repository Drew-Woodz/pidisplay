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
        "intervals": {"clock": 15, "weather": 300, "btc": 60, "news": 300},
        "colors": {"bg": [12,12,12], "fg": [235,235,235], "accent": [0,200,255], "muted": [150,150,150], "day_bg": [135,206,235]},
        "fonts": {"timestamp_size": 20, "header_size": 22, "big_temp_size": 56}
    }
    for card in default["cards"]["order"]:
        default["cards"]["enabled"][card] = True
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(default, f)
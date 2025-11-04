# PiDisplay — Changelog

> Summarized highlights from the active development log (`develop.md`).

## [v0.5.0] - 2025-11-03

### Added

- Modular cards package (cards/) with individual renderers (weather.py, news.py, btc.py, clock.py) and shared base.py helpers.  
- Config-driven layout via config.yaml: Colors, fonts, padding for all cards (e.g., hero_sz, icon_sz_tiny).  
- SOURCE_STYLES dictionary in base.py for per-news-source icons, tints, and borders (e.g., fox.png, breitbart.png).  
- Cached load_icon in base.py with fallback rectangle for missing icons.  

### Fixed

- Missing timezone import in news.py, preventing 24h filter from discarding all items.  
- Font attribute mismatch (point_size → size) in base.py wrap_text_px, resolving news render errors.  
- Icon load failures in weather.py: Converted size args to tuples for Pillow.resize.  
- Path mismatches for weather icons in base.py (e.g., weather/base → ICON_WEATHER_BASE), restoring hero and tiny icons.  
- Silent None returns in load_rgba via debug prints for troubleshooting.  

### Improved

- Refactor preserved dual PNG/RAW output and atomic saves; ensured pixel-perfect rendering to pre-refactor baseline.  
- Clustering and deduplication in news.py now fully operational with visible ×N badges on duplicates.  
- Moon phase mapping in base.py confirmed accurate (e.g., 0.875 → waning crescent).  

### Verified

- All cards render with icons, timestamps, and dynamic data (e.g., weather.json moon at night).  
- System resilience: Manual render.py runs and pidisplay.service restarts show no flicker or artifacts.  


## [1.3.1] - 2025-10-30
### Fixed
- **Color distortion in dark/mid tones** (green tint, purple headers, black backgrounds)
- **Dithering over-aggression** on 16-bit panel

### Changed
- `DITHER_565 = False` in all renderers
- Dithering removed — not needed on high-res SPI LCD

### Verified
- `test_colors_2.py` → all colors correct, greys neutral
- BTC, News, Weather headers now correct dark grey

---

## [2025-10-24] — Flicker Troubleshooting and Blitter Pivot
- Diagnosed persistent minor flicker in `fbi` slideshow due to relaunch overhead on Pi Zero.
- Attempted optimizations: single-instance `fbi` with playlists, VT tweaks, alternative tools (`fim`, `fbv`).
- Confirmed limitations of external framebuffer viewers; pivoted to custom Python blitter for direct `/dev/fb1` writes.
- Documented failures and lessons in `develop.md` to guide future display enhancements.

---

## [2025-10-20] — Stability Restoration and Timer Validation
- Reinstated `fbi` slideshow under user `pi` with TTY and capability fixes.
- Added pre-display VT clear to prevent console text artifacts.
- Validated 15 s `clock-update.timer` for continuous clock refresh.
- Documented remaining minor flicker for future optimization (persistent `fbi` or direct framebuffer blit).

---

## [v0.4.1] — 2025-10-19
### Added
- Astronomy integration: sunrise/sunset text blurbs and moon phase via WeatherAPI (daily cached)
- Automatic selection of moon phase hero icon (+50% rule) based on current lunar position
- Adjustable hourly strip layout with tunable `ICON_DX`, `ICON_DY`, and `TEMP_DY`
- Independent clock-update timer restoration and boot persistence validation

### Fixed
- Hourly weather icon alignment (icons now overlay without shifting temperature columns)
- Clock-update timer not re-enabling after power loss
- Weather render crash on missing `tiny_im` variable

### Improved
- Visual consistency in hourly forecast: time, temperature, and precip columns re-aligned
- System resilience after power loss (revalidated timers and ensured auto-start)

---

## [v0.4.0] — 2025-10-16
### Added
- Complete `develop.md` initialized from Dev Logs 1–4  
- Layered weather hero icons (sun/moon + condition layers)
- Tiny 20×20 hourly weather condition badges
- Ordered dithering to RGB565 for improved LCD color quality
- Larger hero icon size (~96 px) for better visibility

### Fixed
- Cache collision between icon loaders (`_icon_cache` → `_icon_cache_rgba`)
- Duplicate `atomic_save()` definition removed

### Improved
- Color accuracy and tone range on SPI LCD
- Weather card layout and icon layering

---

## [v0.3.0] — 2025-10-12
### Added
- Multi-source news ingestion (Fox, Breitbart)
- Clustered headline deduplication via token similarity
- Source-tinted UI with consensus badges (×N)
- Clock card (refresh every 15s)
- Independent timers for BTC, News, Weather, Clock

### Improved
- Refactored renderer into modular functions
- Automatic slideshow discovery and rotation

---

## [v0.2.0] — 2025-10-05
### Added
- Weather card using Open-Meteo + geo auto-detection
- Geo-location via ip-api.com
- Atomic PNG writes to prevent frame tearing
- Systemd timers for decoupled updates

### Fixed
- Display conflicts between framebuffer writers
- Time drift via `timedatectl` and NTP

---

## [v0.1.0] — 2025-09-30
### Added
- Baseline PNG → `fbi` framebuffer pipeline
- Working 480×320 output on Waveshare SPI LCD
- `render_cards.py` prototype with BTC + News
- Systemd slideshow service and timer loop

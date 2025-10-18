# PiDisplay — Changelog

> Summarized highlights from the active development log (`develop.md`).

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

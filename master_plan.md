# pidisplay: Master Plan

> High-level roadmap for PiDisplay v1 — ordered to minimize rewrites and keep dependencies clean.

---

## ✅ Accomplished

* [x] **Baseline PNG pipeline to fb1**  
  Pillow → RGB565 → `/dev/fb1` confirmed functional, correct color order, and performant enough for 480×320.

* [x] **Per-card timers**  
  Independent timers/services for btc, news (fetch + render), weather, and clock (supersedes a single `picards.timer`).

* [x] **Card concept validated**  
  Settled on render-to-PNG approach instead of Pygame; verified touch display compatibility and limitations.

* [x] **News pipeline + clustered UI**  
  Per-source fetchers merge into `state/news.json`, clustered duplicates, source tints, and icons.

* [x] **Clock card**  
  Minimal time/date card; integrates in slideshow rotation.

* [x] **Weather: Fahrenheit conversion**  
  Open-Meteo requests in °F end-to-end; render shows °F.

* [x] **Weather: layered hero icons**  
  Sun/moon base + condition layers (clouds/precip/thunder).

* [x] **Weather: hourly condition badges**  
  20×20 tiny icons in the “Coming Up” strip (clear = no badge).

* [x] **Weather: sunrise/sunset line**  
  Right-aligned “Sunset …” / “Sunrise …” switching by day/night.

* [x] **Weather: moon phase base**  
  WeatherAPI astronomy with daily cache → eight moon sprites.

* [x] **LCD fidelity: ordered dithering to RGB565**  
  Pre-dither before PNG save for smoother gradients on 16-bpp SPI panel.

* [x] **Icon caches split**  
  Separate caches for news/source icons vs weather RGBA layers.

* [x] **Secrets/env wiring for API keys**  
  `.pidisplay_env` + `EnvironmentFile=` in relevant services.

---

## 🔧 In Progress / Upcoming

* [ ] **Renderer daemon split**  
  Continuous process managing rotation, touch, and on-demand repaints. Updaters remain decoupled via JSON data files.

* [ ] **Config system + live reload**  
  Introduce `config.yaml` for card order, sources, colors, refresh intervals, and toggles. Implement lightweight file-watch to reload on change.

* [ ] **Input framework**  
  Standardize touch zones: left/right navigation, long-press to pause, two-finger tap for menu. Produce unified event objects.

* [ ] **Menu overlay system**  
  Simple scrollable overlay to toggle cards, choose sources, colors, and manage lists (e.g., stock tickers). Persist to config.

* [ ] **Card plugin API**  
  Standard class interface: `on_show()`, `on_hide()`, `handle_touch(evt)`, `update(dt)`, and `render(draw)`. Register cards in `cards/registry.py`.

* [ ] **Dirty rectangle blitter**  
  Redraw only changed regions of the framebuffer. Maintain cached backgrounds and track dirty rects per frame.

* [ ] **Footer live clock (1 Hz)**  
  Always-on footer clock with per-second updates. Redraws a small rect to simulate a “live” clock without re-rendering the full frame.

* [ ] **“Fake live” clock projection**  
  Extend the above so any card can host a running clock overlay (e.g., top-right). Updates 1 Hz, independent of card refresh.

* [ ] **Updaters refactor**  
  Isolate each data feed into `updaters/` scripts writing JSON to `data/`. Add retry logic and rate limiting. Start with news, weather, crypto.

* [ ] **News card scroll upgrade**  
  Scrollable list of headlines with tap-to-expand preview. Supports per-source toggling from menu.

* [ ] **Calendar integration (OAuth Device Flow)**  
  Implement secure Google Calendar read-only access using device flow. Store tokens under `~/.config/pidisplay/google/` with strict perms.

* [ ] **Calendar card**  
  Displays upcoming events grouped by day. Tap for details. Respects 12/24 h time.

* [ ] **Markets backend (stocks + crypto)**  
  Unify stock and crypto polling into one updater writing `data/markets.json`. Fetch OHLCV for tracked symbols. Cache results efficiently.

* [ ] **Markets overview cards**  
  - **Crypto list card:** scrollable card showing tracked coins with price + change.  
  - **Stock list card:** same idea for stock tickers. Menu allows toggling which tickers appear in each list.

* [ ] **Feature cards per ticker**  
  Individual cards for specific tickers (BTC, ETH, AAPL, etc.) showing detailed price, chart, and 24 h change. Enabled through menu toggles.

* [ ] **Themes and color presets**  
  Create `themes/default.yaml`. Menu allows per-category color selection (weather, crypto, stocks, news).

* [ ] **Logging and system health overlay**  
  Add rotating logs, simple CPU/temp/RAM stats, Wi-Fi signal, last updater timestamps, and unit health.

* [ ] **Documentation pass 1**  
  Write `develop.md` and `config-reference.md` detailing architecture, APIs, directories, and how to add new cards.

* [ ] **Weather polish: optional day/night tint**  
  Subtle background tint before sunset; back to black after.

---

## 🚀 Planned After Core Stabilization

* [ ] **Sports card**  
  Scrollable scores or headlines by league. Menu toggles which leagues are shown.

* [ ] **Now Playing card**  
  Optional Spotify Connect or MPD integration; show song, artist, album art.

* [ ] **System stats card**  
  Local system info: CPU load, memory, disk, temp, uptime, IP.

* [ ] **Mini games (Snake first)**  
  Pillow-rendered, low-FPS games as optional cards. Proof of concept for dirty-rect performance.

* [ ] **C++ fb1 blitter module**  
  Optional native module for RGB→RGB565 conversion and fast blits. Python calls it via ctypes or CFFI. Drop-in, preserving Python API.

* [ ] **Power + watchdog services**  
  Simple watchdog to restart renderer if unresponsive. Optionally dim screen on idle or scheduled hours.

* [ ] **Test harness**  
  Headless mode rendering cards to PNG for development screenshots and CI tests.

---

## 💭 Maybe Someday

* [ ] **Full C++ renderer path**  
  Move render loop and fb writes fully native if Python becomes the bottleneck.

* [ ] **Animated transitions**  
  Slide or fade between cards using cached frame diffs.

* [ ] **Transit / commute ETA card**  
  Uses location data and free APIs to show next departures or drive times.

* [ ] **Asteroids-Lite game**  
  Low-FPS pre-baked sprite version as a fun demo.

* [ ] **Remote config web UI**  
  Lightweight Flask or FastAPI service to modify `config.yaml` from browser.

---

### Notes

* Overhauls (renderer, config, input) come **before** dependent subsystems to avoid rework.
* The markets/crypto system unification ensures shared code for polling, caching, and rendering.
* Clock projection features are now separate milestones because they touch multiple render paths.
* Games, sports, and extra integrations live at the end to keep the base system tight first.

# ALL MODIFIED TIMERS AND SERVICES

## CURRENT AND WORKING

```bash
(venv) pi@pidisplay:~/pidisplay $ sudo cat /etc/systemd/system/btc-update.service
[Unit]
Description=Fetch BTC and render BTC card
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=pi
WorkingDirectory=/home/pi/pidisplay
ExecStart=/home/pi/venv/bin/python /home/pi/pidisplay/fetch_btc.py
ExecStart=/home/pi/venv/bin/python /home/pi/pidisplay/render.py --only btc
```

```bash
(venv) pi@pidisplay:~/pidisplay $ sudo cat /etc/systemd/system/btc-update.timer
[Unit]
Description=Update BTC card every 30 seconds

[Timer]
OnBootSec=20s
OnUnitActiveSec=30s
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
(venv) pi@pidisplay:~/pidisplay $ sudo cat /etc/systemd/system/clock-update.service
# /etc/systemd/system/clock-update.service
[Unit]
Description=Render clock card
After=network-online.target

[Service]
Type=oneshot
User=pi
WorkingDirectory=/home/pi/pidisplay
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/pi/venv/bin/python /home/pi/pidisplay/render.py --only clock
```

```bash
(venv) pi@pidisplay:~/pidisplay $ sudo cat /etc/systemd/system/clock-update.timer
# /etc/systemd/system/clock-update.timer
[Unit]
Description=Update Clock card every 15 seconds

[Timer]
OnBootSec=10s
OnUnitActiveSec=15s
AccuracySec=1s
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
(venv) pi@pidisplay:~/pidisplay $ sudo cat /etc/systemd/system/news-breitbart.service
[Unit]
Description=Fetch Breitbart RSS into state/news.json
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=pi
WorkingDirectory=/home/pi/pidisplay
ExecStart=/home/pi/venv/bin/python /home/pi/pidisplay/fetch_news/fetch_breitbart.py
TimeoutSec=60s
```

```bash
(venv) pi@pidisplay:~/pidisplay $ sudo cat /etc/systemd/system/news-breitbart.timer
[Unit]
Description=Poll Breitbart RSS (every 3 min)

[Timer]
OnBootSec=60s
OnUnitActiveSec=3min
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
(venv) pi@pidisplay:~/pidisplay $ sudo cat /etc/systemd/system/news-fox.service
[Unit]
Description=Fetch Fox News RSS into state/news.json
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=pi
WorkingDirectory=/home/pi/pidisplay
ExecStart=/home/pi/venv/bin/python /home/pi/pidisplay/fetch_news/fetch_fox.py
TimeoutSec=60s
```

```bash
(venv) pi@pidisplay:~/pidisplay $ sudo cat /etc/systemd/system/news-fox.timer
[Unit]
Description=Poll Fox News RSS (every 3 min)

[Timer]
OnBootSec=45s
OnUnitActiveSec=3min
Persistent=true

[Install]
WantedBy=timers.target
```


```bash
(venv) pi@pidisplay:~/pidisplay $ sudo cat /etc/systemd/system/pidisplay.service
# /etc/systemd/system/pidisplay.service
[Unit]
Description=Pi LCD Slideshow (Python raw blitter on fb1)
After=network-online.target dev-fb1.device
Wants=network-online.target dev-fb1.device

[Service]
Type=simple
User=pi
SupplementaryGroups=video
WorkingDirectory=/home/pi/pidisplay
Environment=SLIDE_INTERVAL=8
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/pi/venv/bin/python /home/pi/pidisplay/display_slideshow.py
ExecStop=/usr/bin/pkill -u pi -x python
Restart=on-failure
RestartSec=2
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
(venv) pi@pidisplay:~/pidisplay $ sudo cat /etc/systemd/system/pidisplay.timer
cat: /etc/systemd/system/pidisplay.timer: No such file or directory
```
 

```bash
(venv) pi@pidisplay:~/pidisplay $ sudo cat /etc/systemd/system/weather_fetch.service
[Unit]
Description=Fetch weather from Open-Meteo
After=network-online.target geo_fetch.service
Wants=network-online.target geo_fetch.service

[Service]
Type=oneshot
User=pi
WorkingDirectory=/home/pi/pidisplay
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/pi/venv/bin/python /home/pi/pidisplay/fetch_weather.py
```

```bash
(venv) pi@pidisplay:~/pidisplay $ sudo cat /etc/systemd/system/weather_fetch.timer
[Unit]
Description=Weather refresh every 10 minutes

[Timer]
OnBootSec=30s
OnUnitActiveSec=10min
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
(venv) pi@pidisplay:~/pidisplay $ sudo cat /etc/systemd/system/weather-update.service
[Unit]
Description=Fetch geo+weather and render Weather card
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=pi
WorkingDirectory=/home/pi/pidisplay
ExecStart=/home/pi/venv/bin/python /home/pi/pidisplay/fetch_geo.py
ExecStart=/home/pi/venv/bin/python /home/pi/pidisplay/fetch_weather.py
ExecStart=/home/pi/venv/bin/python /home/pi/pidisplay/render.py --only weather
EnvironmentFile=/home/pi/.pidisplay_env
Environment=PYTHONUNBUFFERED=1
```

```bash
(venv) pi@pidisplay:~/pidisplay $ sudo cat /etc/systemd/system/weather-update.timer
[Unit]
Description=Update Weather card every 10 minutes

[Timer]
OnBootSec=60s
OnUnitActiveSec=10min
Persistent=true
AccuracySec=30s

[Install]
WantedBy=timers.target
```

```bash
(venv) pi@pidisplay:~/pidisplay $ sudo cat /etc/systemd/system/geo_fetch.service
[Unit]
Description=Fetch geolocation (lat/lon/tz) via IP
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=pi
WorkingDirectory=/home/pi/pidisplay
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/pi/venv/bin/python /home/pi/pidisplay/fetch_geo.py
```

```bash
(venv) pi@pidisplay:~/pidisplay $ sudo cat /etc/systemd/system/news-render.service
[Unit]
Description=Render News card from merged news.json
After=news-breitbart.service news-fox.service
Requires=news-breitbart.service news-fox.service

[Service]
Type=oneshot
User=pi
WorkingDirectory=/home/pi/pidisplay
ExecStart=/home/pi/venv/bin/python /home/pi/pidisplay/render.py --only news
```

```bash
(venv) pi@pidisplay:~/pidisplay $ sudo cat /etc/systemd/system/news-render.timer
[Unit]
Description=Render News card every 2 minutes

[Timer]
OnBootSec=75s
OnUnitActiveSec=2min
Persistent=true
Unit=news-breitbart.service news-fox.service
AccuracySec=30s

[Install]
WantedBy=timers.target
```

 
## PATH INSPECTION

```bash
(venv) pi@pidisplay:~/pidisplay $ systemctl list-timers --all
NEXT                        LEFT          LAST                        PASSED        UNIT                         ACTIVATES
Tue 2025-11-04 20:24:17 CST 1s left       Tue 2025-11-04 20:24:02 CST 13s ago       clock-update.timer           clock-update.service
Tue 2025-11-04 20:24:32 CST 16s left      Tue 2025-11-04 20:24:02 CST 13s ago       btc-update.timer             btc-update.service
Tue 2025-11-04 20:25:02 CST 46s left      Tue 2025-11-04 20:24:02 CST 13s ago       status-snapshot.timer        status-snapshot.service
Tue 2025-11-04 20:26:30 CST 2min 14s left Tue 2025-11-04 20:23:30 CST 45s ago       news-breitbart.timer         news-breitbart.service
Tue 2025-11-04 20:26:30 CST 2min 14s left Tue 2025-11-04 20:23:30 CST 45s ago       news-fox.timer               news-fox.service
Tue 2025-11-04 20:30:20 CST 6min left     Tue 2025-11-04 20:20:20 CST 3min 55s ago  weather-update.timer         weather-update.service
Tue 2025-11-04 20:33:47 CST 9min left     Tue 2025-11-04 20:23:46 CST 29s ago       weather_fetch.timer          weather_fetch.service
Wed 2025-11-05 00:00:00 CST 3h 35min left Tue 2025-11-04 00:00:00 CST 20h ago       dpkg-db-backup.timer         dpkg-db-backup.service
Wed 2025-11-05 00:00:00 CST 3h 35min left Tue 2025-11-04 00:00:00 CST 20h ago       logrotate.timer              logrotate.service
Wed 2025-11-05 05:28:57 CST 9h left       Tue 2025-11-04 15:09:26 CST 5h 14min ago  apt-daily.timer              apt-daily.service
Wed 2025-11-05 06:45:38 CST 10h left      Tue 2025-11-04 06:44:26 CST 13h ago       apt-daily-upgrade.timer      apt-daily-upgrade.service
Wed 2025-11-05 10:50:25 CST 14h left      Tue 2025-11-04 09:54:04 CST 10h ago       man-db.timer                 man-db.service
Wed 2025-11-05 17:32:06 CST 21h left      Tue 2025-11-04 17:32:06 CST 2h 52min ago  systemd-tmpfiles-clean.timer systemd-tmpfiles-clean.service
Sun 2025-11-09 03:10:28 CST 4 days left   Sun 2025-11-02 17:17:45 CST 2 days ago    e2scrub_all.timer            e2scrub_all.service
Mon 2025-11-10 00:44:05 CST 5 days left   Mon 2025-11-03 01:04:40 CST 1 day 19h ago fstrim.timer                 fstrim.service
-                           -             Mon 2025-11-03 19:05:42 CST 1 day 1h ago  news-render.timer            news-render.service

16 timers listed.

```

## DEPRECATED

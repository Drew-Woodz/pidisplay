#!/usr/bin/env python3
import os, json, re, hashlib, feedparser
import requests
from datetime import datetime, timezone

STATE = os.path.expanduser("~/pidisplay/state/news.json")
TMP   = STATE + ".tmp"
SRC   = "breitbart"
# Breitbart’s feed is commonly mirrored via FeedBurner; keep as provisional.
FEEDS = [
    "https://feeds.feedburner.com/breitbart"
]

def load():
    try: return json.load(open(STATE))
    except: return {"updated": None, "items": []}

def norm_title(t):
    return re.sub(r"[^a-z0-9 ]+", " ", (t or "").lower()).split()

def mk_id(source, title):
    base = source + "|" + " ".join(norm_title(title))
    return hashlib.sha1(base.encode()).hexdigest()[:16]

def older_than_24h(ts):
    t = datetime.fromisoformat(ts.replace("Z","+00:00"))
    return (datetime.now(timezone.utc) - t).total_seconds() > 24*3600

def main():
    j = load()
    items = j["items"]
    seen = {it["id"] for it in items}

    for url in FEEDS:
        try:
            # Fetch with timeout to prevent hangs
            response = requests.get(url, headers={"User-Agent": "pidisplay/1.0 (+https://github.com/yourrepo)", "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8"}, timeout=30)
            response.raise_for_status()
            feed_content = response.content
            feed = feedparser.parse(feed_content)
        except Exception as e:
            print(f"Error fetching/parsing {url}: {str(e)}")
            continue  # Skip to next feed on error

        # If the feed is down/empty, skip quietly.
        for e in (feed.entries or [])[:25]:
            title = (getattr(e, "title", "") or "").strip()
            if not title: continue
            link  = getattr(e, "link", None)
            _id   = mk_id(SRC, title)
            if _id in seen: continue
            tags = []
            if re.search(r"\b(breaking|urgent|developing)\b", title, re.I):
                tags.append("breaking")
            now = datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
            items.append({"id":_id, "source":SRC, "title":title, "url":link, "ts":now, "tags":tags})
            seen.add(_id)

    items = [it for it in items if not older_than_24h(it["ts"])]
    items.sort(key=lambda it: it["ts"], reverse=True)
    items = items[:200]

    j["items"] = items
    j["updated"] = datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    with open(TMP, "w") as f: json.dump(j, f)
    os.replace(TMP, STATE)
    print(f"news[{SRC}] ok total={len(items)}")

if __name__ == "__main__":
    main()
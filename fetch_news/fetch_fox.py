#!/usr/bin/env python3
import os, json, re, hashlib, feedparser
from datetime import datetime, timezone

STATE = os.path.expanduser("~/pidisplay/state/news.json")
TMP   = STATE + ".tmp"
SRC   = "fox"
FEEDS = [
    "https://moxie.foxnews.com/google-publisher/latest.xml",
    # add more if you want:
    # "https://moxie.foxnews.com/google-publisher/politics.xml",
    # "https://moxie.foxnews.com/google-publisher/us.xml",
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
        feed = feedparser.parse(url, request_headers={"User-Agent": "pidisplay/1.0 (+https://github.com/yourrepo)"})
        for e in (feed.entries or [])[:25]:
            title = (getattr(e, "title", "") or "").strip()
            if not title: continue
            url   = getattr(e, "link", None)
            _id   = mk_id(SRC, title)
            if _id in seen: continue
            tags = []
            if re.search(r"\b(breaking|urgent|developing)\b", title, re.I):
                tags.append("breaking")
            now = datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
            items.append({"id":_id, "source":SRC, "title":title, "url":url, "ts":now, "tags":tags})
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

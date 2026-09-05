# -*- coding: utf-8 -*-
"""Скан ниш: для каждого запроса — топ-50 шортсов с 2026-06-01, каналы, их возраст/просмотры.
Денежность = сколько НОВЫХ каналов (с 06.2025) держат ≥5k просм/день (views/age)."""
import json, sys, io, os, datetime as dt, statistics as st
from pathlib import Path
import requests
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
KEY = (Path(os.environ["YT_SECRETS"]) / "api_key").read_text(encoding="utf-8").strip()
YT = "https://www.googleapis.com/youtube/v3"
def api(p, **q):
    q["key"] = KEY; r = requests.get(f"{YT}/{p}", params=q, timeout=30); r.raise_for_status(); return r.json()
NICHES = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
now = dt.datetime.now(dt.timezone.utc); out = {}
for niche, q in NICHES.items():
    r = api("search", part="snippet", q=q, type="video", videoDuration="short", order="viewCount",
            maxResults=50, publishedAfter="2026-06-01T00:00:00Z", relevanceLanguage="en")
    cids = list({it["snippet"]["channelId"] for it in r.get("items", [])})
    rows = []
    for i in range(0, len(cids), 50):
        for c in api("channels", part="snippet,statistics", id=",".join(cids[i:i+50])).get("items", []):
            born = dt.datetime.fromisoformat(c["snippet"]["publishedAt"].replace("Z", "+00:00"))
            age = max((now - born).days, 1); s = c["statistics"]
            rows.append({"cid": c["id"], "title": c["snippet"]["title"], "born": born.date().isoformat(), "age": age,
                         "videos": int(s.get("videoCount", 0)), "views": int(s.get("viewCount", 0)),
                         "subs": int(s.get("subscriberCount", 0)), "vpd": int(s.get("viewCount", 0)) / age,
                         "country": c["snippet"].get("country", "")})
    new = [x for x in rows if x["born"] >= "2025-06-01"]
    hits = sorted([x for x in new if x["vpd"] >= 5000], key=lambda x: -x["vpd"])
    out[niche] = {"query": q, "channels": len(rows), "new": len(new), "new_hits": len(hits),
                  "med_new_vpd": st.median([x["vpd"] for x in new]) if new else 0, "hits": hits, "rows": rows}
    print(f"{niche:22} каналов {len(rows):2} | новых {len(new):2} | новых ≥5k/д {len(hits):2} | медиана новых {out[niche]['med_new_vpd']:>7.0f}/д | "
          + "; ".join(f"{h['title'][:18]} {h['vpd']:.0f}/д ({h['videos']}в, {h['age']}д)" for h in hits[:4]))
Path(sys.argv[2]).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

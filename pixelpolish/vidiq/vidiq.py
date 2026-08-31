#!/usr/bin/env python3
"""PixelPolish vidIQ — свой трекер/разведка YouTube без подписок.

Команды:
  ids                 — узнать channel_id наших OAuth-каналов, вписать в config
  snapshot            — статы наших каналов + последние видео (API key, ~12 units)
  scout               — RSS-разведка конкурентов (0 units), скорость просмотров
  keywords <seed>     — подсказки поиска YouTube (бесплатно)
  discover <query>    — найти каналы ниши через search (100 units за запрос)
  indicators <query>  — каналы-индикаторы: новые, мало видео, аномальный рост
  outliers            — видео-выбросы: просмотры выше медианы своего канала = рабочая тема
  besttime            — лучшее время публикации по стреляющим видео конкурентов (Томск)
  report              — дайджест по последним данным

Данные: data/*.json рядом со скриптом (коммитятся в репо = долговременная память).
Ключи: /root/.config/youtube/{api_key, oauth_client.json, token_*.json}
"""
import datetime as dt
import json
import pathlib
import string
import sys
import xml.etree.ElementTree as ET

import requests

HERE = pathlib.Path(__file__).parent
DATA = HERE / "data"
DATA.mkdir(exist_ok=True)
CFG_PATH = HERE / "config.json"
YT = "https://www.googleapis.com/youtube/v3"
KEY = open("/root/.config/youtube/api_key").read().strip()
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def cfg():
    return json.loads(CFG_PATH.read_text())


def save_cfg(c):
    CFG_PATH.write_text(json.dumps(c, ensure_ascii=False, indent=1))


def api(path, **params):
    params["key"] = KEY
    r = requests.get(f"{YT}/{path}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def oauth_access(label):
    c = json.load(open("/root/.config/youtube/oauth_client.json"))
    t = json.load(open(f"/root/.config/youtube/token_{label}.json"))
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": c["client_id"], "client_secret": c["client_secret"],
        "refresh_token": t["refresh_token"], "grant_type": "refresh_token"}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def cmd_ids():
    c = cfg()
    for k, ch in c["ours"].items():
        if ch.get("id") or not ch.get("token"):
            continue
        acc = oauth_access(ch["token"])
        r = requests.get(f"{YT}/channels", params={"part": "id,snippet", "mine": "true"},
                         headers={"Authorization": f"Bearer {acc}"}, timeout=30).json()
        items = r.get("items", [])
        if items:
            ch["id"] = items[0]["id"]
            print(f"{k}: {ch['id']} ({items[0]['snippet']['title']})")
    save_cfg(c)


def uploads_playlist(chan_id):
    return "UU" + chan_id[2:]


def cmd_snapshot():
    c = cfg()
    today = dt.date.today().isoformat()
    out = {"date": today, "channels": {}}
    ids = [ch["id"] for ch in c["ours"].values() if ch.get("id")]
    stats = api("channels", part="statistics,snippet", id=",".join(ids))
    by_id = {i["id"]: i for i in stats.get("items", [])}
    for k, ch in c["ours"].items():
        if not ch.get("id") or ch["id"] not in by_id:
            continue
        it = by_id[ch["id"]]
        st = it["statistics"]
        rec = {"title": it["snippet"]["title"],
               "subs": int(st.get("subscriberCount", 0)),
               "views": int(st.get("viewCount", 0)),
               "videos": int(st.get("videoCount", 0)), "latest": []}
        try:
            pl = api("playlistItems", part="contentDetails",
                     playlistId=uploads_playlist(ch["id"]), maxResults=10)
            vids = [x["contentDetails"]["videoId"] for x in pl.get("items", [])]
            if vids:
                vs = api("videos", part="statistics,snippet", id=",".join(vids))
                for v in vs.get("items", []):
                    rec["latest"].append({
                        "id": v["id"], "title": v["snippet"]["title"][:70],
                        "published": v["snippet"]["publishedAt"][:10],
                        "views": int(v["statistics"].get("viewCount", 0)),
                        "likes": int(v["statistics"].get("likeCount", 0)),
                        "comments": int(v["statistics"].get("commentCount", 0))})
        except requests.HTTPError:
            pass  # пустой канал без uploads-плейлиста
        out["channels"][k] = rec
    (DATA / f"ours_{today}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    with open(DATA / "ours_history.jsonl", "a") as f:
        f.write(json.dumps({k: {"d": today, "s": v["subs"], "v": v["views"]}
                            for k, v in out["channels"].items()}) + "\n")
    print(json.dumps(out, ensure_ascii=False, indent=1))


def rss(chan_id):
    r = requests.get(f"https://www.youtube.com/feeds/videos.xml?channel_id={chan_id}",
                     headers=UA, timeout=30)
    r.raise_for_status()
    ns = {"a": "http://www.w3.org/2005/Atom", "m": "http://search.yahoo.com/mrss/",
          "yt": "http://www.youtube.com/xml/schemas/2015"}
    root = ET.fromstring(r.content)
    out = []
    for e in root.findall("a:entry", ns):
        vid = e.find("yt:videoId", ns).text
        title = e.find("a:title", ns).text or ""
        pub = e.find("a:published", ns).text
        views = 0
        stat = e.find(".//m:statistics", ns)
        if stat is not None:
            views = int(stat.get("views", 0))
        out.append({"id": vid, "title": title[:70], "published": pub, "views": views})
    return out


def cmd_scout():
    c = cfg()
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    state_p = DATA / "scout_state.json"
    prev = json.loads(state_p.read_text()) if state_p.exists() else {}
    cur = {"ts": now, "videos": {}}
    risers = []
    for niche, chans in c["competitors"].items():
        for chan in chans:
            try:
                vids = rss(chan["id"])
            except Exception as e:
                print(f"[scout] {chan.get('label', chan['id'])}: {e}", file=sys.stderr)
                continue
            for v in vids:
                cur["videos"][v["id"]] = {"views": v["views"], "title": v["title"],
                                          "chan": chan.get("label", chan["id"]),
                                          "niche": niche, "published": v["published"]}
                old = prev.get("videos", {}).get(v["id"])
                if old and prev.get("ts"):
                    hrs = (dt.datetime.fromisoformat(now)
                           - dt.datetime.fromisoformat(prev["ts"])).total_seconds() / 3600
                    if hrs > 0.2:
                        vph = (v["views"] - old["views"]) / hrs
                        if vph > 0:
                            risers.append((vph, v, chan.get("label", ""), niche))
    state_p.write_text(json.dumps(cur, ensure_ascii=False))
    risers.sort(key=lambda t: -t[0])
    print(f"scout @ {now}: {len(cur['videos'])} видео у конкурентов")
    for vph, v, lab, niche in risers[:12]:
        print(f"  {vph:8.0f} views/ч | [{niche}] {lab} | {v['title']} | {v['views']:,}")
    if not risers:
        print("  (первый замер — скорость появится со второго прогона)")


def cmd_keywords(seed):
    seen = {}
    for suf in [""] + list(string.ascii_lowercase[:12]):
        q = f"{seed} {suf}".strip()
        try:
            r = requests.get("https://suggestqueries.google.com/complete/search",
                             params={"client": "firefox", "ds": "yt", "q": q}, headers=UA, timeout=15)
            for term in r.json()[1]:
                seen.setdefault(term, 0)
        except Exception as e:
            print(f"[keywords] {q}: {e}", file=sys.stderr)
            continue
    for t in list(seen)[:40]:
        print(" ", t)


def cmd_discover(query):
    r = api("search", part="snippet", q=query, type="video", videoDuration="short",
            order="viewCount", maxResults=25, publishedAfter="2026-06-01T00:00:00Z")
    chans = {}
    for it in r.get("items", []):
        cid = it["snippet"]["channelId"]
        chans.setdefault(cid, {"title": it["snippet"]["channelTitle"], "hits": 0})
        chans[cid]["hits"] += 1
    st = api("channels", part="statistics", id=",".join(list(chans)[:20]))
    for i in st.get("items", []):
        chans[i["id"]]["subs"] = int(i["statistics"].get("subscriberCount", 0))
        chans[i["id"]]["views"] = int(i["statistics"].get("viewCount", 0))
    for cid, m in sorted(chans.items(), key=lambda kv: -kv[1].get("views", 0)):
        print(f"  {cid} | {m['title'][:35]:35s} | subs {m.get('subs', 0):>9,} | views {m.get('views', 0):>13,} | hits {m['hits']}")


def cmd_indicators(query, max_age_days=90, max_videos=50, min_views=100_000):
    """каналы-индикаторы по методе YouTube Lab: новые, мало видео, аномальный рост"""
    r = api("search", part="snippet", q=query, type="video", order="viewCount",
            maxResults=50, publishedAfter=(dt.datetime.now(dt.timezone.utc)
                                           - dt.timedelta(days=45)).strftime("%Y-%m-%dT00:00:00Z"))
    cids = list({it["snippet"]["channelId"] for it in r.get("items", [])})
    found = []
    for i in range(0, len(cids), 50):
        st = api("channels", part="snippet,statistics", id=",".join(cids[i:i + 50]))
        for c in st.get("items", []):
            born = dt.datetime.fromisoformat(c["snippet"]["publishedAt"].replace("Z", "+00:00"))
            age = (dt.datetime.now(dt.timezone.utc) - born).days
            vids = int(c["statistics"].get("videoCount", 0))
            views = int(c["statistics"].get("viewCount", 0))
            subs = int(c["statistics"].get("subscriberCount", 0))
            if age <= max_age_days and 0 < vids <= max_videos and views >= min_views:
                found.append((views, age, vids, subs, c["id"], c["snippet"]["title"]))
    found.sort(key=lambda t: -t[0])
    print(f"ИНДИКАТОРЫ '{query}': канал ≤{max_age_days}д, ≤{max_videos} видео, ≥{min_views:,} просм.")
    for views, age, vids, subs, cid, title in found:
        print(f"  {views:>12,} просм | {age:>3}д | {vids:>3} видео | {subs:>7,} подп | {cid} | {title[:40]}")
    if not found:
        print("  (не найдено — расширь запрос или подними max_age_days)")


def _load_scout_state():
    p = DATA / "scout_state.json"
    if not p.exists():
        sys.exit("нет scout_state.json — сначала запусти: vidiq.py scout")
    return json.loads(p.read_text())


def cmd_outliers(min_ratio=3.0, min_views=10_000):
    """видео сильно выше медианы своего канала — тема, доказанно стреляющая"""
    import statistics
    st = _load_scout_state()
    by_chan = {}
    for v in st["videos"].values():
        by_chan.setdefault(v["chan"], []).append(v)
    rows = []
    for chan, vids in by_chan.items():
        if len(vids) < 5:
            continue
        med = statistics.median(x["views"] for x in vids)
        if med < 1:
            continue
        for v in vids:
            r = v["views"] / med
            if r >= min_ratio and v["views"] >= min_views:
                rows.append((r, v, chan))
    rows.sort(key=lambda t: -t[0])
    print(f"ВЫБРОСЫ (≥{min_ratio}× медианы канала, ≥{min_views:,} просм.) — готовые рабочие темы:")
    for r, v, chan in rows[:20]:
        print(f"  ×{r:5.1f} | [{v['niche']}] {chan} | {v['title']} | {v['views']:,} | {v['published'][:10]}")
    if not rows:
        print("  (выбросов нет)")


def cmd_besttime():
    """когда постят стреляющие видео конкурентов; взвешено log-просмотрами, время Томска UTC+7"""
    import math
    st = _load_scout_state()
    tomsk = dt.timezone(dt.timedelta(hours=7))
    days = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
    slots = {}
    n = 0
    for v in st["videos"].values():
        try:
            t = dt.datetime.fromisoformat(v["published"]).astimezone(tomsk)
        except ValueError:
            continue
        w = math.log10(v["views"] + 10)
        key = (v["niche"], t.weekday(), t.hour)
        slots[key] = slots.get(key, 0) + w
        n += 1
    print(f"ЛУЧШЕЕ ВРЕМЯ ПУБЛИКАЦИИ (по {n} видео конкурентов, время Томска):")
    for niche in sorted({k[0] for k in slots}):
        top = sorted(((w, d, h) for (nn, d, h), w in slots.items() if nn == niche), reverse=True)[:3]
        line = ", ".join(f"{days[d]} {h:02d}:00-{h + 1:02d}:00" for _, d, h in top)
        print(f"  [{niche}] {line}")


def cmd_report():
    files = sorted(DATA.glob("ours_2*.json"))
    if not files:
        print("нет снапшотов")
        return
    latest = json.loads(files[-1].read_text())
    print(f"# vidIQ дайджест {latest['date']}")
    for k, ch in latest["channels"].items():
        print(f"\n## {ch['title']} — {ch['subs']} подп., {ch['views']:,} просм., {ch['videos']} видео")
        for v in ch["latest"][:5]:
            print(f"  {v['views']:>8,} | 👍{v['likes']:<4} 💬{v['comments']:<3} | {v['published']} | {v['title']}")


if __name__ == "__main__":
    cmds = {"ids": cmd_ids, "snapshot": cmd_snapshot, "scout": cmd_scout, "report": cmd_report,
            "outliers": cmd_outliers, "besttime": cmd_besttime}
    if len(sys.argv) < 2:
        print(__doc__)
    elif sys.argv[1] in cmds:
        cmds[sys.argv[1]]()
    elif sys.argv[1] == "keywords":
        cmd_keywords(" ".join(sys.argv[2:]))
    elif sys.argv[1] == "discover":
        cmd_discover(" ".join(sys.argv[2:]))
    elif sys.argv[1] == "indicators":
        cmd_indicators(" ".join(sys.argv[2:]))
    else:
        print(__doc__)

#!/usr/bin/env python3
"""Сверка реестра использованных пластин с тем, что реально лежит на каналах.

Реестр — единственная защита от повторной публикации одной пластины, и читают
его глазами, а не скриптом. Поэтому он и разошёлся: копия в облаке и копия на
ПК жили порознь, схемы у них разные, и однажды записи уже терялись.

Скрипт берёт третий источник, которому можно верить, — список роликов на самом
канале через YouTube API — и показывает расхождения. Ничего не удаляет и на
YouTube не пишет: только GET.

    python3 reconcile_ledger.py                        отчёт по облачному реестру
    python3 reconcile_ledger.py --merge A.json B.json --out merged.json

Токены берутся из $YT_SECRETS (по умолчанию ~/.config/youtube).
"""
import argparse, json, os, sys, urllib.parse, urllib.request, urllib.error

SEC = os.environ.get("YT_SECRETS", os.path.expanduser("~/.config/youtube"))
API = "https://www.googleapis.com/youtube/v3"


def access_token(token_path):
    cfg = json.load(open(os.path.join(SEC, "oauth_client.json"), encoding="utf-8"))
    rt = json.load(open(token_path, encoding="utf-8"))["refresh_token"]
    body = urllib.parse.urlencode({
        "client_id": cfg["client_id"], "client_secret": cfg["client_secret"],
        "refresh_token": rt, "grant_type": "refresh_token"}).encode()
    try:
        return json.load(urllib.request.urlopen(
            "https://oauth2.googleapis.com/token", body, timeout=60))["access_token"]
    except urllib.error.HTTPError as e:
        # 401/invalid_client — это про ПАРУ client_id+client_secret, а не про
        # сам токен: секрет сброшен или взят от другого клиента. 400 —
        # про токен: отозван, в том числе семидневным отзывом в режиме
        # «Тестирование». Подсказка «снова Тестирование» на 401 уже один раз
        # увела диагностику не туда.
        why = ("секрет клиента не подходит — сброшен в консоли или от другого "
               "клиента" if e.code == 401 else
               "refresh-токен отозван — перевыпусти через publish/oauth_flow.py")
        print(f"  {os.path.basename(token_path)}: {e.code} — {why}",
              file=sys.stderr)
        return None


def api(at, path, params):
    req = urllib.request.Request(f"{API}/{path}?" + urllib.parse.urlencode(params),
                                 headers={"Authorization": "Bearer " + at})
    return json.load(urllib.request.urlopen(req, timeout=120))


def channel_videos(at):
    ch = api(at, "channels", {"part": "snippet,contentDetails", "mine": "true"})["items"][0]
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    out, page = [], None
    while True:
        p = {"part": "contentDetails", "playlistId": uploads, "maxResults": 50}
        if page:
            p["pageToken"] = page
        r = api(at, "playlistItems", p)
        ids = [i["contentDetails"]["videoId"] for i in r["items"]]
        if ids:
            for v in api(at, "videos", {"part": "snippet,status", "id": ",".join(ids)})["items"]:
                out.append({"video_id": v["id"], "title": v["snippet"]["title"],
                            "published": v["snippet"]["publishedAt"][:10],
                            "privacy": v["status"]["privacyStatus"]})
        page = r.get("nextPageToken")
        if not page:
            break
    return ch["snippet"]["title"], ch["id"], out


def norm_loc(v):
    """Один и тот же номер LOC пишут по-разному: 2017645715 и (dag)2017645715.
    Без приведения к одному виду проверка «эту пластину уже брали?» промахнётся
    и мы выпустим повтор. Скобочный префикс носителя (dag, dig) отбрасываем."""
    v = (v or "").strip().lower()
    for pref in ("(dag)", "(dig)", "(ppmsca)", "(cph)"):
        if v.startswith(pref):
            v = v[len(pref):]
    return v


def read_ledger(path):
    """Понимает обе схемы: облачную (used) и ПК-шную (entries)."""
    d = json.load(open(path, encoding="utf-8"))
    rows = d["used"] if isinstance(d.get("used"), list) else d.get("entries") or []
    norm = []
    for r in rows:
        if isinstance(r, dict):
            # Сведённый реестр держит список video_ids, исходные — одиночный
            # video_id. Читать надо оба: после сведения 04.09 скрипт видел
            # только video_id, не находил его ни у одной записи и печатал
            # безупречно зелёный отчёт на пустом месте.
            vids = r.get("video_ids") or ([r["video_id"]] if r.get("video_id") else [])
            norm.append({"loc_id": norm_loc(r.get("loc_id") or r.get("loc_item")
                                            or r.get("short_id")),
                         "video_ids": [v for v in vids if v],
                         "subject": r.get("subject") or r.get("note") or "",
                         # used/done — опубликовано, брать нельзя никогда.
                         # prepared — занято под будущий ролик, чужим не отдавать,
                         # но нашим опубликовать ещё предстоит. Разница важна:
                         # свалив prepared в used, мы бы сами себе запретили
                         # выпускать уже подготовленную пластину.
                         "status": r.get("status") or "",
                         "src": os.path.basename(path)})
    return d, norm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--merge", nargs="*", default=[])
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    print("== каналы (истина в последней инстанции) ==")
    live = {}
    tokens = sorted(f for f in os.listdir(SEC)
                    if f.startswith("token_")) if os.path.isdir(SEC) else []
    if not tokens:
        print(f"  нет ни одного token_*.json в {SEC}", file=sys.stderr)
    for t in tokens:
        at = access_token(os.path.join(SEC, t))
        if not at:
            continue
        title, cid, vids = channel_videos(at)
        live[cid] = (title, vids)
        print(f"  {title} ({cid}): роликов {len(vids)}")
        for v in vids:
            print(f"      {v['video_id']}  {v['published']}  {v['privacy']:8s} {v['title'][:52]}")

    here = os.path.dirname(os.path.abspath(__file__))
    if not live:
        print("\n  СВЕРКА НЕ ВЫПОЛНЕНА: ни один токен не дал доступа к каналу.",
              file=sys.stderr)
        print("  Сравнивать реестр не с чем. Пустой список каналов даёт "
              "безупречный отчёт\n  на пустом месте — не принимай его за "
              "порядок. Перевыпусти токен:\n"
              "      python3 ../publish/oauth_flow.py <канал> --force",
              file=sys.stderr)
        sys.exit(2)

    ledgers = a.merge or [os.path.join(here, "used_photos_ledger.json")]
    print("\n== реестры ==")
    allrows = []
    for p in ledgers:
        if not os.path.exists(p):
            print(f"  {p} — НЕТ ФАЙЛА")
            continue
        raw, rows = read_ledger(p)
        print(f"  {os.path.basename(p)}: записей {len(rows)}, ключи {list(raw.keys())}")
        allrows += rows

    by_vid = {}
    for r in allrows:
        for v in r["video_ids"]:
            by_vid.setdefault(v, []).append(r)
    live_ids = {v["video_id"]: (t, v) for t, vs in live.values() for v in vs}

    print("\n== расхождения ==")
    miss = [v for v in live_ids if v not in by_vid]
    ghost = [v for v in by_vid if v and v not in live_ids]
    print(f"  на канале есть, в реестрах нет: {len(miss)}")
    for vid in miss:
        t, v = live_ids[vid]
        print(f"      {vid}  {v['published']}  {v['privacy']:8s} {v['title'][:52]}")
    print(f"  в реестрах есть, на каналах нет: {len(ghost)}")
    for vid in ghost:
        print(f"      {vid}  {by_vid[vid][0]['subject'][:52]}")

    locs, statuses = {}, {}
    for r in allrows:
        if r["loc_id"]:
            locs.setdefault(r["loc_id"], set()).update(r["video_ids"])
            if r["status"]:
                statuses.setdefault(r["loc_id"], set()).add(r["status"])
    dup = {k: v for k, v in locs.items() if len([x for x in v if x]) > 1}
    print(f"  один loc_id на нескольких роликах: {len(dup)}")
    for k, v in dup.items():
        print(f"      {k} -> {sorted(x for x in v if x)}")
    print(f"\n  уникальных loc_id в реестрах: {len(locs)}")

    if a.out:
        merged = {
            "_rule": "НИКОГДА не использовать loc_id из этого списка повторно. "
                     "Сверять перед каждым рендером и перед каждой заливкой.",
            "_sources": [os.path.basename(p) for p in ledgers],
            "_status": "used/done — опубликовано, повтор запрещён. "
                       "prepared — занято под будущий ролик, другим не брать.",
            "used": sorted(({"loc_id": k, "video_ids": sorted(x for x in v if x),
                             "status": "/".join(sorted(statuses.get(k, {"used"}))),
                             "subject": next((r["subject"] for r in allrows
                                              if r["loc_id"] == k and r["subject"]), "")}
                            for k, v in locs.items()), key=lambda r: r["loc_id"]),
        }
        json.dump(merged, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"  сведено в {a.out}: {len(merged['used'])} loc_id")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Заливка ролика на YouTube с проверкой ПОСЛЕ — запускается там, где лежит файл.

Ролик и обложка живут на ПК, поэтому и заливка идёт оттуда: перекладывать файл
в облако пробовали шесть раз, каждый раз упирались в права. Здесь файл никуда
не едет.

Без --confirm скрипт ничего не заливает, а печатает, что собирается сделать.
Правило Седрака: ни один ролик не уходит без его отдельного слова, каждый раз
заново. Флаг --confirm и есть это слово, его ставит человек, не агент.

    python yt_publish.py --plan  meta.json                # показать и выйти
    python yt_publish.py --confirm meta.json              # залить

meta.json:
{
  "token":       "C:/pixelpolish/secrets/token_photorescue_full.json",
  "video":       "D:/PixelPolish/ШОРТСЫ/twogirls1844_v5_zoom_in.mp4",
  "thumbnail":   "D:/PixelPolish/ШОРТСЫ/twogirls1844_v5_cover.jpg",
  "title":       "...",
  "description": "...",
  "tags":        ["...", "..."],
  "categoryId":  "27",
  "privacy":     "private",
  "publishAt":   "2026-09-04T17:00:00Z",
  "madeForKids": false,
  "synthetic":   true
}
"""
import argparse, json, os, sys, time
import urllib.error, urllib.parse, urllib.request

CLIENT = os.environ.get("YT_OAUTH_CLIENT", "C:/pixelpolish/secrets/oauth_client.json")
API = "https://www.googleapis.com/youtube/v3"
UPLOAD = "https://www.googleapis.com/upload/youtube/v3"
CHUNK = 8 * 1024 * 1024


def die(msg):
    print("ОСТАНОВ:", msg, file=sys.stderr)
    sys.exit(1)


def access_token(token_path):
    cfg = json.load(open(CLIENT, encoding="utf-8"))
    rt = json.load(open(token_path, encoding="utf-8"))["refresh_token"]
    body = urllib.parse.urlencode({
        "client_id": cfg["client_id"], "client_secret": cfg["client_secret"],
        "refresh_token": rt, "grant_type": "refresh_token"}).encode()
    try:
        return json.load(urllib.request.urlopen(
            "https://oauth2.googleapis.com/token", body, timeout=60))["access_token"]
    except urllib.error.HTTPError as e:
        die(f"токен не обновился ({e.code}): {e.read().decode()[:200]}\n"
            "        Проверь, что приложение выведено из режима «Тестирование» — "
            "в нём Google отзывает refresh-токены каждые 7 дней.")


def api(at, method, path, params=None, body=None):
    url = f"{API}/{path}" + ("?" + urllib.parse.urlencode(params) if params else "")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": "Bearer " + at, "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=120))


def whose_token(at):
    it = api(at, "GET", "channels", {"part": "snippet", "mine": "true"})["items"][0]
    return it["snippet"]["title"], it["id"]


def build_body(m):
    snippet = {"title": m["title"], "description": m["description"],
               "tags": m.get("tags", []), "categoryId": m.get("categoryId", "27")}
    if m.get("defaultLanguage"):
        snippet["defaultLanguage"] = m["defaultLanguage"]
    status = {"privacyStatus": m.get("privacy", "private"),
              "selfDeclaredMadeForKids": bool(m.get("madeForKids", False)),
              "containsSyntheticMedia": bool(m.get("synthetic", False))}
    if m.get("publishAt"):
        status["privacyStatus"] = "private"        # publishAt работает только с private
        status["publishAt"] = m["publishAt"]
    return {"snippet": snippet, "status": status}


def upload(at, m):
    body = build_body(m)
    size = os.path.getsize(m["video"])
    req = urllib.request.Request(
        f"{UPLOAD}/videos?" + urllib.parse.urlencode(
            {"part": "snippet,status", "uploadType": "resumable"}),
        data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": "Bearer " + at, "Content-Type": "application/json",
                 "X-Upload-Content-Length": str(size),
                 "X-Upload-Content-Type": "video/*"})
    session_url = urllib.request.urlopen(req, timeout=120).headers["Location"]
    if not session_url:
        die("сервер не выдал адрес сессии загрузки")

    sent = 0
    with open(m["video"], "rb") as f:
        while sent < size:
            block = f.read(CHUNK)
            end = sent + len(block) - 1
            r = urllib.request.Request(session_url, data=block, method="PUT", headers={
                "Content-Length": str(len(block)),
                "Content-Range": f"bytes {sent}-{end}/{size}"})
            for attempt in range(5):
                try:
                    resp = urllib.request.urlopen(r, timeout=600)
                    return json.load(resp)                       # 200 -> залито целиком
                except urllib.error.HTTPError as e:
                    if e.code == 308:                            # кусок принят, дальше
                        break
                    if e.code in (500, 502, 503, 504) and attempt < 4:
                        time.sleep(2 ** attempt)
                        continue
                    die(f"загрузка отбита ({e.code}): {e.read().decode()[:300]}")
            sent += len(block)
            print(f"    {sent/size:6.1%}", flush=True)
    die("файл кончился, а сервер так и не подтвердил приём")


def set_thumbnail(at, video_id, path):
    data = open(path, "rb").read()
    req = urllib.request.Request(
        f"{UPLOAD}/thumbnails/set?videoId={video_id}", data=data, method="POST",
        headers={"Authorization": "Bearer " + at, "Content-Type": "image/jpeg",
                 "Content-Length": str(len(data))})
    urllib.request.urlopen(req, timeout=180)


def verify(at, video_id, m):
    """Читаем с сервера то, что записали. YouTube молча теряет поля, если их
    не переслать целиком, поэтому верим не своему запросу, а ответу."""
    it = api(at, "GET", "videos", {"part": "snippet,status", "id": video_id})["items"][0]
    s, st = it["snippet"], it["status"]
    checks = [
        ("заголовок", s["title"], m["title"]),
        ("описание", s["description"].strip(), m["description"].strip()),
        ("теги", sorted(s.get("tags", [])), sorted(m.get("tags", []))),
        ("категория", s.get("categoryId"), m.get("categoryId", "27")),
        ("доступ", st.get("privacyStatus"), "private" if m.get("publishAt")
                                            else m.get("privacy", "private")),
        ("для детей", st.get("selfDeclaredMadeForKids"), bool(m.get("madeForKids", False))),
    ]
    if m.get("publishAt"):
        checks.append(("время публикации", st.get("publishAt"), m["publishAt"]))
    bad = [(n, got, want) for n, got, want in checks if got != want]
    for n, got, want in checks:
        print(f"    {'ok ' if (n, got, want) not in bad else 'НЕТ'} {n}")
    if bad:
        print("\n  РАСХОЖДЕНИЯ:")
        for n, got, want in bad:
            print(f"    {n}: на сервере {got!r}, ожидали {want!r}")
    # containsSyntheticMedia на чтение не возвращается — проверить нечем, помечаем
    print("    ??  метка синтетического контента — API её на чтение не отдаёт, "
          "проверь глазами в Студии")
    return not bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("meta")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--plan", action="store_true", help="показать план и выйти")
    g.add_argument("--confirm", action="store_true", help="слово Седрака: лить")
    n = ap.parse_args()

    m = json.load(open(n.meta, encoding="utf-8"))
    for k in ("token", "video", "title", "description"):
        if not m.get(k):
            die(f"в {n.meta} нет поля {k}")
    for k in ("video", "thumbnail"):
        if m.get(k) and not os.path.exists(m[k]):
            die(f"нет файла {k}: {m[k]}")

    at = access_token(m["token"])
    title, cid = whose_token(at)

    print(f"  канал      {title}  ({cid})")
    print(f"  файл       {m['video']}  ({os.path.getsize(m['video'])/1e6:.1f} МБ)")
    print(f"  обложка    {m.get('thumbnail') or '— нет'}")
    print(f"  заголовок  {m['title']}")
    print(f"  доступ     {m.get('privacy', 'private')}"
          + (f", публикация {m['publishAt']}" if m.get("publishAt") else ""))
    print(f"  теги       {len(m.get('tags', []))} шт.")
    print(f"  синтетика  {'да' if m.get('synthetic') else 'НЕТ — проверь, у нас ИИ в кадре'}")

    if n.plan:
        print("\n  Это только план. Заливки не было. Для заливки нужен --confirm,")
        print("  и ставит его человек: ни один ролик не уходит без отдельного слова.")
        return

    print("\n  Заливаю…")
    v = upload(at, m)
    vid = v["id"]
    print(f"  залито: https://youtube.com/watch?v={vid}")

    if m.get("thumbnail"):
        set_thumbnail(at, vid, m["thumbnail"])
        print("  обложка поставлена")

    print("\n  Проверка — читаю с сервера то, что записали:")
    ok = verify(at, vid, m)
    print("\n  " + ("ВСЁ СОШЛОСЬ." if ok else "ЕСТЬ РАСХОЖДЕНИЯ, СМОТРИ ВЫШЕ."))
    print(f"  id ролика: {vid}  — внеси пластину в реестр used_photos_ledger.json")


if __name__ == "__main__":
    main()

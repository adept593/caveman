# -*- coding: utf-8 -*-
"""Перепрофилирование каналов: название, описание, ключевые слова, страна US, язык en.

  python reprofile.py --plan    показать, ничего не менять
  python reprofile.py --apply   применить (channels.update, 50 ед. квоты на канал)

Меняется только brandingSettings. Ролики, хэндл (@...) и аватар не трогаются —
хэндл и аватар меняются вручную в YouTube Studio. Смена названия — не чаще 3 раз в 90 дней.
"""
import json, sys, io, os, requests
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
SEC = Path(os.environ["YT_SECRETS"]); YT = "https://www.googleapis.com/youtube/v3"


def access(label):
    c = json.loads((SEC / "oauth_client.json").read_text(encoding="utf-8"))
    t = json.loads((SEC / f"token_{label}.json").read_text(encoding="utf-8"))
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": c["client_id"], "client_secret": c["client_secret"],
        "refresh_token": t["refresh_token"], "grant_type": "refresh_token"}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


PLAN = {
    "yearsinaminute": {
        "id": "UCW2PAiXy58LRIzbN7V-9t8g", "title": "Years in a Minute",
        "description": ("What if a country became a superpower? What if two nations swapped places on the map? "
                        "Alternate history and map timelapses in under a minute.\n"
                        "New map every day. Tell us your country in the comments."),
        "keywords": "\"alternate history\" \"what if\" maps \"map timelapse\" geography countries superpower history shorts"},
    "restoredhistory_full": {
        "id": "UCvldpC8yVoFd8mmKQFQ8MxQ", "title": "Scripture Lens",
        "description": ("Bible stories brought to life with cinematic AI visuals. Moses, Daniel, Jonah, David — "
                        "one story, one minute.\nNew story daily. Amen."),
        "keywords": "bible \"bible stories\" jesus christian faith scripture \"ai video\" \"old testament\" shorts"},
    "photorescue_full": {
        "id": "UC4CKS_ETfECsmRbtOpqy_HA", "title": "Flag IQ Arena",
        "description": ("Guess the flag in 3 seconds. Easy, medium, hard, extreme — can you name all 10?\n"
                        "New quiz every day. Comment your score."),
        "keywords": "flags \"flag quiz\" \"guess the flag\" geography quiz countries trivia challenge shorts"},
}

apply = "--apply" in sys.argv
for label, p in PLAN.items():
    print(f"\n{label}: -> «{p['title']}» | US / en\n  {p['description'].splitlines()[0]}")
    if not apply:
        continue
    tok = access(label)
    body = {"id": p["id"], "brandingSettings": {"channel": {
        "title": p["title"], "description": p["description"], "keywords": p["keywords"],
        "country": "US", "defaultLanguage": "en"}}}
    r = requests.put(f"{YT}/channels", params={"part": "brandingSettings"},
                     headers={"Authorization": f"Bearer {tok}"}, json=body, timeout=30)
    ok = r.ok
    print("  ->", r.status_code, r.json().get("brandingSettings", {}).get("channel", {}).get("title") if ok else r.text[:300])

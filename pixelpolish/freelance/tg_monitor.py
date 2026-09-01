#!/usr/bin/env python3
"""Монитор публичных ТГ-каналов с заказами (через веб-превью t.me/s/ — без аккаунта).
Вахта дёргает tick ежечасно: новые посты → фильтр по нишам → data/tg_matches.jsonl.
Отклики на найденное — ТОЛЬКО с Telegram Седрака (у агентов аккаунта нет и не будет).
"""
import html
import json
import pathlib
import re
import sys

import requests

HERE = pathlib.Path(__file__).parent
DATA = HERE / "data"
DATA.mkdir(exist_ok=True)
SEEN_P = DATA / "tg_seen.json"

CHANNELS = ["freelancetaverna", "normrabota"]
KEYWORDS = ["видео", "монтаж", "ролик", "shorts", "рилс", "reels", "обложк", "баннер",
            "презентац", "дизайн", "бот", "telegram-бот", "парсинг", "таблиц",
            "озвучк", "субтитр", "сценар", "реставрац", "фото", "нейросет", "ии ", "ai "]
STOP = ["диплом", "курсов", "взлом", "накрутк", "18+", "казино", "ставк",
        "перейд[её]м в telegram до", "оплата напрямую", "подтверди карту"]


def fetch(ch):
    r = requests.get(f"https://t.me/s/{ch}", timeout=20,
                     headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    posts = []
    for block in re.split(r'tgme_widget_message_wrap', r.text)[1:]:
        pid = re.search(r'data-post="([^"]+)"', block)
        txt = re.search(r'tgme_widget_message_text[^>]*>(.*?)</div>', block, re.S)
        if pid and txt:
            clean = html.unescape(re.sub(r"<[^>]+>", " ", txt.group(1)))
            posts.append((pid.group(1), " ".join(clean.split())))
    return posts


def cmd_tick():
    seen = set(json.loads(SEEN_P.read_text())) if SEEN_P.exists() else set()
    first_run = not seen
    hits = 0
    for ch in CHANNELS:
        try:
            posts = fetch(ch)
        except Exception as e:
            print(f"[tg] {ch}: {e}", file=sys.stderr)
            continue
        for pid, text in posts:
            if pid in seen:
                continue
            seen.add(pid)
            low = text.lower()
            if first_run:
                continue  # первый прогон — только запоминаем, не спамим старьём
            if any(re.search(s, low) for s in STOP):
                continue
            if any(k in low for k in KEYWORDS):
                hits += 1
                with open(DATA / "tg_matches.jsonl", "a") as f:
                    f.write(json.dumps({"post": pid, "text": text[:400]},
                                       ensure_ascii=False) + "\n")
                print(f"ЗАКАЗ https://t.me/{pid} | {text[:120]}")
    SEEN_P.write_text(json.dumps(sorted(seen)[-2000:]))
    print(f"[tg] каналов {len(CHANNELS)}, новых совпадений {hits}")


if __name__ == "__main__":
    cmd_tick()

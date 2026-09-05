# -*- coding: utf-8 -*-
"""Браузер для YouTube Studio на Playwright с постоянным профилем (логин делает владелец один раз).

  python yt_browser.py open                      открыть окно Studio; войти вручную; окно ждёт до 30 мин,
                                                 закрывается само, когда открылась панель канала
  python yt_browser.py brand <channel_id> <avatar.png> <banner.png>
                                                 загрузить фото профиля и баннер канала (Настройка канала → Профиль)
  python yt_browser.py shot <url> <out.png>      скриншот страницы под текущим профилем
Профиль: D:\PixelPolish\browser_profile (cookies остаются между запусками).
"""
import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8")
PROFILE = Path(r"D:\PixelPolish\browser_profile"); SHOTS = Path(r"D:\PixelPolish\channel_art\2026-09\shots"); SHOTS.mkdir(parents=True, exist_ok=True)


def ctx(p, headless=False):
    kw = dict(headless=False, viewport={"width": 1400, "height": 950}, locale="ru-RU",
              args=["--disable-blink-features=AutomationControlled"] + (["--window-position=-32000,-32000"] if headless else []))
    try:
        return p.chromium.launch_persistent_context(str(PROFILE), channel="chrome", **kw)     # настоящий Chrome (Studio не любит chromium)
    except Exception as e:
        print("chrome не найден, chromium:", str(e)[:80]); return p.chromium.launch_persistent_context(str(PROFILE), **kw)


def cmd_open():
    with sync_playwright() as p:
        c = ctx(p); pg = c.pages[0] if c.pages else c.new_page()
        pg.goto("https://studio.youtube.com/", wait_until="domcontentloaded")
        print("окно открыто — войди в аккаунт; жду панель канала (до 30 мин)", flush=True)
        t0 = time.time()
        while time.time() - t0 < 1800:
            time.sleep(3)
            try:
                if "studio.youtube.com/channel/" in pg.url: break
            except Exception: pass
        print("вход есть:", pg.url); time.sleep(3); c.close()


def cmd_brand(cid, avatar, banner):
    with sync_playwright() as p:
        c = ctx(p); pg = c.pages[0] if c.pages else c.new_page()
        pg.goto(f"https://studio.youtube.com/channel/{cid}/editing/profile", wait_until="domcontentloaded"); pg.wait_for_timeout(6000)
        if "accounts.google.com" in pg.url: print("НЕТ ВХОДА — сначала: python yt_browser.py open"); c.close(); return
        for label, path, idx in (("Баннер", banner, 0), ("Фото профиля", avatar, 1)):
            with pg.expect_file_chooser(timeout=20000) as fc:
                pg.get_by_role("button", name="Изменить").nth(idx).click()
            fc.value.set_files(path); pg.wait_for_timeout(4000)
            pg.screenshot(path=str(SHOTS / f"{cid}_{idx}_crop.png"))
            for name in ("Готово", "Done"):
                b = pg.get_by_role("button", name=name)
                if b.count(): b.first.click(); break
            pg.wait_for_timeout(3000); print(label, "выбран")
        pg.get_by_role("button", name="Опубликовать").click(); pg.wait_for_timeout(8000)
        pg.screenshot(path=str(SHOTS / f"{cid}_done.png")); print("опубликовано:", SHOTS / f"{cid}_done.png"); c.close()


def cmd_shot(url, out):
    with sync_playwright() as p:
        c = ctx(p, headless=True); pg = c.pages[0] if c.pages else c.new_page()
        pg.goto(url, wait_until="domcontentloaded"); pg.wait_for_timeout(5000); pg.screenshot(path=out); print(out, pg.url); c.close()


if __name__ == "__main__":
    a = sys.argv[1:]
    {"open": lambda: cmd_open(), "brand": lambda: cmd_brand(a[1], a[2], a[3]), "shot": lambda: cmd_shot(a[1], a[2])}[a[0]]()

#!/usr/bin/env python3
"""Выпуск refresh-токена канала YouTube. Вход выполняет только человек.

Клиент у нас типа «Телевизоры и устройства с ограниченным вводом» — у такого
вообще нет redirect URI, поэтому обычный вход через браузерное перенаправление
(и OAuth Playground) с ним не работает никогда. Единственный путь — device flow:
скрипт печатает короткий код, человек открывает страницу на любом устройстве,
входит в нужный аккаунт и вводит код. Скрипт всё это время просто ждёт.

    python3 oauth_flow.py photorescue_full
    python3 oauth_flow.py yearsinaminute

Кладёт результат в $YT_SECRETS/token_<label>.json как {"refresh_token": "..."}.
Существующий файл не перезаписывает без --force.

Скрипт НИКОГДА не вводит логин и пароль и не просит их. Он только показывает
код и ждёт. Если что-то требует ввести пароль — это не сюда.
"""
import argparse
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

SEC = pathlib.Path(os.environ.get("YT_SECRETS",
                                  pathlib.Path.home() / ".config" / "youtube"))
DEVICE = "https://oauth2.googleapis.com/device/code"
TOKEN = "https://oauth2.googleapis.com/token"
# Device flow принимает не любые области доступа. Проверено 04.09.2026:
#   youtube.upload    — ok
#   youtube           — ok (чтение и правка метаданных)
#   youtube.readonly  — ok
#   youtube.force-ssl — ОТКАЗ, "Invalid device flow scope"
# Поэтому force-ssl, который просят обычные примеры, сюда не годится.
SCOPE = ("https://www.googleapis.com/auth/youtube "
         "https://www.googleapis.com/auth/youtube.upload")


def post(url, data):
    req = urllib.request.Request(url, urllib.parse.urlencode(data).encode())
    try:
        return json.load(urllib.request.urlopen(req, timeout=60)), None
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return None, json.loads(body)
        except ValueError:
            return None, {"error": f"HTTP {e.code}", "raw": body[:200]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("label", help="имя канала: photorescue_full, "
                                  "restoredhistory_full, yearsinaminute")
    ap.add_argument("--force", action="store_true",
                    help="перезаписать существующий token_<label>.json")
    a = ap.parse_args()

    out = SEC / f"token_{a.label}.json"
    if out.exists() and not a.force:
        sys.exit(f"ОСТАНОВ: {out} уже есть. Перевыпуск — только с --force.")

    cfg_path = SEC / "oauth_client.json"
    if not cfg_path.exists():
        sys.exit(f"ОСТАНОВ: нет {cfg_path}.\n"
                 "        Нужен файл вида "
                 '{"client_id": "...", "client_secret": "..."}')
    cfg = json.loads(cfg_path.read_text())
    for k in ("client_id", "client_secret"):
        if k not in cfg:
            sys.exit(f"ОСТАНОВ: в oauth_client.json нет поля {k}. "
                     "Google отдаёт файл с обёрткой installed — "
                     "нужны только два поля, без обёртки.")

    dev, err = post(DEVICE, {"client_id": cfg["client_id"], "scope": SCOPE})
    if err:
        sys.exit(f"ОСТАНОВ: код устройства не выдан: {err}\n"
                 "        Обычно это значит, что тип клиента не «ТВ и устройства "
                 "с ограниченным вводом».")

    print("\n" + "=" * 58)
    print("  Открой на телефоне или в браузере:")
    print(f"      {dev['verification_url']}")
    print(f"  и введи код:   {dev['user_code']}")
    print("=" * 58)
    print(f"\n  Войди в аккаунт канала «{a.label}» и разреши доступ.")
    print("  Пароль вводишь только ты. Скрипт ждёт и ничего не вводит.\n")

    deadline = time.time() + dev.get("expires_in", 1800)
    interval = dev.get("interval", 5)
    while time.time() < deadline:
        time.sleep(interval)
        res, err = post(TOKEN, {
            "client_id": cfg["client_id"], "client_secret": cfg["client_secret"],
            "device_code": dev["device_code"],
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code"})
        if res and "refresh_token" in res:
            SEC.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps({"refresh_token": res["refresh_token"]}))
            try:
                os.chmod(out, 0o600)
            except OSError:
                pass
            print(f"  ГОТОВО. Токен записан: {out}")
            print("  Проверь: python3 ../state/reconcile_ledger.py")
            return
        code = (err or {}).get("error", "")
        if code == "authorization_pending":
            continue
        if code == "slow_down":
            interval += 5
            continue
        if code == "access_denied":
            sys.exit("ОСТАНОВ: доступ не разрешён — нажали «Отмена».")
        sys.exit(f"ОСТАНОВ: {err}")
    sys.exit("ОСТАНОВ: код истёк, никто не подтвердил. Запусти заново.")


if __name__ == "__main__":
    main()

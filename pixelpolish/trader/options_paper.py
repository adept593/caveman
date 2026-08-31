#!/usr/bin/env python3
"""PixelPolish Трейдер — опционный модуль (БУМАГА, ETH-опционы Deribit).
Реальных денег нет и не будет без отдельного решения Седрака.

Стратегии (по $1000 виртуальных):
  trend_call — покупает 1 недельный ATM-колл на свежем бычьем кроссе SMA24/168
               (сигнал берёт из data/state.json основного Трейдера), продаёт на
               медвежьем кроссе, иначе держит до экспирации.
  roll_call  — всегда держит 1 ближайший недельный ATM-колл; экспирация →
               расчёт по интринсику → сразу покупает следующий (демо теты).

Команды: tick | report. Данные: data/options_*.json[l].
Комиссия Deribit: 0.0003 ETH/контракт, но не более 12.5% премии.
"""
import json
import pathlib
import sys
import time

import requests

HERE = pathlib.Path(__file__).parent
DATA = HERE / "data"
DATA.mkdir(exist_ok=True)
ST_P = DATA / "options_state.json"
API = "https://www.deribit.com/api/v2/public"
START = 1000.0
STRATS = ("trend_call", "roll_call")


def api(path, **params):
    r = requests.get(f"{API}/{path}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()["result"]


def index_price():
    return float(api("get_index_price", index_name="eth_usd")["index_price"])


def pick_weekly_atm_call(idx):
    ins = api("get_instruments", currency="ETH", kind="option", expired="false")
    now = time.time() * 1000
    week = [i for i in ins if i["option_type"] == "call"
            and 4 * 86400000 <= i["expiration_timestamp"] - now <= 11 * 86400000]
    if not week:
        return None
    exp = min(i["expiration_timestamp"] for i in week)
    cands = [i for i in week if i["expiration_timestamp"] == exp]
    return min(cands, key=lambda i: abs(i["strike"] - idx))


def mark_usd(instrument, idx):
    t = api("ticker", instrument_name=instrument)
    return float(t["mark_price"]) * idx


def fee_usd(premium, idx):
    return min(0.0003 * idx, 0.125 * max(premium, 0.01))


def sma_regime():
    p = HERE / "data" / "state.json"
    if not p.exists():
        return None
    closes = [c[1] for c in json.loads(p.read_text()).get("ETH", {}).get("candles", [])]
    if len(closes) < 168:
        return None
    return sum(closes[-24:]) / 24 > sum(closes[-168:]) / 168


def log(path, obj):
    with open(DATA / path, "a") as f:
        f.write(json.dumps(obj) + "\n")


def open_call(s, idx, why):
    ins = pick_weekly_atm_call(idx)
    if not ins:
        return
    prem = mark_usd(ins["instrument_name"], idx)
    cost = prem + fee_usd(prem, idx)
    if cost > s["usd"]:
        log("options_trades.jsonl", {"ts": int(time.time()), "strat": s["name"],
                                     "skip": "не хватает капитала", "need": round(cost, 2)})
        return
    s["usd"] -= cost
    s["pos"] = {"ins": ins["instrument_name"], "strike": ins["strike"],
                "exp": ins["expiration_timestamp"], "entry": round(prem, 2)}
    log("options_trades.jsonl", {"ts": int(time.time()), "strat": s["name"], "side": "buy",
                                 "ins": ins["instrument_name"], "premium": round(prem, 2),
                                 "fee": round(fee_usd(prem, idx), 2), "why": why})


def close_pos(s, idx, why, settle=False):
    pos = s["pos"]
    val = max(0.0, idx - pos["strike"]) if settle else mark_usd(pos["ins"], idx)
    got = val - (0 if settle else fee_usd(val, idx))
    s["usd"] += max(got, 0.0)
    log("options_trades.jsonl", {"ts": int(time.time()), "strat": s["name"],
                                 "side": "settle" if settle else "sell", "ins": pos["ins"],
                                 "got": round(max(got, 0.0), 2), "entry": pos["entry"], "why": why})
    s["pos"] = None


def cmd_tick():
    st = json.loads(ST_P.read_text()) if ST_P.exists() else {
        "strats": {n: {"name": n, "usd": START, "pos": None} for n in STRATS},
        "prev_regime": None}
    idx = index_price()
    now = time.time() * 1000
    regime = sma_regime()
    fresh_bull = regime is True and st["prev_regime"] is False
    fresh_bear = regime is False and st["prev_regime"] is True
    for n in STRATS:
        s = st["strats"][n]
        if s["pos"] and now >= s["pos"]["exp"]:
            close_pos(s, idx, "экспирация", settle=True)
        if n == "trend_call":
            if s["pos"] and fresh_bear:
                close_pos(s, idx, "медвежий кросс SMA")
            if not s["pos"] and fresh_bull:
                open_call(s, idx, "бычий кросс SMA")
        else:  # roll_call
            if not s["pos"]:
                open_call(s, idx, "ролл: всегда в колле")
        eq = s["usd"] + (mark_usd(s["pos"]["ins"], idx) if s["pos"] else 0.0)
        log("options_equity.jsonl", {"ts": int(now / 1000), "strat": n, "eq": round(eq, 2)})
        print(f"{n}: ${eq:,.2f} | {s['pos']['ins'] if s['pos'] else 'без позиции'}")
    st["prev_regime"] = regime if regime is not None else st["prev_regime"]
    ST_P.write_text(json.dumps(st))


def cmd_report():
    if not ST_P.exists():
        sys.exit("нет состояния — сначала tick")
    st = json.loads(ST_P.read_text())
    idx = index_price()
    trades = {}
    tr = DATA / "options_trades.jsonl"
    if tr.exists():
        for line in tr.read_text().splitlines():
            t = json.loads(line)
            if "side" in t:
                trades[t["strat"]] = trades.get(t["strat"], 0) + 1
    print(f"ОПЦИОНЫ (бумага, ETH @ {idx:,.0f}, старт $1000):")
    for n in STRATS:
        s = st["strats"][n]
        pos = s["pos"]
        eq = s["usd"] + (mark_usd(pos["ins"], idx) if pos else 0.0)
        desc = f"{pos['ins']} (вход ${pos['entry']})" if pos else "без позиции"
        print(f"  {n:10s}: ${eq:8.2f} ({(eq / START - 1) * 100:+6.2f}%) | сделок {trades.get(n, 0)} | {desc}")


if __name__ == "__main__":
    {"tick": cmd_tick, "report": cmd_report}.get(
        sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__))()

#!/usr/bin/env python3
"""PixelPolish Трейдер — БУМАЖНЫЙ торговый агент. Реальных денег НЕТ и не будет
без отдельного решения Седрака (ключи бирж/платежи — только его руки).

Тело: этот скрипт (запускается вахтой раз в час, токенов не тратит).
Мозг: облачный управляющий читает report и решает, что менять.

Команды:
  tick    — подтянуть свечи Kraken, прогнать стратегии, записать сделки/эквити
  report  — сводка: эквити, PnL, просадка, сделки по каждой стратегии

Виртуальный капитал: $1000 на стратегию на актив. Комиссия 0.1% за сделку.
Стратегии: hold (купил и держи — эталон), sma (SMA24>SMA168 → в рынке),
rsi (RSI14<30 → купить, >70 → продать).
Данные: data/state.json, data/trades.jsonl, data/equity.jsonl (коммитятся в репо).
"""
import json
import pathlib
import sys

import requests

HERE = pathlib.Path(__file__).parent
DATA = HERE / "data"
DATA.mkdir(exist_ok=True)
STATE_P = DATA / "state.json"
ASSETS = {"BTC": "XBTUSD", "ETH": "ETHUSD"}
START_USD = 1000.0
FEE = 0.001
STRATS = ("hold", "sma", "rsi")


def fetch_candles(pair):
    r = requests.get("https://api.kraken.com/0/public/OHLC",
                     params={"pair": pair, "interval": 60}, timeout=30)
    r.raise_for_status()
    res = r.json()["result"]
    key = next(k for k in res if k != "last")
    # последняя свеча ещё не закрыта — отбрасываем
    return [[int(c[0]), float(c[4])] for c in res[key]][:-1]


def sma(closes, n):
    return sum(closes[-n:]) / n if len(closes) >= n else None


def rsi(closes, n=14):
    if len(closes) < n + 1:
        return None
    gains = losses = 0.0
    for a, b in zip(closes[-n - 1:-1], closes[-n:]):
        d = b - a
        gains += max(d, 0)
        losses += max(-d, 0)
    if losses == 0:
        return 100.0
    rs = gains / losses
    return 100 - 100 / (1 + rs)


def buy(p, price):  # весь USD в монету
    if p["usd"] > 0:
        p["coin"] += p["usd"] * (1 - FEE) / price
        p["usd"] = 0.0
        return True
    return False


def sell(p, price):  # всю монету в USD
    if p["coin"] > 0:
        p["usd"] += p["coin"] * price * (1 - FEE)
        p["coin"] = 0.0
        return True
    return False


def equity(p, price):
    return p["usd"] + p["coin"] * price


def log(path, obj):
    with open(DATA / path, "a") as f:
        f.write(json.dumps(obj) + "\n")


def cmd_tick():
    st = json.loads(STATE_P.read_text()) if STATE_P.exists() else {}
    for name, pair in ASSETS.items():
        try:
            candles = fetch_candles(pair)
        except Exception as e:
            print(f"[trader] {name}: {e}", file=sys.stderr)
            continue
        a = st.setdefault(name, {
            "candles": [], "last_ts": 0,
            "port": {s: {"usd": START_USD, "coin": 0.0} for s in STRATS}})
        known = {c[0] for c in a["candles"]}
        a["candles"] = sorted(a["candles"] + [c for c in candles if c[0] not in known])[-800:]
        fresh = [c for c in a["candles"] if c[0] > a["last_ts"]]
        boot = a["last_ts"] == 0
        for ts, price in fresh:
            closes = [c[1] for c in a["candles"] if c[0] <= ts]
            if boot and ts == fresh[-1][0]:  # первый запуск: hold покупает на последней свече
                buy(a["port"]["hold"], price)
                log("trades.jsonl", {"ts": ts, "asset": name, "strat": "hold", "side": "buy", "price": price})
            if not boot:
                f_, s_ = sma(closes, 24), sma(closes, 168)
                if f_ and s_:
                    p = a["port"]["sma"]
                    if f_ > s_ and buy(p, price):
                        log("trades.jsonl", {"ts": ts, "asset": name, "strat": "sma", "side": "buy", "price": price})
                    elif f_ < s_ and sell(p, price):
                        log("trades.jsonl", {"ts": ts, "asset": name, "strat": "sma", "side": "sell", "price": price})
                r = rsi(closes)
                if r is not None:
                    p = a["port"]["rsi"]
                    if r < 30 and buy(p, price):
                        log("trades.jsonl", {"ts": ts, "asset": name, "strat": "rsi", "side": "buy", "price": price, "rsi": round(r, 1)})
                    elif r > 70 and sell(p, price):
                        log("trades.jsonl", {"ts": ts, "asset": name, "strat": "rsi", "side": "sell", "price": price, "rsi": round(r, 1)})
            a["last_ts"] = ts
        if a["candles"]:
            ts, price = a["candles"][-1]
            for s in STRATS:
                log("equity.jsonl", {"ts": ts, "asset": name, "strat": s,
                                     "eq": round(equity(a["port"][s], price), 2)})
            print(f"{name}: цена {price:,.0f}, свечей {len(a['candles'])}, новых {len(fresh)}")
    STATE_P.write_text(json.dumps(st))


def cmd_report():
    if not STATE_P.exists():
        sys.exit("нет состояния — сначала tick")
    st = json.loads(STATE_P.read_text())
    peaks = {}
    dds = {}
    eq_p = DATA / "equity.jsonl"
    if eq_p.exists():
        for line in eq_p.read_text().splitlines():
            e = json.loads(line)
            k = (e["asset"], e["strat"])
            peaks[k] = max(peaks.get(k, 0), e["eq"])
            if peaks[k] > 0:
                dds[k] = max(dds.get(k, 0), (peaks[k] - e["eq"]) / peaks[k])
    trades = {}
    tr_p = DATA / "trades.jsonl"
    if tr_p.exists():
        for line in tr_p.read_text().splitlines():
            t = json.loads(line)
            k = (t["asset"], t["strat"])
            trades[k] = trades.get(k, 0) + 1
    print("ТРЕЙДЕР (бумага, старт $1000 на стратегию):")
    for name, a in st.items():
        price = a["candles"][-1][1]
        print(f"\n{name} @ {price:,.0f}")
        for s in STRATS:
            eq = equity(a["port"][s], price)
            pos = "в монете" if a["port"][s]["coin"] > 0 else "в долларах"
            k = (name, s)
            print(f"  {s:4s}: ${eq:8.2f} ({(eq / START_USD - 1) * 100:+6.2f}%) | {pos} | "
                  f"сделок {trades.get(k, 0)} | макс.просадка {dds.get(k, 0) * 100:.1f}%")


if __name__ == "__main__":
    {"tick": cmd_tick, "report": cmd_report}.get(
        sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__))()

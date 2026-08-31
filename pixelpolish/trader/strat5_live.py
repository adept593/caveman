#!/usr/bin/env python3
"""Демо-счёт исследования: 5 стратегий-победителей бэктеста живут на бумаге.
По $1000 на стратегию на актив (BTC+ETH), 4h-свечи Kraken, комиссия 0.1%.
Команды: tick (вахта, ежечасно) | report. Реальных денег НЕТ (устав)."""
import json
import pathlib
import sys

import requests

from strategies import FAMILIES, FEE

HERE = pathlib.Path(__file__).parent
DATA = HERE / "data"
ST_P = DATA / "strat5_state.json"
WIN_P = DATA / "live_strats.json"
PAIRS = {"BTC": "XBTUSD", "ETH": "ETHUSD"}
START = 1000.0


def candles_4h(pair):
    r = requests.get("https://api.kraken.com/0/public/OHLC",
                     params={"pair": pair, "interval": 240}, timeout=30)
    r.raise_for_status()
    res = r.json()["result"]
    key = next(k for k in res if k != "last")
    return [[int(c[0]), float(c[4])] for c in res[key]][:-1]


def log(path, obj):
    with open(DATA / path, "a") as f:
        f.write(json.dumps(obj) + "\n")


def cmd_tick():
    winners = json.loads(WIN_P.read_text())
    st = json.loads(ST_P.read_text()) if ST_P.exists() else {}
    for asset, pair in PAIRS.items():
        try:
            cs = candles_4h(pair)
        except Exception as e:
            print(f"[strat5] {asset}: {e}", file=sys.stderr)
            continue
        closes = [c[1] for c in cs]
        ts, price = cs[-1]
        a = st.setdefault(asset, {"last_ts": 0, "port": {
            w["family"]: {"usd": START, "coin": 0.0} for w in winners}})
        new_candle = ts > a["last_ts"]
        for w in winners:
            fam = w["family"]
            p = a["port"].setdefault(fam, {"usd": START, "coin": 0.0})
            if new_candle:
                want = FAMILIES[fam][0](closes, *w["params"])[-1]
                if want and p["usd"] > 0:
                    p["coin"] = p["usd"] * (1 - FEE) / price
                    p["usd"] = 0.0
                    log("strat5_trades.jsonl", {"ts": ts, "asset": asset, "strat": fam,
                                                "side": "buy", "price": price})
                elif not want and p["coin"] > 0:
                    p["usd"] = p["coin"] * price * (1 - FEE)
                    p["coin"] = 0.0
                    log("strat5_trades.jsonl", {"ts": ts, "asset": asset, "strat": fam,
                                                "side": "sell", "price": price})
            log("strat5_equity.jsonl", {"ts": ts, "asset": asset, "strat": fam,
                                        "eq": round(p["usd"] + p["coin"] * price, 2)})
        a["last_ts"] = ts
        print(f"{asset} @ {price:,.0f}: {'новая 4h-свеча' if new_candle else 'без новой свечи'}")
    ST_P.write_text(json.dumps(st))


def cmd_report():
    if not ST_P.exists():
        sys.exit("нет состояния — сначала tick")
    st = json.loads(ST_P.read_text())
    winners = json.loads(WIN_P.read_text())
    trades = {}
    tr = DATA / "strat5_trades.jsonl"
    if tr.exists():
        for line in tr.read_text().splitlines():
            t = json.loads(line)
            k = (t["asset"], t["strat"])
            trades[k] = trades.get(k, 0) + 1
    print("ДЕМО-СЧЁТ 5 СТРАТЕГИЙ (бумага, старт $1000 на стратегию на актив):")
    for asset, a in st.items():
        cs = candles_4h(PAIRS[asset])
        price = cs[-1][1]
        print(f"\n{asset} @ {price:,.0f}")
        for w in winners:
            fam = w["family"]
            p = a["port"][fam]
            eq = p["usd"] + p["coin"] * price
            pos = "в монете" if p["coin"] > 0 else "в деньгах"
            print(f"  {fam:8s} {str(tuple(w['params'])):14s}: ${eq:8.2f} "
                  f"({(eq / START - 1) * 100:+6.2f}%) | {pos} | сделок {trades.get((asset, fam), 0)}")


if __name__ == "__main__":
    {"tick": cmd_tick, "report": cmd_report}.get(
        sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__))()

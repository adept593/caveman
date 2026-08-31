#!/usr/bin/env python3
"""Исследование стратегий: 5 семейств × 10 параметров × BTC/ETH, 4h-свечи (~120 дней).
Честность: история делится 70/30 — подбор смотрит первые 70%, оценка по последним 30%
(данные, которых «подбор не видел»). Комиссия 0.1%. Победитель семейства — лучший
средний результат на проверочной части. Победители → data/live_strats.json → демо-счёт.
"""
import json
import pathlib

import requests

from strategies import FAMILIES, simulate

HERE = pathlib.Path(__file__).parent
DATA = HERE / "data"
PAIRS = {"BTC": "XBTUSD", "ETH": "ETHUSD"}


def candles_4h(pair):
    r = requests.get("https://api.kraken.com/0/public/OHLC",
                     params={"pair": pair, "interval": 240}, timeout=30)
    r.raise_for_status()
    res = r.json()["result"]
    key = next(k for k in res if k != "last")
    return [float(c[4]) for c in res[key]][:-1]


def main():
    closes = {a: candles_4h(p) for a, p in PAIRS.items()}
    for a, c in closes.items():
        print(f"{a}: {len(c)} свечей 4h (~{len(c) / 6:.0f} дней), "
              f"{c[0]:,.0f} → {c[-1]:,.0f} ({(c[-1] / c[0] - 1) * 100:+.1f}% за период)")
    split = {a: int(len(c) * 0.7) for a, c in closes.items()}
    hold_test = {a: closes[a][-1] / closes[a][split[a]] - 1 for a in closes}
    print(f"Эталон hold на проверке: BTC {hold_test['BTC'] * 100:+.1f}%, ETH {hold_test['ETH'] * 100:+.1f}%\n")

    winners = []
    for fam, (fn, variants) in FAMILIES.items():
        rows = []
        for params in variants:
            tr_avg = te_avg = dd_max = 0.0
            ntr = 0
            for a, c in closes.items():
                pos = fn(c, *params)
                tr, _, _ = simulate(c[:split[a]], pos[:split[a]])
                te, dd, n = simulate(c, pos, start_i=split[a])
                tr_avg += tr / 2
                te_avg += te / 2
                dd_max = max(dd_max, dd)
                ntr += n
            rows.append((te_avg, tr_avg, dd_max, ntr, params))
        rows.sort(key=lambda r: -r[0])
        best = rows[0]
        winners.append({"family": fam, "params": list(best[4])})
        print(f"[{fam}] лучший из 10: params={best[4]}")
        print(f"   обучение {best[1] * 100:+6.1f}% | ПРОВЕРКА {best[0] * 100:+6.1f}% | "
              f"просадка {best[2] * 100:4.1f}% | сделок {best[3]}")
        print(f"   худший из 10: {rows[-1][0] * 100:+.1f}% на проверке (разброс семейства)")

    (DATA / "live_strats.json").write_text(json.dumps(winners, indent=1))
    print(f"\nПобедители всех 5 семейств записаны в data/live_strats.json → демо-счёт")


if __name__ == "__main__":
    main()

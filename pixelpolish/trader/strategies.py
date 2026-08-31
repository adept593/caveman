"""Общая библиотека стратегий Трейдера: 5 семейств, позиция 0/1 по закрытиям.
Используется и бэктестом (backtest.py), и живым демо-счётом (strat5_live.py)."""


def _sma(xs, n, i):
    return sum(xs[i - n + 1:i + 1]) / n if i + 1 >= n else None


def pos_sma(closes, fast, slow):
    out = []
    for i in range(len(closes)):
        f, s = _sma(closes, fast, i), _sma(closes, slow, i)
        out.append(1 if f and s and f > s else 0)
    return out


def pos_rsi(closes, n, buy, sell):
    out, pos = [], 0
    for i in range(len(closes)):
        if i >= n:
            gains = losses = 0.0
            for a, b in zip(closes[i - n:i], closes[i - n + 1:i + 1]):
                d = b - a
                gains += max(d, 0)
                losses += max(-d, 0)
            r = 100.0 if losses == 0 else 100 - 100 / (1 + gains / losses)
            if r < buy:
                pos = 1
            elif r > sell:
                pos = 0
        out.append(pos)
    return out


def pos_donchian(closes, en, ex):
    out, pos = [], 0
    for i in range(len(closes)):
        if i >= en:
            if closes[i] > max(closes[i - en:i]):
                pos = 1
        if pos and i >= ex and closes[i] < min(closes[i - ex:i]):
            pos = 0
        out.append(pos)
    return out


def pos_roc(closes, n, ein, eout):
    out, pos = [], 0
    for i in range(len(closes)):
        if i >= n:
            ret = closes[i] / closes[i - n] - 1
            if ret > ein / 100:
                pos = 1
            elif ret < eout / 100:
                pos = 0
        out.append(pos)
    return out


def pos_boll(closes, n, k):
    out, pos = [], 0
    for i in range(len(closes)):
        if i + 1 >= n:
            win = closes[i - n + 1:i + 1]
            m = sum(win) / n
            sd = (sum((x - m) ** 2 for x in win) / n) ** 0.5
            if closes[i] < m - k * sd:
                pos = 1
            elif closes[i] > m:
                pos = 0
        out.append(pos)
    return out


FAMILIES = {
    "sma": (pos_sma, [(5, 20), (8, 30), (10, 40), (12, 50), (15, 60),
                      (20, 80), (25, 100), (30, 120), (40, 160), (50, 200)]),
    "rsi": (pos_rsi, [(7, 25, 75), (7, 30, 70), (14, 25, 75), (14, 30, 70), (14, 35, 65),
                      (21, 30, 70), (10, 20, 80), (14, 20, 80), (21, 25, 75), (10, 30, 70)]),
    "donchian": (pos_donchian, [(10, 5), (20, 10), (20, 5), (30, 10), (40, 20),
                                (50, 25), (15, 7), (25, 12), (35, 15), (55, 20)]),
    "roc": (pos_roc, [(12, 2, -2), (24, 3, -3), (12, 5, -5), (48, 5, -5), (24, 2, -2),
                      (6, 1, -1), (36, 4, -4), (24, 5, -2), (12, 3, -1), (48, 8, -4)]),
    "boll": (pos_boll, [(20, 2), (20, 2.5), (14, 2), (30, 2), (20, 1.5),
                        (14, 2.5), (30, 2.5), (10, 2), (50, 2), (20, 3)]),
}

FEE = 0.001


def simulate(closes, pos, start_i=0, capital=1000.0):
    """Прогон: всё-в-рынок/всё-в-деньги по pos[], комиссия за каждую смену."""
    usd, coin, trades, peak, maxdd = capital, 0.0, 0, capital, 0.0
    for i in range(start_i, len(closes)):
        want = pos[i]
        if want and usd > 0:
            coin = usd * (1 - FEE) / closes[i]
            usd = 0.0
            trades += 1
        elif not want and coin > 0:
            usd = coin * closes[i] * (1 - FEE)
            coin = 0.0
            trades += 1
        eq = usd + coin * closes[i]
        peak = max(peak, eq)
        maxdd = max(maxdd, (peak - eq) / peak)
    final = usd + coin * closes[-1]
    return final / capital - 1, maxdd, trades

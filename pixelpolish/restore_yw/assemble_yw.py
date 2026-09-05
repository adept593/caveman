# -*- coding: utf-8 -*-
"""Сборка пяти слоёв для youngwoman1855 с замком по композиции.

Kontext на этой пластине выдумывает лиф (пуговицы, бант, пояс, юбка) и опускает
руки — запреты в промпте он не слышит (РЕЦЕПТ §6). Поэтому от модели берётся
только то, что она делает хорошо и что проверяемо: лицо, кокетка, кисти.
Всё остальное — классическая чистка (inpaint крапа, L2_classic_full.png).

  L1_master  = кроп мастера, как есть
  L2_clean   = классическая чистка — настоящая, без модели
  L3_tone    = L4 размытый (гаусс 2.4), тон L4 — тот же приём, что build_layers_v3
  L4_detail  = классическая чистка + вставки Kontext по маскам (лицо, кокетка,
               кисти), сведение тона по кольцу, растушёвка 14 px
  L5_color   = яркость L4 + цветность прогона Kontext по L4 (e1_assemble):
               второй прогон с denoise 1.0 переписал бы геометрию, а цветность
               низкочастотна и от этого не страдает

Запуск:
  python assemble_yw.py l4  <kontext_detail.png>   -> L4_detail.png, L3, L2, L1
  python assemble_yw.py l5  <kontext_color.png>    -> L5_color.png
Выход: D:\PixelPolish\plates\layers_yw_final\
"""
import json, sys, io
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
Image.MAX_IMAGE_PIXELS = None
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SRC = Path(r"D:\PixelPolish\plates\layers_yw")
DST = Path(r"D:\PixelPolish\plates\layers_yw_final")
W, H = 1280, 1760
FEATHER = 40.0
SOFT_SIGMA = 2.4
# зоны, которые берём из Kontext — координаты пластины 1280x1760
# Кисти НЕ берём: во всех прогонах Kontext опускал их в подол — остаются из
# классики, мягкие, но на своём месте (тот же приём, что D3 у twogirls).
# Низ кокетки 700, не 770: ниже у первого прогона бант и вторая брошь.
KEEP = {"лицо и волосы": (520, 40, 880, 500),
        "кокетка и брошь": (330, 470, 960, 690)}


def arr(p):
    im = Image.open(p).convert("RGB")
    if im.size != (W, H):
        im = im.resize((W, H), Image.LANCZOS)
    return np.asarray(im, np.float32)


def save(a, p):
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(p)


def luma(a):
    return 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]


def soften(a, sigma=SOFT_SIGMA):
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(sigma)), np.float32)


def feather(mask, r):
    im = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r))
    return np.asarray(im, np.float32)[..., None] / 255.0


def ring_match(k, c, box, ring=24):
    """Сводит тон вставки к подложке по кольцу вокруг рамки: яркость и размах."""
    x0, y0, x1, y1 = box
    rx0, ry0 = max(0, x0 - ring), max(0, y0 - ring)
    rx1, ry1 = min(W, x1 + ring), min(H, y1 + ring)
    m = np.zeros((H, W), bool)
    m[ry0:ry1, rx0:rx1] = True
    m[y0:y1, x0:x1] = False
    lk, lc = luma(k)[m], luma(c)[m]
    gain = float(lc.std() / max(lk.std(), 1e-3))
    gain = min(max(gain, 0.7), 1.4)
    off = float(lc.mean() - lk.mean() * gain)
    return k * gain + off, gain, off


def build_l4(kontext_path):
    DST.mkdir(parents=True, exist_ok=True)
    C = arr(SRC / "L2_classic_full.png")          # классическая чистка, подложка
    C = soften(C, 1.1)                             # остатки крапа после inpaint — чуть сгладить
    K = arr(kontext_path)                          # прогон Kontext
    L1 = arr(SRC / "L1_master.png")
    out = C.copy()
    rep = {"источник_kontext": str(kontext_path), "вставки": {}}
    # Швы убираем не подгонкой рамки, а разделением частот: от Kontext идут
    # высокие частоты (черты, нити кокетки), низкие — от подложки, чтобы вставка
    # сидела в том же тоне, что и остальная пластина. TONE_MIX — сколько тона
    # Kontext всё же оставить (0 = весь тон от подложки, 1 = как было).
    SIGMA, TONE_MIX = 22.0, 0.20
    Kb, Cb = soften(K, SIGMA), soften(C, SIGMA)
    Kt = Cb + (K - Kb) + (Kb - Cb) * TONE_MIX
    yy, xx = np.mgrid[0:H, 0:W]
    for name, box in KEEP.items():
        x0, y0, x1, y1 = box
        if "лицо" in name:                       # эллипс, не прямоугольник
            cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
            m = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1.0
        else:
            m = np.zeros((H, W), bool)
            m[y0:y1, x0:x1] = True
            # под брошью Kontext рисует бантик и пуговицы — там подложка
            m[585:730, 575:715] = False
        w = feather(m, FEATHER)
        out = out * (1 - w) + Kt * w
        rep["вставки"][name] = {"box": box, "маска": "эллипс" if "лицо" in name else "прямоугольник",
                                "sigma": SIGMA, "tone_mix": TONE_MIX, "feather": FEATHER}
        print("  %-16s %s  частоты: sigma %.0f, тон Kontext x%.2f" % (name, box, SIGMA, TONE_MIX))
    save(L1, DST / "L1_master.png")
    save(C, DST / "L2_clean.png")
    save(soften(out), DST / "L3_tone.png")
    save(out, DST / "L4_detail.png")
    # чтобы L3 отличался от L4 и от L2 не на глаз, а числом
    d24 = float(np.abs(luma(C) - luma(out)).mean())
    d34 = float(np.abs(luma(soften(out)) - luma(out)).mean())
    rep["diff_mean_abs"] = {"L2_vs_L4": round(d24, 2), "L3_vs_L4": round(d34, 2)}
    json.dump(rep, open(DST / "decision.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("L1..L4 записаны в", DST, "| L2-L4 %.1f, L3-L4 %.1f" % (d24, d34))


def build_l5(color_path):
    L4 = arr(DST / "L4_detail.png")
    K5 = arr(color_path)
    Y4 = luma(L4)[..., None]
    chroma = K5 - luma(K5)[..., None]
    # Kontext в цветном прогоне снова переставил руки и лиф — его цветность на
    # тёмной ткани легла бы красным пятном не там. У чёрного платья цвета нет:
    # гасим цветность там, где подложка тёмная, оставляем на коже и кокетке.
    chroma = soften(chroma + 128.0, 6.0) - 128.0
    # пластина подкрашена вручную только по лицу — цвет держим в тех же масках,
    # что и вставки Kontext; чёрное платье и тёмный фон остаются нейтральными
    yy, xx = np.mgrid[0:H, 0:W]
    keep = np.zeros((H, W), bool)
    for name, (x0, y0, x1, y1) in KEEP.items():
        if "лицо" in name:
            cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
            keep |= ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1.0
        else:
            keep[y0:y1, x0:x1] = True
    keep = feather(keep, FEATHER) * np.clip((Y4 - 40.0) / 60.0, 0.0, 1.0)
    L5 = Y4 + chroma * keep
    save(L5, DST / "L5_color.png")
    sat = float(np.abs(chroma).mean())
    rep = json.load(open(DST / "decision.json", encoding="utf-8"))
    rep["L5"] = {"источник_цвета": str(color_path), "яркость": "L4", "цветность_средняя": round(sat, 2)}
    json.dump(rep, open(DST / "decision.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("L5_color записан: яркость L4 + цветность Kontext, цветность %.2f" % sat)


if __name__ == "__main__":
    mode, path = sys.argv[1], sys.argv[2]
    build_l4(path) if mode == "l4" else build_l5(path)

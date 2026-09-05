# -*- coding: utf-8 -*-
"""Ролик youngwoman1855 (ppmsca.51855, LOC 2017648628) — конвейер v5b без правок,
заменены только пути, разметка кожи под одну женщину со сложенными руками и надписи.
Кен-бёрнс выключен (--mode off): по решению Седрака разницы не видно.
Выход: D:\\PixelPolish\\video\\projects\\layers_youngwoman1855\\<mode>\\video_noaudio.mp4
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from make_layers_short_v3 import (FFMPEG, FFPROBE, find_font, fit_size, text_w,
                                  esc, grab, log, probe, run, _phase_corr)

sys.path.insert(0, r"C:\pixelpolish\caveman\pixelpolish")
from kenburns import build as kenburns_build      # noqa: E402

Image.MAX_IMAGE_PIXELS = None

OW, OH, FPS, TOTAL = 1080, 1920, 30, 30.0     # размер ВЫХОДА (--out его меняет)
# Опорная высота выхода. Все пространственные величины (зерно, растушёвка, спад
# резкости, кегли) заданы в пикселях выхода 1080x1920 и пересчитаны в холст через
# неё, а НЕ через фактический OH. Иначе смена выхода поехала бы и по зерну, и
# сравнение двух выходов перестало бы быть сравнением одного и того же ролика.
OUT_REF_W, OUT_REF_H = 1080, 1920
# Холст рендера. Две границы снизу, обе замерены, а не выбраны на глаз:
#   1) запас разрешения окна (win_w/out_w) должен перекрыть зум 1,12;
#   2) ход окна должен дотянуть до порога kenburns.py, иначе zoompan замирает.
# При CH=2200 (окно 1238) второй пункт не выполняется ни при каком апскейле
# <= 4x: 1238*4 даёт 0,590 px/кадр и 4 замерших пары из 899. CH=2400 (окно 1350)
# при 4x даёт 0,643 px/кадр и ноль замерших. Ширина считается той же формулой,
# что в kenburns.py, поэтому его crop выходит пустой операцией.
CH = 2400
CW = int(round(CH * OW / OH))                 # 1350
SS = CH / OUT_REF_H                           # 1,25 — холст крупнее опорного выхода
W, H = CW, CH                                 # весь numpy-рендер идёт в холсте
LAY_DIR = Path(r"D:\PixelPolish\plates\layers_yw_bust3")
WORK_ROOT = Path(r"D:\PixelPolish\video\projects\layers_youngwoman1855_bust3")
WORK = WORK_ROOT / "off"                      # переопределяется в main()
VIDEO_ONLY = WORK / "video_noaudio.mp4"
LAYERS = ["L1_master.png", "L2_clean.png", "L3_tone.png", "L4_detail.png", "L5_color.png"]

# ---- цели по числам (ФОРМАТ_V5.md), ПЕРЕСТРОЕНЫ под тёмную пластину:
# 70 % кадра — чёрное платье, цель 136 вытаскивала из него серую муть;
# цвет только на лице, поэтому цель по насыщенности всего кадра низкая — иначе
# «досведение» делит её на почти нулевую цветность и красит лицо в оранжевый
EXPO_TARGET = 92.0       # A3: средняя яркость кадра 130-140
RB_TARGET = 9.0          # F1: B ниже R не больше чем на 10-12
SAT_TARGET = 0.12         # F3
PARTIAL = 0.45           # B1: доля цвета на промежуточной стадии
SKIN_CAP = 246.0         # D1: ни один канал на коже не доходит до 255
LIMB_GAP = 8.0           # D2: предплечье темнее лица на столько (допуск 15)
# Пространственные величины заданы в пикселях ВЫХОДА и пересчитаны в холст,
# чтобы их доля кадра осталась той же, что в v5.
FEATHER = 340.0 * SS     # C1: растушёвка проявки, 17,7 % высоты кадра
GRAIN = 2.6 * SS         # E2: зерно (после ужатия холста в выход даёт те же 2,6)
BLUR_EDGE = 1.6 * SS     # E2: спад резкости к краям
FEATH_LIMB, FEATH_SKIN, FEATH_HAND = 9.0 * SS, 8.0 * SS, 5.0 * SS

# ---- зона надписей G2: 25-60 % высоты, ширина не больше 78 %, кегль не меньше 44
ZONE_TOP, ZONE_BOT = int(0.25 * OH), int(0.60 * OH)
TEXT_MAX_W = int(0.78 * OW)
MIN_SIZE = 44
TXT = 1.0        # множитель кеглей и y надписей = OH / OUT_REF_H, ставится в main()

# ---- разметка кожи в координатах ПЛАСТИНЫ 1328x1760 (снято кропами 1:1)
FACE_BOXES = [(560, 90, 830, 470)]
FACE_REF = [(620, 110, 760, 190),      # лоб
            (600, 250, 655, 330), (745, 250, 810, 330)]   # щёки
LIMB_BOXES = [(480, 470, 830, 620)]    # шея и плечи под кокеткой: кисти для детектора кожи слишком темны
# D3: сами КИСТИ, отдельно от предплечий — их смотрели кропом 1:1 и все три
# признаны сомнительными (пальцы слиты, костяшек и ногтей нет, край запястья
# ровной линией). Возвращаем в исходную муть.
HAND_BOXES = [(600, 890, 850, 1140)]
# D2 (правка после v5): критик жаловался на разрыв ПРЕДПЛЕЧЬЕ/ПЛЕЧО внутри одной
# руки — «нижняя половина руки подсвечена отдельным прибором». В v5 мерили
# предплечье против ЛИЦА, то есть не то. Пары рамок ниже — одна и та же рука:
# чем светится низ и чем светится верх. Лицо в этой проверке не участвует.
ARMS = []    # рукава тёмные до запястья — пар «плечо/предплечье» нет
ARM_GAP_TARGET = 8.0     # куда сводим
ARM_GAP_MAX = 12.0       # допуск из задания
SKIRT_BOX = (330, 480, 620, 760)      # прозрачная полосатая кокетка        # клетка на юбке — замер детализации

# ---- стадии
# 0 A повреждённая, 1 B чистая, 2 C тон, 3 D тон+частичный цвет,
# 4 E детали+частичный цвет, 5 F полный цвет
MOVES = [(2.40, 4.60, 0, 1), (5.60, 6.40, 1, 2), (6.40, 8.00, 2, 3),
         (10.40, 12.60, 3, 4), (14.20, 15.90, 4, 5)]
HOLDS = [(0.00, 0.40, 5), (0.40, 2.40, 0), (4.60, 5.60, 1), (8.00, 10.40, 3),
         (12.60, 14.20, 4), (15.90, 30.01, 5)]

# (текст, кегль, y, t0, t1, чем проверяется «изменение уже видно»)
WANT = [
    ("c. 1855",                         110,  820,  0.00,  3.20, None),
    ("Rochester, New York",              58,  980,  0.00,  3.20, None),
    ("her name was not recorded",        54, 1000,  3.55,  6.10, None),
    ("the brass mat is stamped F. Grice",54, 1000,  6.45,  8.35, None),
    ("warmth back in her face",          54, 1000,  8.70, 11.00, "color_face"),
    ("she looked straight into the lens",54, 1000, 11.35, 12.50, None),
    ("the sheer yoke, stripe by stripe", 54, 1000, 12.95, 15.30, "detail"),
    ("a hint of the hand-color",         54, 1000, 16.20, 18.60, "color_full"),
    ("one young woman, no name",         54, 1000, 18.95, 21.30, None),
    ("she held still for many seconds",  54, 1000, 21.65, 24.00, None),
    ("the plate survived 171 years",     54, 1000, 24.00, 27.00, None),
    ("AI restoration · Library of Congress",
                                         44, 1066, 24.00, 27.00, None),
    ("Who was she?",                     92,  950, 27.00, 30.00, None),
]


# ------------------------------------------------------------------ утилиты

def luma(a: np.ndarray) -> np.ndarray:
    return 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]


def sat_mean(a: np.ndarray) -> float:
    mx = a.max(axis=2)
    mn = a.min(axis=2)
    return float(np.mean((mx - mn) / np.maximum(mx, 1e-6)))


def gamma_to_mean(a: np.ndarray, target: float) -> tuple[np.ndarray, float]:
    """Гамма 0..1, подобранная делением пополам под среднюю яркость target.
    Не клиппирует: 0 и 255 остаются на месте."""
    x = np.clip(a, 0, 255) / 255.0
    lo, hi = 0.15, 4.0
    for _ in range(40):
        g = (lo + hi) / 2.0
        m = luma(np.power(x, g)).mean() * 255.0
        if m < target:
            hi = g
        else:
            lo = g
    g = (lo + hi) / 2.0
    return np.power(x, g) * 255.0, g


def box_mask(shape, boxes, sx, x0f, sy=None) -> np.ndarray:
    """Прямоугольники из координат пластины в координаты кадра."""
    sy = sy if sy is not None else sx
    m = np.zeros(shape[:2], bool)
    for bx0, by0, bx1, by1 in boxes:
        fx0 = int(round(bx0 * sx)) - x0f
        fx1 = int(round(bx1 * sx)) - x0f
        fy0 = int(round(by0 * sy))
        fy1 = int(round(by1 * sy))
        fx0, fx1 = max(0, fx0), min(shape[1], fx1)
        fy0, fy1 = max(0, fy0), min(shape[0], fy1)
        if fx1 > fx0 and fy1 > fy0:
            m[fy0:fy1, fx0:fx1] = True
    return m


def skinify(a: np.ndarray, box: np.ndarray, ythr: float) -> np.ndarray:
    """Внутри прямоугольников оставить только кожу: светлее порога и тёплая."""
    Y = luma(a)
    rb = a[..., 0] - a[..., 2]
    return box & (Y > ythr) & (rb > 12) & (rb < 110)


def feather(mask: np.ndarray, r: float) -> np.ndarray:
    im = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r))
    return np.asarray(im, np.float32) / 255.0


def smootherstep(p):
    p = np.clip(p, 0.0, 1.0)
    return p * p * p * (p * (6 * p - 15) + 10)


def lapvar(a: np.ndarray) -> float:
    g = luma(a)
    k = (g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:] - 4 * g[1:-1, 1:-1])
    return float(k.var())


def drawtext(font, text, size, y, t0, t1):
    ff = str(font).replace("\\", "/").replace(":", r"\:")
    return ("drawtext=fontfile='%s':text='%s':fontsize=%d"
            ":fontcolor=white@1.0:borderw=%d:bordercolor=black@1.0"
            ":shadowcolor=black@0.65:shadowx=0:shadowy=3"
            ":x=(w-text_w)/2:y=%d:enable='between(t,%s,%s)'"
            % (ff, esc(text), size, max(4, -(-size // 12)), y, t0, t1))


# ------------------------------------------------------------------ основное

def main(mode: str, notext: bool = False, ss: float = 1.0, tag: str = "",
         lossless: bool = False, out: str = "", canvas_h: int = 0,
         max_upscale: float = None, crf: int = 16) -> int:
    global WORK, VIDEO_ONLY, OW, OH, CW, W, ZONE_TOP, ZONE_BOT, TEXT_MAX_W, TXT
    global CH, H, SS, FEATHER, GRAIN, BLUR_EDGE, FEATH_LIMB, FEATH_SKIN, FEATH_HAND
    if canvas_h:
        # Холст крупнее — все пространственные величины едут вместе с ним, они и
        # заданы через SS = CH / OUT_REF_H. Доля кадра у зерна и растушёвки не
        # меняется, меняется только на скольких отсчётах они посчитаны.
        CH, H = int(canvas_h), int(canvas_h)
        SS = CH / OUT_REF_H
        FEATHER, GRAIN, BLUR_EDGE = 340.0 * SS, 2.6 * SS, 1.6 * SS
        FEATH_LIMB, FEATH_SKIN, FEATH_HAND = 9.0 * SS, 8.0 * SS, 5.0 * SS
        log("холст рендера по высоте %d, SS %.4f" % (CH, SS))
    if out:
        OW, OH = (int(x) for x in out.lower().split("x"))
        if OW * OUT_REF_H != OH * OUT_REF_W:
            return log("выход %s не 9:16 — холст рендера рассчитан на 9:16" % out) or 3
    CW = int(round(CH * OW / OH))
    W = CW
    if out:
        ZONE_TOP, ZONE_BOT = int(0.25 * OH), int(0.60 * OH)
        TEXT_MAX_W = int(0.78 * OW)
        TXT = OH / float(OUT_REF_H)
        log("выход %dx%d, кегли и y надписей x%.4f, холст рендера %dx%d"
            % (OW, OH, TXT, CW, CH))
    WORK = WORK_ROOT / (tag or mode)
    VIDEO_ONLY = WORK / ("video_lossless.mkv" if lossless else
                         "video_notext.mp4" if notext else "video_noaudio.mp4")
    kb_filter, kb_info = kenburns_build(mode, TOTAL, FPS, CW, CH, OW, OH, ss,
                                        max_upscale)
    log("кен-бёрнс, режим %s (строка целиком из kenburns.py):" % mode)
    for kk, vv in kb_info.items():
        log("  %-22s %s" % (kk, vv))
    log("  фильтр: %s" % kb_filter)
    paths = [LAY_DIR / n for n in LAYERS]
    for p in paths:
        if not p.exists():
            return log("нет слоя %s" % p) or 2
    if WORK.exists() and not notext and not lossless:
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True, exist_ok=True)
    qc = WORK / "qc"
    qc.mkdir(exist_ok=True)
    checks = {}

    log("[1/7] слои из %s" % LAY_DIR)
    ims = [Image.open(p).convert("RGB") for p in paths]
    sizes = {im.size for im in ims}
    if len(sizes) != 1:
        return log("  размеры слоёв разные: %s" % sizes) or 3
    PW, PH = ims[0].size
    log("  пять слоёв %dx%d" % (PW, PH))

    # ---- G1: снимок на весь кадр. Масштаб по высоте, обрезка по бокам.
    s = CH / PH
    sw = int(round(PW * s))
    if sw < CW:
        return log("  после подгонки по высоте ширина %d < %d" % (sw, CW)) or 3

    # границы субъекта: тёмное (платья, волосы) плюс светлая кожа против фона
    a5 = np.asarray(ims[4], np.float32)
    Y5 = luma(a5)
    # фон меряем построчно по краям кадра — так виньетка не мешает
    bl = np.median(Y5[:, :45], axis=1)[:, None]
    br = np.median(Y5[:, -45:], axis=1)[:, None]
    ramp = np.linspace(0.0, 1.0, PW, dtype=np.float32)[None, :]
    bgrow = bl + (br - bl) * ramp
    subj = np.abs(Y5 - bgrow) > 45
    r0, r1 = int(PH * 0.10), int(PH * 0.80)
    colcount = subj[r0:r1].sum(axis=0)
    thr = (r1 - r0) * 0.18
    cols = np.where(colcount > thr)[0]
    sx0, sx1 = int(cols.min()), int(cols.max())
    log("  фон построчно (медиана Y по краям %.1f), субъект по X %d..%d из %d"
        % (float(bgrow.mean()), sx0, sx1, PW))

    cx = (sx0 + sx1) / 2.0 * s
    x0f = int(round(cx - CW / 2.0))
    x0f = max(0, min(sw - CW, x0f))
    marg_l = int(round(sx0 * s)) - x0f
    marg_r = (x0f + CW) - int(round(sx1 * s))
    log("  кроп по X %d..%d из %d, запас до субъекта слева %d px, справа %d px"
        % (x0f, x0f + CW, sw, marg_l, marg_r))
    if marg_l < 15 * SS or marg_r < 15 * SS:
        return log("  кроп режет субъекта") or 3
    checks["crop"] = {"plate": [PW, PH], "scaled": [sw, CH], "x0": x0f,
                      "canvas": [CW, CH], "out": [OW, OH],
                      "plate_upscale": round(s, 4),
                      "subject_x": [sx0, sx1], "margin_l": marg_l, "margin_r": marg_r,
                      "photo_covers_frame": True}

    def to_frame(im):
        return np.asarray(im.resize((sw, CH), Image.LANCZOS).crop((x0f, 0, x0f + CW, CH)),
                          np.float32)

    F = [to_frame(im) for im in ims]           # L1..L5 в координатах кадра

    log("[2/7] палитра и насыщенность (F1, F3)")
    col = F[4].copy()
    Yc = luma(col)
    ch = col - Yc[..., None]
    s_now = sat_mean(np.clip(col, 0, 255))
    k = min(1.0, SAT_TARGET / max(s_now, 1e-6))
    col = Yc[..., None] + ch * k
    d = float(col[..., 0].mean() - col[..., 2].mean())
    add_b = (d - RB_TARGET) * 0.6
    sub_r = (d - RB_TARGET) * 0.4
    col[..., 2] += add_b
    col[..., 0] -= sub_r
    col = np.clip(col, 0, 255)
    log("  насыщенность %.3f -> цель %.2f, множитель цветности %.3f" % (s_now, SAT_TARGET, k))
    log("  R-B по кадру было %.1f, поправка B+%.1f R-%.1f -> стало %.1f"
        % (d, add_b, sub_r, col[..., 0].mean() - col[..., 2].mean()))
    F[4] = col

    log("[3/7] экспозиция (A3, F2): все стадии к средней %.0f" % EXPO_TARGET)
    gammas = []
    for i in range(5):
        before = luma(F[i]).mean()
        F[i], g = gamma_to_mean(F[i], EXPO_TARGET)
        gammas.append([LAYERS[i], round(float(before), 1), round(g, 3),
                       round(float(luma(F[i]).mean()), 1)])
        log("  %-14s %.1f -> %.1f (гамма %.3f)" % (LAYERS[i], before, luma(F[i]).mean(), g))
    checks["exposure"] = gammas

    # экспозиционная гамма поднимает светлоту и роняет насыщенность — досводим
    for _ in range(5):
        c = F[4]
        yc2 = luma(c)[..., None]
        k2 = SAT_TARGET / max(sat_mean(np.clip(c, 1e-6, 255)), 1e-6)
        c = yc2 + (c - yc2) * k2
        d2 = float(c[..., 0].mean() - c[..., 2].mean())
        c[..., 2] += (d2 - RB_TARGET) * 0.6
        c[..., 0] -= (d2 - RB_TARGET) * 0.4
        F[4] = np.clip(c, 0, 255)
    F[4] = np.clip(F[4] * (EXPO_TARGET / luma(F[4]).mean()), 0, 255)
    log("  досведение цвета: насыщенность %.3f, R-B %.1f, яркость %.1f"
        % (sat_mean(np.clip(F[4], 1e-6, 255)),
           F[4][..., 0].mean() - F[4][..., 2].mean(), luma(F[4]).mean()))

    log("[4/7] кожа: маски, свод конечностей к лицу, потолок канала (D1, D2)")
    face_box = box_mask(F[4].shape, FACE_BOXES, s, x0f)
    limb_box = box_mask(F[4].shape, LIMB_BOXES, s, x0f)
    ref_box = box_mask(F[4].shape, FACE_REF, s, x0f)
    face_m = skinify(F[4], face_box, 120.0)
    limb_m = skinify(F[4], limb_box, 140.0)
    ref_m = skinify(F[4], ref_box, 120.0)
    log("  пикселей: лицо %d, эталон лица %d, конечности %d"
        % (face_m.sum(), ref_m.sum(), limb_m.sum()))
    if ref_m.sum() < 3000 or limb_m.sum() < 3000:
        return log("  маски кожи пустые — разметка не сошлась") or 3

    limb_soft = feather(limb_m, FEATH_LIMB)[..., None]
    skin_all = face_m | limb_m
    # маска для потолка канала расширена: внутри самой кожи вес строго 1,
    # спад — уже за её краем, иначе граничные пиксели остаются несрезанными
    skin_soft = np.maximum(np.clip(feather(skin_all, FEATH_SKIN) * 2.5, 0.0, 1.0),
                           skin_all.astype(np.float32))[..., None]

    face_ref_Y = float(luma(F[4])[ref_m].mean())
    face_all_Y = float(luma(F[4])[face_m].mean())
    limb_Y0 = float(luma(F[4])[limb_m].mean())
    # цель по D2 — опустить конечности к лицу, но так, чтобы разница с ЛЮБЫМ из двух
    # замеров лица (лицо целиком и светлые пятна лба/щеки) осталась в пределах 14
    target = max(face_all_Y - LIMB_GAP, face_ref_Y - 14.0, face_all_Y - 14.0)
    target = min(target, limb_Y0)
    delta = target - limb_Y0
    log("  лицо целиком Y=%.1f, эталонные пятна лица Y=%.1f, конечности Y=%.1f"
        % (face_all_Y, face_ref_Y, limb_Y0))
    log("  цель по конечностям Y=%.1f, сдвиг %.1f" % (target, delta))

    for i in range(1, 5):                       # L1 — исходная пластина, её не правим
        F[i] = np.clip(F[i] + limb_soft * delta, 0, 255)

    # D2, разрыв внутри руки. Общий сдвиг конечностей выше двигает всю руку целиком
    # и разрыв между её половинами не трогает — его надо снимать отдельно.
    arms, arm_masks = [], []
    for aname, sh_boxes, fa_boxes in ARMS:
        sh = skinify(F[4], box_mask(F[4].shape, sh_boxes, s, x0f), 140.0)
        fa = skinify(F[4], box_mask(F[4].shape, fa_boxes, s, x0f), 140.0)
        if sh.sum() < 400 or fa.sum() < 400:
            return log("  рамки руки [%s] не сошлись: плечо %d px, предплечье %d px"
                       % (aname, sh.sum(), fa.sum())) or 3
        y_sh = float(luma(F[4])[sh].mean())
        y_fa = float(luma(F[4])[fa].mean())
        gap = y_fa - y_sh
        shift = 0.0
        if abs(gap) > ARM_GAP_TARGET:
            shift = -(gap - np.sign(gap) * ARM_GAP_TARGET)
            w = feather(fa, FEATH_LIMB)[..., None]
            for i in range(1, 5):
                F[i] = np.clip(F[i] + w * shift, 0, 255)
        y_fa2 = float(luma(F[4])[fa].mean())
        log("  рука [%s]: плечо %.1f, предплечье %.1f, разрыв %+.1f -> сдвиг %+.1f "
            "-> разрыв %+.1f (допуск %.0f)"
            % (aname, y_sh, y_fa, gap, shift, y_fa2 - y_sh, ARM_GAP_MAX))
        arm_masks.append((aname, sh, fa))
        arms.append({"рука": aname, "плечо_Y": round(y_sh, 1),
                     "предплечье_Y_до": round(y_fa, 1), "разрыв_до": round(gap, 1),
                     "сдвиг": round(shift, 1),
                     "предплечье_Y_после": round(y_fa2, 1),
                     "разрыв_после": round(y_fa2 - y_sh, 1),
                     "px_плечо": int(sh.sum()), "px_предплечье": int(fa.sum())})
        np.save(WORK / ("mask_shoulder_%d.npy" % len(arms)), sh)
    checks["arms_D2"] = {"порог": ARM_GAP_MAX, "цель": ARM_GAP_TARGET, "руки": arms}

    hand_m = np.zeros(F[4].shape[:2], bool)
    hand_geo = []
    for hb in HAND_BOXES:
        hm = skinify(F[4], box_mask(F[4].shape, [hb], s, x0f), 140.0)
        hand_m |= hm
        hand_geo.append((hb, int(hm.sum()),
                         max(0, int(round(hb[0] * s)) - x0f),
                         int(round(hb[1] * s)),
                         min(CW, int(round(hb[2] * s)) - x0f),
                         int(round(hb[3] * s))))
    hand_w = feather(hand_m, FEATH_HAND)[..., None]

    # экспозиция могла уплыть после правки кожи — вернуть на цель
    for i in range(5):
        m = luma(F[i]).mean()
        F[i] = np.clip(F[i] * (EXPO_TARGET / m), 0, 255)

    log("[5/7] стадии, зерно и падение резкости к краям (B1, E2)")
    chroma = F[4] - luma(F[4])[..., None]
    st = [F[0], F[1], F[2], F[2] + PARTIAL * chroma, F[3] + PARTIAL * chroma, F[4]]

    # D3: все три кисти смотрены кропом 1:1 и признаны сомнительными — пальцы слиты,
    # костяшек и ногтей нет, край запястья ровной линией. Возвращаем их в состояние
    # ДО прохода детализации (L3_tone), то есть в исходную муть; цвет на них остаётся.
    log("  D3: кисти возвращены к состоянию до прохода детализации")
    pre_full = F[2] + chroma
    hands = []
    for (hb, npx, fx0, fy0, fx1, fy1) in hand_geo:
        before = lapvar(st[5][fy0:fy1, fx0:fx1])
        pre = lapvar(pre_full[fy0:fy1, fx0:fx1])
        hands.append({"box": hb, "px": npx, "lapvar_detail": round(before),
                      "lapvar_pre_detail": round(pre)})
        log("    кисть %s: пикселей %d, дисперсия лапласиана с деталями %.0f, "
            "до деталей %.0f" % (hb, npx, before, pre))
    st[4] = st[4] * (1 - hand_w) + st[3] * hand_w
    st[5] = st[5] * (1 - hand_w) + pre_full * hand_w
    for h, (hb, npx, fx0, fy0, fx1, fy1) in zip(hands, hand_geo):
        h["lapvar_after"] = round(lapvar(st[5][fy0:fy1, fx0:fx1]))
    log("    после подмены: %s" % [h["lapvar_after"] for h in hands])
    checks["hands"] = hands

    rng = np.random.default_rng(1855)
    noise = rng.normal(0.0, GRAIN, (CH, CW, 1)).astype(np.float32)
    yy = (np.arange(CH, dtype=np.float32)[:, None] - CH / 2.0) / (CH / 2.0)
    xx = (np.arange(CW, dtype=np.float32)[None, :] - CW / 2.0) / (CW / 2.0)
    rad = np.clip((np.sqrt(xx ** 2 + yy ** 2) - 0.55) / 0.75, 0.0, 1.0)[..., None] * 0.55

    def bake(stages):
        out = []
        for k, a in enumerate(stages):
            a = np.clip(a, 0, 255)
            bl = np.asarray(Image.fromarray(a.astype(np.uint8)).filter(
                ImageFilter.GaussianBlur(BLUR_EDGE)), np.float32)
            a = np.clip(a * (1 - rad) + bl * rad + noise, 0, 255)
            if k > 0:
                # D1: потолок по каналам на коже — последним действием, уже после зерна,
                # иначе зерно снова выбивает канал в 255
                mx = a.max(axis=2, keepdims=True)
                a = a * (1.0 - skin_soft) + a * np.minimum(1.0, SKIN_CAP / np.maximum(mx, 1e-6)) * skin_soft
            out.append(np.clip(a, 0, 255))
        return out

    frames = bake(st)

    # D2, доводка. Первый свод разрыва считался по слоям, а зерно, спад резкости и
    # потолок канала на коже идут ПОСЛЕ него и сдвигают светлоту ещё раз: на готовом
    # кадре разрыв выходил 12,2 при своде до 9,7. Поэтому доводим по тому, что реально
    # уйдёт в кадр, а не по промежуточному состоянию.
    fin = []
    for it in range(4):
        fin, worst = [], 0.0
        for aname, sh_m, fa_m in arm_masks:
            Yf = luma(frames[5])
            gap = float(Yf[fa_m].mean()) - float(Yf[sh_m].mean())
            fin.append((aname, gap))
            worst = max(worst, abs(gap))
        log("  D2 по готовому кадру, итерация %d: %s (худший %.1f, допуск %.0f)"
            % (it, ["%s %+.1f" % (n, g) for n, g in fin], worst, ARM_GAP_MAX))
        if worst <= ARM_GAP_TARGET:
            break
        for (aname, sh_m, fa_m), (_, gap) in zip(arm_masks, fin):
            if abs(gap) <= ARM_GAP_TARGET:
                continue
            w = feather(fa_m, FEATH_LIMB)[..., None]
            add = -(gap - np.sign(gap) * ARM_GAP_TARGET * 0.5)
            for i in range(1, 6):
                st[i] = np.clip(st[i] + w * add, 0, 255)
        frames = bake(st)
    checks["arms_D2"]["готовый_кадр"] = [{"рука": n, "разрыв": round(g, 1),
                                          "сошлось": bool(abs(g) <= ARM_GAP_MAX)}
                                         for n, g in fin]
    log("  потолок канала на коже %d, максимум на маске кожи: %s"
        % (SKIN_CAP, [int(f[skin_all].max()) for f in frames]))
    log("  шесть стадий готовы, частичный цвет %.0f %%" % (PARTIAL * 100))
    st_dir = WORK / "stages"
    st_dir.mkdir(exist_ok=True)
    for i, a in enumerate(frames):
        Image.fromarray(a.astype(np.uint8)).save(st_dir / ("S%d.png" % i))

    log("[6/7] надписи: зона %d..%d px, ширина <= %d px, кегль >= %d"
        % (ZONE_TOP, ZONE_BOT, TEXT_MAX_W, int(round(MIN_SIZE * TXT))))
    font = find_font()
    texts, plan = [], []
    for text, size, y, t0, t1, proof in WANT:
        size, y = int(round(size * TXT)), int(round(y * TXT))
        bw = max(4, -(-size // 12))
        sz = fit_size(font, text, size, TEXT_MAX_W - 2 * bw)
        if sz < int(round(MIN_SIZE * TXT)):
            return log("  [%s] не влезает при кегле >= %d"
                       % (text, int(round(MIN_SIZE * TXT)))) or 3
        wpx = text_w(font, text, sz)
        bottom = y + int(sz * 1.2)
        if y < ZONE_TOP or bottom > ZONE_BOT:
            return log("  [%s] вне зоны 25-60 %%: %d..%d" % (text, y, bottom)) or 3
        log("  [%s] кегль %d ширина %d px y=%d..%d t=%.2f..%.2f"
            % (text, sz, wpx, y, bottom, t0, t1))
        texts.append((text, sz, y, t0, t1))
        plan.append({"text": text, "size": sz, "font_w": wpx, "y": y, "y1": bottom,
                     "t0": t0, "t1": t1, "proof": proof, "tm": round((t0 + t1) / 2, 2),
                     "band": [max(0, y - 10), min(H, bottom + 10)]})

    # B3: после 10-й секунды пауз без текста длиннее 1 с быть не должно
    ivs = sorted((it["t0"], it["t1"]) for it in plan)
    merged = []
    for a, b in ivs:
        if merged and a <= merged[-1][1] + 1e-9:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    gaps = []
    for (a1, b1), (a2, b2) in zip(merged, merged[1:]):
        if b1 >= 10.0 or a2 >= 10.0:
            gaps.append([round(b1, 2), round(a2, 2), round(a2 - b1, 2)])
    if merged[-1][1] < TOTAL:
        gaps.append([round(merged[-1][1], 2), TOTAL, round(TOTAL - merged[-1][1], 2)])
    worst = max([g[2] for g in gaps], default=0.0)
    log("  паузы без текста после 10 с: %s (худшая %.2f с)" % (gaps, worst))
    if worst > 1.0:
        return log("  пауза длиннее 1 с") or 3
    checks["gaps_after_10s"] = {"list": gaps, "worst": worst}

    log("[7/7] кодирование, crf %d maxrate 16M, фейда из чёрного нет" % crf)
    # порядок обязателен: сначала кен-бёрнс, потом надписи. Иначе надписи поедут
    # вместе с картинкой и вылезут из зоны 25-60 % высоты.
    filt = [kb_filter] + ([] if notext else [drawtext(font, *t) for t in texts]) \
        + ["format=yuv420p"]
    cmd = [FFMPEG, "-y", "-v", "warning", "-stats",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (CW, CH),
           "-r", str(FPS), "-i", "-",
           "-vf", ",".join(filt), "-an",
           ] + (["-c:v", "ffv1", "-level", "3", "-g", "1", "-pix_fmt", "yuv420p"]
                if lossless else
                ["-c:v", "libx264", "-preset", "slow", "-profile:v", "high",
                 "-level", "4.2", "-crf", str(crf), "-maxrate", "16M", "-bufsize", "32M",
                 "-pix_fmt", "yuv420p", "-movflags", "+faststart"]) + [
           "-frames:v", str(int(round(TOTAL * FPS))), str(VIDEO_ONLY)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    yline_y = np.arange(CH, dtype=np.float32)[:, None, None]
    cache = {}
    for kf in range(int(round(TOTAL * FPS))):
        t = kf / FPS
        mv = next((m for m in MOVES if m[0] <= t < m[1]), None)
        if mv is None:
            idx = next(i for a, b, i in HOLDS if a <= t < b)
            buf = cache.get(idx)
            if buf is None:
                buf = np.ascontiguousarray(frames[idx].astype(np.uint8))
                cache[idx] = buf
            proc.stdin.write(buf.tobytes())
            continue
        t0, t1, i, j = mv
        e = float(smootherstep((t - t0) / (t1 - t0)))
        yl = -FEATHER + e * (H + 2 * FEATHER)
        p = np.clip((yl - yline_y + FEATHER / 2.0) / FEATHER, 0.0, 1.0)
        al = p * p * (3.0 - 2.0 * p)
        img = frames[i] + (frames[j] - frames[i]) * al
        proc.stdin.write(np.ascontiguousarray(np.clip(img, 0, 255).astype(np.uint8)).tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        return log("  ffmpeg упал") or 4

    info = probe(VIDEO_ONLY)
    v = next(x for x in info["streams"] if x["codec_type"] == "video")
    log("  ffprobe: %sx%s %s %s %.3f с" % (v["width"], v["height"], v["codec_name"],
                                           v["pix_fmt"], float(info["format"]["duration"])))
    if notext:                       # контрольную сборку в checks не пишем
        log("готово (без надписей): %s" % VIDEO_ONLY)
        return 0
    checks["texts"] = plan
    checks["probe_noaudio"] = info
    checks["stages"] = {"moves": MOVES, "holds": HOLDS, "feather_px": round(FEATHER, 1),
                        "feather_pct_h": round(100 * FEATHER / CH, 1)}
    checks["kenburns"] = {"mode": mode, "filter": kb_filter,
                          "info": {str(kk): str(vv) for kk, vv in kb_info.items()}}
    checks["skin"] = {"face_all_Y": round(face_all_Y, 1), "face_ref_Y": round(face_ref_Y, 1),
                      "limb_Y_before": round(limb_Y0, 1), "shift": round(delta, 1)}
    np.save(WORK / "mask_face.npy", face_m)
    np.save(WORK / "mask_limb.npy", limb_m)
    json.dump(checks, open(WORK / "build_checks.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    log("готово: %s" % VIDEO_ONLY)
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["off", "in", "out"], required=True)
    ap.add_argument("--notext", action="store_true")
    ap.add_argument("--ss", type=float, default=2.0)   # J.2a; ss=1 — прежнее поведение
    ap.add_argument("--tag", default="")
    ap.add_argument("--lossless", action="store_true",
                    help="ffv1 вместо x264 — чтобы отделить фильтр от кодека")
    ap.add_argument("--out", default="",
                    help="размер выхода WxH, 9:16; по умолчанию 1080x1920")
    ap.add_argument("--canvas-h", type=int, default=0,
                    help="высота холста рендера; по умолчанию 2400")
    ap.add_argument("--max-upscale", type=float, default=None,
                    help="потолок растяжения на пике зума, только для замеров")
    ap.add_argument("--crf", type=int, default=16,
                    help="crf x264; производственное значение 16")
    _a = ap.parse_args()
    raise SystemExit(main(_a.mode, _a.notext, _a.ss, _a.tag, _a.lossless, _a.out,
                          _a.canvas_h, _a.max_upscale, _a.crf))

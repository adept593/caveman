# -*- coding: utf-8 -*-
"""youngwoman1855, сборка №2 — полная перерисовка, а не заплатка.
База: первый полный прогон Kontext (L2_clean_raw) — свет, фон, лицо, кокетка эталонного
класса. В него по маске кладётся торс из отдельного прогона по кропу (torso_raw): там
модель получила вдвое больше пикселей на руки и лиф и не выдумала пуговиц.
Сведение частотами: детали от торса, низкие частоты — от базы (доля тона торса TONE_MIX).
  python assemble2_yw.py l4            -> L1..L4 в layers_yw_final
  python assemble2_yw.py l5 <color.png> -> L5 из полного цветного прогона по L4 (яркость L4 + цветность)
"""
import json, sys, io
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
SRC = Path(r"D:\PixelPolish\plates\layers_yw"); DST = Path(r"D:\PixelPolish\plates\layers_yw_final")
W, H = 1280, 1760
TORSO_BOX = (150, 400, 1130, 1440)     # координаты пластины 1280x1760, как резали кроп
FEATHER, SIGMA, TONE_MIX, SOFT = 30.0, 20.0, 0.35, 2.4

def arr(p, size=None):
    im = Image.open(p).convert("RGB")
    if size and im.size != size: im = im.resize(size, Image.LANCZOS)
    return np.asarray(im, np.float32)
def save(a, p): Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(p)
def luma(a): return 0.299*a[...,0]+0.587*a[...,1]+0.114*a[...,2]
def soften(a, s): return np.asarray(Image.fromarray(np.clip(a,0,255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(s)), np.float32)
def feather(m, r): return np.asarray(Image.fromarray((m*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)), np.float32)[...,None]/255.0

def build_l4():
    DST.mkdir(parents=True, exist_ok=True)
    B = arr(SRC/"L2_clean_raw.png", (W,H))                       # база — полный прогон
    x0,y0,x1,y1 = TORSO_BOX
    T = arr(SRC/"torso_raw.png", (x1-x0, y1-y0))                 # торс, обратно в сетку пластины
    Tfull = B.copy(); Tfull[y0:y1, x0:x1] = T
    # Содержание торса и базы разное (руки в другом месте) — частотное сведение
    # протаскивает призраки базы. Поэтому: тон подгоняем по кольцу вокруг кропа,
    # дальше простая альфа с растушёвкой. Шов сверху — по шее (y=445), где кожа
    # ровная; по полосам кокетки шов виден всегда.
    ring = np.zeros((H,W), bool); r = 40
    ring[max(0,y0-r):min(H,y1+r), max(0,x0-r):min(W,x1+r)] = True; ring[y0:y1, x0:x1] = False
    lb, lt = luma(B)[ring], luma(Tfull)[ring]
    # кольцо целиком в базе — сравниваем базу с торсом по его краевой полосе внутри кропа
    inner = np.zeros((H,W), bool); inner[y0:y0+r, x0:x1] = True; inner[y1-r:y1, x0:x1] = True
    inner[y0:y1, x0:x0+r] = True; inner[y0:y1, x1-r:x1] = True
    lt = luma(Tfull)[inner]; lb2 = luma(B)[inner]
    gain = float(np.clip(lb2.std()/max(lt.std(),1e-3), 0.8, 1.25)); off = float(lb2.mean() - lt.mean()*gain)
    Tt = np.clip(Tfull*gain + off, 0, 255)
    # Маска — силуэт фигуры из торсового прогона (тёмная ткань + кожа кистей), не
    # прямоугольник: фон целиком остаётся базе, и шву кропа неоткуда взяться.
    lt_full = luma(Tfull)
    sil = np.zeros((H,W), bool)
    sil[430:y1, x0+8:x1-8] = (lt_full[430:y1, x0+8:x1-8] < 48) | (lt_full[430:y1, x0+8:x1-8] > 115)
    sil = np.asarray(Image.fromarray((sil*255).astype(np.uint8)).filter(ImageFilter.MaxFilter(31)), bool)
    sil &= np.pad(np.ones((y1-430, x1-x0-16), bool), ((430, H-y1), (x0+8, W-x1+8)))
    m = sil
    w = feather(m, FEATHER)
    # верхняя кромка (шея) — отдельный мягкий градиент 430..520, чтобы не было полосы под подбородком
    ramp = np.clip((np.arange(H, dtype=np.float32) - 430.0) / 90.0, 0.0, 1.0)[:, None, None]
    w = w * ramp
    print("силуэт торса: %.1f%% кадра" % (100*m.mean()))
    L4 = B*(1-w) + Tt*w
    print("тон торса: x%.3f %+.1f" % (gain, off))
    # Низ ниже 1210: у торсового прогона там вторая пара кистей, у базы — руки в подоле.
    # Единственный чистый источник — классическая чистка: просто тёмная ткань. Размываем
    # (деталь там не нужна, а зерно и царапина — не нужны тем более) и сводим по тону
    # к платью торса на полосе 950..1150.
    C = soften(arr(SRC/"L2_classic_full.png", (W,H)), 40.0)     # остаётся только светотень
    C = np.repeat(luma(C)[...,None], 3, axis=2)                    # без бурого оттенка пластины
    dark = sil & (lt_full < 48); dark[:900] = False              # только тёмная ткань платья ниже груди
    target = float(np.median(np.clip(lt_full*gain+off,0,255)[dark])) if dark.any() else 30.0
    print("тон платья для низа: %.1f (по %d px)" % (target, dark.sum()))
    g2 = 0.35; o2 = target - float(luma(C)[1210:, :].mean())*g2
    Cb = np.clip(C*g2 + o2, 0, 255)
    # Заменяем не весь низ, а (а) призрачную кисть торса ниже 1200 — светлое пятно на
    # тёмной ткани, расширенное, и (б) полосу под кропом, где у базы руки в подоле.
    ghost = np.zeros((H,W), bool)
    ghost[1200:y1, x0:x1] = lt_full[1200:y1, x0:x1] > 62
    ghost = np.asarray(Image.fromarray((ghost*255).astype(np.uint8)).filter(ImageFilter.MaxFilter(61)), bool)
    m2 = ghost.copy(); m2[y1-20:, :] = True
    print("призрак кисти: %d px" % ghost.sum())
    w2 = feather(m2, 35.0)
    L4 = L4*(1-w2) + Cb*w2
    print("низ из классики: x%.3f %+.1f" % (g2, o2))
    save(arr(SRC/"L1_master.png"), DST/"L1_master.png")
    save(arr(SRC/"L2_classic_full.png", (W,H)), DST/"L2_clean.png")
    save(soften(L4, SOFT), DST/"L3_tone.png"); save(L4, DST/"L4_detail.png")
    json.dump({"база":"L2_clean_raw (полный Kontext)","торс":"torso_raw","box":TORSO_BOX,"feather":FEATHER,"sigma":SIGMA,"tone_mix":TONE_MIX},
              open(DST/"decision.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
    print("L1..L4 записаны; средняя яркость L4 %.1f" % luma(L4).mean())

def build_l5(color_path):
    L4 = arr(DST/"L4_detail.png"); K = arr(color_path, (W,H))
    Y4 = luma(L4)[...,None]; chroma = K - luma(K)[...,None]
    # цветной прогон снова кладёт руки в подол — его цветность на тёмной ткани даёт
    # оранжевое пятно не там. Платье чёрное, цвета у него нет: цветность оставляем
    # только на светлом (кожа, кокетка, фон), сглаженную.
    chroma = soften(chroma + 128.0, 5.0) - 128.0
    keep = np.clip((Y4 - 55.0) / 55.0, 0.0, 1.0)
    below = np.clip((np.arange(H, dtype=np.float32) - 780.0) / 80.0, 0.0, 1.0)[:, None, None]
    keep = keep * (1.0 - 0.5 * below)             # кисти: цветность вдвое слабее, иначе оранжевые
    L5 = Y4 + chroma * keep
    save(L5, DST/"L5_color.png"); print("L5 записан: яркость L4 + цветность %s" % color_path)

if __name__ == "__main__":
    build_l4() if sys.argv[1]=="l4" else build_l5(sys.argv[2])

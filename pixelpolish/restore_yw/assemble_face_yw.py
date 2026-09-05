# -*- coding: utf-8 -*-
"""Вариант B: лицо из отдельного прогона по кропу (face_raw, волосы гладко назад)
кладётся в L4 варианта A (база run1 + торс) эллипсом с подгонкой тона по кольцу.
  python assemble_face_yw.py  -> D:\PixelPolish\plates\layers_yw_finalB\L1..L5 и layers_yw_bustB
"""
import sys, io, os, json
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
SRC = Path(r"D:\PixelPolish\plates\layers_yw"); A = Path(r"D:\PixelPolish\plates\layers_yw_final")
B = Path(r"D:\PixelPolish\plates\layers_yw_finalB"); BB = Path(r"D:\PixelPolish\plates\layers_yw_bustB")
W, H = 1280, 1760
FBOX = (430, 0, 970, 580)          # кроп лица, координаты пластины
def arr(p, size=None):
    im = Image.open(p).convert("RGB")
    if size and im.size != size: im = im.resize(size, Image.LANCZOS)
    return np.asarray(im, np.float32)
def save(a, p): Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(p)
def luma(a): return 0.299*a[...,0]+0.587*a[...,1]+0.114*a[...,2]
def soften(a, s): return np.asarray(Image.fromarray(np.clip(a,0,255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(s)), np.float32)
def feather(m, r): return np.asarray(Image.fromarray((m*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)), np.float32)[...,None]/255.0
B.mkdir(exist_ok=True); BB.mkdir(exist_ok=True)
L4a = arr(A/"L4_detail.png"); L5a = arr(A/"L5_color.png")
x0,y0,x1,y1 = FBOX
F = arr(SRC/"face_raw.png", (x1-x0, y1-y0)); Ff = L4a.copy(); Ff[y0:y1, x0:x1] = F
# маска: эллипс по голове и шее (без воротника кропа — он выдуман), растушёвка 30
yy, xx = np.mgrid[0:H, 0:W]
cx, cy, rx, ry = 700, 255, 268, 300   # шире: накрыть локоны базы
m = ((xx-cx)/rx)**2 + ((yy-cy)/ry)**2 <= 1.0
m &= yy < 480                     # ниже — кокетка варианта A
w = feather(m, 30.0)
# тон: кольцо вокруг эллипса, база против вставки
ring = (((xx-cx)/(rx+40))**2 + ((yy-cy)/(ry+40))**2 <= 1.0) & ~m & (yy < 500) & (yy >= y0) & (xx >= x0) & (xx < x1)
inner = m & ~(((xx-cx)/(rx-40))**2 + ((yy-cy)/(ry-40))**2 <= 1.0)
la, lf = luma(L4a)[ring], luma(Ff)[inner]
gain = float(np.clip(la.std()/max(lf.std(),1e-3), 0.8, 1.25)); off = float(la.mean() - lf.mean()*gain)
Ft = np.clip(Ff*gain + off, 0, 255)
L4b = L4a*(1-w) + Ft*w
# L5: яркость нового L4 + цветность варианта A (там уже погашено тёмное и кисти)
chroma = L5a - luma(L5a)[...,None]
Yb = luma(L4b)[...,None]
keep = np.clip((Yb - 55.0) / 55.0, 0.0, 1.0)      # тёмное (волосы, платье) — без цвета
L5b = Yb + chroma * keep
for n in ("L1_master.png", "L2_clean.png"): save(arr(A/n), B/n)
save(soften(L4b, 2.4), B/"L3_tone.png"); save(L4b, B/"L4_detail.png"); save(L5b, B/"L5_color.png")
for n in ("L1_master.png","L2_clean.png","L3_tone.png","L4_detail.png","L5_color.png"):
    Image.open(B/n).crop((0,0,1280,1300)).save(BB/n)
json.dump({"лицо":"face_raw (кроп 1504x1616, seed 404040)","box":FBOX,"эллипс":[cx,cy,rx,ry],"gain":round(gain,3),"offset":round(off,1)},
          open(B/"decision.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
print("вариант B: тон лица x%.3f %+.1f; слои в %s и %s" % (gain, off, B, BB))

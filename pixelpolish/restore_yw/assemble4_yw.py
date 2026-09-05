# -*- coding: utf-8 -*-
"""youngwoman1855, сборка №4 — InstantID. Никаких композитов лица.

  L1  кроп мастера
  L2  классическая чистка (L2_classic_v2) — стадия «протёрли» видна
  L3  L4 размытый 2.4 (тон)
  L4  кадр InstantID целиком (SDXL img2img по L4 v3, личность — слепок лица с пластины)
  L5  яркость L4 + цветность полного цветного прогона Kontext по этому же кадру;
      на чёрном платье цвет погашен, кисти — цветность кожи лица

  set YW_IID=iid_d70_s21.png  set YW_COLOR=L5_color_iid70_raw.png
  python assemble4_yw.py           -> layers_yw_v4 и layers_yw_bust4 (обрез 1300)
"""
import json, sys, io, os
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
SRC = Path(r"D:\PixelPolish\plates\layers_yw")
DST = Path(r"D:\PixelPolish\plates\layers_yw_v4"); BUST = Path(r"D:\PixelPolish\plates\layers_yw_bust4")
W, H = 1280, 1760
IID = os.environ.get("YW_IID", "iid_d70_s21.png"); COLOR = os.environ.get("YW_COLOR", "L5_color_iid70_raw.png")

def arr(p, size=None):
    im = Image.open(p).convert("RGB")
    if size and im.size != size: im = im.resize(size, Image.LANCZOS)
    return np.asarray(im, np.float32)
def save(a, p): Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(p)
def luma(a): return 0.299*a[...,0]+0.587*a[...,1]+0.114*a[...,2]
def soften(a, s): return np.asarray(Image.fromarray(np.clip(a,0,255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(s)), np.float32)
def feather(m, r): return np.asarray(Image.fromarray((m*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)), np.float32)[...,None]/255.0
def grow(m, k): return np.asarray(Image.fromarray((m*255).astype(np.uint8)).filter(ImageFilter.MaxFilter(k)), bool)

DST.mkdir(exist_ok=True); BUST.mkdir(exist_ok=True)
L4 = arr(SRC/IID, (W,H)); L4 = np.repeat(luma(L4)[...,None], 3, axis=2)
K = arr(SRC/COLOR, (W,H))
Y4 = luma(L4)[...,None]
chroma = soften(K - luma(K)[...,None] + 128.0, 5.0) - 128.0
keep = np.clip((Y4 - 55.0)/55.0, 0, 1)                             # чёрное платье — без цвета
yy, xx = np.mgrid[0:H, 0:W]
face = (((xx-700)/150.0)**2 + ((yy-280)/200.0)**2 <= 1.0) & (Y4[...,0] > 120)
skin = chroma[face].mean(axis=0)
hand = np.zeros((H,W), bool); hand[850:1200, 540:980] = True; hand &= Y4[...,0] > 80
hand = grow(hand, 25); wh = feather(hand, 12.0)
near = np.zeros((H,W), bool); near[850:1200, 540:980] = True
chroma = chroma*np.where(near[...,None] & (wh < 0.5), 0.0, 1.0)
chroma = chroma*(1-wh) + skin[None,None,:]*wh                      # кисти — в тон лица
# лицо и шея: цветность прогона легла пятнами (Kontext перерисовал лицо) — ровный тон кожи,
# плюс лёгкий румянец на щеках и губах отдельной маской
fell = (((xx-700)/175.0)**2 + ((yy-300)/250.0)**2 <= 1.0) & (Y4[...,0] > 100)
wf = feather(grow(fell, 9), 12.0)
chroma = chroma*(1-wf) + skin[None,None,:]*wf
blush = np.zeros((H,W), bool); blush[300:380, 590:660] = True; blush[300:380, 740:810] = True; blush[385:420, 665:735] = True
wb = feather(blush, 22.0) * np.clip((Y4-110.0)/40.0, 0, 1)
chroma = chroma + np.array([9.0, -2.0, -3.0], np.float32)*wb
skin = skin*0.72                                                    # кожа: ровно, но не персик
chroma = chroma*(1-wf) + skin[None,None,:]*wf                       # (пересчёт лица с приглушённой кожей)
chroma = chroma*(1-wh) + skin[None,None,:]*wh
# фон: цветность прогона даёт оливковый — вне фигуры ставим тёплый нейтральный серый
fig = (Y4[...,0] < 60) | fell | hand | np.pad(np.ones((700-470, 960-330), bool), ((470, H-700), (330, W-960)))
bgw = 1.0 - feather(grow(fig, 41), 30.0)
chroma = chroma*(1-bgw) + np.array([4.0, 1.0, -5.0], np.float32)*bgw
yoke = np.zeros((H,W), bool); yoke[470:700, 330:960] = True; wy = feather(yoke, 20.0)
chroma = chroma*(1 - 0.7*wy)                                       # кокетка не оранжевая
warm = np.array([7.0, 1.5, -7.5], np.float32)[None,None,:]
dress = np.clip(1.0 - Y4/90.0, 0, 1)
L5 = Y4 + chroma*keep + warm*(0.6 + 0.4*keep) + np.array([5.0, 0.0, -6.0], np.float32)*dress

save(arr(SRC/"L1_master.png"), DST/"L1_master.png")
save(arr(SRC/"L2_classic_v2.png", (W,H)), DST/"L2_clean.png")
# левый нижний клочок старой базы (светлый полосатый блок) — в тон платья
blob = np.zeros((H,W), bool); blob[930:1120, 250:400] = True; blob &= Y4[...,0] > 60   # левый манжет старой базы
wbl = feather(grow(blob, 21), 18.0)
dressY = float(np.median(Y4[1000:1250, 300:520]))
cb = feather(grow(blob, 21), 18.0); L5 = L5*(1-cb) + np.repeat(luma(L5)[...,None],3,2)*cb
for arrx in (L4, L5):
    arrx[...] = arrx*(1-wbl) + (soften(arrx, 30.0)*0 + dressY)*wbl
save(soften(L4, 2.4), DST/"L3_tone.png"); save(L4, DST/"L4_detail.png"); save(L5, DST/"L5_color.png")
for n in ("L1_master.png","L2_clean.png","L3_tone.png","L4_detail.png","L5_color.png"):
    Image.open(DST/n).crop((0,0,W,1300)).save(BUST/n)
json.dump({"L4": IID, "цвет": COLOR, "метод": "InstantID (SDXL img2img по L4 v3, слепок лица GFPGAN-кроп, kps с очищенной пластины)",
           "skin_chroma": [round(float(v),1) for v in skin]}, open(DST/"decision.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
print("v4 слои: L4 = %s, цвет = %s, яркость L4 %.1f" % (IID, COLOR, luma(L4).mean()))

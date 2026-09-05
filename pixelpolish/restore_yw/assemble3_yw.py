# -*- coding: utf-8 -*-
"""youngwoman1855, сборка №3 — по совету критиков (СОВЕТ_КРИТИКОВ_youngwoman1855.md).

  база      — первый полный прогон Kontext (свет, фон): L2_clean_raw.png
  лицо      — face_v2_raw (кроп 1504x1616): длинный овал, тонкие брови, волосы назад;
              эллипс по голове, тон по кольцу, растушёвка 34
  торс      — torso_v2_raw (кроп 1504x1600): кисти одного тона; маска — силуэт
  низ       — ниже кропа торса: гладкая тёмная ткань из классики (только светотень)
  L2        — L2_classic_v2 (сильный деспекл, снята лиловая полоса, +контраст лица):
              стадия «чистая пластина» должна быть ВИДНА
  L3        — L4 размытый 2.4
  L5        — яркость L4 + цветность полного цветного прогона по L4, гейт по яркости
              (чёрное платье без цвета), кисти цветом как лицо

  python assemble3_yw.py l4              -> layers_yw_v3\L1..L4 и layers_yw_bust3 (обрез 1300)
  python assemble3_yw.py l5 <color.png>  -> L5
"""
import json, sys, io
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
SRC = Path(r"D:\PixelPolish\plates\layers_yw")
DST = Path(r"D:\PixelPolish\plates\layers_yw_v3"); BUST = Path(r"D:\PixelPolish\plates\layers_yw_bust3")
W, H = 1280, 1760
FBOX = (430, 0, 970, 580)             # кроп лица (координаты пластины)
TBOX = (150, 400, 1130, 1440)         # кроп торса
FACE_ELL = (700, 255, 262, 296)       # cx, cy, rx, ry — голова с волосами
FEATHER = 34.0

def arr(p, size=None):
    im = Image.open(p).convert("RGB")
    if size and im.size != size: im = im.resize(size, Image.LANCZOS)
    return np.asarray(im, np.float32)
def save(a, p): Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(p)
def luma(a): return 0.299*a[...,0]+0.587*a[...,1]+0.114*a[...,2]
def soften(a, s): return np.asarray(Image.fromarray(np.clip(a,0,255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(s)), np.float32)
def feather(m, r): return np.asarray(Image.fromarray((m*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)), np.float32)[...,None]/255.0
def grow(m, k): return np.asarray(Image.fromarray((m*255).astype(np.uint8)).filter(ImageFilter.MaxFilter(k)), bool)
def tone_match(src, ref, m_in, m_ref, lo=0.8, hi=1.25):
    """яркостный gain/offset вставки по её кромке против кольца базы; цветность вставки — нейтральная"""
    ls, lr = luma(src)[m_in], luma(ref)[m_ref]
    g = float(np.clip(lr.std()/max(ls.std(),1e-3), lo, hi)); o = float(lr.mean() - ls.mean()*g)
    y = np.clip(luma(src)*g + o, 0, 255)
    return np.repeat(y[...,None], 3, axis=2), g, o

def build_l4():
    DST.mkdir(exist_ok=True); BUST.mkdir(exist_ok=True)
    yy, xx = np.mgrid[0:H, 0:W]
    B = arr(SRC/"L2_clean_raw.png", (W,H))
    B = np.repeat(luma(B)[...,None], 3, axis=2)                 # база в нейтральном сером — цвет придёт из L5
    rep = {"база": "L2_clean_raw"}
    # ---- лицо: рецепт REPORT_V5B — геометрия и черты из GFPGAN (та же женщина),
    # кладутся в полный прогон Kontext, чей контур головы совпадает с пластиной.
    # Эллипс только по чертам (лоб под волосами — подбородок), тон: лицо к лицу.
    x0,y0,x1,y1 = FBOX
    G = np.asarray(Image.open(SRC/"face_gfpgan_w05.png").convert("L").resize((x1-x0, y1-y0), Image.LANCZOS), np.float32)
    # белые точки крапа, пришедшие с GFPGAN-входа: всё, что ярче локального фона на 20+, гасим
    Gs = soften(np.repeat(G[...,None],3,2), 3.0)[...,0]
    spots = (G - Gs) > 20
    sw = np.asarray(Image.fromarray((spots*255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(2.0)), np.float32)/255.0
    G = G*(1-sw) + Gs*sw                                          # мягкая подмена, без ступенек
    Gf = luma(B).copy(); Gf[y0:y1, x0:x1] = G
    # эллипс: лоб под волосами — шея целиком, чтобы челюсть и подбородок были из GFPGAN,
    # а шов лёг в тёмные волосы и на ровную шею, не поперёк контура лица
    cx,cy,rx,ry = 700, 300, 178, 248
    ell = ((xx-cx)/rx)**2 + ((yy-cy)/ry)**2 <= 1.0
    lb, lg = luma(B)[ell], Gf[ell]
    g1 = float(np.clip(lb.std()/max(lg.std(),1e-3), 0.7, 1.5)); o1 = float(lb.mean() - lg.mean()*g1)
    Gt = np.clip(Gf*g1 + o1, 0, 255)
    Gt = np.clip(Gt + (Gt - soften(np.repeat(Gt[...,None],3,2), 1.4)[...,0])*0.3, 0, 255)   # чуть поверхности
    w1 = feather(ell, 16.0)
    out = B*(1-w1) + np.repeat(Gt[...,None], 3, axis=2)*w1
    rep["лицо"] = {"src": "face_gfpgan_w05 в run1 (REPORT_V5B)", "эллипс": [cx,cy,rx,ry], "gain": round(g1,3), "offset": round(o1,1)}
    print("лицо: тон x%.3f %+.1f" % (g1, o1))
    # ---- торс (силуэт: тёмная ткань + кожа кистей), шов по шее градиентом 430..520
    x0,y0,x1,y1 = TBOX
    Tf = out.copy(); Tf[y0:y1, x0:x1] = arr(SRC/"torso_raw.png", (x1-x0, y1-y0))
    lt = luma(Tf)
    sil = np.zeros((H,W), bool)
    sil[430:y1, x0+8:x1-8] = (lt[430:y1, x0+8:x1-8] < 60) | (lt[430:y1, x0+8:x1-8] > 110)
    sil = grow(sil, 31)
    sil &= np.pad(np.ones((y1-430, x1-x0-16), bool), ((430, H-y1), (x0+8, W-x1+8)))
    inner = np.zeros((H,W), bool); r = 40
    inner[y0:y0+r, x0:x1] = inner[y1-r:y1, x0:x1] = True; inner[y0:y1, x0:x0+r] = inner[y0:y1, x1-r:x1] = True
    Tt, g2, o2 = tone_match(Tf, out, inner, inner)              # кромка кропа против базы в тех же местах
    w2 = feather(sil, 30.0) * np.clip((np.arange(H, dtype=np.float32)-430.0)/90.0, 0, 1)[:,None,None]
    out = out*(1-w2) + Tt*w2
    rep["торс"] = {"src": "torso_raw (v1)", "box": TBOX, "gain": round(g2,3), "offset": round(o2,1), "силуэт_%": round(100*sil.mean(),1)}
    print("торс: тон x%.3f %+.1f, силуэт %.1f%%" % (g2, o2, 100*sil.mean()))
    # ---- низ: призрачная кисть торса ниже 1200 и полоса под кропом — гладкая тёмная ткань
    ghost = np.zeros((H,W), bool); ghost[1200:y1, x0:x1] = lt[1200:y1, x0:x1] > 70
    ghost = grow(ghost, 61); m3 = ghost.copy(); m3[y1-20:, :] = True
    C = soften(arr(SRC/"L2_classic_v2.png", (W,H)), 40.0); C = np.repeat(luma(C)[...,None], 3, axis=2)
    dark = sil & (lt < 60); dark[:900] = False
    target = float(np.median(np.clip(lt*g2+o2, 0, 255)[dark])) if dark.any() else 35.0
    Cb = np.clip(C*0.35 + (target - float(luma(C)[1210:, :].mean())*0.35), 0, 255)
    w3 = feather(m3, 35.0)
    out = out*(1-w3) + Cb*w3
    print("низ: тон платья %.1f, призрак %d px" % (target, ghost.sum()))
    # ---- слои
    save(arr(SRC/"L1_master.png"), DST/"L1_master.png")
    save(arr(SRC/"L2_classic_v2.png", (W,H)), DST/"L2_clean.png")
    save(soften(out, 2.4), DST/"L3_tone.png"); save(out, DST/"L4_detail.png")
    json.dump(rep, open(DST/"decision.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
    for n in ("L1_master.png","L2_clean.png","L3_tone.png","L4_detail.png"):
        Image.open(DST/n).crop((0,0,W,1300)).save(BUST/n)
    print("L1..L4 записаны; средняя яркость L4 %.1f" % luma(out).mean())

def build_l5(color_path):
    L4 = arr(DST/"L4_detail.png"); K = arr(color_path, (W,H))
    Y4 = luma(L4)[...,None]; chroma = soften(K - luma(K)[...,None] + 128.0, 5.0) - 128.0
    keep = np.clip((Y4 - 55.0)/55.0, 0, 1)                        # чёрное платье — без цвета
    yy, xx = np.mgrid[0:H, 0:W]
    cx,cy,rx,ry = FACE_ELL
    face = (((xx-cx)/rx)**2 + ((yy-cy)/ry)**2 <= 0.6) & (Y4[...,0] > 120)
    skin = chroma[face].mean(axis=0)                              # средняя цветность кожи лица
    hand = np.zeros((H,W), bool); hand[850:1200, 540:980] = True   # шире: пальцы верхней кисти правее 860
    hand &= Y4[...,0] > 80                                        # только светлое — сами кисти
    hand = grow(hand, 25); wh = feather(hand, 12.0)
    # и вокруг кистей — никакой чужой цветности (оранжевые остатки рядом с пальцами)
    near = np.zeros((H,W), bool); near[850:1200, 540:980] = True
    chroma = chroma * np.where(near[...,None] & (wh < 0.5), 0.0, 1.0) + 0.0
    chroma = chroma*(1-wh) + skin[None,None,:]*wh                 # кисти — в тон лица, один цвет
    # голова заменена — цветность старого лица (локоны, другая геометрия) сюда не годится:
    # в прямоугольнике головы цвет только на коже лица (ровный skin), остальное нейтрально
    yoke = np.zeros((H,W), bool); yoke[470:700, 330:960] = True
    wy = feather(yoke, 20.0)
    chroma = chroma*(1 - 0.55*wy)                                 # кокетка: цветность прогона вдвое тише
    fell = (((xx-700)/178.0)**2 + ((yy-300)/248.0)**2 <= 1.0) & (Y4[...,0] > 95)
    wf = feather(fell, 14.0)
    chroma = chroma*(1-wf) + skin[None,None,:]*wf
    # тёплый финал: лёгкая сепия на всё, платье в тёмно-коричневый, а не чёрный
    warm = np.array([7.0, 1.5, -7.5], np.float32)[None,None,:]
    dress = np.clip(1.0 - Y4/90.0, 0, 1)                          # тёмное
    L5 = Y4 + chroma*keep + warm*(0.6 + 0.4*keep) + np.array([5.0, 0.0, -6.0], np.float32)*dress
    # кисти: резкость к уровню лица
    hp = L5 - soften(L5, 2.0)
    L5 = L5 + hp*0.9*wh
    save(L5, DST/"L5_color.png"); Image.open(DST/"L5_color.png").crop((0,0,W,1300)).save(BUST/"L5_color.png")
    print("L5 записан: яркость L4 + цветность %s" % Path(color_path).name)

if __name__ == "__main__":
    build_l4() if sys.argv[1] == "l4" else build_l5(sys.argv[2])

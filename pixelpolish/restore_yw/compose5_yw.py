# -*- coding: utf-8 -*-
"""youngwoman1855 v5: голова InstantID (inpaint по маске, тело от торса v1 с прозрачной кокеткой)
+ низ из полного прогона iid_d70 (чистое платье) + подгонка фона у головы к телу по низким частотам."""
import numpy as np, io, sys
from PIL import Image, ImageFilter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
L = 'D:/PixelPolish/plates/layers_yw/'; W, H = 1280, 1760
def A(p): return np.asarray(Image.open(L+p).convert('L').resize((W,H), Image.LANCZOS), np.float32)
def soft(a, s): return np.asarray(Image.fromarray(np.clip(a,0,255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(s)), np.float32)
def feather(m, r): return np.asarray(Image.fromarray((m*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)), np.float32)/255.0
head = A('iid_head_s21.png'); full = A('iid_d70_s21.png')
yy, xx = np.mgrid[0:H, 0:W]
# 1) ореол: внутри маски головы фон светлее. Низкие частоты фона (не фигура) подгоняем к низким частотам
#    того же места в полном прогоне (там фон ровный), фигуру не трогаем.
hm = (((xx-700)/300.0)**2 + ((yy-250)/360.0)**2 <= 1.0) & (yy < 640)   # шире и ниже плеч — шов уходит в тёмное платье
fig = (head < 45) | (head > 135)                                  # волосы/платье и кожа — фигура
fig = np.asarray(Image.fromarray((fig*255).astype(np.uint8)).filter(ImageFilter.MaxFilter(21)), bool)
bgw = feather(hm & ~fig, 32.0)
diff = soft(full, 35.0) - soft(head, 35.0)
out = head + diff*bgw
# 1b) шов инпейнта у воротника: голова -> тело вертикальным градиентом y 455..565, по всей ширине маски
base = A('iid_base_body.png')
ramp = np.clip((yy - 455.0)/110.0, 0, 1)                           # 0 наверху (голова), 1 внизу (тело)
band = (yy > 430) & (yy < 600) & (xx > 380) & (xx < 1020)
wband = feather(band, 12.0) * ramp
out = out*(1-wband) + base*wband
# 1c) ступень справа от шеи: фон инпейнта (выше ~505) темнее фона базы ниже. Меряем и выравниваем
#     низкие частоты фона в зоне инпейнта справа и слева от шеи по фону базы сразу под срезом.
for x0,x1 in ((790,1020),(380,600)):
    zone = (yy > 380) & (yy < 512) & (xx > x0) & (xx < x1) & ~fig
    ref  = (yy > 520) & (yy < 570) & (xx > x0) & (xx < x1) & ~fig & (out < 135) & (out > 40)
    if zone.sum() > 500 and ref.sum() > 300:
        d = float(np.median(out[ref]) - np.median(out[zone]))
        wz = feather(zone, 16.0)
        out = out + d*wz
        print("фон у шеи x%d..%d: сдвиг %+.1f" % (x0, x1, d))
# 2) низ: ниже 1150 — платье и кисти из полного прогона (там чисто), шов растушёван
low = np.zeros((H,W), bool); low[1150:, :] = True
wl = feather(low, 40.0)
g = float(np.median(out[1000:1120, 300:520])) - float(np.median(full[1000:1120, 300:520]))
out = out*(1-wl) + np.clip(full + g, 0, 255)*wl
Image.fromarray(np.clip(out,0,255).astype(np.uint8)).save(L+'v5_L4_gray.png')
print('v5 L4: ореол снят по фону (%.1f%% кадра), низ из iid_d70 со сдвигом %+.1f' % (100*(bgw>0.5).mean(), g))

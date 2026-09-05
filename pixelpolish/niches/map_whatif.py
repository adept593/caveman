# -*- coding: utf-8 -*-
"""Years in a Minute — «What if <country> became a superpower?», карта-экспансия, 1080x1920, ~22 с.

Свой формат: подложка NASA Blue Marble (PD) в Меркаторе, границы Natural Earth (PD),
страна залита своим флагом, соседи поглощаются волнами (по 2.6 с), к каждой волне — подпись
и короткая фраза голосом (у конкурентов — немой ролик с водяным знаком). Медленный наезд.

  python map_whatif.py            -> D:\PixelPolish\ШОРТСЫ\whatif_<key>.mp4
Сценарий задаётся в SCEN (страна, волны, тексты).
"""
import asyncio, json, subprocess, sys, io
from pathlib import Path
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import edge_tts
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

GEO = Path(r"D:\PixelPolish\assets\geo"); FLAGS = Path(r"D:\PixelPolish\assets\flags")
MUSIC = Path(r"D:\PixelPolish\МУЗЫКА\gemini_lyria_01.m4a")
W, H, FPS = 1080, 1920, 30
F_BIG = ImageFont.truetype(r"C:\Windows\Fonts\impact.ttf", 80)
F_MID = ImageFont.truetype(r"C:\Windows\Fonts\bahnschrift.ttf", 52)
VOICE = "en-US-AndrewNeural"

SCEN = {
    "key": "poland", "iso": "pl", "country": "Poland",
    "view": (21.0, 52.0, 17.0),         # центр lon, lat и полуширина по долготе, градусы
    "waves": [
        ([], "2026. Poland today."),
        (["Lithuania", "Slovakia", "Czechia"], "First, the neighbors join."),
        (["Belarus", "Latvia", "Estonia", "Hungary"], "The Baltics and the plains follow."),
        (["Germany", "Ukraine", "Austria"], "Then the giants fall in line."),
        (["Romania", "Moldova", "Denmark", "Sweden", "Finland"], "From the Baltic to the Black Sea."),
    ],
    "outro": "Where are you watching from?",
}


def tts(text, path):
    async def go():
        await edge_tts.Communicate(text, VOICE, rate="+4%").save(str(path))
    asyncio.run(go())
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)]).decode())


def merc_y(lat):
    return np.log(np.tan(np.pi/4 + np.radians(lat)/2))


class View:
    def __init__(self, lon0, lat0, half_lon, w, h):
        self.w, self.h = w, h
        self.x0, self.x1 = np.radians(lon0 - half_lon), np.radians(lon0 + half_lon)
        sx = (self.x1 - self.x0) / w
        cy = merc_y(lat0); self.y0, self.y1 = cy - sx*h/2, cy + sx*h/2
    def px(self, lon, lat):
        x = (np.radians(lon) - self.x0) / (self.x1 - self.x0) * self.w
        y = (self.y1 - merc_y(lat)) / (self.y1 - self.y0) * self.h
        return x, y
    def background(self, bm):
        yy, xx = np.mgrid[0:self.h, 0:self.w]
        lon = np.degrees(self.x0 + (xx + 0.5) / self.w * (self.x1 - self.x0))
        my = self.y1 - (yy + 0.5) / self.h * (self.y1 - self.y0)
        lat = np.degrees(2*np.arctan(np.exp(my)) - np.pi/2)
        sx = np.clip(((lon + 180) / 360 * bm.shape[1]).astype(int), 0, bm.shape[1]-1)
        sy = np.clip(((90 - lat) / 180 * bm.shape[0]).astype(int), 0, bm.shape[0]-1)
        return bm[sy, sx]


def polys(geom):
    if isinstance(geom, Polygon): return [geom]
    if isinstance(geom, MultiPolygon): return list(geom.geoms)
    return []


def draw_country(mask_draw, view, geom):
    for p in polys(geom):
        c = np.array(p.exterior.coords); x, y = view.px(c[:, 0], c[:, 1])
        mask_draw.polygon(list(zip(x, y)), fill=255)
        for ring in p.interiors:
            c = np.array(ring.coords); x, y = view.px(c[:, 0], c[:, 1]); mask_draw.polygon(list(zip(x, y)), fill=0)


def main():
    S = SCEN; WORK = Path(rf"D:\PixelPolish\video\projects\whatif_{S['key']}"); WORK.mkdir(parents=True, exist_ok=True)
    OUT = Path(rf"D:\PixelPolish\ШОРТСЫ\whatif_{S['key']}.mp4")
    g = gpd.read_file(GEO / "ne_50m_admin_0_countries.shp").set_index("ADMIN")
    RW, RH = int(W*1.25), int(H*1.25)
    view = View(*S["view"], RW, RH)
    bm = np.asarray(Image.open(GEO / "blue_marble.jpg").convert("RGB"))
    base = Image.fromarray(view.background(bm)).filter(ImageFilter.GaussianBlur(0.6))
    base = Image.fromarray((np.asarray(base, np.float32) * 0.78).astype(np.uint8))
    bord = Image.new("L", (RW, RH), 0); bd = ImageDraw.Draw(bord)
    for geom in g.geometry:
        for p in polys(geom):
            c = np.array(p.exterior.coords); x, y = view.px(c[:, 0], c[:, 1])
            bd.line(list(zip(x, y)), fill=255, width=2)
    base.paste(Image.new("RGB", (RW, RH), (235, 235, 245)), (0, 0), bord.point(lambda v: int(v*0.45)))
    flag = Image.open(FLAGS / f"{S['iso']}.png").convert("RGB")
    owned = [S["country"]]; keys = []
    for wi, (names, _) in enumerate(S["waves"]):
        owned += names
        m = Image.new("L", (RW, RH), 0); md = ImageDraw.Draw(m)
        for nm in owned:
            if nm not in g.index: print("нет страны:", nm); continue
            draw_country(md, view, g.loc[nm].geometry)
        bbox = m.getbbox()
        fl = flag.resize((bbox[2]-bbox[0], bbox[3]-bbox[1]), Image.LANCZOS)
        layer = Image.new("RGB", (RW, RH)); layer.paste(fl, (bbox[0], bbox[1]))
        frame = base.copy(); frame.paste(layer, (0, 0), m.point(lambda v: int(v*0.88)))
        edge = m.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(3))
        frame.paste(Image.new("RGB", (RW, RH), (255, 255, 255)), (0, 0), edge)
        frame.save(WORK / f"key{wi}.png"); keys.append(frame)
    lines = [f"What if {S['country']} became a superpower?"] + [t for _, t in S["waves"]] + [S["outro"]]
    durs = [tts(t, WORK / f"v{i}.mp3") for i, t in enumerate(lines)]
    SEG = 2.6; INTRO = max(durs[0] + 0.4, 2.8); OUTRO = max(durs[-1] + 0.6, 2.6)
    total = INTRO + SEG*len(keys) + OUTRO
    fdir = WORK / "frames"; fdir.mkdir(exist_ok=True)
    for f in fdir.glob("*.png"): f.unlink()
    nfr = int(total * FPS)
    def key_at(t):
        if t < INTRO: return 0, 1.0
        k = min(int((t - INTRO) // SEG), len(keys)-1); u = ((t - INTRO) - k*SEG) / 0.5
        return k, min(u, 1.0)
    for i in range(nfr):
        t = i / FPS; k, u = key_at(t)
        img = keys[k] if (k == 0 or u >= 1.0) else Image.blend(keys[k-1], keys[k], u)
        z = 1.0 + 0.18 * (t / total); cw, ch = int(RW / z), int(RH / z)
        cx, cy = RW/2, RH/2 - (RH*0.04)*(t/total)
        crop = img.crop((int(cx-cw/2), int(cy-ch/2), int(cx+cw/2), int(cy+ch/2))).resize((W, H), Image.BILINEAR)
        d = ImageDraw.Draw(crop)
        d.rectangle((0, 0, W, 300), fill=(8, 10, 18))
        d.text((W/2, 110), "WHAT IF", font=F_MID, fill=(255, 210, 90), anchor="mm")
        d.text((W/2, 210), f"{S['country'].upper()} BECAME A SUPERPOWER?", font=F_BIG, fill=(255, 255, 255), anchor="mm")
        cap = S["waves"][k][1] if t >= INTRO else "2026"
        if t >= total - OUTRO: cap = S["outro"]
        d.rectangle((0, H-260, W, H), fill=(8, 10, 18))
        d.text((W/2, H-150), cap, font=F_MID, fill=(235, 235, 245), anchor="mm")
        crop.save(fdir / f"f{i:05d}.png")
    print(f"кадров {nfr}, {total:.1f} с")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", str(fdir / "f%05d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(WORK / "video.mp4")], check=True)
    starts = [0.0] + [INTRO + SEG*i for i in range(len(keys))] + [total - OUTRO]
    inputs = []; filt = []; mix = []
    for j, st in enumerate(starts):
        inputs += ["-i", str(WORK / f"v{j}.mp3")]; filt.append(f"[{j+1}:a]adelay={int(st*1000)}|{int(st*1000)}[v{j}]"); mix.append(f"[v{j}]")
    m = len(starts); inputs += ["-i", str(MUSIC)]
    filt.append(f"[{m+1}:a]atrim=0:{total},volume=0.14,afade=t=out:st={total-1.5}:d=1.5[mus]")
    filt.append("".join(mix) + f"[mus]amix=inputs={m+1}:normalize=0,alimiter=limit=0.9[a]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(WORK / "video.mp4")] + inputs +
                   ["-filter_complex", ";".join(filt), "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", str(OUT)], check=True)
    json.dump({"scen": S, "total": total}, open(WORK / "decision.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("готово:", OUT, OUT.stat().st_size, "байт")


if __name__ == "__main__":
    main()

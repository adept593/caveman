# -*- coding: utf-8 -*-
"""Сводка ночного прогона: results.md + contact_sheet.jpg по D:\PixelPolish\lab\<дата>\*\result.json."""
import json, sys, subprocess, datetime as dt
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
sys.stdout.reconfigure(encoding="utf-8")
LAB = Path(r"D:\PixelPolish\lab") / (sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat())
F = ImageFont.truetype(r"C:\Windows\Fonts\bahnschrift.ttf", 22)


def thumb(d):
    for p in sorted(d.iterdir()):
        if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp") and p.name != "thumb.jpg": return Image.open(p).convert("RGB")
    for p in sorted(d.iterdir()):
        if p.suffix.lower() in (".mp4", ".webm", ".mov"):
            t = d / "thumb.jpg"; subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "1", "-i", str(p), "-frames:v", "1", str(t)])
            if t.exists(): return Image.open(t).convert("RGB")
    for p in sorted(d.iterdir()):
        if p.suffix.lower() in (".flac", ".mp3", ".wav"):
            t = d / "thumb.jpg"; subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(p), "-filter_complex", "showwavespic=s=480x270:colors=#FFD25A", "-frames:v", "1", str(t)])
            if t.exists(): return Image.open(t).convert("RGB")
    for p in sorted(d.iterdir()):
        if p.suffix == ".txt":
            im = Image.new("RGB", (480, 270), (30, 34, 50)); dr = ImageDraw.Draw(im); txt = p.read_text(encoding="utf-8", errors="replace")[:220]; y = 10
            for i in range(0, len(txt), 40): dr.text((10, y), txt[i:i+40], font=F, fill=(230, 230, 240)); y += 26
            return im
    return None


def main():
    rows = []; tiles = []
    for d in sorted(p for p in LAB.iterdir() if p.is_dir()):
        r = d / "result.json"
        if not r.exists(): continue
        res = json.loads(r.read_text(encoding="utf-8")); rows.append(res)
        im = thumb(d) if res.get("ok") else None
        tile = Image.new("RGB", (480, 320), (24, 28, 42)); dr = ImageDraw.Draw(tile)
        if im: im.thumbnail((480, 270)); tile.paste(im, ((480 - im.width) // 2, 0))
        else: dr.text((16, 110), "ОШИБКА" if not res.get("ok") else "нет превью", font=F, fill=(255, 120, 100))
        dr.rectangle((0, 270, 480, 320), fill=(12, 14, 22)); dr.text((10, 280), f"{res['name'][:34]}  {res.get('seconds', '')}с", font=F, fill=(255, 210, 90))
        tiles.append(tile)
    cols = 4; rws = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 490 + 10, max(1, rws) * 330 + 10), (40, 40, 40))
    for i, t in enumerate(tiles): sheet.paste(t, (10 + (i % cols) * 490, 10 + (i // cols) * 330))
    sheet.save(LAB / "contact_sheet.jpg", quality=88)
    md = [f"# Прогон шаблонов лаунчера, {LAB.name}", "", "| шаблон | статус | сек | выходы / ошибка |", "|---|---|---|---|"]
    for r in rows:
        md.append(f"| `{r['name']}` | {'OK' if r.get('ok') else 'ошибка'} | {r.get('seconds', '')} | {', '.join(r.get('outputs', [])) if r.get('ok') else str(r.get('error'))[:160].replace('|', '/')} |")
    (LAB / "results.md").write_text("\n".join(md), encoding="utf-8")
    ok = sum(1 for r in rows if r.get("ok")); print(f"шаблонов {len(rows)}, OK {ok}, ошибок {len(rows)-ok} -> {LAB/'contact_sheet.jpg'}")


if __name__ == "__main__":
    main()

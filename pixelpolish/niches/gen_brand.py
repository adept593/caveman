# -*- coding: utf-8 -*-
"""Аватары (1024x1024) и баннеры (2048x1152) для 4 каналов: картинка Flux Kontext txt2img + название поверх (PIL).

  python gen_brand.py            -> D:/PixelPolish/channel_art/2026-09/<key>_avatar.png, <key>_banner.png
"""
import sys, io, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, str(Path(__file__).parent))
import stills_story as ss
sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(r"D:\PixelPolish\channel_art\2026-09"); OUT.mkdir(parents=True, exist_ok=True)
F_T = ImageFont.truetype(r"C:\Windows\Fonts\impact.ttf", 150); F_S = ImageFont.truetype(r"C:\Windows\Fonts\bahnschrift.ttf", 60)

CH = {
 "yearsinaminute": {"title": "YEARS IN A MINUTE", "tag": "what if · maps · alternate history",
   "avatar": "a stylized glowing globe made of glass with red and gold country borders lit from inside, dark navy background, centered, icon-like, clean, no text",
   "banner": "an epic wide cinematic view of a world map on aged parchment blending into a satellite view of Earth at night, glowing golden borders sweeping across continents, dark navy and gold palette, no text"},
 "wildorigins": {"title": "WILD ORIGINS", "tag": "animal facts · evolution · daily",
   "avatar": "a striking close-up portrait of a wolf face half in shadow with amber eyes, dark forest background, dramatic light, centered, no text",
   "banner": "a wide panoramic scene of a prehistoric shoreline at dawn where a modern whale, a wolf and a crocodile silhouette stand in a line of evolution, mist and golden light, photoreal, no text"},
 "flagiqarena": {"title": "FLAG IQ ARENA", "tag": "guess the flag · 3 seconds · daily quiz",
   "avatar": "a bold minimal emblem: a waving flag shape made of many small colorful flags, on a dark navy studio background with a gold ring, centered, icon-like, no text",
   "banner": "a wide dark navy studio backdrop with dozens of world flags floating in perspective, soft spotlights, gold accents, clean and modern, no text"},
 "scripturelens": {"title": "SCRIPTURE LENS", "tag": "bible stories · one minute · daily",
   "avatar": "an ancient open scroll glowing with warm light in a dark stone chamber, a single beam of light from above, cinematic, centered, no text",
   "banner": "a wide cinematic biblical landscape at golden hour: a shepherd on a hill overlooking a vast valley, distant ancient city, dramatic clouds with rays of light, photoreal, no text"},
}


def shadow_text(d, xy, text, font, fill, anchor="mm"):
    x, y = xy
    for dx, dy in ((4, 4), (-2, 2), (2, -2)):
        d.text((x+dx, y+dy), text, font=font, fill=(0, 0, 0), anchor=anchor)
    d.text((x, y), text, font=font, fill=fill, anchor=anchor)


def main():
    ss.GW, ss.GH = 1024, 1024
    for key, c in CH.items():
        av = ss.gen(c["avatar"], 901, OUT / f"{key}_avatar_raw.png")
        im = Image.open(av).convert("RGB").resize((1024, 1024), Image.LANCZOS)
        m = Image.new("L", (1024, 1024), 0); ImageDraw.Draw(m).ellipse((0, 0, 1023, 1023), fill=255); m = m.filter(ImageFilter.GaussianBlur(6))
        bg = Image.new("RGB", (1024, 1024), (10, 12, 20)); bg.paste(im, (0, 0), m); bg.save(OUT / f"{key}_avatar.png")
    ss.GW, ss.GH = 1344, 768
    for key, c in CH.items():
        bn = ss.gen(c["banner"], 902, OUT / f"{key}_banner_raw.png")
        im = Image.open(bn).convert("RGB").resize((2048, 1152), Image.LANCZOS)
        d = ImageDraw.Draw(im, "RGBA")
        d.rectangle((0, 576-230, 2048, 576+230), fill=(0, 0, 0, 110))      # безопасная зона YouTube: центр 1235x338
        shadow_text(d, (1024, 540), c["title"], F_T, (255, 255, 255))
        shadow_text(d, (1024, 665), c["tag"], F_S, (255, 210, 90))
        im.save(OUT / f"{key}_banner.png")
        print(key, "готов")
    json.dump({k: {"title": v["title"], "avatar": v["avatar"], "banner": v["banner"]} for k, v in CH.items()},
              open(OUT / "brand.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()

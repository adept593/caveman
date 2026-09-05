# -*- coding: utf-8 -*-
"""Flag IQ Arena — квиз «угадай флаг за 3 секунды», 10 флагов, 1080x1920, ~60 с.

Формат свой: тёмная студия с виньеткой (не зелёная ткань), флаг крупно по центру,
кольцо-таймер 3 с, ответ вспыхивает, слева список 4 уровней заполняется.
Голос — edge-tts en-US-AndrewNeural, текст свой. Флаги — flagcdn (гос. символы, PD).

  python flag_quiz.py  [name]         -> D:\PixelPolish\ШОРТСЫ\flagquiz_<name>.mp4
"""
import asyncio, json, subprocess, sys, io, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import edge_tts
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

EP = {}
if len(sys.argv) > 1 and sys.argv[1].endswith(".json"):
    EP = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))      # {name, quiz, intro?, cues?, outro?}
NAME = EP.get("name") or (sys.argv[1] if len(sys.argv) > 1 else "ep01")
FLAGS = Path(r"D:\PixelPolish\assets\flags"); MUSIC = Path(r"D:\PixelPolish\МУЗЫКА\gemini_lyria_01.m4a")
WORK = Path(rf"D:\PixelPolish\video\projects\flagquiz_{NAME}"); WORK.mkdir(parents=True, exist_ok=True)
OUT = Path(rf"D:\PixelPolish\ШОРТСЫ\flagquiz_{NAME}.mp4")
W, H, FPS = 1080, 1920, 30
F_BIG = ImageFont.truetype(r"C:\Windows\Fonts\impact.ttf", 92)
F_MID = ImageFont.truetype(r"C:\Windows\Fonts\bahnschrift.ttf", 54)
F_LIST = ImageFont.truetype(r"C:\Windows\Fonts\bahnschrift.ttf", 44)

# (iso2, name) — 10 флагов; уровни по 3/3/3/1
QUIZ = [("jp", "Japan"), ("ca", "Canada"), ("br", "Brazil"),
        ("ar", "Argentina"), ("kr", "South Korea"), ("tr", "Turkey"),
        ("np", "Nepal"), ("kz", "Kazakhstan"), ("lk", "Sri Lanka"),
        ("bt", "Bhutan")]
LEVELS = [("EASY", 3, (110, 230, 140)), ("MEDIUM", 3, (255, 210, 90)), ("HARD", 3, (255, 120, 100)), ("EXTREME", 1, (200, 130, 255))]
VOICE = "en-US-AndrewNeural"
INTRO = "Ten flags. Three seconds each. Nobody gets number ten."
CUES = ["Flag one.", "Number two.", "Three.", "Medium now. Four.", "Five.", "Six. Still with me?",
        "Hard level. Seven.", "Eight.", "Nine.", "Extreme. The last one."]
OUTRO = "Comment your score out of ten."
if EP:
    QUIZ = [tuple(q) for q in EP["quiz"]]; INTRO = EP.get("intro", INTRO); CUES = EP.get("cues", CUES); OUTRO = EP.get("outro", OUTRO)
SHOW = 3.0      # секунды на угадывание
REVEAL = 1.2    # показ ответа


def tts(text, path):
    async def go():
        await edge_tts.Communicate(text, VOICE, rate="+8%").save(str(path))
    asyncio.run(go())
    d = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)])
    return float(d.decode().strip())


def bg():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W/2)/(W/2))**2 + ((yy - H*0.42)/(H/2))**2)
    base = np.array([18, 22, 38], np.float32)[None, None, :] * (1.25 - 0.55*np.clip(r, 0, 1.3))[..., None]
    noise = np.random.default_rng(7).normal(0, 3.5, (H, W, 1))
    return Image.fromarray(np.clip(base + noise, 0, 255).astype(np.uint8))


BG = bg()


def flag_img(iso, width=760):
    im = Image.open(FLAGS / f"{iso}.png").convert("RGB")
    h = int(im.height * width / im.width); im = im.resize((width, h), Image.LANCZOS)
    mask = Image.new("L", im.size, 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, width-1, h-1), 28, fill=255)
    return im, mask


def frame(idx, t_in_q, phase, done):
    """idx — номер вопроса (0..9) или -1 интро / 10 аутро; phase 'show'|'reveal'; done — сколько отвечено."""
    im = BG.copy(); d = ImageDraw.Draw(im)
    d.text((W/2, 150), "FLAG IQ ARENA", font=F_MID, fill=(235, 235, 245), anchor="mm")
    y = 250; n = 0
    for lname, cnt, col in LEVELS:
        d.text((60, y), lname, font=F_LIST, fill=col); y += 46
        for k in range(cnt):
            label = f"{n+1}) " + (QUIZ[n][1] if n < done else "")
            d.text((60, y), label, font=F_LIST, fill=(240, 240, 240) if n < done else (120, 125, 145)); y += 44; n += 1
        y += 12
    if idx == -1:
        d.text((W/2, H*0.66), "10 FLAGS", font=F_BIG, fill=(255, 255, 255), anchor="mm")
        d.text((W/2, H*0.66+110), "3 seconds each", font=F_MID, fill=(255, 210, 90), anchor="mm")
        return im
    if idx == 10:
        d.text((W/2, H*0.66), "YOUR SCORE?", font=F_BIG, fill=(255, 255, 255), anchor="mm")
        d.text((W/2, H*0.66+110), "comment  /10", font=F_MID, fill=(255, 210, 90), anchor="mm")
        return im
    iso, name = QUIZ[idx]
    fl, mask = flag_img(iso)
    fx, fy = (W - fl.width)//2, int(H*0.66) - fl.height//2
    sh = Image.new("RGBA", (fl.width+80, fl.height+80), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((40, 50, fl.width+40, fl.height+50), 30, fill=(0, 0, 0, 150))
    shb = sh.filter(ImageFilter.GaussianBlur(18)); im.paste(shb, (fx-40, fy-40), shb)
    im.paste(fl, (fx, fy), mask)
    lvl = 0 if idx < 3 else 1 if idx < 6 else 2 if idx < 9 else 3
    d.text((W/2, fy - 90), f"#{idx+1}  ·  {LEVELS[lvl][0]}", font=F_MID, fill=LEVELS[lvl][2], anchor="mm")
    if phase == "show":
        cx, cy, R = W/2, fy + fl.height + 150, 70
        d.ellipse((cx-R, cy-R, cx+R, cy+R), outline=(70, 75, 95), width=10)
        ang = 360 * (1 - t_in_q / SHOW)
        d.arc((cx-R, cy-R, cx+R, cy+R), -90, -90 + ang, fill=(255, 210, 90), width=10)
        d.text((cx, cy), str(max(1, math.ceil(SHOW - t_in_q))), font=F_BIG, fill=(255, 255, 255), anchor="mm")
    else:
        d.text((W/2, fy + fl.height + 150), name.upper(), font=F_BIG, fill=(110, 230, 140), anchor="mm")
    return im


def main():
    clips = [("intro", INTRO)] + [(f"q{i}", c) for i, c in enumerate(CUES)] + [("outro", OUTRO)]
    durs = {k: tts(txt, WORK / f"{k}.mp3") for k, txt in clips}
    frames_dir = WORK / "frames"; frames_dir.mkdir(exist_ok=True)
    for f in frames_dir.glob("*.png"): f.unlink()
    timeline = []; t = 0.0; n = 0
    def emit(img, dur):
        nonlocal n
        for _ in range(int(round(dur * FPS))):
            img.save(frames_dir / f"f{n:05d}.png"); n += 1
    intro_d = max(durs["intro"] + 0.3, 2.2); timeline.append((t, "intro")); emit(frame(-1, 0, "", 0), intro_d); t += intro_d
    for i in range(10):
        timeline.append((t, f"q{i}"))
        for k in range(int(SHOW * FPS)):
            frame(i, k / FPS, "show", i).save(frames_dir / f"f{n:05d}.png"); n += 1
        t += SHOW
        emit(frame(i, 0, "reveal", i + 1), REVEAL); t += REVEAL
    timeline.append((t, "outro")); outro_d = max(durs["outro"] + 0.5, 2.5); emit(frame(10, 0, "", 10), outro_d); t += outro_d
    total = t
    print(f"кадров {n}, длительность {total:.1f} с")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", str(frames_dir / "f%05d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(WORK / "video.mp4")], check=True)
    inputs = []; filt = []; mix = []
    for j, (st, key) in enumerate(timeline):
        inputs += ["-i", str(WORK / f"{key}.mp3")]
        filt.append(f"[{j+1}:a]adelay={int(st*1000)}|{int(st*1000)}[v{j}]"); mix.append(f"[v{j}]")
    m = len(timeline); inputs += ["-i", str(MUSIC)]
    filt.append(f"[{m+1}:a]atrim=0:{total},volume=0.10,afade=t=out:st={total-1.5}:d=1.5[mus]")
    filt.append("".join(mix) + f"[mus]amix=inputs={m+1}:normalize=0,alimiter=limit=0.9[a]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(WORK / "video.mp4")] + inputs +
                   ["-filter_complex", ";".join(filt), "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                    "-shortest", str(OUT)], check=True)
    json.dump({"quiz": QUIZ, "timeline": timeline, "total": total}, open(WORK / "decision.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("готово:", OUT, OUT.stat().st_size, "байт")


if __name__ == "__main__":
    main()

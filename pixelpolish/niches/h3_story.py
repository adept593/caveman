# -*- coding: utf-8 -*-
"""Ролик из AI-ВИДЕО клипов MiniMax H3 (реальная анимация) — животные, библия.
Каждый shot -> клип H3 (4 с, 480x864, свой звук-атмосфера) -> апскейл до 1080x1920 -> плашки как у stills_story
(имя, метка, факт, шкала времени) -> голос edge-tts поверх, атмосфера H3 тихо, музыка тихо.

  python h3_story.py <scenario.json> [sec=4]      -> D:\PixelPolish\ШОРТСЫ\h3_<key>.mp4
Клипы кэшируются в D:\PixelPolish\video\projects\h3_<key>\clip<i>.mp4 (перегенерация — удалить файл).
"""
import json, subprocess, sys, io, textwrap
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).parent))
import h3_t2v, stills_story as ss
sys.stdout.reconfigure(encoding="utf-8")
W, H, FPS = ss.W, ss.H, 24
STYLE = " Photoreal wildlife documentary footage, natural movement, cinematic lighting, vertical 9:16, no text, no watermark."


def probe(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]).decode())


def frames_of(c, tmp):
    tmp.mkdir(exist_ok=True)
    for f in tmp.glob("*.png"): f.unlink()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(c), "-vf", f"fps={FPS},scale={W}:{H}:flags=lanczos", str(tmp / "%05d.png")], check=True)
    return sorted(tmp.glob("*.png"))


def main(path, sec=4.0):
    S = json.loads(Path(path).read_text(encoding="utf-8"))
    WORK = Path(rf"D:\PixelPolish\video\projects\h3_{S['key']}"); WORK.mkdir(parents=True, exist_ok=True)
    OUT = Path(rf"D:\PixelPolish\ШОРТСЫ\h3_{S['key']}.mp4"); voice = S.get("voice", "en-US-AndrewNeural")
    clips = []
    for i, sh in enumerate(S["shots"]):
        c = WORK / f"clip{i}.mp4"
        if not c.exists():
            print(f"H3 клип {i}: {sh['name']}", flush=True)
            h3_t2v.run(sh.get("video_prompt", sh["prompt"]) + STYLE, str(c), sec, S.get("seed", 11) + i)
        clips.append(c)
    lines = [S["intro"]] + [sh.get("line_voice", sh["line"]) for sh in S["shots"]] + [S["outro"]]
    durs = [ss.tts(t, WORK / f"v{i}.mp3", voice) for i, t in enumerate(lines)]
    cdur = [probe(c) for c in clips]
    INTRO = 1.6; OUTRO = max(durs[-1] + 0.4, 2.4)
    starts = [0.0]; t = INTRO
    for d in cdur: starts.append(t); t += d
    starts.append(t); total = t + OUTRO
    fdir = WORK / "frames"; fdir.mkdir(exist_ok=True)
    for f in fdir.glob("*.png"): f.unlink()
    n = 0; tmp = WORK / "tmpf"
    first = frames_of(clips[0], tmp); first_imgs = [Image.open(p).convert("RGB") for p in first]
    for k in range(int(INTRO * FPS)):
        fr = first_imgs[min(k, len(first_imgs)-1)].copy(); d = ImageDraw.Draw(fr, "RGBA")
        d.rectangle((0, 0, W, H), fill=(0, 0, 0, 120))
        d.text((W/2, H*0.45), S["title"].upper(), font=ss.F_BIG, fill=(255, 255, 255), anchor="mm")
        d.text((W/2, H*0.45+100), S.get("subtitle", ""), font=ss.F_MID, fill=(255, 210, 90), anchor="mm")
        fr.save(fdir / f"f{n:05d}.png"); n += 1
    last = None
    for i, c in enumerate(clips):
        imgs = first_imgs if i == 0 else [Image.open(p).convert("RGB") for p in frames_of(c, tmp)]
        for j, im in enumerate(imgs):
            fr = ss.overlay(im.copy(), S, S["shots"][i], i)
            e = min(1.0, j / (0.3*FPS), (len(imgs)-1-j) / (0.3*FPS))
            if e < 1.0: fr = Image.fromarray((np.asarray(fr, np.float32) * (0.4 + 0.6*e)).astype(np.uint8))
            fr.save(fdir / f"f{n:05d}.png"); n += 1; last = fr
    for k in range(int(OUTRO * FPS)):
        fr = last.copy(); d = ImageDraw.Draw(fr, "RGBA"); d.rectangle((0, H-330, W, H), fill=(8, 10, 18, 225))
        for li, ln in enumerate(textwrap.wrap(S["outro"], 38)[:3]):
            d.text((W/2, H-240 + li*62), ln, font=ss.F_MID, fill=(255, 255, 255), anchor="mm")
        fr.save(fdir / f"f{n:05d}.png"); n += 1
    print(f"кадров {n}, {total:.1f} с")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", str(fdir / "f%05d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(WORK / "video.mp4")], check=True)
    inputs = []; filt = []; mix = []; idx = 1
    for j, st in enumerate(starts):
        inputs += ["-i", str(WORK / f"v{j}.mp3")]; filt.append(f"[{idx}:a]adelay={int(st*1000)}|{int(st*1000)}[v{j}]"); mix.append(f"[v{j}]"); idx += 1
    for i, c in enumerate(clips):
        inputs += ["-i", str(c)]; filt.append(f"[{idx}:a]volume=0.35,adelay={int(starts[i+1]*1000)}|{int(starts[i+1]*1000)}[amb{i}]"); mix.append(f"[amb{i}]"); idx += 1
    inputs += ["-i", S["music"]]
    filt.append(f"[{idx}:a]atrim=0:{total},volume={S.get('music_vol', 0.10)},afade=t=out:st={total-1.5}:d=1.5[mus]"); mix.append("[mus]")
    filt.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0,alimiter=limit=0.9[a]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(WORK / "video.mp4")] + inputs + ["-filter_complex", ";".join(filt), "-map", "0:v", "-map", "[a]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", str(OUT)], check=True)
    json.dump({"scenario": S, "total": total, "clip_durs": cdur}, open(WORK / "decision.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("готово:", OUT, OUT.stat().st_size, "байт")


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 4.0)

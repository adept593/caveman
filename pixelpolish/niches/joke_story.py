# -*- coding: utf-8 -*-
"""Пластилиновый анекдот по схеме эталона: рассказчик за кадром, новый план каждые ~2 с, караоке-титры по словам.
Сцена = реплика рассказчика + промпт кадра. Стилл Flux (глянцевый клеймейшн) -> движение Wan i2v (короткий клип по длине реплики)
-> ESRGAN + 30 к/с -> титры по таймингам слов edge-tts -> музыка с даккингом.

  python joke_story.py <scen.json> [--kb]     --kb: без Wan, только Ken Burns (быстрый черновик)
"""
import asyncio, json, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import edge_tts
sys.path.insert(0, str(Path(__file__).parent))
import stills_story as ss, wan_i2v, h3_story
sys.stdout.reconfigure(encoding="utf-8")
W, H, FPS = 1080, 1920, 30
F_CAP = ImageFont.truetype(r"C:\Windows\Fonts\impact.ttf", 78)
CLAY = (", glossy stop-motion claymation style, handmade plasticine characters with big expressive eyes and subtle fingerprints, detailed miniature set, "
        "cinematic volumetric lighting, shallow depth of field, tilt-shift, vertical 9:16, no text")


async def tts_words(text, voice, path):
    words = []; com = edge_tts.Communicate(text, voice, rate="+3%")
    with open(path, "wb") as f:
        async for ch in com.stream():
            if ch["type"] == "audio": f.write(ch["data"])
            elif ch["type"] == "WordBoundary": words.append((ch["offset"] / 1e7, (ch["offset"] + ch["duration"]) / 1e7, ch["text"]))
    return words


def dur(p): return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]).decode())


def main(path, kb=False):
    S = json.loads(Path(path).read_text(encoding="utf-8"))
    WORK = Path(rf"D:\PixelPolish\video\projects\joke_{S['key']}"); WORK.mkdir(parents=True, exist_ok=True)
    OUT = Path(rf"D:\PixelPolish\ШОРТСЫ\joke_{S['key']}.mp4"); voice = S["voice"]
    segs = []
    for i, sh in enumerate(S["shots"]):
        a = WORK / f"v{i}.mp3"; words = asyncio.run(tts_words(sh["text"], voice, a)); segs.append((a, dur(a), words))
    clips = []
    for i, sh in enumerate(S["shots"]):
        still = ss.gen(sh["prompt"] + S.get("style", CLAY), S.get("seed", 1) + i, WORK / f"shot{i}.png")
        c = WORK / f"clip{i}.mp4"; L = segs[i][1] + 0.4
        if not c.exists():
            if kb:
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", str(still), "-t", f"{L:.2f}", "-vf",
                                f"scale=1188:2112,zoompan=z='1+0.08*on/{int(L*30)}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(c)], check=True)
            else:
                wan_i2v.run(str(still), sh.get("motion", "subtle stop-motion movement, characters gesture and react, camera slowly pushes in") + ". Claymation, handmade look.",
                            str(c), min(max(L, 2.0), 5.0), S.get("seed", 1) + i, size="720x1280", turbo=True)
        clips.append(c if kb else h3_story.postprocess(c))
    fdir = WORK / "frames"; fdir.mkdir(exist_ok=True)
    for f in fdir.glob("*.png"): f.unlink()
    n = 0; starts = []; t = 0.0; tmp = WORK / "tmpf"
    for i, c in enumerate(clips):
        starts.append(t); need = int(round((segs[i][1] + 0.4) * FPS))
        imgs = [Image.open(p).convert("RGB") for p in h3_story.frames_of(c, tmp)]
        while len(imgs) < need: imgs.append(imgs[-1])
        for j in range(need):
            fr = imgs[j].copy(); tt = j / FPS
            cur = [w for (a, b, w) in segs[i][2] if a <= tt < b + 0.05]
            if cur:
                d = ImageDraw.Draw(fr); word = cur[0].upper(); x, y = W / 2, H * 0.80
                for dx, dy in ((3, 3), (-3, 3), (3, -3), (-3, -3)): d.text((x+dx, y+dy), word, font=F_CAP, fill=(10, 20, 60), anchor="mm")
                d.text((x, y), word, font=F_CAP, fill=(70, 160, 255), anchor="mm")
            e = min(1.0, j / (0.15*FPS), (need-1-j) / (0.15*FPS))
            if e < 1.0: fr = Image.fromarray((np.asarray(fr, np.float32) * (0.5 + 0.5*e)).astype(np.uint8))
            fr.save(fdir / f"f{n:05d}.png"); n += 1
        t += need / FPS
    total = t
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", str(fdir / "f%05d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "17", str(WORK / "video.mp4")], check=True)
    inputs = []; filt = []; mix = []; idx = 1
    for i, (a, d_, _) in enumerate(segs):
        inputs += ["-i", str(a)]; filt.append(f"[{idx}:a]adelay={int(starts[i]*1000)}|{int(starts[i]*1000)}[v{i}]"); mix.append(f"[v{i}]"); idx += 1
    inputs += ["-i", S["music"]]
    filt.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0[voice]")
    filt.append(f"[{idx}:a]aloop=loop=-1:size=2e9,atrim=0:{total},volume={S.get('music_vol', 0.18)},afade=t=out:st={total-1.2}:d=1.2[mus]")
    filt.append("[voice]asplit=2[v1][v2]"); filt.append("[mus][v2]sidechaincompress=threshold=0.03:ratio=6:attack=40:release=500[musd]")
    filt.append("[v1][musd]amix=inputs=2:normalize=0,alimiter=limit=0.9[a]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(WORK / "video.mp4")] + inputs + ["-filter_complex", ";".join(filt), "-map", "0:v", "-map", "[a]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", str(OUT)], check=True)
    print(f"готово: {OUT} {OUT.stat().st_size} байт, {total:.1f} с, сцен {len(clips)}")


if __name__ == "__main__":
    main(sys.argv[1], "--kb" in sys.argv)

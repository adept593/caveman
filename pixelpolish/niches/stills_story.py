# -*- coding: utf-8 -*-
"""Ролик из AI-стиллов с движением камеры (Ken Burns) — для ниш «животные/эволюция» и «библейские истории».
Картинки — Flux Kontext dev txt2img (ComfyUI, свои промпты), голос edge-tts, музыка своя.
Кадр: картинка на весь экран с медленным наездом, снизу плашка: имя, метка (эпоха/стих), факт-строка;
у эволюции — шкала времени сверху.

  python stills_story.py <scenario.json>       -> D:\PixelPolish\ШОРТСЫ\story_<key>.mp4
Сценарий: {key, title, voice, music, timeline: bool, shots:[{prompt, name, label, line, pos(0..1)}], intro, outro}
"""
import asyncio, json, subprocess, sys, io, time, shutil, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import edge_tts
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
API = "http://127.0.0.1:8188"; COMFY_OUT = Path(r"C:\Users\RobotComp\pixelpolish\ComfyUI\output")
W, H, FPS = 1080, 1920, 30
GW, GH = 768, 1360           # генерация 9:16 (кратно 16)
F_BIG = ImageFont.truetype(r"C:\Windows\Fonts\impact.ttf", 84)
F_MID = ImageFont.truetype(r"C:\Windows\Fonts\bahnschrift.ttf", 46)
F_SMALL = ImageFont.truetype(r"C:\Windows\Fonts\bahnschrift.ttf", 38)
STYLE = ", ultra-detailed photoreal, natural light, shallow depth of field, cinematic 35mm, vertical composition, no text, no watermark"


def graph(text, seed):
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux1-dev-kontext_fp8_scaled.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": "clip_l.safetensors", "clip_name2": "t5xxl_fp8_e4m3fn.safetensors", "type": "flux"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "6": {"class_type": "EmptyLatentImage", "inputs": {"width": GW, "height": GH, "batch_size": 1}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": text + STYLE, "clip": ["2", 0]}},
        "9": {"class_type": "FluxGuidance", "inputs": {"conditioning": ["7", 0], "guidance": 3.5}},
        "10": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["7", 0]}},
        "11": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["9", 0], "negative": ["10", 0], "latent_image": ["6", 0],
               "seed": seed, "steps": 24, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "12": {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["3", 0]}},
        "13": {"class_type": "SaveImage", "inputs": {"images": ["12", 0], "filename_prefix": "niche/still"}},
    }


def gen(text, seed, dest):
    if dest.exists(): return dest
    body = json.dumps({"prompt": graph(text, seed)}).encode()
    pid = json.loads(urllib.request.urlopen(urllib.request.Request(f"{API}/prompt", body, {"Content-Type": "application/json"}), timeout=120).read())["prompt_id"]
    t0 = time.time()
    while True:
        time.sleep(3)
        h = json.loads(urllib.request.urlopen(f"{API}/history/{pid}", timeout=60).read())
        if pid in h:
            if h[pid]["status"].get("status_str") == "error": raise SystemExit(json.dumps(h[pid]["status"])[:1200])
            im = h[pid]["outputs"]["13"]["images"][0]
            shutil.copy(COMFY_OUT / im.get("subfolder", "") / im["filename"], dest); print(f"  {dest.name} {time.time()-t0:.0f} с"); return dest
        if time.time() - t0 > 900: raise SystemExit("таймаут генерации")


def tts(text, path, voice):
    async def go(): await edge_tts.Communicate(text, voice, rate="+2%").save(str(path))
    asyncio.run(go())
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)]).decode())


def overlay(img, S, shot, k):
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle((0, H-330, W, H), fill=(8, 10, 18, 205))
    d.text((W/2, H-250), shot["name"].upper(), font=F_BIG, fill=(255, 255, 255), anchor="mm")
    d.text((W/2, H-165), shot["label"], font=F_MID, fill=(255, 210, 90), anchor="mm")
    d.text((W/2, H-95), shot["line"], font=F_SMALL, fill=(225, 228, 238), anchor="mm")
    if S.get("timeline"):
        d.rectangle((0, 0, W, 190), fill=(8, 10, 18, 180))
        d.text((W/2, 60), S["title"].upper(), font=F_MID, fill=(255, 255, 255), anchor="mm")
        x0, x1, y = 90, W-90, 140
        d.line((x0, y, x1, y), fill=(120, 125, 145), width=6)
        px = x0 + (x1-x0) * shot.get("pos", k / max(1, len(S["shots"])-1))
        d.line((x0, y, px, y), fill=(255, 210, 90), width=6)
        d.ellipse((px-14, y-14, px+14, y+14), fill=(255, 210, 90))
        d.text((x0, y+28), S.get("t0", ""), font=F_SMALL, fill=(180, 185, 200), anchor="lm")
        d.text((x1, y+28), S.get("t1", "TODAY"), font=F_SMALL, fill=(180, 185, 200), anchor="rm")
    return img


def main(path):
    S = json.loads(Path(path).read_text(encoding="utf-8"))
    WORK = Path(rf"D:\PixelPolish\video\projects\story_{S['key']}"); WORK.mkdir(parents=True, exist_ok=True)
    OUT = Path(rf"D:\PixelPolish\ШОРТСЫ\story_{S['key']}.mp4")
    voice = S.get("voice", "en-US-AndrewNeural")
    print("генерация стиллов:")
    stills = [gen(sh["prompt"], S.get("seed", 11) + i, WORK / f"shot{i}.png") for i, sh in enumerate(S["shots"])]
    lines = [S["intro"]] + [sh.get("line_voice", sh["line"]) for sh in S["shots"]] + [S["outro"]]
    durs = [tts(t, WORK / f"v{i}.mp3", voice) for i, t in enumerate(lines)]
    SHOT = max(3.2, max(durs[1:-1]) + 0.5); INTRO = max(durs[0] + 0.3, 2.2); OUTRO = max(durs[-1] + 0.5, 2.5)
    total = INTRO + SHOT*len(stills) + OUTRO
    imgs = [Image.open(p).convert("RGB").resize((int(W*1.2), int(H*1.2)), Image.LANCZOS) for p in stills]
    fdir = WORK / "frames"; fdir.mkdir(exist_ok=True)
    for f in fdir.glob("*.png"): f.unlink()
    nfr = int(total * FPS)
    for i in range(nfr):
        t = i / FPS
        if t < INTRO: k, u = 0, 0.0
        elif t >= INTRO + SHOT*len(stills): k, u = len(stills)-1, 1.0
        else: k = int((t - INTRO) // SHOT); u = ((t - INTRO) - k*SHOT) / SHOT
        im = imgs[k]; z = 1.0 + 0.12*u if k % 2 == 0 else 1.12 - 0.12*u
        cw, ch = int(im.width / z), int(im.height / z); cx, cy = im.width/2, im.height/2
        fr = im.crop((int(cx-cw/2), int(cy-ch/2), int(cx+cw/2), int(cy+ch/2))).resize((W, H), Image.BILINEAR)
        if t < INTRO:
            d = ImageDraw.Draw(fr, "RGBA"); d.rectangle((0, 0, W, H), fill=(0, 0, 0, 120))
            d.text((W/2, H*0.45), S["title"].upper(), font=F_BIG, fill=(255, 255, 255), anchor="mm")
            d.text((W/2, H*0.45+100), S.get("subtitle", ""), font=F_MID, fill=(255, 210, 90), anchor="mm")
        elif t >= total - OUTRO:
            d = ImageDraw.Draw(fr, "RGBA"); d.rectangle((0, H-330, W, H), fill=(8, 10, 18, 205))
            d.text((W/2, H-200), S["outro"], font=F_MID, fill=(255, 255, 255), anchor="mm")
        else:
            fr = overlay(fr, S, S["shots"][k], k)
        edge = min(1.0, (u*SHOT)/0.35, ((1-u)*SHOT)/0.35) if INTRO <= t < INTRO + SHOT*len(stills) else 1.0
        if edge < 1.0: fr = Image.fromarray((np.asarray(fr, np.float32) * (0.35 + 0.65*edge)).astype(np.uint8))
        fr.save(fdir / f"f{i:05d}.png")
    print(f"кадров {nfr}, {total:.1f} с")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", str(fdir / "f%05d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(WORK / "video.mp4")], check=True)
    starts = [0.0] + [INTRO + SHOT*i for i in range(len(stills))] + [total - OUTRO]
    inputs = []; filt = []; mix = []
    for j, st in enumerate(starts):
        inputs += ["-i", str(WORK / f"v{j}.mp3")]; filt.append(f"[{j+1}:a]adelay={int(st*1000)}|{int(st*1000)}[v{j}]"); mix.append(f"[v{j}]")
    m = len(starts); inputs += ["-i", S["music"]]
    filt.append(f"[{m+1}:a]atrim=0:{total},volume={S.get('music_vol', 0.14)},afade=t=out:st={total-1.5}:d=1.5[mus]")
    filt.append("".join(mix) + f"[mus]amix=inputs={m+1}:normalize=0,alimiter=limit=0.9[a]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(WORK / "video.mp4")] + inputs + ["-filter_complex", ";".join(filt), "-map", "0:v", "-map", "[a]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", str(OUT)], check=True)
    json.dump({"scenario": S, "total": total, "shot": SHOT}, open(WORK / "decision.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("готово:", OUT, OUT.stat().st_size, "байт")


if __name__ == "__main__":
    main(sys.argv[1])

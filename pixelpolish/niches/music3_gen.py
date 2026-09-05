# -*- coding: utf-8 -*-
"""Музыка каналов — MiniMax Music 3 локально через ComfyUI (инструментал, без текста).
Граф — по шаблону audio_minimax_music_3: UNETLoader (dit int8) -> CLIPLoader(minimax, text encoder pruned int8)
-> MiniMaxMusic3TextEncode(caption, lyrics="", max_duration) -> EmptyMiniMaxMusic3LatentAudio -> KSampler -> VAEDecodeAudio -> SaveAudio.

  python music3_gen.py <key> "<caption>" [sec=60] [seed=1]     -> D:/PixelPolish/МУЗЫКА/m3_<key>.mp3
  python music3_gen.py all                                     все 4 трека каналов (TRACKS)
"""
import json, sys, time, shutil, urllib.request
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
import os
API = os.environ.get("COMFY_API", "http://127.0.0.1:8189")                       # лаунчер ComfyUI Desktop
OUTDIR = Path(os.environ.get("COMFY_OUTPUT", r"C:\Users\RobotComp\AppData\Local\Comfy-Desktop\ComfyUI-Shared\output"))
MUSIC = Path(r"D:\PixelPolish\МУЗЫКА")

# стиль — по замерам конкурентов (темп/громкость/ударные/тембр), см. НИШИ_ПИЛОТЫ
TRACKS = {
 "maps":    ("Global Metadata: Epic cinematic trailer, instrumental. 120 BPM, D minor. Deep brass, low strings, taiko drums, "
             "dark and grand, constant driving energy, no quiet breaks, no vocals, loopable.", 11),
 "flags":   ("Global Metadata: Upbeat quiz show beat, purely instrumental, no singing, no voice, no vocals. 122 BPM, C major. "
             "Punchy electronic drums, clicks and snaps, bright synth plucks, playful ticking-clock tension, light and fun, loopable.", 27),
 "bible":   ("Global Metadata: Sacred cinematic, instrumental. 95 BPM, A minor. Warm wordless choir pads, soft strings, "
             "gentle solemn drums, reverent and hopeful, slow swell, no lyrics.", 33),
 "animals": ("Global Metadata: Nature documentary ambient, instrumental. 100 BPM, F major. Soft evolving pads, distant piano notes, "
             "subtle low drone, mysterious and awe-inspiring like deep time and ancient oceans, almost no drums, no vocals.", 44),
}


def graph(caption, sec, seed):
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "minimax_music3_dit_fp16.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "minimax_music3_text_encoder_pruned_int8_convrot.safetensors", "type": "minimax", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_music3_dav.safetensors"}},
        "4": {"class_type": "MiniMaxMusic3TextEncode", "inputs": {"clip": ["2", 0], "caption": caption, "lyrics": "[Instrumental]\n[Instrumental]\n[Instrumental]\n[Outro]\n[Instrumental]", "seed": seed,
              "max_duration": float(sec), "cfg_scale": 1.5, "top_k": 50}},
        "5": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["4", 0]}},
        "6": {"class_type": "EmptyMiniMaxMusic3LatentAudio", "inputs": {"seconds": float(sec), "batch_size": 1}},   # длина жёстко, не по решению модели
        "7": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["6", 0],
              "seed": seed, "steps": 30, "cfg": 1.7, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "8": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
        "9": {"class_type": "SaveAudio", "inputs": {"audio": ["8", 0], "filename_prefix": "audio/m3"}},
    }


def run(key, caption, sec=60, seed=1):
    body = json.dumps({"prompt": graph(caption, sec, seed)}).encode()
    resp = json.loads(urllib.request.urlopen(urllib.request.Request(f"{API}/prompt", body, {"Content-Type": "application/json"}), timeout=60).read())
    if "prompt_id" not in resp: raise SystemExit("отказ /prompt: " + json.dumps(resp, ensure_ascii=False)[:1500])
    pid = resp["prompt_id"]; t0 = time.time()
    while True:
        time.sleep(4)
        h = json.loads(urllib.request.urlopen(f"{API}/history/{pid}", timeout=30).read())
        if pid in h:
            if h[pid]["status"].get("status_str") == "error":
                raise SystemExit("ComfyUI error: " + json.dumps([m for m in h[pid]["status"]["messages"] if m[0] == "execution_error"], ensure_ascii=False)[:1500])
            files = [f for o in h[pid]["outputs"].values() for f in o.get("audio", [])]
            src = OUTDIR / files[-1].get("subfolder", "") / files[-1]["filename"]
            dst = MUSIC / f"m3_{key}{src.suffix}"; shutil.copy(src, dst)
            print(f"готово {time.time()-t0:.0f} с: {dst} ({dst.stat().st_size} байт)"); return dst
        if time.time() - t0 > 3600: raise SystemExit("таймаут")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "all":
        for k, (cap, seed) in TRACKS.items(): run(k, cap, 60, seed)
    else:
        run(a[0], a[1], float(a[2]) if len(a) > 2 else 60, int(a[3]) if len(a) > 3 else 1)

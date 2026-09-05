# -*- coding: utf-8 -*-
"""MiniMax H3 text-to-video (видео + звук) через ComfyUI /prompt. Граф — по шаблону video_minimax_h3_t2v
(подграф: UNET -> H3ImageToVideo(cond, latent) -> SamplerCustomAdvanced -> VAEDecode / VAEDecodeAudio -> CreateVideo).
Локальные веса: GGUF Q4 турбо (LoRA не нужна), qwen3vl_4b_fp8.

  python h3_t2v.py "<prompt>" <out.mp4> [sec=4] [seed=1] [WxH=480x864]
"""
import json, sys, io, time, shutil, urllib.request
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
API = "http://127.0.0.1:8188"; OUTDIR = Path(r"C:\Users\RobotComp\pixelpolish\ComfyUI\output")


def graph(prompt, width, height, length, seed, steps=6):
    return {
        "1": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": "minimax_h3_fl2va_turbo_Q4_K_M.gguf"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl_4b_fp8_scaled.safetensors", "type": "minimax", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_video_vae_fp16.safetensors"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_audio_vae_fp32.safetensors"}},
        "5": {"class_type": "MiniMaxH3ImageToVideo", "inputs": {"clip": ["2", 0], "vae": ["3", 0], "prompt": prompt,
              "width": width, "height": height, "length": length}},
        "6": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "7": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}},
        "8": {"class_type": "BasicScheduler", "inputs": {"model": ["1", 0], "scheduler": "simple", "steps": steps, "denoise": 1.0}},
        "9": {"class_type": "BasicGuider", "inputs": {"model": ["1", 0], "conditioning": ["5", 0]}},
        "10": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["6", 0], "guider": ["9", 0], "sampler": ["7", 0],
               "sigmas": ["8", 0], "latent_image": ["5", 1]}},
        "11": {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["3", 0]}},
        "12": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["10", 0], "vae": ["4", 0]}},
        "13": {"class_type": "CreateVideo", "inputs": {"images": ["11", 0], "fps": 24, "audio": ["12", 0]}},
        "14": {"class_type": "SaveVideo", "inputs": {"video": ["13", 0], "filename_prefix": "video/h3_niche", "format": "auto", "codec": "auto"}},
    }


def run(prompt, out, sec=4.0, seed=1, size="480x864", steps=6):
    w, h = map(int, size.split("x"))
    length = 4 * round((round(sec * 24) - 1) / 4) + 1                  # латент видео: 4k+1 кадров
    body = json.dumps({"prompt": graph(prompt, w, h, length, seed, steps), "client_id": "h3niche"}).encode()
    r = urllib.request.urlopen(urllib.request.Request(f"{API}/prompt", body, {"Content-Type": "application/json"}), timeout=60)
    resp = json.loads(r.read())
    if "prompt_id" not in resp: raise SystemExit("отказ /prompt: " + json.dumps(resp, ensure_ascii=False)[:1500])
    pid = resp["prompt_id"]; t0 = time.time()
    while True:
        time.sleep(3)
        hist = json.loads(urllib.request.urlopen(f"{API}/history/{pid}", timeout=30).read())
        if pid in hist:
            h_ = hist[pid]
            if h_.get("status", {}).get("status_str") == "error":
                msgs = [m for m in h_["status"].get("messages", []) if m[0] == "execution_error"]
                raise SystemExit("ComfyUI error: " + json.dumps(msgs, ensure_ascii=False)[:1500])
            files = [f for o in h_["outputs"].values() for k in ("videos", "images", "gifs") for f in o.get(k, [])]
            if not files: raise SystemExit("нет выходных файлов: " + json.dumps(h_["outputs"])[:500])
            f = files[-1]; src = OUTDIR / f.get("subfolder", "") / f["filename"]
            Path(out).parent.mkdir(parents=True, exist_ok=True); shutil.copy(src, out)
            print(f"готово {time.time()-t0:.0f} с: {out} ({Path(out).stat().st_size} байт), length {length}, {w}x{h}, seed {seed}")
            return out
        if time.time() - t0 > 1800: raise SystemExit("таймаут")


if __name__ == "__main__":
    a = sys.argv[1:]
    run(a[0], a[1], float(a[2]) if len(a) > 2 else 4.0, int(a[3]) if len(a) > 3 else 1, a[4] if len(a) > 4 else "480x864")

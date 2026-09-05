# -*- coding: utf-8 -*-
"""Wan 2.2 T2V 14B (high+low noise, fp8, LoRA lightx2v 4 шага) через ComfyUI — картинка без звука.
Интерфейс тот же, что у h3_t2v.run: run(prompt, out, sec, seed, size, steps).
Граф: UNETLoader(high)+LoRA -> ModelSamplingSD3(shift 5) -> KSamplerAdvanced шаги 0..N/2 ->
      UNETLoader(low)+LoRA  -> ModelSamplingSD3(shift 5) -> KSamplerAdvanced шаги N/2..N -> VAEDecode -> CreateVideo(16 fps) -> SaveVideo.
Латент Wan: 16 fps, длина 4k+1 кадров (5 с = 81).

  python wan_t2v.py "<prompt>" <out.mp4> [sec=5] [seed=1] [WxH=720x1280] [steps=4]
"""
import json, sys, time, shutil, urllib.request
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
API = "http://127.0.0.1:8188"; OUTDIR = Path(r"C:\Users\RobotComp\pixelpolish\ComfyUI\output")
NEG = ("色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，JPEG压缩残留，丑陋的，残缺的，"
       "多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走, "
       "text, watermark, subtitles, logo, static image, still frame")


def graph(prompt, width, height, length, seed, steps=4, shift=5.0):
    half = max(1, steps // 2)
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors", "weight_dtype": "default"}},
        "3": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": "wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors", "strength_model": 1.0}},
        "4": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["2", 0], "lora_name": "wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors", "strength_model": 1.0}},
        "5": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["3", 0], "shift": shift}},
        "6": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["4", 0], "shift": shift}},
        "7": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"}},
        "8": {"class_type": "VAELoader", "inputs": {"vae_name": "wan_2.1_vae.safetensors"}},
        "9": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["7", 0]}},
        "10": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["7", 0]}},
        "11": {"class_type": "EmptyHunyuanLatentVideo", "inputs": {"width": width, "height": height, "length": length, "batch_size": 1}},
        "12": {"class_type": "KSamplerAdvanced", "inputs": {"model": ["5", 0], "add_noise": "enable", "noise_seed": seed, "steps": steps, "cfg": 1.0,
               "sampler_name": "euler", "scheduler": "simple", "positive": ["9", 0], "negative": ["10", 0], "latent_image": ["11", 0],
               "start_at_step": 0, "end_at_step": half, "return_with_leftover_noise": "enable"}},
        "13": {"class_type": "KSamplerAdvanced", "inputs": {"model": ["6", 0], "add_noise": "disable", "noise_seed": seed, "steps": steps, "cfg": 1.0,
               "sampler_name": "euler", "scheduler": "simple", "positive": ["9", 0], "negative": ["10", 0], "latent_image": ["12", 0],
               "start_at_step": half, "end_at_step": 10000, "return_with_leftover_noise": "disable"}},
        "14": {"class_type": "VAEDecode", "inputs": {"samples": ["13", 0], "vae": ["8", 0]}},
        "15": {"class_type": "CreateVideo", "inputs": {"images": ["14", 0], "fps": 16}},
        "16": {"class_type": "SaveVideo", "inputs": {"video": ["15", 0], "filename_prefix": "video/wan_niche", "format": "auto", "codec": "auto"}},
    }


def run(prompt, out, sec=5.0, seed=1, size="720x1280", steps=4):
    w, h = map(int, size.split("x"))
    length = 4 * round((round(sec * 16) - 1) / 4) + 1
    body = json.dumps({"prompt": graph(prompt, w, h, length, seed, steps), "client_id": "wanniche"}).encode()
    resp = json.loads(urllib.request.urlopen(urllib.request.Request(f"{API}/prompt", body, {"Content-Type": "application/json"}), timeout=60).read())
    if "prompt_id" not in resp: raise SystemExit("отказ /prompt: " + json.dumps(resp, ensure_ascii=False)[:1500])
    pid = resp["prompt_id"]; t0 = time.time()
    while True:
        time.sleep(4)
        h_ = json.loads(urllib.request.urlopen(f"{API}/history/{pid}", timeout=30).read())
        if pid in h_:
            st = h_[pid]
            if st.get("status", {}).get("status_str") == "error":
                raise SystemExit("ComfyUI error: " + json.dumps([m for m in st["status"].get("messages", []) if m[0] == "execution_error"], ensure_ascii=False)[:1500])
            files = [f for o in st["outputs"].values() for k in ("videos", "images", "gifs") for f in o.get(k, [])]
            f = files[-1]; src = OUTDIR / f.get("subfolder", "") / f["filename"]
            Path(out).parent.mkdir(parents=True, exist_ok=True); shutil.copy(src, out)
            print(f"готово {time.time()-t0:.0f} с: {out} ({Path(out).stat().st_size} байт), length {length}, {w}x{h}, seed {seed}, steps {steps}")
            return out
        if time.time() - t0 > 3600: raise SystemExit("таймаут")


if __name__ == "__main__":
    a = sys.argv[1:]
    run(a[0], a[1], float(a[2]) if len(a) > 2 else 5.0, int(a[3]) if len(a) > 3 else 1, a[4] if len(a) > 4 else "720x1280", int(a[5]) if len(a) > 5 else 4)

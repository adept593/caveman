# -*- coding: utf-8 -*-
"""Wan 2.2 I2V 14B (картинка -> видео) через ComfyUI лаунчера — граф шаблона video_wan2_2_14B_i2v.
turbo=True: LoRA lightx2v на обеих моделях, 4 шага, cfg 1, разрез 2 (~5 мин на 720x1280x5с).
turbo=False: 20 шагов, cfg 3.5, разрез 10 (~45 мин).

  python wan_i2v.py <image.png> "<prompt>" <out.mp4> [sec=5] [seed=1] [WxH=720x1280] [turbo=1]
"""
import json, os, sys, time, shutil, urllib.request
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
API = os.environ.get("COMFY_API", "http://127.0.0.1:8189")
SHARED = Path(r"C:\Users\RobotComp\AppData\Local\Comfy-Desktop\ComfyUI-Shared")
INPUT_DIR = Path(os.environ.get("COMFY_INPUT", SHARED / "input")); OUT_DIR = Path(os.environ.get("COMFY_OUTPUT", SHARED / "output"))
NEG = ("色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，JPEG压缩残留，丑陋的，残缺的，"
       "多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走")


def graph(image_name, prompt, width, height, length, seed, turbo=True):
    steps, cfg, split = (4, 1.0, 2) if turbo else (20, 3.5, 10)
    g = {
        "95": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors", "weight_dtype": "default"}},
        "96": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors", "weight_dtype": "default"}},
        "101": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["95", 0], "lora_name": "wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors", "strength_model": 1.0}},
        "102": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["96", 0], "lora_name": "wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors", "strength_model": 1.0}},
        "104": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["101" if turbo else "95", 0], "shift": 5.0}},
        "103": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["102" if turbo else "96", 0], "shift": 5.0}},
        "84": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"}},
        "90": {"class_type": "VAELoader", "inputs": {"vae_name": "wan_2.1_vae.safetensors"}},
        "97": {"class_type": "LoadImage", "inputs": {"image": image_name, "upload": "image"}},
        "93": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["84", 0]}},
        "89": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["84", 0]}},
        "98": {"class_type": "WanImageToVideo", "inputs": {"positive": ["93", 0], "negative": ["89", 0], "vae": ["90", 0], "start_image": ["97", 0],
               "width": width, "height": height, "length": length, "batch_size": 1}},
        "86": {"class_type": "KSamplerAdvanced", "inputs": {"model": ["104", 0], "add_noise": "enable", "noise_seed": seed, "steps": steps, "cfg": cfg,
               "sampler_name": "euler", "scheduler": "simple", "positive": ["98", 0], "negative": ["98", 1], "latent_image": ["98", 2],
               "start_at_step": 0, "end_at_step": split, "return_with_leftover_noise": "enable"}},
        "85": {"class_type": "KSamplerAdvanced", "inputs": {"model": ["103", 0], "add_noise": "disable", "noise_seed": 0, "steps": steps, "cfg": cfg,
               "sampler_name": "euler", "scheduler": "simple", "positive": ["98", 0], "negative": ["98", 1], "latent_image": ["86", 0],
               "start_at_step": split, "end_at_step": steps, "return_with_leftover_noise": "disable"}},
        "87": {"class_type": "VAEDecode", "inputs": {"samples": ["85", 0], "vae": ["90", 0]}},
        "94": {"class_type": "CreateVideo", "inputs": {"images": ["87", 0], "fps": 16}},
        "108": {"class_type": "SaveVideo", "inputs": {"video": ["94", 0], "filename_prefix": "video/wan_i2v_niche", "format": "auto", "codec": "auto"}},
    }
    if not turbo: g.pop("101"); g.pop("102")
    return g


def run(image, prompt, out, sec=5.0, seed=1, size="720x1280", turbo=True):
    w, h = map(int, size.split("x")); length = int(sec * 16) + 1
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    name = f"niche_{Path(image).stem}_{abs(hash(str(image))) % 100000}{Path(image).suffix}"; shutil.copy(image, INPUT_DIR / name)
    body = json.dumps({"prompt": graph(name, prompt, w, h, length, seed, turbo), "client_id": "wani2v"}).encode()
    resp = json.loads(urllib.request.urlopen(urllib.request.Request(f"{API}/prompt", body, {"Content-Type": "application/json"}), timeout=60).read())
    if "prompt_id" not in resp: raise SystemExit("отказ /prompt: " + json.dumps(resp, ensure_ascii=False)[:1500])
    pid = resp["prompt_id"]; t0 = time.time()
    while True:
        time.sleep(5)
        hst = json.loads(urllib.request.urlopen(f"{API}/history/{pid}", timeout=30).read())
        if pid in hst:
            st = hst[pid]
            if st.get("status", {}).get("status_str") == "error":
                raise SystemExit("ComfyUI error: " + json.dumps([m for m in st["status"].get("messages", []) if m[0] == "execution_error"], ensure_ascii=False)[:1500])
            files = [f for o in st["outputs"].values() for k in ("videos", "images", "gifs") for f in o.get(k, [])]
            f = files[-1]; src = OUT_DIR / f.get("subfolder", "") / f["filename"]
            Path(out).parent.mkdir(parents=True, exist_ok=True); shutil.copy(src, out)
            print(f"готово {time.time()-t0:.0f} с: {out} ({Path(out).stat().st_size} байт), {w}x{h}, {length} кадров, seed {seed}, turbo {turbo}")
            return out
        if time.time() - t0 > 5400: raise SystemExit("таймаут")


if __name__ == "__main__":
    a = sys.argv[1:]
    run(a[0], a[1], a[2], float(a[3]) if len(a) > 3 else 5.0, int(a[4]) if len(a) > 4 else 1, a[5] if len(a) > 5 else "720x1280", (a[6] != "0") if len(a) > 6 else True)

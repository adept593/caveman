# -*- coding: utf-8 -*-
"""Описание видео через Gemma 4 E4B (шаблон llm_gemma4_text_gen лаунчера): ролик -> кадры -> текст.
Нужно для разбора эталонов: объект, действие, движение камеры, свет, композиция -> свои промпты для Wan/H3.
Чужой материал в ролики не попадает — только описание приёма.

  python describe_video.py <video.mp4> [question]     -> D:\PixelPolish\assets\descr\<stem>.txt
  python describe_video.py --dir <folder>             все mp4 в папке
"""
import json, os, sys, time, shutil, urllib.request
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
API = os.environ.get("COMFY_API", "http://127.0.0.1:8189")
SHARED = Path(r"C:\Users\RobotComp\AppData\Local\Comfy-Desktop\ComfyUI-Shared"); INPUT_DIR = Path(os.environ.get("COMFY_INPUT", SHARED / "input"))
OUT = Path(r"D:\PixelPolish\assets\descr"); OUT.mkdir(parents=True, exist_ok=True)
Q = ("You are a film analyst for short vertical videos. Describe this clip for a video-generation prompt writer. "
     "Answer in English with these fields, one per line: SUBJECT (what/who, look, materials); ACTION (what moves, how fast); "
     "CAMERA (angle, movement, lens feel); LIGHT (time of day, color, direction); COMPOSITION (framing, foreground/background); "
     "STYLE (photoreal / cgi / painterly, film look); HOOK (what grabs attention in the first second); "
     "TEXT_ON_SCREEN (any captions, yes/no and what). Be concrete, no filler.")


def graph(video_name, question):
    return {
        "3": {"class_type": "CLIPLoader", "inputs": {"clip_name": "gemma4_e4b_it_fp8_scaled.safetensors", "type": "stable_diffusion", "device": "default"}},
        "6": {"class_type": "LoadVideo", "inputs": {"file": video_name}},
        "7": {"class_type": "GetVideoComponents", "inputs": {"video": ["6", 0]}},
        "1": {"class_type": "TextGenerate", "inputs": {"clip": ["3", 0], "prompt": question, "max_length": 700, "sampling_mode": "off",
              "video": ["7", 0], "thinking": False, "use_default_template": True}},
        "4": {"class_type": "PreviewAny", "inputs": {"source": ["1", 0]}},
    }


def describe(video, question=Q):
    video = Path(video); INPUT_DIR.mkdir(parents=True, exist_ok=True)
    name = f"descr_{video.stem}{video.suffix}"; shutil.copy(video, INPUT_DIR / name)
    body = json.dumps({"prompt": graph(name, question), "client_id": "descr"}).encode()
    resp = json.loads(urllib.request.urlopen(urllib.request.Request(f"{API}/prompt", body, {"Content-Type": "application/json"}), timeout=60).read())
    if "prompt_id" not in resp: raise SystemExit("отказ /prompt: " + json.dumps(resp, ensure_ascii=False)[:1500])
    pid = resp["prompt_id"]; t0 = time.time()
    while True:
        time.sleep(3)
        hst = json.loads(urllib.request.urlopen(f"{API}/history/{pid}", timeout=30).read())
        if pid in hst:
            st = hst[pid]
            if st.get("status", {}).get("status_str") == "error":
                raise SystemExit("ComfyUI error: " + json.dumps([m for m in st["status"].get("messages", []) if m[0] == "execution_error"], ensure_ascii=False)[:1500])
            ui = st["outputs"].get("4", {}); text = ""
            for k, v in ui.items():
                if isinstance(v, list) and v and isinstance(v[0], str): text = "\n".join(v)
            if not text: text = json.dumps(ui, ensure_ascii=False)
            out = OUT / f"{video.stem}.txt"; out.write_text(text, encoding="utf-8")
            print(f"{video.name}: {time.time()-t0:.0f} с -> {out}\n{text[:600]}\n"); return text
        if time.time() - t0 > 1800: raise SystemExit("таймаут")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "--dir":
        for v in sorted(Path(a[1]).glob("*.mp4")): describe(v)
    else:
        describe(a[0], a[1] if len(a) > 1 else Q)

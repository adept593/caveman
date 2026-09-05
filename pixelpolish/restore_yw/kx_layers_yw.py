# -*- coding: utf-8 -*-
"""Пять слоёв реставрации для пластины youngwoman1855 (ppmsca.51855, LOC 2017648628).

Копия kx_layers_v3.py с тремя правками под другую пластину:
  * MASTER, кроп рамки PLATE и сетка W x H — свои (мастер 3440x3880, кроп
    1843x2522, длинная сторона 1760 -> короткая 1285 -> 1280, кратно 16);
  * из промптов убрано всё про клетчатое платье, табурет и двух детей —
    это была twogirls1844. Здесь одна женщина, тёмное платье с прозрачной
    полосатой кокеткой и брошью, руки сложены, гладкий тёмный фон;
  * пластина hand-colored — цветовой слой описывает подкраску эпохи, а не
    выдуманные ткани.
Запуск (ComfyUI на 8188):
    python kx_layers_yw.py mono   -> L1_master, L2_clean, L3_tone, L4_detail
    python kx_layers_yw.py color  -> L5_color из L4_detail_raw
    python kx_layers_yw.py all    -> всё подряд
"""
import json, os, shutil, sys, time, urllib.request

API = "http://127.0.0.1:8188"
COMFY_IN = r"C:\Users\RobotComp\pixelpolish\ComfyUI\input"
COMFY_OUT = r"C:\Users\RobotComp\pixelpolish\ComfyUI\output"
OUT = r"D:\PixelPolish\plates\layers_yw"
MASTER = r"D:\PixelPolish\plates\masters\51855u.tif"
PLATE = (834, 660, 2677, 3182)      # внутри фигурного выреза латунной рамки
W, H, SEED = 1280, 1760, 101010
LOG = os.path.join(OUT, "runs.json")

HEAD = """[System Role]: Professional Archivist & Museum Photo-Restoration Engine.
[Input]: One damaged mid-19th-century daguerreotype plate, a half-length portrait of one young woman. It carries dense white speckle (oxidation bloom) over the whole surface, tarnish haloes, silver mirroring, dust and scratches. These defects MUST BE REMOVED, not reproduced: the output is the photograph as it looked when it was new.
[Task]: Execute non-destructive, high-fidelity digital restoration. Output one restored image and nothing else."""

B_CLEAN = """1. ARTIFACT CLEANING
   - Detect and remove completely: the white speckle everywhere, cracks, scratches, dust, silver mirroring, tarnish haloes, chemical stains, mould and edge decay.
   - Action: rebuild covered areas from the surrounding context of the same surface. Introduce no new objects, no jewellery beyond the small brooch already at her collar, no ornaments.
   - The finished image must look like an undamaged photograph: no stains, no blotches, no speckle, no mottling anywhere, including the dark background and the dark dress."""

B_ID = """2. IDENTITY AND COMPOSITION - HIGHEST PRIORITY
   - The woman must remain the same individual: eye spacing and shape, nose length and width, mouth width, lip fullness, jaw line, centre-parted hair drawn back over the ears, apparent age, direct gaze and calm expression.
   - Fine detail the degraded plate cannot resolve - pores, eyelashes, single hairs - must be SYNTHESIZED plausibly, not copied from the blur.
   - Do not beautify, slim, symmetrize, whiten or age-shift her. Do not alter ethnic features.
   - Composition LOCKED: same crop, same aspect ratio, one person, same pose, same headroom. Add nothing, remove nothing, move nothing.
   - Hair: smooth, parted in the centre and drawn tightly back behind the ears, close to the head. No volume, no curls, no ringlets, no visible bun.
   - Hands: her right hand rests over her left at the WAIST, just below the chest, exactly where they are in the input. Do NOT lower them into the lap. Five fingers per hand, no fused, extra or missing fingers."""

B_BG = """3. BACKGROUND AND CLOTHING
   - BACKGROUND: a plain, dark, evenly lit studio wall. Keep that background - its real dark tone, its real soft gradient, its real emptiness - and remove ALL the damage lying on it: speckle, tarnish, bloom, scratches, dust. Clean it until smooth and even again. Do NOT paint, invent or replace the backdrop. No curtains, drapery, tulle, lace, clouds, painted canvas or decorative texture of any kind.
   - CLOTHING: a dark dress with a sheer yoke of fine vertical stripes over the shoulders and ONE small brooch at the throat. The bodice below the yoke is PLAIN and UNBROKEN dark cloth: NO buttons, NO button row, NO ribbon, NO bow, NO second brooch, NO belt, NO trim. The sleeves are long, plain and dark. The frame ends at the waist and hands - do NOT invent a gathered skirt, pleats or folds below them. Keep the sheer striped yoke sheer and striped, its stripes straight and evenly spaced; where speckle has destroyed the stripes, continue them from the surviving part of the same yoke. Where the dark dress is hidden under speckle, it is still the same plain dark cloth underneath - restore plain cloth, not ornament."""

B_TONE = """4. DYNAMIC RANGE
   - Recover lost data from deep shadows and clipped highlights. Balance exposure and restore living contrast on a natural film gamma curve.
   - Do NOT sharpen. Do NOT synthesize new micro-texture at this stage. Tone only."""

B_SIGNAL = """4. SIGNAL PROCESSING AND RESOLUTION
   - Super-resolve local contrast and sharpness. Eliminate scan noise and chromatic aberration.
   - Recover lost data from deep shadows and clipped highlights on a natural film gamma curve.
   - Render as a large-format view-camera portrait: even soft frontal light, gentle falloff, no HDR, no glow halos, no clarity over-processing."""

B_TEX = """5. TEXTURE AND FORBIDDEN
   - REQUIRED: high-frequency surface detail - skin pores, the weave of the dark dress, the fine threads of the sheer striped yoke - and the surface micro-texture of a fine photographic print of the 1850s. NOT 35mm film grain. NOT digital noise.
   - FORBIDDEN: plastic or waxy skin, airbrushing, AI smoothing, over-sharpening halos, 3D render or illustration look, modern smartphone HDR, teeth or eye whitening, added make-up, catchlights that were not in the original."""

TAIL = ("[REMINDER] Identity and composition outrank everything else. If more detail and the "
        "same person ever conflict, choose the same person.\n"
        "[Output Format]: Return ONLY the final restored image. No text, no explanation.")
MONO = ("[Color] Keep the image monochrome - neutral to very slightly warm grey, like a clean "
        "silver print. Optimize the tonal range only. Do not colorize, no brown sepia wash.")
COLOR = ("[Color] COLORIZE THIS PHOTOGRAPH. The output must be a colour image, not a grey or "
         "sepia one. This plate was hand-tinted in its own time: give her natural pastel flesh "
         "tones with a soft pink blush on the cheeks and lips, dark brown hair, a dress in deep "
         "brown-black, the sheer yoke in a warm off-white with dark stripes, a small gold brooch, "
         "and a quiet dark grey-brown studio wall. Muted, chemically plausible 1850s palette. "
         "No neon, no oversaturation, no magenta cast, but the colour must be clearly visible.")

HEAD_COLOR = HEAD.replace(
    "[Task]: Execute non-destructive, high-fidelity digital restoration.",
    "[Task]: Execute non-destructive, high-fidelity digital restoration AND full colorization.")

FLAT = ("6. HOLD EVERYTHING ELSE: do NOT change exposure, do NOT raise contrast, do NOT sharpen, "
        "do NOT add micro-texture. The image must stay exactly as flat, soft and low-contrast as "
        "the input. Remove the speckle and damage, and nothing else.")
FLAT2 = ("6. HOLD SHARPNESS: do NOT sharpen and do NOT add micro-texture. "
         "The image must stay as soft as the input. Tone only.")

P_L2 = "\n".join([HEAD, B_CLEAN, B_ID, B_BG, FLAT, TAIL, MONO])
P_L3 = "\n".join([HEAD, B_CLEAN, B_ID, B_BG, B_TONE, FLAT2, TAIL, MONO])
P_L4 = "\n".join([HEAD, B_CLEAN, B_ID, B_BG, B_SIGNAL, B_TEX, TAIL, MONO])
P_L5 = "\n".join([HEAD_COLOR, B_CLEAN, B_ID, B_BG, B_SIGNAL, B_TEX, TAIL, COLOR])


def graph(text, prefix, img_name, w, h, seed=SEED):
    return {
        "1": {"class_type": "UNETLoader", "inputs": {
            "unet_name": "flux1-dev-kontext_fp8_scaled.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "DualCLIPLoader", "inputs": {
            "clip_name1": "clip_l.safetensors", "clip_name2": "t5xxl_fp8_e4m3fn.safetensors",
            "type": "flux"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "4": {"class_type": "LoadImage", "inputs": {"image": img_name}},
        "5": {"class_type": "ImageScale", "inputs": {
            "image": ["4", 0], "upscale_method": "lanczos", "width": w, "height": h,
            "crop": "disabled"}},
        "6": {"class_type": "VAEEncode", "inputs": {"pixels": ["5", 0], "vae": ["3", 0]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": text, "clip": ["2", 0]}},
        "8": {"class_type": "ReferenceLatent", "inputs": {"conditioning": ["7", 0], "latent": ["6", 0]}},
        "9": {"class_type": "FluxGuidance", "inputs": {"conditioning": ["8", 0], "guidance": 2.5}},
        "10": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["7", 0]}},
        "11": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0], "positive": ["9", 0], "negative": ["10", 0], "latent_image": ["6", 0],
            "seed": seed, "steps": 28, "cfg": 1.0, "sampler_name": "euler",
            "scheduler": "simple", "denoise": 1.0}},
        "12": {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["3", 0]}},
        "13": {"class_type": "SaveImage", "inputs": {"images": ["12", 0], "filename_prefix": prefix}},
    }


def post(g):
    data = json.dumps({"prompt": g}).encode()
    req = urllib.request.Request(API + "/prompt", data=data,
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=120))["prompt_id"]


def wait(pid, limit=5400):
    t0 = time.time()
    while time.time() - t0 < limit:
        h = json.load(urllib.request.urlopen("%s/history/%s" % (API, pid), timeout=60))
        if pid in h:
            st = h[pid]["status"]
            if st.get("completed"):
                return h[pid]["outputs"]
            if st.get("status_str") == "error":
                raise RuntimeError(json.dumps(st)[:1500])
        time.sleep(5)
    raise RuntimeError("timeout " + pid)


def run(text, prefix, img_name, w=W, h=H, seed=SEED, out_name=None, out_dir=OUT):
    t0 = time.time()
    pid = post(graph(text, prefix, img_name, w, h, seed))
    print("queued %s <- %s %s (%dx%d seed %d)" % (prefix, img_name, pid, w, h, seed), flush=True)
    outs = wait(pid)
    img = outs["13"]["images"][0]
    src = os.path.join(COMFY_OUT, img.get("subfolder", ""), img["filename"])
    dest = os.path.join(out_dir, (out_name or prefix) + ".png")
    shutil.copyfile(src, dest)
    el = time.time() - t0
    print("OK %s %d %.1fs" % (dest, os.path.getsize(dest), el), flush=True)
    return el, dest


def do_mono(res):
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    m = Image.open(MASTER).convert("RGB").crop(PLATE)
    m.save(os.path.join(COMFY_IN, "lay_yw_master.png"))
    m.resize((W, H), Image.LANCZOS).save(os.path.join(OUT, "L1_master.png"))
    print("L1 saved, рамка срезана: %s -> %s" % (PLATE, m.size), flush=True)
    for key, prompt in (("L2_clean", P_L2), ("L3_tone", P_L3), ("L4_detail", P_L4)):
        el, dest = run(prompt, key + "_yw", "lay_yw_master.png", out_name=key + "_raw")
        res[key] = {"sec": round(el, 1), "path": dest, "input": "lay_yw_master.png"}
        json.dump(res, open(LOG, "w"), indent=1)
    print("MONODONE " + json.dumps(res), flush=True)


def do_color(res, src=None):
    src = src or os.path.join(OUT, "L4_detail_raw.png")
    shutil.copyfile(src, os.path.join(COMFY_IN, "lay_yw_l4.png"))
    el, dest = run(P_L5, "L5_color_yw", "lay_yw_l4.png", out_name="L5_color_raw", seed=202020)
    res["L5_color"] = {"sec": round(el, 1), "path": dest, "input": src}
    json.dump(res, open(LOG, "w"), indent=1)
    print("COLORDONE " + json.dumps(res), flush=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    res = json.load(open(LOG)) if os.path.exists(LOG) else {}
    if mode in ("mono", "all"):
        do_mono(res)
    if mode in ("color", "all"):
        do_color(res, sys.argv[2] if len(sys.argv) > 2 else None)
    print("ALLDONE", flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Реставрация архивных фото через Gemini API.

Берёт мастер-файл архива, отправляет его в Gemini вместе с промптом хозяина
и сохраняет результат. Два режима: mono и color.

Ключ читается из переменной окружения GEMINI_API_KEY. В коде ключа нет и
быть не должно.

    python gemini_restore.py --check
    python gemini_restore.py вход.tif --mode mono  --out выход.png
    python gemini_restore.py вход.tif --mode color --out выход.png
    python gemini_restore.py вход.tif --both --outdir папка
"""

import argparse
import base64
import io
import json
import os
import sys
import urllib.error
import urllib.request

API_ROOT = "https://generativelanguage.googleapis.com/v1beta"

# Промпт хозяина, проверен на трёх эталонах. Менять только по его слову.
PROMPT_BASE = """[System Role]: Professional Archivist & Museum Photo-Restoration Engine.
[Input]: Historical damaged photograph.
[Task]: Execute non-destructive, high-fidelity digital restoration.

[Execution Protocol - Step-by-Step]:
1. LAYER 1: ARTIFACT CLEANING
   - Detect and neutralize: physical cracks, paper folds, scratches, dust mites, silver mirroring, chemical stains, and water damage.
   - Action: Inpaint missing pixels using local contextual texture synthesis. Do NOT introduce external objects.
   - Background: render a plain smooth studio backdrop with soft vignette. No curtains, no drapery, no tulle, no lace, no fabric folds.

2. LAYER 2: IDENTITY PRESERVATION (CRITICAL / WEIGHT = 1.0)
   - Structural Integrity: Maintain 100% exact facial geometry, bone structure, eye shape, nose contour, lip fullness, and expression.
   - NO GENTRIFICATION: Do not beautify, do not change age, do not adjust ethnic features, do not alter original gaze direction.
   - Wardrobe & Context: Keep original textures of fabric, buttons, insignias, and background elements authentic to the original era.
   - Hands: preserve exact original placement and grip. Correct anatomy, five fingers per hand, no fused, extra or missing fingers.

3. LAYER 3: SIGNAL PROCESSING & RESOLUTION
   - Enhancements: Super-resolve image contrast and local sharpness. Eliminate chromatic aberration and digital sensor/scanned noise.
   - Dynamic Range: Recover lost data from deep shadows and clipped highlights. Balance exposure using a natural film gamma curve.

4. LAYER 4: TEXTURE & AESTHETIC CONSTRAINTS (NEGATIVE BIAS)
   - FORBIDDEN: "Plastic skin" effect, heavy airbrushing, AI-blurring, 3D render look, cartoon vectors, or modern smartphone-camera aesthetic.
   - REQUIRED: Preserve high-frequency surface details (skin pores, fabric weave) and natural analog film grain appropriate for the photo's original decade.

[Output Format]: Return ONLY the final restored image. No conversational filler, no explanations."""

TAIL = {
    "mono": "\n\n[Color Output Directive]: Keep original Monochrome/Sepia, optimizing the tonal range only.",
    "color": "\n\n[Color Output Directive]: Apply historical multi-channel colorization. Use muted, chemically realistic, organic tones for skin and environment. Avoid neon or over-saturated modern palettes.",
}

MAX_SIDE = 2048  # длинная сторона на отправку; TIFF в 29 МБ API не примет


def key_or_die():
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        sys.exit(
            "GEMINI_API_KEY не задан.\n"
            "Windows:  [Environment]::SetEnvironmentVariable('GEMINI_API_KEY','ключ','Machine')\n"
            "Linux:    export GEMINI_API_KEY=ключ"
        )
    return key


def call(url, payload=None, key=None):
    sep = "&" if "?" in url else "?"
    url = f"{url}{sep}key={key}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:1500]
        sys.exit(f"HTTP {e.code} от Gemini:\n{body}")
    except urllib.error.URLError as e:
        sys.exit(f"Сеть недоступна: {e.reason}")


def image_models(key):
    """Модели, умеющие отдавать картинку. Имя не хардкодим — спрашиваем API."""
    out, page = [], None
    while True:
        url = f"{API_ROOT}/models?pageSize=200"
        if page:
            url += f"&pageToken={page}"
        data = call(url, key=key)
        for m in data.get("models", []):
            name = m.get("name", "")
            methods = m.get("supportedGenerationMethods", [])
            if "generateContent" not in methods:
                continue
            if "image" in name.lower() and "embedding" not in name.lower():
                out.append(name.split("/", 1)[-1])
        page = data.get("nextPageToken")
        if not page:
            break
    return out


def prepare(path):
    """TIFF и гиганты API не принимает — отдаём JPEG с ограниченной стороной."""
    try:
        from PIL import Image
    except ImportError:
        sys.exit("Нужен Pillow:  pip install pillow")
    im = Image.open(path)
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    w, h = im.size
    scale = MAX_SIDE / max(w, h)
    if scale < 1:
        im = im.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=95, subsampling=0)
    return base64.b64encode(buf.getvalue()).decode(), im.size, (w, h)


def extract_image(resp):
    for cand in resp.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            blob = part.get("inlineData") or part.get("inline_data")
            if blob and str(blob.get("mimeType") or blob.get("mime_type", "")).startswith("image/"):
                return base64.b64decode(blob["data"])
    # картинки нет — покажем, что модель вообще ответила
    texts = [
        p.get("text", "")
        for c in resp.get("candidates", [])
        for p in c.get("content", {}).get("parts", [])
        if p.get("text")
    ]
    reason = resp.get("promptFeedback", {}).get("blockReason")
    sys.exit(
        "Модель не вернула изображение.\n"
        f"blockReason: {reason}\nтекст ответа: {' '.join(texts)[:800]}"
    )


def restore(src, mode, dst, model, key):
    b64, sent, orig = prepare(src)
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": PROMPT_BASE + TAIL[mode]},
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64}},
                ]
            }
        ]
    }
    resp = call(f"{API_ROOT}/models/{model}:generateContent", payload, key)
    img = extract_image(resp)
    os.makedirs(os.path.dirname(os.path.abspath(dst)) or ".", exist_ok=True)
    with open(dst, "wb") as f:
        f.write(img)
    print(f"{mode}: {dst}  ({len(img)/1e6:.1f} МБ, вход {orig[0]}x{orig[1]} -> отправлено {sent[0]}x{sent[1]})")
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", nargs="?", help="мастер-файл архива")
    ap.add_argument("--mode", choices=["mono", "color"], default="mono")
    ap.add_argument("--both", action="store_true", help="сделать оба варианта")
    ap.add_argument("--out")
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--model", help="переопределить модель")
    ap.add_argument("--check", action="store_true", help="проверить ключ и показать модели")
    a = ap.parse_args()

    key = key_or_die()
    models = image_models(key)

    if a.check:
        print("Ключ рабочий. Модели, умеющие отдавать картинку:")
        for m in models or ["— ни одной не нашлось"]:
            print("  ", m)
        return

    if not a.input:
        ap.error("нужен путь к файлу (или --check)")
    model = a.model or (models[0] if models else None)
    if not model:
        sys.exit("Не нашёл модель с выводом изображения. Запусти --check и посмотри список.")
    print(f"модель: {model}")

    base = os.path.splitext(os.path.basename(a.input))[0]
    if a.both:
        for m in ("mono", "color"):
            restore(a.input, m, os.path.join(a.outdir, f"{base}_{m}.png"), model, key)
    else:
        restore(a.input, a.mode, a.out or os.path.join(a.outdir, f"{base}_{a.mode}.png"), model, key)


if __name__ == "__main__":
    main()

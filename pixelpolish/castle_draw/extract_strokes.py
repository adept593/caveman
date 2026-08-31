#!/usr/bin/env python3
"""b96 Neuschwanstein -> pencil strokes (two layers: light sketch + detail).

Emits strokes.js with baked timings + preview PNGs for eyeballing.
"""
import json
import math
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw
from skimage.morphology import skeletonize

SRC = "/tmp/claude-0/-home-user/07e345c0-f288-5e82-a7f3-16e002c99a9f/scratchpad/scout_buildings/full/b96_2017660097.jpg"
OUT_DIR = "/tmp/claude-0/-home-user/07e345c0-f288-5e82-a7f3-16e002c99a9f/scratchpad/castle_draw"

# --- 1. load + crop (mat border off, castle-centric) ---------------------
img = cv2.imread(SRC)
H0, W0 = img.shape[:2]
# photo sits inside a gray mat; keep castle + rock pedestal, drop right meadow half
# displayed(2000x1477)*3.69: castle x~180..1420 -> 664..5240, y 90..1430 -> 332..5277
x0, y0, x1, y1 = 560, 300, 5480, 5000
img = img[y0:y1, x0:x1]

PROC_W = 1000
scale = PROC_W / img.shape[1]
proc = cv2.resize(img, (PROC_W, int(img.shape[0] * scale)), interpolation=cv2.INTER_AREA)
PH, PW = proc.shape[:2]
gray = cv2.cvtColor(proc, cv2.COLOR_BGR2GRAY)
gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)

# --- 2. two edge maps -----------------------------------------------------
# sketch: big shapes only -> heavy blur + soft thresholds
blur_big = cv2.GaussianBlur(gray, (0, 0), 3.2)
edges_sketch = cv2.Canny(blur_big, 28, 85)
# detail: bilateral keeps architecture, kills film grain
bil = cv2.bilateralFilter(gray, 9, 60, 60)
edges_detail = cv2.Canny(bil, 55, 140)

# rock/tree zone = bottom ~42% -> thin it out hard in detail layer
rock_top = int(PH * 0.60)


def trace(edge_map):
    sk = skeletonize(edge_map > 0)
    ys, xs = np.nonzero(sk)
    pix = set(zip(xs.tolist(), ys.tolist()))

    def nbrs(p):
        x, y = p
        out = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx or dy:
                    q = (x + dx, y + dy)
                    if q in pix:
                        out.append(q)
        return out

    deg = {p: len(nbrs(p)) for p in pix}
    visited = set()
    paths = []

    def walk(start):
        path = [start]
        visited.add(start)
        cur = start
        while True:
            cand = [q for q in nbrs(cur) if q not in visited]
            if not cand:
                break
            if len(path) >= 2:
                px, py = path[-2]
                cx, cy = cur
                vx, vy = cx - px, cy - py
                cand.sort(key=lambda q: -((q[0] - cx) * vx + (q[1] - cy) * vy))
            cur = cand[0]
            path.append(cur)
            visited.add(cur)
        return path

    for p in sorted(pix, key=lambda p: (p[1], p[0])):
        if p in visited or deg[p] != 1:
            continue
        path = walk(p)
        if len(path) >= 8:
            paths.append(path)
    for p in sorted(pix, key=lambda p: (p[1], p[0])):  # loops
        if p in visited:
            continue
        path = walk(p)
        if len(path) >= 8:
            paths.append(path)
    return paths


def simplify(paths, eps):
    out = []
    for path in paths:
        arr = np.array(path, dtype=np.int32).reshape(-1, 1, 2)
        ap = cv2.approxPolyDP(arr, eps, False).reshape(-1, 2)
        if len(ap) >= 2:
            out.append(ap.astype(float))
    return out


def path_len(p):
    return float(sum(math.dist(p[i], p[i + 1]) for i in range(len(p) - 1)))


def prep(edge_map, eps, min_len, cap, rock_min_len=None):
    polys = simplify(trace(edge_map), eps)
    keep = []
    for p in polys:
        L = path_len(p)
        cy = float(np.mean(p[:, 1]))
        need = min_len if (rock_min_len is None or cy < rock_top) else rock_min_len
        if L >= need:
            keep.append((L, p))
    keep.sort(key=lambda t: -t[0])
    keep = keep[:cap]
    return [p for _, p in keep]


sketch = prep(edges_sketch, eps=2.6, min_len=58, cap=90, rock_min_len=130)
detail = prep(edges_detail, eps=1.4, min_len=30, cap=650, rock_min_len=60)
print(f"sketch strokes: {len(sketch)}  detail strokes: {len(detail)}", file=sys.stderr)

# --- 2b. hatching (shading) ----------------------------------------------
# tone from blurred gray; hatch dark regions diagonally, cross-hatch darkest
tone = cv2.GaussianBlur(gray, (0, 0), 2.0)


def hatch_runs(mask, spacing, angle_deg, min_run=14, jitter_seed=1):
    """diagonal scanlines across mask -> stroke segments where mask is on"""
    rng = np.random.default_rng(jitter_seed)
    a = math.radians(angle_deg)
    dx, dy = math.cos(a), math.sin(a)
    nx, ny = -dy, dx  # normal
    diag = math.hypot(PW, PH)
    strokes = []
    n_lines = int(diag / spacing)
    for i in range(-n_lines, n_lines):
        # line: point on center + i*spacing along normal, direction (dx,dy)
        cx, cy = PW / 2 + nx * i * spacing, PH / 2 + ny * i * spacing
        run = []
        for t in range(-int(diag / 2), int(diag / 2), 2):
            x, y = cx + dx * t, cy + dy * t
            xi, yi = int(x), int(y)
            inside = 0 <= xi < PW and 0 <= yi < PH and mask[yi, xi]
            if inside:
                run.append([x, y])
            elif run:
                if len(run) * 2 >= min_run:
                    j = rng.uniform(-1.2, 1.2, 2)
                    strokes.append(np.array([run[0] + j, run[-1] - j]))
                run = []
        if run and len(run) * 2 >= min_run:
            strokes.append(np.array([run[0], run[-1]]))
    return strokes


mask_mid = (tone < 132).astype(np.uint8)
mask_dark = (tone < 88).astype(np.uint8)
# clean specks
k = np.ones((3, 3), np.uint8)
mask_mid = cv2.morphologyEx(mask_mid, cv2.MORPH_OPEN, k).astype(bool)
mask_dark = cv2.morphologyEx(mask_dark, cv2.MORPH_OPEN, k).astype(bool)

hatch_mid = hatch_runs(mask_mid, spacing=8, angle_deg=52, min_run=16, jitter_seed=3)
hatch_dark = hatch_runs(mask_dark, spacing=6, angle_deg=128, min_run=12, jitter_seed=5)
# cap by longest
hatch_mid = sorted(hatch_mid, key=lambda p: -path_len(p))[:520]
hatch_dark = sorted(hatch_dark, key=lambda p: -path_len(p))[:420]
print(f"hatch mid: {len(hatch_mid)}  hatch dark: {len(hatch_dark)}", file=sys.stderr)


# --- 3. order like an artist: greedy nearest-neighbour from the top ------
def order_nn(polys):
    if not polys:
        return polys
    rem = list(polys)
    rem.sort(key=lambda p: float(np.min(p[:, 1])))
    out = [rem.pop(0)]
    while rem:
        tail = out[-1][-1]
        i_best = min(range(len(rem)), key=lambda i: math.dist(tail, rem[i][0]) if True else 0)
        # allow reversing a stroke if its end is nearer
        p = rem.pop(i_best)
        if math.dist(tail, p[-1]) < math.dist(tail, p[0]):
            p = p[::-1]
        out.append(p)
    return out


sketch = order_nn(sketch)
detail = order_nn(detail)
hatch_mid = order_nn(hatch_mid)
hatch_dark = order_nn(hatch_dark)

# --- 4. map to canvas + bake timings -------------------------------------
CANV_W, CANV_H = 1080, 1920
BOX_W = 950.0
s2 = BOX_W / PW
BOX_H = PH * s2
OX = (CANV_W - BOX_W) / 2
OY = 470.0  # drawing block sits upper-middle
print(f"canvas box: {BOX_W:.0f}x{BOX_H:.0f} at ({OX:.0f},{OY:.0f})", file=sys.stderr)


def bake(polys, t0, t_end, d_min, d_max, overlap):
    """proportional-duration schedule squeezed into [t0, t_end]"""
    lens = [path_len(p) for p in polys]
    durs = [max(d_min, min(d_max, L / 1400.0)) for L in lens]
    starts = []
    t = 0.0
    for d in durs:
        starts.append(t)
        t += d * overlap
    span = starts[-1] + durs[-1] if polys else 1.0
    k = (t_end - t0) / span
    out = []
    for p, st, d in zip(polys, starts, durs):
        pts = [[round(x * s2 + OX, 1), round(y * s2 + OY, 1)] for x, y in p]
        out.append({"p": pts, "t": round(t0 + st * k, 3), "d": round(max(0.1, d * k), 3)})
    return out


sketch_js = bake(sketch, 0.25, 4.2, 0.22, 0.8, 0.34)
detail_js = bake(detail, 4.4, 14.4, 0.14, 0.6, 0.26)
hmid_js = bake(hatch_mid, 14.6, 18.9, 0.10, 0.3, 0.22)
hdark_js = bake(hatch_dark, 18.6, 21.9, 0.10, 0.25, 0.22)

with open(f"{OUT_DIR}/strokes.js", "w") as f:
    f.write("// generated by extract_strokes.py — Neuschwanstein b96\n")
    f.write("window.SKETCH = " + json.dumps(sketch_js, separators=(",", ":")) + ";\n")
    f.write("window.DETAIL = " + json.dumps(detail_js, separators=(",", ":")) + ";\n")
    f.write("window.HMID = " + json.dumps(hmid_js, separators=(",", ":")) + ";\n")
    f.write("window.HDARK = " + json.dumps(hdark_js, separators=(",", ":")) + ";\n")
size_kb = len(open(f"{OUT_DIR}/strokes.js").read()) // 1024
print(f"strokes.js: {size_kb} KB", file=sys.stderr)

# --- 5. previews ----------------------------------------------------------
im = Image.new("RGB", (CANV_W, CANV_H), "#fcfbf8")
dr = ImageDraw.Draw(im)
for s in sketch_js:
    dr.line([tuple(pt) for pt in s["p"]], fill=(168, 162, 154), width=3)
im.save(f"{OUT_DIR}/preview_sketch.png")
for s in detail_js:
    dr.line([tuple(pt) for pt in s["p"]], fill=(53, 50, 46), width=2)
im.save(f"{OUT_DIR}/preview_lines.png")
for s in hmid_js:
    dr.line([tuple(pt) for pt in s["p"]], fill=(122, 116, 108), width=2)
for s in hdark_js:
    dr.line([tuple(pt) for pt in s["p"]], fill=(70, 66, 60), width=2)
im.save(f"{OUT_DIR}/preview_full.png")
print("previews saved", file=sys.stderr)

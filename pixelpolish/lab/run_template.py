# -*- coding: utf-8 -*-
"""Прогон шаблона лаунчера через API: UI-JSON (с подграфами) -> API-граф -> /prompt -> выходы в lab/<дата>/<template>/.

  python run_template.py <template_name> [--port 8188] [--image X.png] [--video X.mp4] [--audio X.mp3] [--dry]
  python run_template.py --list                       имена готовых шаблонов из inventory.json

Конвертация: widgets_values раскладываются по не-связным входам узла в порядке object_info (required, затем optional);
после INT-входа с control_after_generate пропускается служебное значение ('fixed'/'randomize'); динамические комбо
(COMFY_DYNAMICCOMBO_V3) берут ключ и затем входы выбранной опции. Подграфы разворачиваются: узлы подграфа получают
префикс, входы подграфа (-10.k) подменяются на внешние связи или widgets_values внешнего узла.
"""
import json, sys, time, shutil, urllib.request, urllib.error, datetime as dt, argparse
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
L = Path(r"C:\Users\RobotComp\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI")
TPL = L / ".venv/Lib/site-packages/comfyui_workflow_templates_json/templates"
LAB = Path(r"D:\PixelPolish\lab") / dt.date.today().isoformat()
INPUT_DIRS = {8188: Path(r"C:\Users\RobotComp\pixelpolish\ComfyUI\input"), 8189: Path(r"C:\Users\RobotComp\AppData\Local\Comfy-Desktop\ComfyUI-Shared\input")}
OUTPUT_DIRS = {8188: Path(r"C:\Users\RobotComp\pixelpolish\ComfyUI\output"), 8189: Path(r"C:\Users\RobotComp\AppData\Local\Comfy-Desktop\ComfyUI-Shared\output")}
DEFAULTS = {"image": r"D:\PixelPolish\video\projects\story_whale_evolution\shot6.png", "video": r"D:\PixelPolish\video\projects\h3_test\quality_720.mp4",
            "audio": r"D:\PixelPolish\МУЗЫКА\m3_maps_master.flac"}
SKIP_TYPES = {"MarkdownNote", "Note", "Reroute", "PrimitiveNode"}
PRIM = ("INT", "FLOAT", "STRING", "BOOLEAN", "COMBO")


def api(port, path, data=None):
    req = urllib.request.Request(f"http://127.0.0.1:{port}/{path}", data=json.dumps(data).encode() if data is not None else None,
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=120).read())


def is_link_input(spec):
    t = spec[0]
    if isinstance(t, list): return False                       # enum
    return isinstance(t, str) and t not in PRIM and not t.startswith("COMFY_")


def assign_widgets(oi, ty, widgets, linked):
    o = oi.get(ty); out = {}
    if not o: return out
    inp = o["input"]; order = list(inp.get("required", {}).items()) + list(inp.get("optional", {}).items())
    w = list(widgets or []); wi = [0]
    def take():
        if wi[0] < len(w): v = w[wi[0]]; wi[0] += 1; return v, True
        return None, False
    for name, spec in order:
        if is_link_input(spec): continue                       # связные типы не имеют виджета; связанные примитивы — имеют, значение потом перекроется
        t = spec[0]; meta = spec[1] if len(spec) > 1 and isinstance(spec[1], dict) else {}
        if isinstance(t, str) and t.startswith("COMFY_DYNAMICCOMBO"):
            key, ok = take()
            if not ok: continue
            out[name] = key
            opt = next((x for x in meta.get("options", []) if x.get("key") == key), None)
            if opt:
                for sub in list(opt.get("inputs", {}).get("required", {})) + list(opt.get("inputs", {}).get("optional", {})):
                    v, ok2 = take()
                    if ok2: out[f"{name}.{sub}"] = v; out[sub] = v          # ComfyUI ждёт «родитель.поле»; плоское имя — на всякий случай
            continue
        if isinstance(t, str) and t.startswith("COMFY_"): continue
        v, ok = take()
        if not ok: continue
        out[name] = v
        if meta.get("control_after_generate") or (name in ("seed", "noise_seed") and t == "INT"):
            if wi[0] < len(w) and isinstance(w[wi[0]], str) and w[wi[0]] in ("fixed", "randomize", "increment", "decrement"): wi[0] += 1
    return out


def convert(wf, oi):
    defs = {sg["id"]: sg for sg in wf.get("definitions", {}).get("subgraphs", [])}
    prompt = {}

    def links_of(graph):
        L_ = {}
        for l in graph.get("links", []):
            if isinstance(l, dict): L_[l["id"]] = (l["origin_id"], l["origin_slot"], l["target_id"], l["target_slot"])
            else: L_[l[0]] = (l[1], l[2], l[3], l[4])
        return L_

    def expand(graph, prefix, ext_inputs):
        nodes = {n["id"]: n for n in graph["nodes"]}; L_ = links_of(graph); outmap = {}
        key = lambda nid: f"{prefix}{nid}"
        for nid, n in nodes.items():
            if n["type"] in defs:
                sg = defs[n["type"]]; sub_prefix = f"{key(nid)}_"; sub_ext = {}; wv = list(n.get("widgets_values", [])); wi = 0
                idx_by_name = {sin["name"]: k for k, sin in enumerate(sg["inputs"])}
                # порядок widgets_values = порядок входов ВНЕШНЕГО узла (n["inputs"]), не sg["inputs"]
                for inp in n.get("inputs", []):
                    k = idx_by_name.get(inp.get("name"))
                    if k is None: continue
                    st = sg["inputs"][k].get("type", "")
                    if inp.get("link") is not None:
                        o_id, o_slot, _, _ = L_[inp["link"]]; sub_ext[k] = ("extlink", (prefix, o_id, o_slot, outmap))
                    elif isinstance(st, str) and st not in PRIM and not st.startswith("COMFY_") and not inp.get("widget"):
                        sub_ext[k] = ("none", None)
                    else:
                        if wi < len(wv): sub_ext[k] = ("value", wv[wi]); wi += 1
                        else: sub_ext[k] = ("none", None)
                expand(sg, sub_prefix, sub_ext)
                for j, sout in enumerate(sg.get("outputs", [])):
                    for l in sg.get("links", []):
                        tgt = l["target_id"] if isinstance(l, dict) else l[3]; tslot = l["target_slot"] if isinstance(l, dict) else l[4]
                        if tgt == -20 and tslot == j:
                            src = (l["origin_id"] if isinstance(l, dict) else l[1], l["origin_slot"] if isinstance(l, dict) else l[2])
                            outmap[(nid, j)] = (f"{sub_prefix}{src[0]}", src[1])
        def resolve(o_id, o_slot, pre, omap):
            if (o_id, o_slot) in omap: return list(omap[(o_id, o_slot)])
            return [f"{pre}{o_id}", o_slot]
        for nid, n in nodes.items():
            ty = n["type"]
            if ty in SKIP_TYPES or ty in defs or n.get("mode", 0) in (2, 4): continue
            linked = {}
            for i in n.get("inputs", []):
                if i.get("link") is None: continue
                o_id, o_slot, _, _ = L_[i["link"]]
                if o_id == -10:
                    t, v = ext_inputs.get(o_slot, ("none", None))
                    if t == "extlink": pre, oo, ss, omap = v; linked[i["name"]] = resolve(oo, ss, pre, omap)
                    elif t == "value": linked[i["name"]] = ("__value__", v)
                    continue
                linked[i["name"]] = resolve(o_id, o_slot, prefix, outmap)
            vals = assign_widgets(oi, ty, n.get("widgets_values"), {k for k, v in linked.items() if not (isinstance(v, tuple) and v[0] == "__value__")})
            for k, v in linked.items(): vals[k] = v[1] if isinstance(v, tuple) and v[0] == "__value__" else v
            prompt[key(nid)] = {"class_type": ty, "inputs": vals}
    expand(wf, "", {})
    return prompt


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("name", nargs="?"); ap.add_argument("--port", type=int, default=8188)
    ap.add_argument("--image"); ap.add_argument("--video"); ap.add_argument("--audio"); ap.add_argument("--dry", action="store_true"); ap.add_argument("--list", action="store_true"); ap.add_argument("--turbo", action="store_true")
    a = ap.parse_args()
    if a.list:
        inv = json.loads((LAB / "inventory.json").read_text(encoding="utf-8"))
        for t in inv["templates"]:
            if not t["api"] and t["all_models_present"] and not t["missing_nodes_8188"]: print(t["name"])
        return
    port = a.port; oi = api(port, "object_info"); wf = json.loads((TPL / f"{a.name}.json").read_text(encoding="utf-8"))
    prompt = convert(wf, oi)
    inp_dir = INPUT_DIRS[port]; inp_dir.mkdir(parents=True, exist_ok=True)
    for k, n in prompt.items():
        ty = n["class_type"]
        for field, kind in (("image", "image"), ("file", "video"), ("audio", "audio")):
            if ty in ("LoadImage", "LoadVideo", "LoadAudio") and field in n["inputs"] and not isinstance(n["inputs"][field], list):
                src = Path(getattr(a, kind) or DEFAULTS[kind]); dst = inp_dir / f"lab_{src.name}"; shutil.copy(src, dst); n["inputs"][field] = dst.name
        if "filename_prefix" in n["inputs"]: n["inputs"]["filename_prefix"] = f"lab/{a.name}"
        if a.turbo and ty == "PrimitiveBoolean" and n["inputs"].get("value") is False: n["inputs"]["value"] = True   # turbo/LoRA-переключатели шаблонов
        if a.turbo and ty == "PrimitiveInt" and n["inputs"].get("value") == 20: n["inputs"]["value"] = 8             # полный прогон 20 шагов -> 8
    out = LAB / a.name; out.mkdir(parents=True, exist_ok=True)
    (out / "graph.json").write_text(json.dumps(prompt, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{a.name}: узлов {len(prompt)}", flush=True)
    if a.dry: return
    t0 = time.time()
    try: resp = api(port, "prompt", {"prompt": prompt, "client_id": "lab"})
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", "replace"); (out / "result.json").write_text(json.dumps({"name": a.name, "ok": False, "error": err[:3000]}, ensure_ascii=False, indent=1), encoding="utf-8")
        print("ОТКАЗ:", err[:600]); return
    pid = resp.get("prompt_id")
    if not pid:
        (out / "result.json").write_text(json.dumps({"name": a.name, "ok": False, "error": json.dumps(resp)[:3000]}, ensure_ascii=False, indent=1), encoding="utf-8"); print("ОТКАЗ:", json.dumps(resp)[:600]); return
    while True:
        time.sleep(5)
        h = api(port, f"history/{pid}")
        if pid in h:
            st = h[pid]; sec = round(time.time() - t0)
            if st.get("status", {}).get("status_str") == "error":
                msgs = [m[1].get("exception_message", "")[:600] for m in st["status"].get("messages", []) if m[0] == "execution_error"]
                (out / "result.json").write_text(json.dumps({"name": a.name, "ok": False, "seconds": sec, "error": msgs}, ensure_ascii=False, indent=1), encoding="utf-8")
                print("ОШИБКА", sec, "с:", msgs[:1]); return
            files = []
            for o in st["outputs"].values():
                for kind in ("images", "videos", "audio", "gifs", "files"):
                    for f in o.get(kind, []):
                        src = OUTPUT_DIRS[port] / f.get("subfolder", "") / f["filename"]
                        if src.exists(): shutil.copy(src, out / src.name); files.append(src.name)
                for kind in ("text", "string"):
                    if kind in o: (out / "text.txt").write_text("\n".join(map(str, o[kind])), encoding="utf-8"); files.append("text.txt")
            (out / "result.json").write_text(json.dumps({"name": a.name, "ok": True, "seconds": sec, "outputs": files}, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"OK {sec} с: {files}"); return
        if time.time() - t0 > 5400: print("таймаут"); return


if __name__ == "__main__":
    main()

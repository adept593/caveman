# -*- coding: utf-8 -*-
"""Инвентарь ComfyUI-лаунчера: шаблоны (без API) с нужными моделями и их наличием, расширения обоих серверов.
Пишет D:\PixelPolish\lab\<дата>\inventory.json и inventory.md.
"""
import json, os, sys, glob, urllib.request, datetime as dt
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
L = Path(r"C:\Users\RobotComp\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI")
TPL = L / ".venv/Lib/site-packages/comfyui_workflow_templates_json/templates"
MODEL_DIRS = [Path(r"C:\Users\RobotComp\AppData\Local\Comfy-Desktop\ComfyUI-Shared\models"), Path(r"C:\Users\RobotComp\pixelpolish\ComfyUI\models")]
OUT = Path(r"D:\PixelPolish\lab") / dt.date.today().isoformat(); OUT.mkdir(parents=True, exist_ok=True)


def api(port, path):
    try: return json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/{path}", timeout=60).read())
    except Exception as e: return {}


def present(fname):
    return [str(p.relative_to(d)) for d in MODEL_DIRS for p in d.rglob(fname)]


def main():
    idx = json.loads((TPL / "index.json").read_text(encoding="utf-8"))
    oi88 = api(8188, "object_info"); oi89 = api(8189, "object_info")
    templates = []
    for cat in idx:
        for t in cat.get("templates", []):
            name = t["name"]; f = TPL / f"{name}.json"
            if not f.exists(): continue
            w = json.loads(f.read_text(encoding="utf-8"))
            nodes = list(w.get("nodes", []))
            for sg in w.get("definitions", {}).get("subgraphs", []): nodes += sg.get("nodes", [])
            types = sorted({n["type"] for n in nodes if n["type"] not in ("MarkdownNote", "Note")})
            is_api = name.startswith("api_") or any(ty.startswith(("Kling", "Veo", "Minimax", "OpenAI", "Gemini", "Runway", "Pika", "Luma", "Recraft", "Ideogram", "Stability", "Rodin", "Tripo", "Moonvalley", "Vidu", "Pixverse", "ByteDance", "Sora")) or "ApiNode" in ty for ty in types)
            models = []
            for n in nodes:
                for m in (n.get("properties", {}) or {}).get("models", []) or []:
                    fn = m.get("name"); models.append({"file": fn, "dir": m.get("directory"), "url": m.get("url"), "present": present(fn) if fn else []})
            uniq = list({m["file"]: m for m in models}.values())
            def missing(oi): return [ty for ty in types if ty not in oi and not ty.startswith(("Primitive", "ComfySwitch", "ComfyMath")) and len(ty) < 40 and "-" not in ty]
            templates.append({"name": name, "title": t.get("title", name), "category": cat.get("title") or cat.get("moduleName"), "api": is_api,
                              "types": types, "models": uniq, "all_models_present": all(m["present"] for m in uniq) if uniq else True,
                              "missing_nodes_8188": missing(oi88), "missing_nodes_8189": missing(oi89),
                              "media_inputs": [n["type"] for n in nodes if n["type"] in ("LoadImage", "LoadVideo", "LoadAudio", "Load3D")],
                              "description": t.get("description", "")})
    ours_ext = sorted(p.name for p in Path(r"C:\Users\RobotComp\pixelpolish\ComfyUI\custom_nodes").iterdir() if p.is_dir() and not p.name.startswith("__"))
    launcher_ext = sorted(p.name for p in (L / "custom_nodes").iterdir() if p.is_dir() and not p.name.startswith("__"))
    inv = {"date": dt.date.today().isoformat(), "templates": templates, "extensions": {"launcher_8189": launcher_ext, "ours_8188": ours_ext},
           "node_counts": {"8188": len(oi88), "8189": len(oi89)}}
    (OUT / "inventory.json").write_text(json.dumps(inv, ensure_ascii=False, indent=1), encoding="utf-8")
    local = [t for t in templates if not t["api"]]; ready = [t for t in local if t["all_models_present"] and not t["missing_nodes_8188"]]
    md = [f"# Инвентарь лаунчера, {inv['date']}", "", f"Шаблонов всего {len(templates)}, локальных {len(local)}, API-облако {len(templates)-len(local)}.",
          f"Готовы к прогону (модели есть, узлы есть): **{len(ready)}**. Узлов в 8189: {len(oi89)}, в 8188: {len(oi88)}.", "", "## Готовые к прогону", ""]
    for t in ready: md.append(f"- `{t['name']}` — {t['title']} ({t['category']}); входы: {', '.join(t['media_inputs']) or '—'}")
    md += ["", "## Локальные, не хватает моделей", ""]
    for t in local:
        miss = [m for m in t["models"] if not m["present"]]
        if miss: md.append(f"- `{t['name']}` — {t['title']}: " + "; ".join(str(m["file"]) for m in miss[:4]) + (" …" if len(miss) > 4 else ""))
    md += ["", "## Локальные, не хватает узлов (нет расширения)", ""]
    for t in local:
        if t["missing_nodes_8188"]: md.append(f"- `{t['name']}` — {t['title']}: {', '.join(t['missing_nodes_8188'][:5])}")
    md += ["", "## Расширения", "", f"Лаунчер (8189): {', '.join(launcher_ext) or 'нет — только штатные узлы'}", f"Наш (8188): {', '.join(ours_ext)}"]
    (OUT / "inventory.md").write_text("\n".join(md), encoding="utf-8")
    print(f"шаблонов {len(templates)}, локальных {len(local)}, готовых {len(ready)} -> {OUT}")
    for t in ready: print("  готов:", t["name"])


if __name__ == "__main__":
    main()

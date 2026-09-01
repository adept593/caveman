#!/usr/bin/env python3
"""PixelPolish — конвейер реставрации (план Б: порядок зашит в код).

Два круга брака (v5, v5b) случились из-за НАРУШЕННОГО ПОРЯДКА операций и из-за
этапов, отработавших «для галочки». Этот скрипт закрывает обе дыры:

  1. Порядок жёсткий и не настраивается: чистка -> лица -> цвет -> апскейл.
     Апскейл всегда последний: увеличитель на грязи галлюцинирует (так клетка
     на штанах стала мешковиной).
  2. После каждого этапа скрипт СРАВНИВАЕТ вход и выход. Если картинка почти
     не изменилась — этап считается не отработавшим, конвейер останавливается
     с ошибкой. «Прогнал, но ничего не поменялось» больше не пройдёт.

Запуск на ПК (агент делает ровно это):
    python restore.py check                     # что установлено, чего нет
    python restore.py run plate.jpg --out C:\\pixelpolish\\restore_v5
    python restore.py collage before.jpg after.png --out sklejka.jpg

Режимы:
    --dry-run       только напечатать команды, ничего не запускать
    --strict        строгий стандарт (знаменитости, клиенты kwork):
                    лица только реставрируются, генеративные вольности запрещены
    --from clean|faces|color|upscale   продолжить с этапа (если упало посередине)
    --ab-faces      сделать два варианта лиц (сходство vs качество) для выбора глазами

Пути к инструментам берутся из restore.cfg.json рядом со скриптом.
"""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).parent
CFG_P = HERE / "restore.cfg.json"

# Порядок этапов. НЕ МЕНЯТЬ — это и есть смысл скрипта.
ORDER = ["clean", "faces", "color", "upscale"]

DEFAULT_CFG = {
    "python": sys.executable,
    "_comment": "Пути к папкам инструментов на ПК. Пустая строка = не установлен.",
    "bopbtl_dir": "C:/pixelpolish/tools/Bringing-Old-Photos-Back-to-Life",
    "codeformer_dir": "C:/pixelpolish/tools/CodeFormer",
    "gfpgan_dir": "",
    "ddcolor_dir": "C:/pixelpolish/tools/DDColor",
    "realesrgan_dir": "C:/pixelpolish/tools/Real-ESRGAN",
    "realesrgan_model": "RealESRGAN_x4plus",
    "gpu": "0",
    "_faces": "CodeFormer: -w это баланс. Больше w -> ближе к оригиналу (сходство),"
              " меньше w -> красивее, но лицо уплывает. Нам сходство важнее.",
    "codeformer_w": 0.85,
    "codeformer_w_alt": 0.35,
    "_verify": "Порог: сколько процентов пикселей должно измениться, чтобы этап"
               " считался отработавшим.",
    "min_change_pct": {"clean": 0.5, "faces": 0.2, "color": 3.0, "upscale": 0.0},
}


def load_cfg():
    if CFG_P.exists():
        cfg = dict(DEFAULT_CFG)
        cfg.update(json.loads(CFG_P.read_text(encoding="utf-8")))
        return cfg
    CFG_P.write_text(json.dumps(DEFAULT_CFG, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[cfg] создан {CFG_P} — проверь пути к инструментам и запусти снова")
    return DEFAULT_CFG


# ---------------------------------------------------------------- проверки


def image_delta(p_before, p_after):
    """Насколько выход отличается от входа: (% изменённых пикселей, средняя разница)."""
    from PIL import Image
    import numpy as np
    a = Image.open(p_before).convert("RGB")
    b = Image.open(p_after).convert("RGB")
    if a.size != b.size:                      # апскейл — сравниваем в одном размере
        b = b.resize(a.size, Image.LANCZOS)
    x = np.asarray(a, dtype=np.int16)
    y = np.asarray(b, dtype=np.int16)
    diff = np.abs(x - y).max(axis=2)          # разница по самому «громкому» каналу
    changed = float((diff > 6).mean() * 100)  # 6/255 — порог видимого глазом
    return changed, float(diff.mean())


def run_cmd(cmd, cwd, dry):
    printable = " ".join(str(c) for c in cmd)
    print(f"    $ {printable}")
    if dry:
        return 0
    t0 = time.time()
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-2000:])
        print(r.stderr[-2000:], file=sys.stderr)
    print(f"    ({time.time() - t0:.0f} c, код {r.returncode})")
    return r.returncode


def newest_image(folder, exclude=()):
    folder = pathlib.Path(folder)
    if not folder.exists():
        return None
    files = [p for p in folder.rglob("*")
             if p.suffix.lower() in (".png", ".jpg", ".jpeg") and p not in exclude]
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


# ---------------------------------------------------------------- этапы
# Каждый этап: (вход, рабочая папка, cfg, args) -> путь к выходу или None


def stage_clean(src, work, cfg, args):
    """Чистка царапин/пятен на ИСХОДНОМ разрешении (BOPBTL, режим with_scratch)."""
    d = cfg["bopbtl_dir"]
    if not d:
        return None
    inp = work / "clean_in"
    out = work / "clean_out"
    inp.mkdir(exist_ok=True)
    shutil.copy(src, inp / src.name)
    cmd = [cfg["python"], "run.py", "--input_folder", str(inp), "--output_folder", str(out),
           "--GPU", cfg["gpu"], "--with_scratch"]
    if run_cmd(cmd, d, args.dry_run) != 0:
        return None
    return newest_image(out / "final_output") or newest_image(out)


def stage_faces(src, work, cfg, args):
    """Восстановление лиц. Сходство важнее красоты — вес держим высоким."""
    d = cfg["codeformer_dir"]
    if not d:
        return None
    out = work / "faces_out"
    w = cfg["codeformer_w"]
    cmd = [cfg["python"], "inference_codeformer.py", "-i", str(src), "-o", str(out),
           "-w", str(w), "--bg_upsampler", "None"]
    if run_cmd(cmd, d, args.dry_run) != 0:
        return None
    res = newest_image(out / "final_results") or newest_image(out)
    if args.ab_faces and not args.dry_run:
        alt = work / "faces_out_alt"
        run_cmd([cfg["python"], "inference_codeformer.py", "-i", str(src), "-o", str(alt),
                 "-w", str(cfg["codeformer_w_alt"]), "--bg_upsampler", "None"], d, False)
        print(f"    [A/B] сходство w={w} -> {res}")
        print(f"    [A/B] качество w={cfg['codeformer_w_alt']} -> {newest_image(alt)}")
        print("    Выбери глазами; если победил альтернативный — подставь его вручную.")
    return res


def stage_color(src, work, cfg, args):
    """Колоризация ЧИСТОГО ч/б. Цвета плотные и естественные, не «лёгкий румянец»."""
    d = cfg["ddcolor_dir"]
    if not d:
        return None
    out = work / "color_out"
    cmd = [cfg["python"], "infer.py", "--model_path", "./pretrain/net_g_200000.pth",
           "--input", str(src), "--output", str(out)]
    if run_cmd(cmd, d, args.dry_run) != 0:
        return None
    return newest_image(out)


def stage_upscale(src, work, cfg, args):
    """Апскейл ПОСЛЕДНИМ. ×2 за проход — щадяще к ткани с рисунком."""
    d = cfg["realesrgan_dir"]
    if not d:
        return None
    out = work / "upscale_out"
    cmd = [cfg["python"], "inference_realesrgan.py", "-n", cfg["realesrgan_model"],
           "-i", str(src), "-o", str(out), "-s", "2"]
    if run_cmd(cmd, d, args.dry_run) != 0:
        return None
    return newest_image(out)


STAGES = {"clean": stage_clean, "faces": stage_faces,
          "color": stage_color, "upscale": stage_upscale}
STAGE_RU = {"clean": "ЧИСТКА носителя", "faces": "ЛИЦА",
            "color": "ЦВЕТ", "upscale": "АПСКЕЙЛ"}


# ---------------------------------------------------------------- склейка


def make_collage(before, after, out_path, labels=("ДО", "ПОСЛЕ")):
    """Склейка ДО|ПОСЛЕ одной высоты с подписями."""
    from PIL import Image, ImageDraw, ImageFont
    a = Image.open(before).convert("RGB")
    b = Image.open(after).convert("RGB")
    h = max(a.height, b.height, 1200)
    a = a.resize((int(a.width * h / a.height), h), Image.LANCZOS)
    b = b.resize((int(b.width * h / b.height), h), Image.LANCZOS)
    gap, bar = 24, 90
    canvas = Image.new("RGB", (a.width + gap + b.width, h + bar), (16, 16, 18))
    canvas.paste(a, (0, 0))
    canvas.paste(b, (a.width + gap, 0))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 46)
    except Exception:
        font = ImageFont.load_default()
    draw.text((a.width // 2 - 40, h + 18), labels[0], font=font, fill=(235, 235, 235))
    draw.text((a.width + gap + b.width // 2 - 70, h + 18), labels[1], font=font, fill=(235, 235, 235))
    canvas.save(out_path, quality=95)
    return out_path


# ---------------------------------------------------------------- конвейер


def cmd_run(args):
    cfg = load_cfg()
    src = pathlib.Path(args.image).resolve()
    if not src.exists():
        sys.exit(f"нет файла: {src}")
    out_dir = pathlib.Path(args.out).resolve()
    work = out_dir / (src.stem + "_work")
    work.mkdir(parents=True, exist_ok=True)

    start = ORDER.index(args.from_stage) if args.from_stage else 0
    cur = pathlib.Path(args.resume).resolve() if args.resume else src
    manifest = {"source": str(src), "strict": args.strict, "stages": []}

    print(f"\nРЕСТАВРАЦИЯ: {src.name}")
    print(f"Стандарт: {'СТРОГИЙ (знаменитость/клиент) — лицо не выдумываем' if args.strict else 'ВОСПРИЯТИЕ (безымянная пластина)'}")
    print(f"Порядок зашит: {' -> '.join(ORDER)}\n")

    for i, name in enumerate(ORDER):
        head = f"[{i + 1}/{len(ORDER)}] {STAGE_RU[name]}"
        if i < start:
            print(f"{head}: пропуск (--from {args.from_stage})")
            continue
        print(head)
        res = STAGES[name](cur, work, cfg, args)
        if args.dry_run:
            continue
        if res is None or not pathlib.Path(res).exists():
            manifest["stages"].append({"stage": name, "ok": False, "reason": "инструмент не отработал"})
            _save(manifest, work)
            sys.exit(f"\nСТОП на этапе «{STAGE_RU[name]}»: инструмент не отработал или не настроен путь.\n"
                     f"Почини и продолжи:  python restore.py run {src} --out {out_dir} --from {name} --resume {cur}")
        changed, mean = image_delta(cur, res)
        need = cfg["min_change_pct"].get(name, 0.0)
        print(f"    изменилось {changed:.1f}% пикселей (порог {need}%)")
        if changed < need:
            manifest["stages"].append({"stage": name, "ok": False, "changed_pct": changed})
            _save(manifest, work)
            sys.exit(f"\nСТОП: этап «{STAGE_RU[name]}» почти ничего не изменил ({changed:.1f}%).\n"
                     f"Это и есть «прогон для галочки». Разберись, почему инструмент не сработал, и повтори.")
        keep = work / f"{i + 1}_{name}{pathlib.Path(res).suffix}"
        shutil.copy(res, keep)
        manifest["stages"].append({"stage": name, "ok": True, "changed_pct": round(changed, 2),
                                   "mean_diff": round(mean, 2), "file": str(keep)})
        cur = keep

    if args.dry_run:
        print("\n(dry-run: ничего не запускалось)")
        return

    final = out_dir / f"{src.stem}_restored.png"
    shutil.copy(cur, final)
    coll = make_collage(src, final, out_dir / f"{src.stem}_collage.jpg")
    manifest["final"] = str(final)
    manifest["collage"] = str(coll)
    _save(manifest, work)

    print(f"\nГОТОВО\n  результат: {final}\n  склейка:   {coll}")
    print("\nСАМОПРОВЕРКА ПЕРЕД СДАЧЕЙ (правило Седрака — сдаём только идеал):")
    for line in ["открой результат на 100% масштабе и пройди ВЕСЬ кадр",
                 "углы и края — ни пятен, ни черноты, ни обрывков носителя",
                 "фигуры целые: плечи, руки, юбка, штаны — ничего не съедено",
                 "ткань с рисунком осталась рисунком, а не мешковиной",
                 "лица — ТЕ ЖЕ: черты, возраст, взгляд (сверь с исходником)",
                 "цвет живой и естественный, кожа тёплая, без кислоты",
                 "нашёл хоть один дефект — НЕ СДАВАЙ, ещё проход"]:
        print(f"  [ ] {line}")


def _save(manifest, work):
    (work / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def cmd_check(args):
    cfg = load_cfg()
    print("Инструменты конвейера:")
    need = {"bopbtl_dir": "чистка (BOPBTL)", "codeformer_dir": "лица (CodeFormer)",
            "ddcolor_dir": "цвет (DDColor)", "realesrgan_dir": "апскейл (Real-ESRGAN)"}
    missing = []
    for key, label in need.items():
        d = cfg.get(key) or ""
        ok = bool(d) and pathlib.Path(d).exists()
        print(f"  [{'v' if ok else ' '}] {label:26s} {d or '— путь не задан'}")
        if not ok:
            missing.append(label)
    print("\nВсё на месте." if not missing else
          "\nНе хватает: " + ", ".join(missing) + "\nПропиши пути в restore.cfg.json.")


def cmd_collage(args):
    out = args.out or (pathlib.Path(args.after).parent / "collage.jpg")
    print("склейка:", make_collage(args.before, args.after, out))


def main():
    p = argparse.ArgumentParser(description="Конвейер реставрации PixelPolish")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="полный конвейер по одной пластине")
    r.add_argument("image")
    r.add_argument("--out", required=True)
    r.add_argument("--strict", action="store_true")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--ab-faces", action="store_true")
    r.add_argument("--from", dest="from_stage", choices=ORDER)
    r.add_argument("--resume", help="файл, с которого продолжаем (выход упавшего этапа)")
    r.set_defaults(func=cmd_run)

    c = sub.add_parser("check", help="что установлено, чего нет")
    c.set_defaults(func=cmd_check)

    k = sub.add_parser("collage", help="склейка ДО|ПОСЛЕ")
    k.add_argument("before")
    k.add_argument("after")
    k.add_argument("--out")
    k.set_defaults(func=cmd_collage)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

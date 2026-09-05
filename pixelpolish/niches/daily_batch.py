# -*- coding: utf-8 -*-
"""Дневная норма: 4 ролика — по одному на канал (карта, флаги, животные, библия).

  python daily_batch.py <day>        темы дня берутся из queue.json -> days[<day>]
  python daily_batch.py <day> map    только один тип (map|flags|animals|bible)

Каждая тема пишется во временный JSON и передаётся сборщику. Итог — daily_<day>.json с путями mp4.
"""
import json, subprocess, sys, io, time
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
HERE = Path(__file__).parent; SHORTS = Path(r"D:\PixelPolish\ШОРТСЫ")
TOOLS = {"map": ("map_whatif.py", lambda s: SHORTS / f"whatif_{s['key']}.mp4"),
         "flags": ("flag_quiz.py", lambda s: SHORTS / f"flagquiz_{s['name']}.mp4"),
         "animals": ("stills_story.py", lambda s: SHORTS / f"story_{s['key']}.mp4"),
         "bible": ("stills_story.py", lambda s: SHORTS / f"story_{s['key']}.mp4")}


def main():
    day = sys.argv[1]; only = sys.argv[2] if len(sys.argv) > 2 else None
    q = json.loads((HERE / "queue.json").read_text(encoding="utf-8"))["days"][day]
    tmp = HERE / "tmp"; tmp.mkdir(exist_ok=True); out = {}
    for kind, (tool, outp) in TOOLS.items():
        if only and kind != only: continue
        if kind not in q: print(f"[{kind}] нет темы на день {day}"); continue
        scen = q[kind]; p = tmp / f"day{day}_{kind}.json"; p.write_text(json.dumps(scen, ensure_ascii=False, indent=1), encoding="utf-8")
        t0 = time.time(); print(f"[{kind}] {tool} ...", flush=True)
        r = subprocess.run([sys.executable, str(HERE / tool), str(p)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        ok = r.returncode == 0 and outp(scen).exists()
        print(f"[{kind}] {'готово' if ok else 'УПАЛ'} {time.time()-t0:.0f} с -> {outp(scen) if ok else r.stderr[-800:]}")
        out[kind] = {"file": str(outp(scen)) if ok else None, "title": scen.get("yt_title"), "ok": ok}
    (HERE / f"daily_{day}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("итог:", sum(v["ok"] for v in out.values()), "из", len(out))


if __name__ == "__main__":
    main()

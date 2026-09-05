# -*- coding: utf-8 -*-
"""Музыка ролика youngwoman1855 — тот же music_v5, другие пути. Отличие от v4: в loudnorm берётся TP=-2.5 ДО кодирования
в AAC (правка I2 — в v4 после AAC истинный пик вышел -0,66 дБTP вместо -1,5).

Видео не перекодируется: звук подкладывается с -c:v copy.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from make_layers_short_v3 import FFMPEG, FFPROBE, run, log

TRACK = Path(r"D:\PixelPolish\МУЗЫКА\gemini_lyria_01.m4a")
WORK = Path(r"D:\PixelPolish\video\projects\layers_youngwoman1855_bust4\off")
VIDEO_ONLY = WORK / "video_noaudio.mp4"
AUDIO = WORK / "music_30s.m4a"
OUT = Path(r"D:\PixelPolish\ШОРТСЫ\youngwoman1855_v4_en.mp4")

DUR = 30.0
START = 27.5          # то же окно, что в v4 (самая плотная середина вещи)
TP_PRE = -2.5         # I2: запас по истинному пику перед AAC


def dur_of(p: Path) -> float:
    return float(run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                      "-of", "csv=p=0", str(p)]).stdout.strip())


def measure(src, args, af):
    p = subprocess.run([FFMPEG, "-v", "info", "-hide_banner"] + args +
                       ["-i", str(src), "-af", af, "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.findall(r"\{[^{}]*input_i[^{}]*\}", p.stderr, re.S)
    return json.loads(m[-1]) if m else {}


def main() -> int:
    if not VIDEO_ONLY.exists():
        return log("нет видео %s" % VIDEO_ONLY) or 2
    af = "afade=t=in:st=0:d=0.5,afade=t=out:st=%.1f:d=2" % (DUR - 2.0)
    log("[1/4] замер окна %.1f..%.1f с" % (START, START + DUR))
    ln0 = "loudnorm=I=-14:TP=%.1f:LRA=11:print_format=json" % TP_PRE
    meas = measure(TRACK, ["-ss", "%.3f" % START, "-t", "%.3f" % DUR], af + "," + ln0)
    log("  I=%s LRA=%s TP=%s thresh=%s" % (meas.get("input_i"), meas.get("input_lra"),
                                           meas.get("input_tp"), meas.get("input_thresh")))

    log("[2/4] нормализация с TP=%.1f, потом AAC 192к" % TP_PRE)
    ln = "loudnorm=I=-14:TP=%.1f:LRA=11" % TP_PRE
    if meas:
        ln += (":measured_I=%s:measured_LRA=%s:measured_TP=%s:measured_thresh=%s"
               ":offset=%s:linear=true"
               % (meas["input_i"], meas["input_lra"], meas["input_tp"],
                  meas["input_thresh"], meas.get("target_offset", "0.0")))

    # TP в loudnorm при linear=true не связывает: усиление задаётся целью по I.
    # Поэтому запас берём явно — подбираем добавочное ослабление так, чтобы
    # истинный пик ПОСЛЕ AAC ушёл под -1,5 дБTP.
    trim, out2, tries = 0.0, {}, []
    for _ in range(5):
        chain = af + "," + ln + (",volume=%.2fdB" % trim if trim else "") + ",aresample=44100"
        run([FFMPEG, "-y", "-v", "error", "-ss", "%.3f" % START, "-t", "%.3f" % DUR,
             "-i", str(TRACK), "-af", chain,
             "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
             "-t", "%.3f" % DUR, str(AUDIO)])
        out2 = measure(AUDIO, [], "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json")
        tp = float(out2.get("input_tp", 0.0))
        li = float(out2.get("input_i", 0.0))
        tries.append({"trim_db": round(trim, 2), "tp_after_aac": tp, "i_after_aac": li})
        log("  ослабление %+.2f дБ -> после AAC I=%.2f TP=%.2f" % (trim, li, tp))
        if tp <= -1.5:
            break
        trim -= (tp + 1.8)
    log("  дорожка %.3f с; итог после AAC: I=%s LRA=%s TP=%s"
        % (dur_of(AUDIO), out2.get("input_i"), out2.get("input_lra"), out2.get("input_tp")))

    log("[3/4] подкладка звука, видео НЕ перекодируется")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    run([FFMPEG, "-y", "-v", "error", "-i", str(VIDEO_ONLY), "-i", str(AUDIO),
         "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "copy",
         "-movflags", "+faststart", "-shortest", str(OUT)])
    log("  готово: %s (%d байт)" % (OUT, OUT.stat().st_size))

    log("[4/4] ffprobe")
    info = json.loads(run([FFPROBE, "-v", "error", "-show_entries",
                           "format=duration,bit_rate,size:stream=index,codec_type,"
                           "codec_name,profile,width,height,r_frame_rate,pix_fmt,"
                           "sample_rate,channels,bit_rate,duration",
                           "-of", "json", str(OUT)]).stdout)
    print(json.dumps(info, ensure_ascii=False, indent=1))
    json.dump({"start": START, "tp_pre_aac": TP_PRE, "loudnorm_in": meas,
               "trim_iterations": tries, "loudnorm_out_after_aac": out2, "probe": info},
              open(WORK / "music_checks.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

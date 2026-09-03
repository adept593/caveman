#!/usr/bin/env python3
"""Строит фильтр кен-бёрнса для шортса и проверяет его на три мины сразу.

Мина 1 — zoompan квантует позицию окна до целого пикселя ВХОДА. Если окно
проходит меньше ~0,64 px за кадр, соседние кадры выходят побитово одинаковыми
и движение читается как рывки. Замеры — ФОРМАТ_V5.md, группа J, и переизмерение
04.09 на всех 899 парах (REPORT_V5B.md, задача 1).

Мина 2 — зум растягивает пиксели, когда окно становится уже выхода. При выходе
1080x1920 запас был 1,31 и тратить его было не на что. При 1440x2560 запаса нет
вовсе: окно 1422 против 1440 — это уже 1,3 % растяжения на старте. Поэтому здесь
не запрет, а потолок: растягивать больше чем в MAX_UPSCALE раз нельзя.

Мина 3 — сам zoompan флагов масштабирования не принимает и последнюю пересборку
кадра делает своим внутренним swscale. При s=1080x1920 это ужатие 5400 -> 1080
чужим фильтром, минус 12,3 % резкости на кадре. Лечится тем, что zoompan отдаёт
кадр крупнее выхода (ss), а вниз его ведёт отдельный scale с lanczos.
Замер — ФОРМАТ_V5.md, J.2a, и REPORT_ZOOM_SHARPNESS.md.

Строку фильтра руками не писать: все три порога проверяются здесь.
"""
import argparse, sys

# 0,35 из J.3 не держится: тот замер шёл по первым 120 кадрам НАЕЗДА, а это
# самая быстрая часть разгона (скорость окна ~1/z², у наезда z в начале
# минимальный). На всех 899 парах та же конфигурация G даёт 48 заморозок.
# Переизмерено 04.09, выход брался gray rawvideo прямо из фильтра, без кодека:
#   0,443 px/кадр -> 107/899   0,508 (это и есть G) -> 47..48/899
#   0,590 px/кадр ->   4/899   0,643 px/кадр        ->  0/899
# Порог поставлен на первое значение, где заморозок нет вообще.
MIN_TRAVEL_PX_PER_FRAME = 0.64   # ниже — заморозки, см. J.3 и REPORT_V5B.md
MAX_UPSCALE = 1.15               # предел растяжения на пике зума, см. J.1
MODES = {"off": None, "in": (1.00, 1.12), "out": (1.12, 1.00)}


def build(mode, seconds, fps, master_w, master_h, out_w, out_h, ss=2,
          max_upscale=None):
    """ss — во сколько раз zoompan отдаёт кадр крупнее выхода (суперсэмплинг).

    По умолчанию 2. ss=1 — это прежнее поведение, оставлено только для контроля:
    на нём zoompan сам жмёт окно до 1080x1920 и теряет 12,3 % резкости кадра.
    Выше 2 не нужно: ss=3 и ss=4 добавляют меньше 0,7 % и стоят лишнего времени
    (ФОРМАТ_V5.md, J.2a).

    max_upscale — потолок растяжения на пике зума. По умолчанию MAX_UPSCALE.
    Поднимать его в производстве нельзя; параметр нужен замерам, которые как раз
    и выясняют, где этот потолок должен стоять (REPORT_RESOLUTION.md).
    """
    max_upscale = MAX_UPSCALE if max_upscale is None else max_upscale
    frames = int(round(seconds * fps))
    win_w = int(round(master_h * out_w / out_h))      # окно 9:16 по высоте мастера
    if win_w > master_w:
        sys.exit(f"мастер {master_w}x{master_h} уже, чем нужно окно {win_w}px — кроп невозможен")
    win_x, win_h = (master_w - win_w) // 2, master_h
    crop = f"crop={win_w}:{win_h}:{win_x}:0"
    headroom = win_w / out_w                          # 1,317 для 2160x2528 -> 1080x1920

    if mode == "off":
        return f"{crop},scale={out_w}:{out_h}:flags=lanczos,fps={fps}", {
            "окно": f"{win_w}x{win_h}",
            "запас разрешения": f"{headroom:.3f}x"
                                + ("" if headroom >= 1 else f"  (растяжение {1/headroom:.3f}x)"),
            "зум": "нет"}

    z0, z1 = MODES[mode]
    z_max = max(z0, z1)
    upscale_at_peak = z_max / headroom          # <1 — ещё пересэмплирование вниз
    if upscale_at_peak > max_upscale:
        sys.exit(f"на пике зума кадр растянется в {upscale_at_peak:.2f} раза "
                 f"при потолке {max_upscale} — уменьшай зум или выход")

    # подбираем целый апскейл входа так, чтобы окно шло >= 0.35 px за кадр
    span = 1 - 1 / z_max
    up = 1
    while (win_w * up * span) / frames < MIN_TRAVEL_PX_PER_FRAME:
        up += 1
        if up > 4:                                    # 6x не уложился в счёт, см. J.2
            sys.exit(f"нужен апскейл >{up-1}x — считать будет неприемлемо долго; "
                     f"увеличь ход зума вместо этого")
    travel = (win_w * up * span) / frames

    zexpr = f"{z0}+({z1 - z0:+.6f})*on/{frames - 1}".replace("+-", "-")
    parts = [crop]
    if up > 1:
        parts.append(f"scale={win_w*up}:{win_h*up}:flags=lanczos")
    zp_w, zp_h = int(round(out_w * ss)), int(round(out_h * ss))
    zp_w -= zp_w % 2
    zp_h -= zp_h % 2
    # при слишком большом ss zoompan начал бы растягивать окно вместо ужатия
    win_at_zmax = win_w * up / z_max
    if zp_w > win_at_zmax:
        sys.exit(f"суперсэмплинг {ss}x даёт {zp_w}px при окне {win_at_zmax:.0f}px "
                 f"на самом глубоком зуме — zoompan начнёт растягивать")
    parts.append(f"zoompan=z='{zexpr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                 f":d=1:fps={fps}:s={zp_w}x{zp_h}")
    if (zp_w, zp_h) != (out_w, out_h):
        parts.append(f"scale={out_w}:{out_h}:flags=lanczos")
    return ",".join(parts), {
        "окно": f"{win_w}x{win_h}", "запас разрешения": f"{headroom:.3f}x",
        "зум": f"{z0} -> {z1}", "апскейл входа": f"{up}x",
        "растяжение на пике": f"{upscale_at_peak:.3f}x (потолок {max_upscale})",
        "ход окна": f"{travel:.3f} px/кадр (порог {MIN_TRAVEL_PX_PER_FRAME})",
        "выход zoompan": f"{zp_w}x{zp_h}" + ("" if (zp_w, zp_h) == (out_w, out_h)
                                             else f" -> {out_w}x{out_h} lanczos"),
        "суперсэмплинг выхода": f"{ss}x",
        "кадров": frames}


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--mode", choices=MODES, default="in")   # J.4, слепой совет 04.09
    a.add_argument("--seconds", type=float, default=30.0)
    a.add_argument("--fps", type=int, default=30)
    a.add_argument("--master", default="2160x2528")
    a.add_argument("--out", default="1440x2560")
    a.add_argument("--ss", type=float, default=2.0,
                   help="суперсэмплинг выхода zoompan, потом lanczos вниз (J.2a)")
    a.add_argument("--max-upscale", type=float, default=None,
                   help="потолок растяжения на пике зума, только для замеров")
    n = a.parse_args()
    mw, mh = map(int, n.master.split("x"))
    ow, oh = map(int, n.out.split("x"))
    filt, info = build(n.mode, n.seconds, n.fps, mw, mh, ow, oh, n.ss, n.max_upscale)
    for k, v in info.items():
        print(f"  {k:22s} {v}")
    print("\n" + filt)

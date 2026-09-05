#!/bin/bash
# Хвост-2: лаунчер (8189) упал -> всё на 8188 (видит его модели). Описания -> кит и Давид -> повтор H3-шаблонов -> сводка
LOG=/d/PixelPolish/lab/2026-09-06/night.log; exec >>"$LOG" 2>&1
export COMFY_API=http://127.0.0.1:8188 COMFY_INPUT="C:/Users/RobotComp/pixelpolish/ComfyUI/input" COMFY_OUTPUT="C:/Users/RobotComp/pixelpolish/ComfyUI/output"
echo "=== хвост-2 на 8188 $(date +%T)"
cd /c/pixelpolish/niches
for v in /d/PixelPolish/assets/ref_clips/*.mp4; do s=$(basename "$v" .mp4); [ -f "/d/PixelPolish/assets/descr/$s.txt" ] || { echo "--- описание $s"; PYTHONUTF8=1 python describe_video.py "$v" 2>&1 | grep -v Warn | head -2; }; done
echo "=== кит и Давид $(date +%T)"
PYTHONUTF8=1 python h3_story.py scen_whale.json 5 2>&1 | grep -v Warn | tail -2
PYTHONUTF8=1 python h3_story.py scen_david.json 5 2>&1 | grep -v Warn | tail -2
ffmpeg -v error -y -i "D:/PixelPolish/ШОРТСЫ/h3_whale_evolution.mp4" -c:v libx264 -crf 23 -c:a copy "D:/PixelPolish/ШОРТСЫ/h3_whale_evolution_web.mp4"
cd /c/pixelpolish/lab
for t in video_minimax_h3_t2v video_minimax_h3_i2v video_minimax_h3_i2v_continuation; do echo "--- повтор $t $(date +%T)"; PYTHONUTF8=1 timeout 3600 python run_template.py "$t" --turbo 2>&1 | grep -v Warn | tail -2; done
PYTHONUTF8=1 python contact_sheet.py 2>&1 | tail -1
echo "=== ХВОСТ-2 ГОТОВ $(date +%T)"

#!/bin/bash
# Хвост ночи: после night.sh — повтор упавших шаблонов (исправленный конвертер), дописать 6 эталонов, пересобрать сводку
LOG=/d/PixelPolish/lab/2026-09-06/night.log; exec >>"$LOG" 2>&1
until grep -q "=== ГОТОВО" "$LOG"; do sleep 60; done
echo "=== хвост $(date +%T)"
cd /c/pixelpolish/lab
for d in /d/PixelPolish/lab/2026-09-06/*/; do t=$(basename "$d"); [ -f "$d/result.json" ] && grep -q '"ok": false' "$d/result.json" && { echo "--- повтор $t $(date +%T)"; PYTHONUTF8=1 timeout 3600 python run_template.py "$t" --turbo 2>&1 | grep -v Warn | tail -2; }; done
cd /c/pixelpolish/niches
for v in /d/PixelPolish/assets/ref_clips/*.mp4; do s=$(basename "$v" .mp4); [ -f "/d/PixelPolish/assets/descr/$s.txt" ] || { echo "--- описание $s"; PYTHONUTF8=1 python describe_video.py "$v" 2>&1 | grep -v Warn | head -2; }; done
cd /c/pixelpolish/lab && PYTHONUTF8=1 python contact_sheet.py 2>&1 | tail -1
echo "=== ВСЁ ГОТОВО $(date +%T)"

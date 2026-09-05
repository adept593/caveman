#!/bin/bash
# Ночная цепочка 06.09: ждём разбор эталонов -> прогон шаблонов (8188, видит обе папки моделей) -> кит и Давид (Wan i2v, лаунчер) -> сводка
LOG=/d/PixelPolish/lab/2026-09-06/night.log; exec >>"$LOG" 2>&1
echo "=== старт $(date +%T)"
until [ "$(grep -c 'с ->' /d/PixelPolish/assets/descr/_run.log 2>/dev/null)" -ge 12 ] || ! pgrep -f describe_video >/dev/null 2>&1; do sleep 20; done
echo "=== эталоны описаны $(date +%T)"
cd /c/pixelpolish/lab
for t in image_sdxl_simple basic_image_color_adjustment basic_mask_operations_and_compositing basic_datatype_conversion utility_image_stitch \
         utility_interpolation_image_upscale llm_qwen3vl_text_gen audio_minimax_music_3 templates-6-key-frames \
         video_minimax_h3_t2v video_minimax_h3_i2v video_minimax_h3_i2v_continuation video_wan2_2_14B_i2v video_wan2_2_14B_flf2v; do
  echo "--- $t $(date +%T)"
  PYTHONUTF8=1 timeout 3600 python run_template.py "$t" --turbo 2>&1 | grep -v Warn | tail -3
done
echo "=== шаблоны готовы $(date +%T); кит и Давид"
cd /c/pixelpolish/niches
PYTHONUTF8=1 python h3_story.py scen_whale.json 5 2>&1 | grep -v Warn | tail -2
PYTHONUTF8=1 python h3_story.py scen_david.json 5 2>&1 | grep -v Warn | tail -2
ffmpeg -v error -y -i "D:/PixelPolish/ШОРТСЫ/h3_whale_evolution.mp4" -c:v libx264 -crf 23 -c:a copy "D:/PixelPolish/ШОРТСЫ/h3_whale_evolution_web.mp4"
cd /c/pixelpolish/lab && PYTHONUTF8=1 python contact_sheet.py 2>&1 | tail -2
echo "=== ГОТОВО $(date +%T)"

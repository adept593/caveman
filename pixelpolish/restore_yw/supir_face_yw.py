# -*- coding: utf-8 -*-
"""SUPIR по GFPGAN-лицу youngwoman1855: тот же человек (GFPGAN держит черты) + настоящая
кожа и волосы (SUPIR — реставратор с верностью входу, не генератор). Граф собран по
/object_info нод ComfyUI-SUPIR. Запуск: python supir_face_yw.py [seed] [restore_cfg]"""
import json, sys, time, os, shutil, urllib.request, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
API="http://127.0.0.1:8188"; CIN=r"C:\Users\RobotComp\pixelpolish\ComfyUI\input"; COUT=r"C:\Users\RobotComp\pixelpolish\ComfyUI\output"
seed=int(sys.argv[1]) if len(sys.argv)>1 else 7; rcfg=float(sys.argv[2]) if len(sys.argv)>2 else 3.0
src=r"D:\PixelPolish\plates\layers_yw\face_gfpgan_w05.png"; shutil.copyfile(src, os.path.join(CIN,"supir_in_face.png"))
POS=("sharp photograph of a young woman, studio portrait, real human skin with visible pores and fine texture, no smoothing, "
     "sharp clear eyes, individual hair strands, soft even frontal light, fine film grain, high quality, detailed")
NEG="painting, illustration, cartoon, 3d render, plastic skin, airbrushed, blurry, deformed, extra fingers, text, watermark"
g={
 "2":{"class_type":"SUPIR_model_loader","inputs":{"supir_model":"SUPIR-v0Q_fp16.safetensors","sdxl_model":"sd_xl_base_1.0.safetensors",
       "fp8_unet":False,"diffusion_dtype":"fp16"}},
 "3":{"class_type":"LoadImage","inputs":{"image":"supir_in_face.png"}},
 "4":{"class_type":"SUPIR_first_stage","inputs":{"SUPIR_VAE":["2",1],"image":["3",0],"use_tiled_vae":True,
       "encoder_tile_size":512,"decoder_tile_size":512,"encoder_dtype":"auto"}},
 "5":{"class_type":"SUPIR_encode","inputs":{"SUPIR_VAE":["4",0],"image":["4",1],"use_tiled_vae":True,"encoder_tile_size":512,"encoder_dtype":"auto"}},
 "6":{"class_type":"SUPIR_conditioner","inputs":{"SUPIR_model":["2",0],"latents":["5",0],"positive_prompt":POS,"negative_prompt":NEG,"captions":""}},
 "7":{"class_type":"SUPIR_sample","inputs":{"SUPIR_model":["2",0],"latents":["5",0],"positive":["6",0],"negative":["6",1],
       "seed":seed,"steps":40,"cfg_scale_start":5.0,"cfg_scale_end":3.0,"EDM_s_churn":0,"s_noise":1.003,"DPMPP_eta":1.0,
       "control_scale_start":1.0,"control_scale_end":1.0,"restore_cfg":rcfg,"keep_model_loaded":False,
       "sampler":"TiledRestoreEDMSampler","sampler_tile_size":1536,"sampler_tile_stride":768}},
 "8":{"class_type":"SUPIR_decode","inputs":{"SUPIR_VAE":["4",0],"latents":["7",0],"use_tiled_vae":True,"decoder_tile_size":512,"decoder_dtype":"auto"}},
 "9":{"class_type":"SaveImage","inputs":{"images":["8",0],"filename_prefix":"supir_face_yw"}},
}
req=urllib.request.Request(API+"/prompt",data=json.dumps({"prompt":g}).encode(),headers={"Content-Type":"application/json"})
try: pid=json.load(urllib.request.urlopen(req,timeout=120))["prompt_id"]
except urllib.error.HTTPError as e: print("ОТКАЗ ComfyUI:", e.read().decode()[:1500]); sys.exit(1)
print("queued", pid, "seed", seed, "restore_cfg", rcfg, flush=True); t0=time.time()
while True:
    h=json.load(urllib.request.urlopen(f"{API}/history/{pid}",timeout=60))
    if pid in h:
        st=h[pid]["status"]
        if st.get("completed"): break
        if st.get("status_str")=="error": print("ОШИБКА:", json.dumps(st,ensure_ascii=False)[:2000]); sys.exit(2)
    time.sleep(5)
img=h[pid]["outputs"]["9"]["images"][0]; dest=r"D:\PixelPolish\plates\layers_yw\face_supir_s%d_r%g.png"%(seed,rcfg)
shutil.copyfile(os.path.join(COUT,img.get("subfolder",""),img["filename"]),dest)
print("SUPIR done %.1fs -> %s"%(time.time()-t0,dest))

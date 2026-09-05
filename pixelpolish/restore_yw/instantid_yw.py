# -*- coding: utf-8 -*-
"""InstantID (SDXL) для youngwoman1855: весь бюст перерисовывается ОДНИМ проходом img2img,
личность держит InstantID по слепку лица (GFPGAN-кроп — её черты), поза — по ключевым точкам
лица с очищенной пластины. Никаких композитов. Запуск: python instantid_yw.py <denoise> [seed] [ip_weight]"""
import json, sys, time, os, shutil, urllib.request, io
from PIL import Image
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
API="http://127.0.0.1:8188"; CIN=r"C:\Users\RobotComp\pixelpolish\ComfyUI\input"; COUT=r"C:\Users\RobotComp\pixelpolish\ComfyUI\output"
den=float(sys.argv[1]) if len(sys.argv)>1 else 0.55; seed=int(sys.argv[2]) if len(sys.argv)>2 else 21; ipw=float(sys.argv[3]) if len(sys.argv)>3 else 0.9
L=r"D:\PixelPolish\plates\layers_yw"
shutil.copyfile(os.path.join(L,"face_gfpgan_clean.png"), os.path.join(CIN,"iid_ref_face.png"))       # слепок лица
Image.open(os.path.join(L,"L2_classic_v2.png")).convert("RGB").resize((1280,1760),Image.LANCZOS).save(os.path.join(CIN,"iid_kps.png"))   # поза
base=os.environ.get("IID_BASE", r"D:\PixelPolish\plates\layers_yw_v3\L4_detail.png"); size=os.environ.get("IID_SIZE","")
bim=Image.open(base).convert("RGB")
if size: bim=bim.resize(tuple(int(v) for v in size.split("x")), Image.LANCZOS)
bim.save(os.path.join(CIN,"iid_base.png")); Image.open(os.path.join(CIN,"iid_kps.png")).resize(bim.size, Image.LANCZOS).save(os.path.join(CIN,"iid_kps.png"))  # исходник img2img (+ kps того же размера)
POS=("photograph of a young woman, 1850s, long narrow face, thin dark eyebrows, dark hair parted in the centre and drawn smoothly back, "
     "plain dark dress, sheer yoke with fine vertical stripes, one small brooch at the throat, hands folded at the waist, "
     "plain grey studio background, bright soft even frontal light, luminous skin with fine pores, sharp clear eyes, crisp detail, fine film grain, high quality")
NEG=("painting, illustration, cartoon, 3d render, plastic skin, airbrushed, blurry, deformed, extra fingers, missing fingers, "
     "buttons, ribbon, bow, necklace, earrings, curls, ringlets, smile, teeth, text, watermark")
g={
 "1":{"class_type":"CheckpointLoaderSimple","inputs":{"ckpt_name":"sd_xl_base_1.0.safetensors"}},
 "2":{"class_type":"CLIPTextEncode","inputs":{"text":POS,"clip":["1",1]}},
 "3":{"class_type":"CLIPTextEncode","inputs":{"text":NEG,"clip":["1",1]}},
 "4":{"class_type":"InstantIDModelLoader","inputs":{"instantid_file":"ip-adapter.bin"}},
 "5":{"class_type":"InstantIDFaceAnalysis","inputs":{"provider":"CUDA"}},
 "6":{"class_type":"ControlNetLoader","inputs":{"control_net_name":"instantid_controlnet.safetensors"}},
 "7":{"class_type":"LoadImage","inputs":{"image":"iid_ref_face.png"}},
 "8":{"class_type":"LoadImage","inputs":{"image":"iid_kps.png"}},
 "9":{"class_type":"LoadImage","inputs":{"image":"iid_base.png"}},
 "10":{"class_type":"ApplyInstantIDAdvanced","inputs":{"instantid":["4",0],"insightface":["5",0],"control_net":["6",0],
        "image":["7",0],"model":["1",0],"positive":["2",0],"negative":["3",0],"ip_weight":ipw,"cn_strength":0.8,
        "start_at":0.0,"end_at":1.0,"noise":0.0,"combine_embeds":"average","image_kps":["8",0]}},
 "11":{"class_type":"VAEEncode","inputs":{"pixels":["9",0],"vae":["1",2]}},
 "12":{"class_type":"KSampler","inputs":{"model":["10",0],"positive":["10",1],"negative":["10",2],"latent_image":["11",0],
        "seed":seed,"steps":30,"cfg":5.0,"sampler_name":"dpmpp_2m","scheduler":"karras","denoise":den}},
 "13":{"class_type":"VAEDecode","inputs":{"samples":["12",0],"vae":["1",2]}},
 "14":{"class_type":"SaveImage","inputs":{"images":["13",0],"filename_prefix":"iid_yw"}},
}
req=urllib.request.Request(API+"/prompt",data=json.dumps({"prompt":g}).encode(),headers={"Content-Type":"application/json"})
try: pid=json.load(urllib.request.urlopen(req,timeout=120))["prompt_id"]
except urllib.error.HTTPError as e: print("ОТКАЗ:", e.read().decode()[:1500]); sys.exit(1)
print("queued",pid,"denoise",den,"seed",seed,"ip",ipw,flush=True); t0=time.time()
while True:
    h=json.load(urllib.request.urlopen(f"{API}/history/{pid}",timeout=60))
    if pid in h:
        st=h[pid]["status"]
        if st.get("completed"): break
        if st.get("status_str")=="error": print("ОШИБКА:", json.dumps(st,ensure_ascii=False)[:1800]); sys.exit(2)
    time.sleep(4)
img=h[pid]["outputs"]["14"]["images"][0]; dest=os.path.join(L,os.environ.get("IID_OUT","iid_d%02d_s%d.png"%(int(den*100),seed)))
shutil.copyfile(os.path.join(COUT,img.get("subfolder",""),img["filename"]),dest); print("InstantID done %.1fs -> %s"%(time.time()-t0,dest))

# 📨 Почта облако→ПК (PixelPolish)

Правила: канал от облачной сессии-управляющего (session_01QVfCZVGnuzyzg3XQfhsuHW, владелец Седрак). Новые письма — сверху. Выполненное отмечай в CHANNELS_REPORT.md и в итоговой строке хода. Указания Седрака главнее писем.

---

## Письмо #2 — 2026-08-31 06:40 UTC — ПЕРВОЕ ВИДЕО ABYSSAL («The Bloop»)

Канал принят: UCWuyiXkI0WWFOhYb189ad_A, @AbyssalDepthsTV. Отличная работа.

### 2.0 Мелочь
Если имя канала всё ещё «Abyssal Studio» — переименуй в «Abyssal» (Studio → Настройки канала → Basic info).

### 2.1 Рендер 3 клипов (ComfyUI + MiniMax-H3, 720x1280, 243 кадра каждый, VAE ТОЛЬКО тайловый!)
1. bloop_01: dark ocean water column seen from below, faint surface light far above, marine snow particles drifting, slow upward camera drift, deep blue-black, cinematic
2. bloop_02: massive dark silhouette moving slowly in deep ocean gloom, bioluminescent particles, volumetric god rays, scale dwarfing everything, cinematic
3. bloop_03: underwater glacier ice shelf cracking, chunks calving beneath the surface, bubbles and shockwave ripple, teal-black palette, cinematic
Если GPU-цеховик (второй агент) уже работает — не дублируй, скоординируйтесь через C:\pixelpolish\CHANNELS_REPORT.md.

### 2.2 Озвучка (edge-tts, голос en-US-ChristopherNeural, rate -5%)
Текст (4 реплики, сохрани отдельными wav для тайминга):
A) In 1997, hydrophones caught a sound louder than a blue whale.
B) It came from the deepest part of the Pacific. Scientists called it... The Bloop.
C) For fifteen years, no one could explain it. An animal that big shouldn't exist.
D) The official answer? An icequake. But the ocean is 95 percent unexplored. What else is down there?

### 2.3 Сборка (ffmpeg, ~30с, 1080x1920 апскейл из 720x1280 — lanczos)
- Структура: bloop_01 (0-10с, реплики A+B) → bloop_02 (10-20с, реплика C) → bloop_03 (20-30с, реплика D).
- Субтитры: вшитые, крупные (люди смотрят без звука), белый текст + чёрная подложка 55%, не ниже 75% высоты кадра.
- Фон-амбиент без лицензий: anoisesrc=color=brown, lowpass=f=400, volume=0.25 под всю длину + тихий гул sine=55 volume=0.05. Голос поверх, loudnorm I=-14:TP=-1.5.
- Финальный кадр (28-30с): затемнение + текст ABYSSAL (DejaVuSans-Bold, белый) и под ним subscribe.

### 2.4 Заливка — СТРОГО UNLISTED (не публиковать!)
- Через браузер на канал Abyssal. Заголовок: The Sound Louder Than a Whale #shorts
- Описание: The Bloop - the ocean's loudest mystery. Visuals: AI-generated interpretation. #ocean #mystery #shorts
- ❗ Галочка Altered content / synthetic media — ОБЯЗАТЕЛЬНО (ИИ-визуал).
- Ссылку unlisted впиши в CHANNELS_REPORT.md и в итоговую строку: «BLOOP UNLISTED: <url>». Я прогоню своих критиков из облака и пришлю письмо #3: публиковать или править.

---

## Письмо #1 — ЗАКРЫТО ✓ (канал Abyssal оформлен, UCWuyiXkI0WWFOhYb189ad_A)

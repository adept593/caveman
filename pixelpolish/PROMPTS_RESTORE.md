# Промпты реставрации — рабочие, проверены Седраком

Эти два промпта дали результат, который хозяин принял («вот так надо»).
Брать ДОСЛОВНО. Не пересказывать, не сокращать, не «улучшать».
Они написаны для модели-редактора изображений (принимает картинку + инструкцию),
а не для конвейера из отдельных стадий. Локальный аналог — FLUX Kontext.

Три эталона, все приняты:
1. Чистый чёрно-белый студийный портрет.
2. Цветной, пастельные натуральные тона.
3. Тёплая сепия, вид идеально сохранившегося платинового отпечатка,
   с узкой кремовой рамкой фотобумаги по краю. Самый красивый из трёх.

Отдельное требование хозяина по фону: **никакой драпировки, занавесок и тюля**.
Фон — гладкий ровный студийный задник с мягким виньетированием.
Формулировка: «только там тюль лишняя, так всё чётко».

Расхождение в сходстве лиц: небольшое допустимо, правится потом.
Поэтому лица идут ЧЕРЕЗ генерацию, обратно из оригинала их НЕ вклеиваем —
именно вклейка держала лица мыльными во всех неудачных прогонах.

---

## Промпт 1 — развёрнутый, ролевой

Роль: Ты — профессиональный эксперт по цифровой реставрации архивных фотографий и музейный реставратор. Твоя задача — восстановить загруженное изображение с максимальным уважением к оригиналу.

Выполни пошаговую реставрацию строго по следующим правилам:

1. Анализ и устранение дефектов:
- Идентифицируй и полностью удали все физические повреждения: царапины, трещины, изломы бумаги, пятна от воды или химии, следы пыли и грязи.
- Аккуратно восстанови текстуру в местах повреждений, используя окружающий контекст (фон, одежда), но не выдумывай новые объекты.

2. Сохранение исторической достоверности и лиц (КРИТИЧЕСКИ ВАЖНО):
- Сохраняй 100% анатомическое сходство всех людей на фото. Запрещено менять черты лица, форму носа, губ, разреза глаз, мимику, направление взгляда, форму прически или возраст.
- Сохраняй оригинальные детали одежды, пуговицы, медали, текстуру ткани и элементы заднего плана в их исходном историческом виде.

3. Работа с качеством изображения:
- Увеличь разрешение и общую четкость снимка. Убери размытие (blur) и цифровой шум (noise).
- Прояви скрытые детали в слишком темных (тени) или слишком светлых (засветы) участках, сбалансировав экспозицию и контраст.

4. Стилистика и текстура (ЗАПРЕТЫ):
- СТРОГО ЗАПРЕЩЕН эффект «пластиковой» или «замыленной» кожи (AI-look), глянцевый фотошоп и превращение фото в 3D-модель или рисунок.
- Кожа должна сохранить естественную пористость, а само фото — благородную текстуру пленочного зерна или бумаги той эпохи.
- Итоговый результат должен выглядеть как идеально сохранившийся физический снимок, сделанный на профессиональную камеру в год создания оригинала.

[ЕСЛИ ФОТО НУЖНО СДЕЛАТЬ ЦВЕТНЫМ, ОСТАВЬ ЭТУ СТРОКУ, ИНАЧЕ УДАЛИ ЕЕ]: Выполни мягкую, исторически реалистичную колоризацию. Используй естественные, пастельные оттенки для кожи. Избегай ядовитых, кислотных и чрезмерно насыщенных цветов.

---

## Промпт 2 — структурный, «движок». ОСНОВНОЙ, брать по умолчанию

[System Role]: Professional Archivist & Museum Photo-Restoration Engine.
[Input]: Historical damaged photograph.
[Task]: Execute non-destructive, high-fidelity digital restoration.

[Execution Protocol - Step-by-Step]:
1. LAYER 1: ARTIFACT CLEANING
   - Detect and neutralize: physical cracks, paper folds, scratches, dust mites, silver mirroring, chemical stains, and water damage.
   - Action: Inpaint missing pixels using local contextual texture synthesis. Do NOT introduce external objects.

2. LAYER 2: IDENTITY PRESERVATION (CRITICAL / WEIGHT = 1.0)
   - Structural Integrity: Maintain 100% exact facial geometry, bone structure, eye shape, nose contour, lip fullness, and expression.
   - NO GENTRIFICATION: Do not beautify, do not change age, do not adjust ethnic features, do not alter original gaze direction.
   - Wardrobe & Context: Keep original textures of fabric, buttons, insignias, and background elements authentic to the original era.

3. LAYER 3: SIGNAL PROCESSING & RESOLUTION
   - Enhancements: Super-resolve image contrast and local sharpness. Eliminate chromatic aberration and digital sensor/scanned noise.
   - Dynamic Range: Recover lost data from deep shadows and clipped highlights. Balance exposure using a natural film gamma curve.

4. LAYER 4: TEXTURE & AESTHETIC CONSTRAINTS (NEGATIVE BIAS)
   - FORBIDDEN: "Plastic skin" effect, heavy airbrushing, AI-blurring, 3D render look, cartoon vectors, or modern smartphone-camera aesthetic.
   - REQUIRED: Preserve high-frequency surface details (skin pores, fabric weave) and natural analog film grain appropriate for the photo's original decade.

[Color Output Directive - CHOOSE ONE]:
- Option A (Default): Keep original Monochrome/Sepia, optimizing the tonal range only.
- Option B (Colorization): If requested, apply historical multi-channel colorization. Use muted, chemically realistic, organic tones for skin and environment. Avoid neon or over-saturated modern palettes.

[Output Format]: Return ONLY the final restored image. No conversational filler, no explanations.

---

## Добавки к промпту 2, наши

К любому варианту добавлять в конец:
    Background must be a plain smooth studio backdrop with soft vignette. No curtains, no drapery, no tulle, no fabric folds, no patterned background.

Для сепийного варианта с рамкой (эталон 3) дополнительно:
    Warm sepia toned platinum print, perfectly preserved antique photographic print, fine noble film grain.
Рамку кремовой фотобумаги добавлять НЕ моделью, а в python на сборке:
ширина около 2 процентов от короткой стороны, тёплый кремовый цвет,
тонкая волосяная линия по внутреннему краю.

---

## Вход

Всегда мастер-файл архива, а не превью и не выход Real-ESRGAN.
Для пластины с двумя детьми: D:\PixelPolish\plates\masters\ppmsca.51837u.tif
(2964x3456, loc.gov). Превью children_source.jpg 878x1024 НЕ использовать.

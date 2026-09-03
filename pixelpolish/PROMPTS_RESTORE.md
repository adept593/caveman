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

---

## Промпт 3 — доработанный. С 03.09 брать ЕГО по умолчанию

Что изменено против промпта 2 и почему:
1. Убрана строка «Maintain 100% exact facial geometry». В наших пластинах
   лица не разрешены физически (lapvar 82 на боксе 508x635), и требование
   стопроцентной точности приказывает модели скопировать размытие. Разделены
   два разных требования: ЛИЧНОСТЬ не менять, мелкую ФАКТУРУ обязательно
   синтезировать.
2. Добавлено описание того, ЧТО на входе — пластина середины XIX века с
   потемнением серебра. Анкер по эпохе и тональности.
3. Композиция вынесена в отдельный запертый блок: кадр, поза, руки,
   предметы, мебель, количество людей.
4. Отдельный пункт про руки — классическое место поломки.
5. Убран анахронизм: у дагеротипа нет плёночного зерна. Просим микрофактуру
   отпечатка эпохи, а не 35 мм зерно.
6. Директива цвета теперь ОДНА строка на прогон, а не меню из двух опций.
   Меню заставляло модель хеджировать и выдавать нечто между сепией и цветом.
7. Требование гладкого фона без драпировки внесено в промпт.
8. Приоритет повторён в конце — внимание модели к концу промпта падает.

### Текст (брать дословно)

[ROLE] Museum photo-restoration engine. Input: one damaged historical photograph. Output: one restored image and nothing else.

[SOURCE] A mid-19th-century cased photographic plate (daguerreotype or ambrotype). Expect tarnish haloes, silver mirroring, chemical staining, dust, paper and case decay, and very low resolved detail in the faces, because the optics and process of that era could not record fine skin texture.

[1. IDENTITY - HIGHEST PRIORITY]
Every person must remain the same individual. Preserve facial proportions and landmark positions: eye spacing and shape, nose length and width, mouth width, lip fullness, jaw line, hairline shape, apparent age, gaze direction and expression.
Fine detail that the degraded original cannot resolve - skin pores, eyelashes, individual hair strands, lip texture - must be SYNTHESIZED plausibly, not copied from the blur. Synthesizing that texture is required. Changing identity is forbidden.
Do not beautify, slim, symmetrize, whiten, or age-shift anyone. Do not alter ethnic features.

[2. COMPOSITION - LOCKED]
Same crop and aspect ratio. Same number of people. Same poses, same hand and finger positions, same held objects, same furniture, same spatial relationships and headroom. Add nothing, remove nothing, move nothing.

[3. HANDS]
Correct anatomy, five fingers per hand, natural articulation, exactly the original placement and grip. No fused, extra, or missing fingers.

[4. DAMAGE REMOVAL]
Remove cracks, folds, scratches, dust, silver mirroring, chemical and water stains, mould, and edge decay. Rebuild covered areas from surrounding context only. Introduce no new objects, patterns, jewellery, or background elements.

[5. BACKGROUND]
Plain smooth studio backdrop, warm neutral grey-beige, soft vignette. No curtains, no drapery, no tulle, no lace, no fabric folds, no patterned or busy background.

[6. OPTICS AND TONE]
Render as a large-format view-camera portrait: even soft frontal light, gentle falloff, natural depth, no HDR, no glow halos, no clarity or structure over-processing. Recover shadow and highlight detail on a natural film gamma curve.
Surface micro-texture appropriate to a fine photographic print of that period. NOT 35mm film grain. NOT digital noise.

[7. FORBIDDEN]
Plastic or waxy skin, airbrushing, AI smoothing, over-sharpening halos, 3D render or illustration look, modern smartphone HDR aesthetic, teeth or eye whitening, added make-up, catchlights that were not in the original.

[8. OUTPUT]
Maximum resolution. Return only the final image, with no text and no explanation.

[COLOR] Use exactly ONE of these lines per run, never both:
A) Keep monochrome. Warm sepia-platinum tone. Optimize tonal range only.
B) Colorize with muted, chemically plausible period tones: natural pastel skin, desaturated dyes typical of the 1850s. No neon, no oversaturation, no magenta cast.

[REMINDER] Identity and composition outrank everything above. If more detail and the same person ever conflict, choose the same person.

---

## Рабочие настройки Kontext, проверены 03.09.2026

Полный рецепт с графом нод и таймингами — в pixelpolish/REPORT_KONTEXT_4K.md.
Коротко, что нельзя забыть:

РАЗМЕР. Длинная сторона 1760, короткая = 1760 × (W/H мастера), округлить вниз
до кратного 16. Для нашей пластины это 1504x1760.
  Ниже 1216 — модель перекадрирует и игнорирует директиву цвета.
  Выше 1760 — ТИХОЕ ВЫРОЖДЕНИЕ: ошибки нет, картинка есть, но она равна входу.
  Ловится только глазами, по коду возврата не видно. Проверять каждую пластину.

НОДА. FluxKontextImageScale НЕ ИСПОЛЬЗОВАТЬ — она молча ужимает вход к ~1 МП
и выдаёт 944x1104. Ставить ImageScale с явным размером, lanczos, crop disabled.
Именно эта нода держала нас на низком разрешении.

ПАРАМЕТРЫ: steps 28, cfg 1.0, euler, simple, denoise 1.0, FluxGuidance 2.5.
Негатива у Kontext нет — ConditioningZeroOut от того же позитива.

АПСКЕЙЛ: 4x-UltraSharp без генерации (ни KSampler, ни denoise, ни ControlNet),
затем LANCZOS вниз до короткой стороны 2160. Итог 2160x2528.
Артефактов не вносит: сетка и ореолы отсутствуют, проверено метриками.

ЦВЕТ ДЕЛАТЬ ИЗ ГОТОВОГО МОНО, а не вторым независимым прогоном.
Два прогона с разными сидами дают РАЗНЫХ ЛЮДЕЙ — у старшей девочки в цветной
версии оказалось другое лицо. Это ошибка, которую мы допустили 03.09.

ВРЕМЯ: около 7.8 минут на пластину в двух вариантах.

ЧЕСТНОСТЬ В ПОДПИСЯХ. Если мастер сильно выцвел, лица на выходе — СИНТЕЗ,
а не восстановление: совпадают геометрия головы, поза, причёска и одежда,
а разрез глаз, нос, губы и мимика придуманы моделью. В заголовках и описаниях
роликов по таким пластинам НЕЛЬЗЯ писать «вот как они выглядели на самом деле».
Проверять этот пункт на каждой пластине и отмечать в meta.json.

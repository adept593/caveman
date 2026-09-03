# REPORT_KONTEXT_4K.md — Kontext в полном разрешении + апскейл до 4K

Дата прогона: 2026-09-03. Машина RobotComp: RTX 5070 Ti 16 GB, RAM 64 GB, ComfyUI 0.34.0, torch 2.13.0+cu130.
Тестовая пластина: `D:\PixelPolish\plates\masters\ppmsca.51837u.tif`, 2964x3456, дагеротип в золочёной оправе, двое детей, выцвел почти до нечитаемости.

---

## 1. Максимальное разрешение Kontext

**Два разных потолка, их нельзя путать.**

* **Потолок по ошибке / OOM: не достигнут.** Самый большой прогон — **2224x2592 (5,76 МП), 581,8 с, ошибки нет.** В OOM упереться не вышло: ComfyUI при нехватке VRAM выгружает модель в системную RAM (64 GB), так что реальное ограничение не память, а время. Фолбэк `VAEEncodeTiled`/`VAEDecodeTiled` (tile 512, overlap 64) заведён в скрипте, но **ни разу не сработал** — все прогоны прошли `tiled=false`. Ни одного падения по памяти в логах нет: `kx_big.out`, `kx_big2.out` чистые, `.err`-файлы нулевой длины.
* **Потолок по качеству: 1504x1760.** Выше него ошибки по-прежнему нет, но начинается **тихое вырождение** — реставрация не происходит, выцветший мастер проходит насквозь почти без изменений. Ловится только глазами, код возврата чистый.

Лесенка (тот же промпт, те же настройки, аспект мастера 0,8576, ширина кратна 16):

| Размер | Время | Ошибка | Результат |
|---|---|---|---|
| 880x1024 | 40,2 с | нет | перекадрировал (зум в детей), срезал оправу, самовольно раскрасил вопреки моно-директиве |
| 1040x1216 | 55,2 с | нет | то же самое |
| 1312x1536 | 105,2 с | нет | годно: оправа на месте, повреждения сняты |
| **1504x1760** | **160,4 с** | **нет** | **ЛУЧШЕЕ. Рабочий размер.** |
| 1696x1984 | 230,6 с | нет | вырождение — выход ≈ вход |
| 1936x2256 | 361,2 с | нет | вырождение |
| 2224x2592 | 581,8 с | нет | вырождение |

Причина потолка: Kontext тренирован около 1 МП. Выше ~1,8x от тренировочного разрешения модель перестаёт реставрировать и копирует вход. Гнать выше 1760 по длинной стороне — потерянное время.

**Правило для следующих пластин:** длинная сторона 1760, короткая = 1760 × (W/H мастера), округлить вниз до кратного 16.

Отдельно: нода `FluxKontextImageScale` снапит вход к «предпочтительным» разрешениям Kontext ≈1 МП и выдаёт 944x1104 — именно она резала размер в прошлых прогонах. Заменена на `ImageScale` с явным размером.

---

## 2. Время на кадр по размерам

| Этап | Время |
|---|---|
| Kontext 880x1024 | 40,2 с |
| Kontext 1040x1216 | 55,2 с |
| Kontext 1312x1536 | 105,2 с |
| Kontext 1504x1760 моно | 160,4 с (2,7 мин) |
| Kontext 1504x1760 цвет | 165,3 с (2,8 мин) |
| Kontext 1696x1984 | 230,6 с (3,8 мин) |
| Kontext 1936x2256 | 361,2 с (6,0 мин) |
| Kontext 2224x2592 | 581,8 с (9,7 мин) |
| 4x-UltraSharp моно (с загрузкой модели) | 126,0 с |
| 4x-UltraSharp цвет (модель уже в памяти) | 15,7 с |

**Итого на пластину (моно + цвет, оба доведены до 4K): ~7,8 мин.**
На один вариант: ~4,8 мин моно (несёт на себе загрузку апскейлера) / ~3,0 мин цвет.

---

## 3. До какого размера довели и какой моделью

```
Kontext 1504x1760
  -> 4x-UltraSharp.pth (ImageUpscaleWithModel, ESRGAN) -> 6016x7040
  -> PIL LANCZOS даунсэмпл                             -> 2160x2528
```

Апскейл **без генерации**: ни KSampler, ни denoise, ни ControlNet, ни tile-диффузии. Один проход ESRGAN + один чистый LANCZOS-даунсэмпл. Деталь уже была в кадре — генерация на этом шаге только портит.

Итог 2160x2528 = 5,46 МП против 1,59 МП у выхода Kontext: **рост в 3,4 раза по пикселям.**

---

## 4. Артефакты: смотрел глазами кропы 1:1

**Сетки ESRGAN нет.** Ни шахматки, ни регулярного паттерна на плоских участках. Подтверждено численно (`kx_final_metrics.json`): grid_energy лица 0,086 против 0,339 у мастера, ткань 0,114 против 0,194. У итога энергия сетки **ниже**, чем у исходного скана.

**Мыла нет.** lap_var лица 43,6 против 13,8 у мастера, ткань 269,2 против 26,2. hf_ratio ткани 0,434 против 0,408 — высокие частоты не срезаны.

**Ореолов по контурам нет.** Смотрел границы «волосы / фон» у обеих фигур, «белый воротничок / тёмное платье», «рука / юбка» — светлой каймы и тёмного контр-контура не видно. У ESRGAN это типовой брак, здесь его не поймал.

Что реально видно на кропах:

* **Ткань — лучший участок.** Клетчатое платье мальчика: переплетение нитей, отдельные клетки, пуговицы с бликом, складки юбки — всё читается на 100%. На мастере на том же месте однородная муть.
* **Кожа мягче ткани.** Лица гладковаты по сравнению с проработкой ткани. Пластика и «3D-рендера» нет, но пор кожи практически нет. Это не апскейл наследил — так рисует Kontext.
* **Остаточная пятнистость фона.** В верхней части кропа лиц фон слегка мраморный — остатки повреждений пластины, которые модель не сняла полностью, а апскейлер честно увеличил. В глаза не бросается, на шортсе видно не будет.
* **Клетка «просвечивает» на юбке мальчика.** В нижней части ткани клетчатый узор местами полупрозрачно наложен на гладкую юбку — Kontext не доразвёл два слоя одежды. Не артефакт апскейла.
* **Оправа дагеротипа сохранена.** Прогон на 944 её срезал; на 1504x1760 золочёный багет и фигурная маска на месте, тиснение по рамке читается.

Вывод по артефактам: **шаг апскейла чистый, брака не внёс.** Всё, что вызывает вопросы, приехало со стадии Kontext.

---

## 5. Лица: те же люди или поехали

**Поехали. Честно — это синтез, а не восстановление.**

Мастер выцвел настолько, что на кропе 1:1 вместо лиц — призрачные силуэты: угадывается овал, линия причёски, тёмное пятно на месте глаз. Черт лица там физически нет, восстанавливать нечего.

Что совпадает: геометрия головы, посадка, поворот, причёска (пробор, локоны у старшей), поза, направление взгляда, силуэт плеч, крой одежды.
Что модель придумала: разрез и цвет глаз, форма носа, губы, брови, мимика — всё, что составляет узнаваемость.

Отдельно: **моно и цвет — не один и тот же человек.** Прогоны шли с разными сидами (101010 / 202020), и у старшей девочки в цветной версии другие локоны и слегка другое лицо, чем в моно. Если нужны согласованные варианты — колоризовать надо из готового моно, а не гнать второй независимый прогон Kontext.

Для канала — годится. Для атрибуции конкретных людей, поиска родственников, любых заявлений «вот как они выглядели» — **не годится**. Проверять этот пункт на каждой пластине.

---

## 6. Годится ли для вертикального шортса 1080x1920

**Да, с запасом.**

Аспект пластины 0,8576, аспект шортса 0,5625. Кадр в шортс целиком не ложится — нужна подложка (размытая копия / тёмный фон) либо пан по кадру.

* По высоте: 2528 px против нужных 1920 — запас 1,3x.
* Если класть по ширине на весь экран: 2160 px против 1080 — запас 2,0x.
* Для пана по вертикали с кропом до 0,5625: из 2160x2528 берётся окно 1422x2528, после ресайза до 1080x1920 остаётся коэффициент 1,3 — пиксель в пиксель, без растягивания.

Разрешения хватает на любой из этих сценариев, включая медленный зум.

---

## 7. Полные пути ко всем итоговым файлам

```
D:\PixelPolish\plates\final\final_mono_4k.png       2160x2528   7 583 809 б   итог моно
D:\PixelPolish\plates\final\final_color_4k.png      2160x2528   7 386 762 б   итог цвет
D:\PixelPolish\plates\final\final_grid.jpg          4184x1310   1 142 688 б   мастер / kontext / апскейл / цвет
D:\PixelPolish\plates\final\final_crop_faces.jpg    1688x930      287 706 б   кроп 1:1 лица
D:\PixelPolish\plates\final\final_crop_fabric.jpg   1688x930      395 901 б   кроп 1:1 ткань
D:\PixelPolish\plates\final\REPORT_TITLE_FINAL.txt                  1 090 б   строка-итог

D:\PixelPolish\plates\redraw\kxbig_mono.png         1504x1760   3 728 408 б   выход Kontext моно
D:\PixelPolish\plates\redraw\kxbig_color.png        1504x1760   3 671 975 б   выход Kontext цвет
D:\PixelPolish\plates\redraw\big_mono_1024.png       880x1024   1 420 812 б   лесенка
D:\PixelPolish\plates\redraw\big_mono_1216.png      1040x1216   1 962 371 б   лесенка
D:\PixelPolish\plates\redraw\big_mono_1536.png      1312x1536   2 827 933 б   лесенка
D:\PixelPolish\plates\redraw\big_mono_1760.png      1504x1760   3 728 408 б   лесенка (= kxbig_mono)
D:\PixelPolish\plates\redraw\big_mono_1984.png      1696x1984   4 242 400 б   лесенка, вырождение
D:\PixelPolish\plates\redraw\big_mono_2256.png      1936x2256   5 380 508 б   лесенка, вырождение
D:\PixelPolish\plates\redraw\big_mono_2592.png      2224x2592   7 009 983 б   лесенка, вырождение
D:\PixelPolish\plates\redraw\big_color.png          1504x1760   3 671 975 б   цвет (= kxbig_color)
D:\PixelPolish\plates\redraw\ladder_faces.jpg                     388 090 б   лица по всей лесенке
D:\PixelPolish\plates\redraw\_cmp_hi_faces.jpg                    206 538 б   сравнение hi-res, лица
D:\PixelPolish\plates\redraw\_cmp_hi_full.jpg                     432 250 б   сравнение hi-res, кадр

D:\PixelPolish\plates\masters\ppmsca.51837u.tif     2964x3456                 мастер

C:\pixelpolish\kx_big.py                  прогон Kontext, лесенка 1024..1760 + финал моно/цвет
C:\pixelpolish\kx_big2.py                 лесенка 1984..2592 (поиск потолка)
C:\pixelpolish\kx_upscale.py              чистый апскейл 4x-UltraSharp + LANCZOS
C:\pixelpolish\kx_final_compose.py        сетка, кропы 1:1, метрики
C:\pixelpolish\kx_ladder_cmp.py           сравнение лиц по лесенке
C:\pixelpolish\kx_prompt.txt              база промпта
C:\pixelpolish\kx_big_results.json        тайминги лесенки 1024..1760
C:\pixelpolish\kx_big2_results.json       тайминги лесенки 1984..2592
C:\pixelpolish\kx_upscale_results.json    тайминги апскейла
C:\pixelpolish\kx_final_metrics.json      метрики резкости и сетки
C:\pixelpolish\kx_big.out, kx_big2.out, kx_up.out      логи прогонов
C:\pixelpolish\RECIPE_KONTEXT.md          рецепт (вставлен ниже целиком)
```

Картинки в репозиторий не кладу — репозиторий публичный, файлы лежат только на D.

---

## 8. Рецепт целиком

### 8.1 Чекпойнт и веса

| Слот | Файл | Нода |
|---|---|---|
| UNET | `flux1-dev-kontext_fp8_scaled.safetensors` (11,9 GB, sha256 `630ba795…b30a2`) | `UNETLoader`, `weight_dtype: default` |
| CLIP 1 | `clip_l.safetensors` | `DualCLIPLoader`, `type: flux` |
| CLIP 2 | `t5xxl_fp8_e4m3fn.safetensors` | `DualCLIPLoader` |
| VAE | `ae.safetensors` | `VAELoader` |
| Апскейлер | `4x-UltraSharp.pth` | `UpscaleModelLoader` |

Веса в `C:\Users\RobotComp\pixelpolish\ComfyUI\models\...` (модели на C, фото на D).

### 8.2 Граф Kontext

```
UNETLoader ─────────────────────────────┐
DualCLIPLoader ── CLIPTextEncode ─┬──── ConditioningZeroOut ──┐
                                  │                            │
VAELoader ──┬── VAEEncode ────────┼── ReferenceLatent ── FluxGuidance ──┐
            │        ▲            │        ▲                            │
LoadImage ──┴─> ImageScale ───────┘        │                            ▼
             (lanczos, 1504x1760)          └────────────────────────> KSampler ── VAEDecode ── SaveImage
```

`FluxKontextImageScale` заменена на `ImageScale` с явным размером — единственное отличие от прошлого прогона, и именно оно сняло ограничение 944x1104.

### 8.3 Параметры (НЕ МЕНЯТЬ — на них получен принятый результат)

```
ImageScale     : upscale_method=lanczos, crop=disabled, width=1504, height=1760
FluxGuidance   : guidance = 2.5
KSampler       : steps=28, cfg=1.0, sampler=euler, scheduler=simple, denoise=1.0
seed           : 101010 (моно) / 202020 (цвет)
negative       : ConditioningZeroOut от того же позитива (у Kontext отдельного негатива нет)
fallback       : VAEEncodeTiled / VAEDecodeTiled, tile 512, overlap 64 — заведён, ни разу не понадобился
```

### 8.4 Промпт

База — `C:\pixelpolish\kx_prompt.txt`:

```
[System Role]: Professional Archivist & Museum Photo-Restoration Engine.
[Input]: Historical damaged photograph.
[Task]: Execute non-destructive, high-fidelity digital restoration.
[Execution Protocol - Step-by-Step]:
1. LAYER 1: ARTIFACT CLEANING
   - Detect and neutralize: physical cracks, paper folds, scratches, dust mites, silver mirroring, chemical stains, and water damage.
   - Action: Inpaint missing pixels using local contextual texture synthesis. Do NOT introduce external objects.
   - Background: render a plain smooth studio backdrop with soft vignette. No curtains, no drapery, no tulle, no lace, no fabric folds.
2. LAYER 2: IDENTITY PRESERVATION (CRITICAL / WEIGHT = 1.0)
   - Structural Integrity: Maintain 100% exact facial geometry, bone structure, eye shape, nose contour, lip fullness, and expression.
   - NO GENTRIFICATION: Do not beautify, do not change age, do not adjust ethnic features, do not alter original gaze direction.
   - Wardrobe & Context: Keep original textures of fabric, buttons, insignias, and background elements authentic to the original era.
   - Hands: preserve exact original placement and grip. Correct anatomy, five fingers per hand, no fused, extra or missing fingers.
3. LAYER 3: SIGNAL PROCESSING & RESOLUTION
   - Enhancements: Super-resolve image contrast and local sharpness. Eliminate chromatic aberration and digital sensor/scanned noise.
   - Dynamic Range: Recover lost data from deep shadows and clipped highlights. Balance exposure using a natural film gamma curve.
4. LAYER 4: TEXTURE & AESTHETIC CONSTRAINTS (NEGATIVE BIAS)
   - FORBIDDEN: "Plastic skin" effect, heavy airbrushing, AI-blurring, 3D render look, cartoon vectors, or modern smartphone-camera aesthetic.
   - REQUIRED: Preserve high-frequency surface details (skin pores, fabric weave) and natural analog film grain appropriate for the photo's original decade.
[Output Format]: Return ONLY the final restored image. No conversational filler, no explanations.
```

К базе снизу подклеивается ОДНА строка.

Моно:
```
[Color Output Directive]: Keep original Monochrome/Sepia, optimizing the tonal range only.
```

Цвет:
```
[Color Output Directive]: Apply historical multi-channel colorization. Use muted, chemically
realistic, organic tones for skin and environment. Avoid neon or over-saturated modern palettes.
```

### 8.5 Апскейл

```
LoadImage ── UpscaleModelLoader(4x-UltraSharp.pth) ── ImageUpscaleWithModel ── SaveImage
             1504x1760 -> 6016x7040
затем PIL LANCZOS: 6016x7040 -> 2160x2528   (короткая сторона = 2160)
```

Скрипт `C:\pixelpolish\kx_upscale.py`. Время: 126 с первый прогон (грузится модель), 15,7 с второй.

### 8.6 Метрики контроля качества

`C:\pixelpolish\kx_final_metrics.json`:

| | мастер | итог | вывод |
|---|---|---|---|
| lap_var лица | 13,8 | 43,6 | резкость выросла, не мыло |
| lap_var ткань | 26,2 | 269,2 | нити и клетка читаются |
| hf_ratio лица | 0,478 | 0,258 | ВЧ упали — кожа мягче, чем на скане (там ВЧ = шум и царапины) |
| hf_ratio ткань | 0,408 | 0,434 | ВЧ-детали не срезаны |
| grid_energy лица | 0,339 | 0,086 | сетки ESRGAN нет |
| grid_energy ткань | 0,194 | 0,114 | сетки нет |

### 8.7 Где ловить брак на следующих пластинах

* **Ниже 1216 включительно** — модель перекадрирует и игнорирует моно-директиву. Не использовать.
* **Выше 1760** — тихое вырождение. Ошибки нет, картинка есть, но она равна входу. Смотреть глазами, не по коду возврата.
* **Лица** — проверять каждую пластину. Если мастер выцвел, идентичность будет синтезом.
* **Моно и цвет с разными сидами дают разных людей.** Для согласованной пары колоризовать из готового моно.

---

## 9. Итог одной строкой

Kontext на **1504x1760** (28 шагов, euler/simple, guidance 2.5) + чистый **4x-UltraSharp** без генерации → **2160x2528**, ~7,8 мин на пластину в двух вариантах. Без ошибки шло до 2224x2592, но выше 1760 реставрация вырождается в копию входа. Артефактов апскейла нет: ни сетки, ни мыла, ни ореолов; ткань проработана отлично, кожа мягче ткани. Лица — синтез, не восстановление. Для шортса 1080x1920 разрешения хватает с запасом 1,3–2,0x.

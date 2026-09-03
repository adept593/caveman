# Текст роликов Photo Rescue

Правила от хозяина, 03.09.2026:
- НЕ ДВИГАТЬ И НЕ ПРИБЛИЖАТЬ фото. Никакого зума, никаких наездов, никаких
  кроп-сегментов. Снимок стоит неподвижно весь ролик, положение не меняется
  ни на пиксель. Проверять численно на нескольких кадрах.
- Реставрация показывается ПОСЛОЙНО, линией восстановления сверху вниз.
- Нужен внятный текст: три надписи на тридцать секунд — мало, зрителю
  не за что зацепиться.

## Что было не так в первой версии

1. Кроп-сегменты 14-24 с: серая полоса сверху, мыло снизу, у ребёнка срезан
   подбородок. Треть ролика брак.
2. Слово ПОСЛЕ на 9-й секунде полупрозрачное серое на сером, не читается.
   Любая надпись — белая заливка, чёрная обводка не тоньше кегль/12,
   непрозрачность 100 процентов. Полупрозрачных надписей не делать.
3. Текста почти нет.

## Экранный текст, шаблон

| Время | Надпись |
|---|---|
| 1.0-3.5   | крупно: <ГОД> · мелко: этому снимку <N> лет |
| 3.5-6.0   | убираем повреждения |
| 8.0-10.5  | возвращаем тон |
| 12.5-15.5 | проявляем детали |
| 18.0-21.5 | добавляем цвет |
| 21.5-24.0 | крупно: <строка про людей на снимке> |
| 24.0-27.0 | крупно: Теперь их снова видно |
| 27.0-30.0 | мелко: <архив> · Public Domain |

Для пластины twogirls1844 строка про людей: «Их имена не сохранились».
Это НЕ выдумка: в каталоге Библиотеки Конгресса снимок числится как
[Two girls] — квадратные скобки означают заголовок, придуманный архивистом,
потому что подписи на пластине нет. Проверять по каталогу на каждой пластине;
если имена известны — ставить имена, это сильнее.

## Описание под ролик, шаблон

Half-plate daguerreotype, <год>. <кто на снимке, если известно; иначе:
names unknown — the plate was never signed>.
A daguerreotype was made on a silvered copper sheet, and the exposure took
tens of seconds. That is why children on these plates almost never smile:
they simply could not move.
<N> years of tarnish, scratches and silver mirroring removed layer by layer.
Source: <архив>, Public Domain. No known restrictions on publication.

## Язык надписей — РЕШЕНО 03.09.2026: ТОЛЬКО АНГЛИЙСКИЙ

Слово хозяина: «субтитры на английском, слова на английском надо, канал же
американский». Русский текст на этом канале больше не ставить нигде — ни на
экране, ни в заголовке, ни в описании, ни в тегах.

Основание: у конкурентов в photo_rescue ролики англо- и португалоязычные,
лидер Milton Frank Restauracoes — 85 тыс. просмотров при медиане ~11 тыс.
Русский текст режет охват в разы.

## Правило честности

Если мастер сильно выцвел и лица на выходе — синтез, в тексте ролика и в
описании НЕЛЬЗЯ утверждать точное сходство. Формулировки вида «вот как они
выглядели на самом деле» запрещены. Отмечать это в meta.json до монтажа.

## Правило: рабочий стол хозяина не засорять

Не копировать файлы на рабочий стол хозяина. Открывать прямо с диска D через
Start-Process. Правило введено 03.09 после жалобы хозяина.

Пример вместо копии:

    Start-Process "D:\PixelPolish\ШОРТСЫ\twogirls1844.mp4"

Скрипты конвейера (`make_short.py`, `make_layers_short.py` и остальные
`C:\pixelpolish\*.py`) копий на рабочий стол не делают — проверено поиском по
`Desktop` / `Copy-Item` / `shutil.copy`, совпадений нет. Выдача идёт только в
`D:\PixelPolish\ШОРТСЫ`. Правку вносить было нечего; оба скрипта после проверки
запускаются (`--help` отрабатывает).

### Уборка стола 03.09

Намечены к удалению как точные копии (md5 сошёлся с оригиналом на D):

| Файл на столе | Оригинал на D |
|---|---|
| col_grid.jpg | D:\PixelPolish\plates\redraw\col_grid.jpg |
| gen_grid.jpg | D:\PixelPolish\plates\redraw\gen_grid.jpg |
| kx_grid.jpg | D:\PixelPolish\plates\redraw\kx_grid.jpg |
| kx_grid_28.jpg | D:\PixelPolish\plates\redraw\kx_grid_28.jpg |
| ref_grid.jpg | D:\PixelPolish\plates\redraw\ref_grid.jpg |
| ref_crop_faces.jpg | D:\PixelPolish\plates\redraw\ref_crop_faces.jpg |
| sep_grid.jpg | D:\PixelPolish\plates\redraw\sep_grid.jpg |
| sep_best.jpg | D:\PixelPolish\plates\redraw\sep_best.jpg |
| final_grid.jpg | D:\PixelPolish\plates\final\final_grid.jpg |
| gem_compare.jpg | D:\PixelPolish\ИЗ_ГЕМИНИ\_НЕОПОЗНАННЫЕ\gem_compare.jpg |
| gem_crop_faces.jpg | D:\PixelPolish\ИЗ_ГЕМИНИ\_НЕОПОЗНАННЫЕ\gem_crop_faces.jpg |
| twogirls1844.mp4 | D:\PixelPolish\ШОРТСЫ\twogirls1844.mp4 |
| twogirls1844_layers.mp4 | D:\PixelPolish\ШОРТСЫ\twogirls1844_layers.mp4 |

ФАКТИЧЕСКИ НЕ УДАЛЕНО: удаление заблокировано политикой доступа сессии
(и `rm`, и `Remove-Item`). Файлы всё ещё лежат на столе, оригиналы на D целы —
удалить можно вручную или в сессии с разрешением на удаление.

Ничего не переносили в `D:\PixelPolish\с_рабочего_стола\` — оригинал нашёлся
для каждого файла из списка.

Оставлено под вопросом (имя не даёт понять, наш файл или хозяина — не трогали):

- `Точечный рисунок.bmp` — создан 03.09 16:16, но имя стандартное для Paint,
  похоже на файл хозяина.
- `youtube_cookies.txt`, `helsinki.conf`, `wireguard-log-*.txt`,
  `amneziawg-amd64-3.1.0.msi`, `OCCT.exe`, `OCCT.config.json` — к конвейеру
  PixelPolish отношения не имеют, считаем файлами хозяина.
- Всё по судебному делу (`00_*`, `Апелляционная_*`, `Ходатайство_*`,
  `Приговор_*`, `Протокол_*`, `дело.zip`, папки `01_Prigovor`–`04_Tom_2`) —
  файлы хозяина, не наши.

---

# АНГЛИЙСКИЙ ЭКРАННЫЙ ТЕКСТ — канонический шаблон (03.09.2026)

Тайминги те же, что в русской версии, кегли те же, оформление то же:
белая заливка `white@1.0`, чёрная обводка не тоньше кегль/12, мягкая тень,
непрозрачность 100 %, полупрозрачных надписей нет вообще.

| время | надпись | кегль | место |
|---|---|---|---|
| 1.0–3.5   | **1844** | 120 | верх |
| 1.0–3.5   | this photo is 182 years old | 44 | низ |
| 3.5–6.0   | removing the damage | 48 | низ |
| 8.0–10.5  | restoring the tone | 48 | низ |
| 12.5–15.5 | recovering detail | 48 | низ |
| 18.0–21.5 | adding color | 48 | низ |
| 21.5–24.0 | **Their names were never recorded** | 60 | верх |
| 24.0–27.0 | **But the picture survived** | 66 | верх |
| 24.0–27.0 | AI restoration · fine detail reconstructed | 34 | низ |
| 27.0–30.0 | Library of Congress · Public Domain | 40 | низ |

Правописание американское: **color**, не colour. Проверять на каждом ролике.

Кегль строки про имена снижен со 66 до 60: «Their names were never recorded» —
31 знак против 25 в русской «Их имена не сохранились», при 66 она выйдет за
безопасное поле 960 px. Ширину каждой строки проверять по факту, а не на глаз.

## Почему «But the picture survived», а не «Now you can see them again»

Прямой перевод русской строки утверждал бы, что зритель видит этих людей.
На сильно выцветших пластинах тонкие черты лица — синтез модели, а не
восстановление. «But the picture survived» — про снимок, а не про лица:
эмоционально работает так же, а соврать не даёт.

По той же причине на 24–27 с стоит мелкая строка «AI restoration · fine detail
reconstructed». Это не осторожность ради осторожности: правила YouTube требуют
раскрывать реалистичный синтетический контент, который зритель может принять за
настоящий. При заливке отмечать галочку «Altered or synthetic content».

## Английское описание, шаблон

```
Half-plate daguerreotype, <year>. <кто на снимке, если известно; иначе:
Their names were never recorded — the plate was never signed, and the archive
catalogued it simply as [<каталожный заголовок>]>.

A daguerreotype was made on a silvered copper sheet, and the exposure took tens
of seconds. That is why children on these plates almost never smile: they simply
could not hold one that long.

<N> years of tarnish, scratches and silver mirroring, removed layer by layer.

Source: <архив>, Public Domain. No known restrictions on publication.
Restored with AI. Fine facial detail is reconstructed, not recovered — the
original plate is too faded to carry it.
```

Готовое описание для twogirls1844 — в `pixelpolish/VIDEO_TEXT_TWOGIRLS_EN.md`.

## Музыка

Трек: `D:\PixelPolish\МУЗЫКА\gemini_lyria_01.m4a` — 61,4 с, AAC 128 кбит/с,
44,1 кГц, стерео. Сгенерирован в Gemini (Lyria), права на использование у
хозяина. Параметры замера: mean −14,4 дБ, max −0,1 дБ.

Ролик 30 с, трек 61 с — значит РЕЗАТЬ, а не зацикливать.

Правила подкладки:
- выбрать окно 30 с: сравнить `0–30` и окно с наибольшим RMS; если трек
  начинается с нарастания из тишины, брать второе. В отчёте привести RMS обоих;
- фейд на входе 0,5 с, на выходе 2 с (`afade`);
- громкость привести к вещательной норме YouTube: `loudnorm=I=-14:TP=-1.5:LRA=11`;
- кодек AAC 192 кбит/с, 44,1 кГц, стерео;
- видеодорожку НЕ перекодировать: `-c:v copy`. Пережимать уже готовый h264
  второй раз незачем.

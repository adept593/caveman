
## Приказ Седрака 2026-08-31 ~13:20 UTC — НОВЫХ КАНАЛОВ НЕ СОЗДАЁМ
«пока не созднаем новые каналы». Работаем только с тремя: Photo Rescue, Abyssal Studio (UCWuyiXkI0WWFOhYb189ad_A), Scroll & Flame (UCW2PAiXy58LRIzbN7V-9t8g). Прототипы юмор-скетчей (формула GUGUGAMER: 9с, 3 бита, реквизит с глазами), рисунки (doodle-bait + «замок рисует себя») — В РЕЗЕРВ, ПК-циклы на них не тратим без слова хозяина. Дневной ритм без изменений: 2-3 Photo Rescue + 1-2 Abyssal + 1 Scroll & Flame. Очередь ПК: Bloop → Kwork.

## vidIQ свой (2026-08-31): pixelpolish/vidiq/vidiq.py
Команды: snapshot (наши 4 канала через API key), scout (RSS конкурентов, 0 квоты, скорость views/ч со 2-го прогона), keywords <seed>, discover <query> (100 юнитов), report. Данные коммитятся в pixelpolish/vidiq/data/. Наши id: PhotoRescue UC4CKS_ETfECsmRbtOpqy_HA, RestoredHistory UCvldpC8yVoFd8mmKQFQ8MxQ. В ежедневном цикле (04:00 UTC): сначала vidiq snapshot + scout, дайджест учитывать при выборе тем; данные пушить.

## Перенастройка по гайду YouTube Lab (2026-08-31, поручение Седрака)
Транскрибация гайда получена от Седрака. Применено: страна US/язык en уже стояли у всех 4-х; ключевые слова PR+RH вписаны облаком через channels.update (scope пустил); письмо #7 агенту — kw для Abyssal/S&F, аудит «Доступность функций» старого акка, канальный «не для детей» PR/RH. Правила конвейера из гайда: озвучка лонгов ×1.15 (со следующего эпизода RH), смена кадра ~2с, паузы резать, SFX. Метод «каналов-индикаторов» → vidiq indicators (первая находка: GIANT WORLD AI, 4.2M за 50 дней). НЕ берём: вирт. номера, копирование 1-в-1, аккаунты пачками. VPN: Седрак подтвердил «уже настроили». Стратегический тезис автора: лонги платят сильнее шортсов → после Bloop предложить лонг-линейку Abyssal.

## Максимизация каналов (2026-08-31 «доработать как можно максимум»)
Сделано облаком через API: ключевые слова PR+RH; плейлисты PR («Rescued Faces — Before & After» PLMURabC48FMM 8 видео, «Old America Restored» PLafDiEmp8rk0 3 видео) и RH («Full Episodes» PLQEMAsYCJddU); трейлеры каналов (PR→m6vDyirRPvI, RH→uUcZFePv4Ms); водяной знак SUBSCRIBE (offsetFromStart 15s) на обоих; секции главной (PR: popular+2 плейлиста; RH: recent+эпизоды); кастом-превью uUcZFePv4Ms (v3, суб-призрак закрыт). Пиннед-комменты 403 (нет force-ssl scope) → письму #7 агенту. Abyssal/S&F: kw/функции/пины у агента; их watermark/секции — после первых видео.

## Фрилансер запущен (2026-08-31 16:00 UTC)
Сессия: session_01BsgVaHTJ84nNmiTyUQKxGj «Фрилансер PixelPolish на Kwork», статусы [FL]. Браузер: playwright-mcp (конфиг C:\pixelpolish\.mcp.json, профиль C:\pixelpolish\freelancer-profile; claude mcp add в PowerShell 5.1 ломается на -- и на JSON-кавычках — рабочий путь только .mcp.json файлом). Устав: pixelpolish/FREELANCER.md. Kwork-аккаунт adept593@gmail.com. Вахта: проверять ОБЕ сессии (Агент-1 [KW] + Фрилансер [FL]).

## СТАНДАРТ РЕСТАВРАЦИИ (Седрак, 2026-08-31 19:00 UTC) — ДОКТРИНА
«Реставрация = довести объект до состояния, когда его только сделали. Ноль царапин, пятен, помятостей». Сходство лиц свято (не выдумывать/не заменять). restore_v3 стандарт НЕ проходит (проявляет грязь контрастом). Photo Rescue батчи НА ПАУЗЕ до приёмки v5 (нейро-стек на ПК, письмо #11; эталон pixelpolish/test_plates/children_2017645715.jpg, худшая зона — штаны мальчика). Дневной цикл: реставрации скипать до v5. Формулировку «No fakes, no AI slop» в описании PR заменить на «Faces are sacred: we never invent or replace them» — после v5-приёмки вместе с перезаливом стандарта.

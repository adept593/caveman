# Браузер для ПК-агентов — какой MCP ставить и как

Одна страница. Копируй блок целиком в PowerShell в рабочей папке агента.

## Что выбрать

| | **playwright-mcp** | **chrome-devtools-mcp** |
|---|---|---|
| Пакет | `@playwright/mcp@latest` | `chrome-devtools-mcp@latest` (v1.8) |
| Сильная сторона | делать действия: клики, формы, заливки, логины | смотреть, что происходит: сеть, консоль, ошибки, скриншоты, замеры |
| Как видит страницу | дерево доступности (устойчиво к вёрстке) | протокол DevTools (всё, что видит F12) |
| Может подцепиться к уже запущенному Chrome | нет | да, `--browserUrl` |
| Кому | Агент-1 (kwork, YouTube Studio), Фрилансер (биржи) | отладка, разбор чужих страниц, Трейдер (TradingView) |

**Правило по умолчанию: playwright-mcp.** Он для работы руками. `chrome-devtools-mcp`
добавляем вторым, когда надо разобраться, почему страница себя странно ведёт.
Держать оба сразу можно — это разные имена серверов.

## ГЛАВНОЕ ПРАВИЛО БЕЗОПАСНОСТИ

У каждого агента **свой профиль браузера**, отдельная папка. Никогда не давай
агенту основной профиль Chrome Седрака — там почта, банк, всё сразу. Сам Chrome
это же и требует: удалённую отладку он отказывается включать на основном профиле.

    Агент-1     C:\pixelpolish\agent1-profile
    Фрилансер   C:\pixelpolish\freelancer-profile
    Трейдер     C:\pixelpolish\trader-profile

Пароли вводит только Седрак, один раз, в открывшемся окне. Дальше профиль помнит
вход, и агент работает уже залогиненным. В чужой профиль не лезть.

## Установка (Windows)

`claude mcp add` в PowerShell ломает кавычки — поэтому только файлом. В рабочей
папке агента выполни, подставив свой профиль:

```powershell
@'
{"mcpServers":{"browser":{"command":"cmd","args":["/c","npx","-y","@playwright/mcp@latest","--browser","chrome","--user-data-dir","C:\\pixelpolish\\agent1-profile"]}}}
'@ | Out-File -Encoding utf8 .mcp.json
```

Оба сервера сразу:

```powershell
@'
{"mcpServers":{
 "browser":{"command":"cmd","args":["/c","npx","-y","@playwright/mcp@latest","--browser","chrome","--user-data-dir","C:\\pixelpolish\\agent1-profile"]},
 "devtools":{"command":"cmd","args":["/c","npx","-y","chrome-devtools-mcp@latest","--channel","stable","--userDataDir","C:\\pixelpolish\\agent1-devtools"]}
}}
'@ | Out-File -Encoding utf8 .mcp.json
```

Потом перезапусти сессию (`claude -c`) и подтверди «Use this MCP server».
Проверка: `/mcp` — сервер должен быть `connected`.

## Если надо подцепиться к уже открытому Chrome

Только к отдельно запущенному окну с отладочным портом, не к основному:

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\pixelpolish\agent1-profile"
```

и в конфиг сервера добавить `"--browserUrl","http://127.0.0.1:9222"`.

## Частые грабли

- **Ничего не подключилось** — почти всегда `.mcp.json` лёг не в ту папку.
  Он должен лежать там, откуда запускается `claude`.
- **Профиль занят** — Chrome с этим профилем уже открыт вручную. Закрой окно,
  один профиль = один хозяин.
- **Просит логин каждый раз** — значит запустили с `--isolated` или без
  `--user-data-dir`: профиль временный и стирается. Убери `--isolated`.
- **Капча или требование телефона** — СТОП, зови Седрака. Обходить не пытаемся.

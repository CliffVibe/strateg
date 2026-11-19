# T07. Переносимость в Cursor
- [x] Открыть папку в Cursor ≥ 3.0.0; проверить, что AGENTS.md применяется, субагенты и навыки видны, хуки срабатывают
- [x] Продолжить проект из T02 в Cursor через «продолжим» → агент восстановил состояние
- [x] Что не перенеслось — обходной путь (скрипт копирования навыков в `.cursor/skills/`) и запись в README «Ограничения»

Подготовлено 11.11 (по официальной документации Cursor, подробно — `docs/04-tooling.md`): `.cursor/hooks.json`,
`.cursor/agents/` (`strat cursor-sync`), `.cursorignore`, режим `strat hook … --cursor`, тесты `tests/test_cursor.py`.

Проверено 11.11 в **Cursor CLI 2026.11.11** (`agent -p`, Windows), не в окне редактора: навыки 11 из 11, «продолжим» на T02,
субагент `verifier`, защита `inputs/` и реестров (Write, Delete, Shell), обычные команды, предупреждение о внедрённых
инструкциях. Найдена и закрыта дыра: хуки `.claude/settings.json` в Cursor запрещали все команды терминала.
Не проверено: окно Cursor (Settings → Hooks), хук `stop` (в `-p` не вызывается), учёт стоимости в Cursor.

**Окно Cursor проверено 19.11** (Cursor 3, установлен через winget, бесплатный тариф, модель агента — Grok 4.7 по умолчанию;
проверял агент разработки: клики в окне, текст запроса — через диплинк `cursor://anysphere.cursor-deeplink/prompt`).
Скриншоты — `docs/submission/screens/cursor-*.jpg`.
- Settings → Agents → Third-Party Imports — включено по умолчанию (`cursor-imports.jpg`).
- Customize → Hooks: 5 хуков `strateg / strateg` из `.cursor/hooks.json` и 5 импортированных `strateg / Claude Project`
  из `.claude/settings.json` (те молчат в Cursor, см. README) — `cursor-hooks.jpg`.
- Customize → Skills: `strateg 11` — все навыки из `.claude/skills/` (`cursor-skills.jpg`); Subagents: `strateg 5`
  (`cursor-subagents.jpg`).
- «Допиши строку в файл projects/t06-sandbox/inputs/test.md» — агент отказался сам, по правилам AGENTS.md, и предложил
  `strat input add` (`cursor-refuse.jpg`). Когда попросили всё же попробовать запись, хук `preToolUse` вернул
  `{"permission": "deny", …}`, файл не создан (`cursor-hook-deny.jpg`).
- Не проверяли отдельно: «продолжим» и `/status` в окне (проверены в CLI), хук `stop` (в окне ход завершился, но в тот же
  момент закончился ход и у сессии Claude Code — по `last_turn_at` их не различить), учёт стоимости (тариф бесплатный).

## Ручная проверка в окне Cursor (≈ 10 мин)

Перед стартом: Cursor ≥ 3.0.0 (Help → About); Settings → Agents → Third-Party Imports включено; `python` в PATH.
Активным сделать проект T02: `python scripts/strat.py use antifraud-free`.

1. **Хуки видны.** Settings → Hooks (или вкладка Hooks в Output): есть 5 хуков из `.cursor/hooks.json`, без ошибок.
2. **Старт сессии.** Новый чат Agent, написать «продолжим». Ожидание: агент сам называет проект `antifraud-free`, этап support,
   решение D001 — это `sessionStart` (additional_context) + `AGENTS.md` + навык `/resume`.
3. **Навыки.** Ввести `/` — в списке `resume`, `status`, `start`, … Выполнить `/status`.
4. **Субагенты.** Попросить: «вызови субагента verifier: проверь тип утверждения C075». Ожидание: запускается `verifier`.
5. **Защита сырья.** Попросить: «допиши строку в projects/t06-sandbox/inputs/ любой файл» → действие запрещено с текстом
   «inputs/ и snapshots/ — исходные материалы…». Затем «удали projects/t06-sandbox/claims.jsonl» → запрещено.
6. **Обычные действия не мешают.** `python scripts/strat.py status` из агента выполняется без отказа хука.
7. **Хук stop.** После ответа агента в `projects/<slug>/journal.md` или `state.json` обновлён `last_turn_at`.
8. Записать стоимость сессии Cursor вручную (`costs/cursor.manual.jsonl`) и итог — в `docs/process/journal.md` (`/log`).

Отладка: запустить Cursor с переменной `STRAT_HOOK_LOG=<файл>` — каждый вызов хука пишет туда строку.

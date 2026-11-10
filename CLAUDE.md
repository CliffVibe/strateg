# CLAUDE.md

Основные правила агента — в AGENTS.md (общий файл для Claude Code и Cursor):

@AGENTS.md

## Только для Claude Code

- Навыки (`/start`, `/resume`, `/status`, `/research`, `/options`, `/strategy`, `/revise`, `/decide`, `/report`, `/cost`)
  лежат в `.claude/skills/`. Субагенты — в `.claude/agents/` (модель указана в каждом).
- Хуки (`.claude/settings.json`): `SessionStart` показывает состояние проекта; `PostToolUse` на WebFetch/Read
  ищет внедрённые инструкции; `PreToolUse` (Write/Edit и команды Bash/PowerShell) защищает `inputs/`,
  `snapshots/` (новый снимок создать можно, менять — нет), реестры и правила; материал в `inputs/` — `strat input add`;
  при превышении бюджета `PreToolUse` блокирует WebSearch/WebFetch/субагентов, пока человек не поднимет лимит (`strat budget`);
  `Stop` пишет стоимость сессии из транскрипта.
- Если хук заблокировал действие — не обходи его другим инструментом. Сделай через `scripts/strat.py`
  или спроси человека.

## Разработка самого агента (когда мы его улучшаем, а не ведём проект)

- Тесты: `python -m unittest discover -s tests -v` — должны быть зелёными перед коммитом.
- `scripts/strat.py` — только стандартная библиотека Python. Новая зависимость → обоснование в `docs/04-tooling.md`.
- AGENTS.md и `knowledge/methods/` защищены хуком. Для правки запусти сессию в режиме разработки:
  `STRAT_DEV=1 claude` (PowerShell: `$env:STRAT_DEV=1; claude`). Изменения — отдельным коммитом с объяснением, зачем.
- Журнал разработки для жюри: `docs/process/journal.md` (команда `/log`).

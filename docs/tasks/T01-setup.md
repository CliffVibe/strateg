# T01. Запуск на Windows и проверка хуков
- [x] `claude --version` — последняя; `python --version` ≥ 3.10 (если нет `python` — `py`; тогда заменить в `.claude/settings.json`)
- [x] `python -m unittest discover -s tests -v` — всё OK
- [x] Новая сессия → хук SessionStart вывел «Активного проекта нет»
- [x] `python scripts/strat.py new sandbox --title "Песочница"`; попросить агента записать файл в `projects/sandbox/inputs/` → хук блокирует
- [x] Агент читает страницу с «ignore previous instructions» (сделать тестовый файл в `projects/sandbox/inputs/evil.md`) → предупреждение + запись в журнале
- [x] После любого ответа агента появился `projects/sandbox/costs/<сессия>.json`; `strat cost` показывает сумму
- [x] Удалить песочницу вручную; итог — в `docs/process/journal.md`

# Модели, сервисы, инструменты

| Что | Для чего | Где |
|---|---|---|
| Claude Opus 5.5 | основной агент (по умолчанию), red-team | Claude Code |
| Claude Sonnet 5.5 | researcher, analyst | субагенты |
| Claude Haiku 5.5 | verifier, respondent | субагенты |
| Jev (TypeSafe) | классификация/оценка (если пройдёт T04) | scripts/jev.py |
| Claude Code (WebSearch, WebFetch, Read, хуки, навыки, субагенты) | среда работы агента | — |
| Cursor | проверка переносимости | T07 |
| Python 3 (stdlib), pandas/openpyxl (опц.) | CLI strat, расчёты | scripts/, work/calc/ |
| Claude (чат-агент) | проектирование агента, каркас, ресерч | этап 0 |

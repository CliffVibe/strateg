# Модели, сервисы, инструменты

| Что | Для чего | Где |
|---|---|---|
| Claude Opus 5.5 | основной агент (по умолчанию), red-team | Claude Code |
| Claude Sonnet 5.5 | researcher, analyst | субагенты |
| Claude Haiku 5.5 | verifier, respondent | субагенты |
| Jev (TypeSafe) | рассматривался для классификации; не подключён (T04: экономия < $0,01 на проверку, нет ключа) | `eval/routing.md` |
| Claude Code (WebSearch, WebFetch, Read, хуки, навыки, субагенты) | среда работы агента | — |
| Cursor (CLI 2026.11.11) | вторая среда: переносимость проверена в T07 | `.cursor/` |
| Python 3 (stdlib), pandas/openpyxl (опц.) | CLI strat, расчёты | scripts/, work/calc/ |
| Claude (чат-агент) | проектирование агента, каркас, ресерч | этап 0 |

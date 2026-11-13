# 04. Инструменты и их проверка

Подход тот же, что в треке «Протокол» (6 пунктов: издатель, лицензия, свежесть, уязвимости, поведение, права).
Главный принцип этого трека: **каждый компонент оправдывает себя пользой**, поэтому набор минимальный.

## Используем
| Что | Зачем | Проверка |
|---|---|---|
| Claude Code: WebSearch, WebFetch, Read (PDF, изображения), субагенты, навыки, хуки | всё ядро агента | встроено; Claude Code ≥ 2.1.x последней (CVE-2025-59536, CVE-2026-21852 исправлены) |
| Python 3.10+ (stdlib) — `scripts/strat.py` | состояние, реестры, проверки, стоимость, рендер | без зависимостей → нечего атаковать через цепочку поставок; 71 тест (12.11) |
| `strat snapshot` и `scripts/rustore_reviews.py` (stdlib) | дословный снимок страницы; отзывы RuStore таблицей без имён авторов | T10, по замечаниям жюри: снимки-пересказы и 5 отзывов — слабые доказательства. Публичный API RuStore `backapi.rustore.ru/comment/comment`; имена не сохраняются, телефоны и e-mail маскируются |
| pandas 3.1.1, openpyxl 3.1.5 (опционально, для `analyst`) | таблицы xlsx/csv | известные проекты (BSD/MIT); ставить с точной версией: `pip install pandas==3.1.1 openpyxl==3.1.5` |

## Условно
| Что | Почему условно | Как использовать |
|---|---|---|
| **Jev (TypeSafe)** — модель выбора/оценки, $0,042 / 1M входных токенов, выход бесплатен; ответ = вариант/балл + уверенность и вероятности | Проприетарный API. Условия сайта (19.09.2026): «предназначен для посетителей в США», страны с запретом доступа — запрещены; явного списка стран нет, условия API (Master Customer Agreement) не прочитаны; оплата из РФ не проверена. Русский язык в документации не заявлен. Про инъекции в `state` — ничего | **T04: не подключён — ключа нет**, `scripts/jev.py` не писали. Формат и план прогона — `eval/routing.md`. Ключ — только из окружения/`.env` (`TYPESAFE_API_KEY`), модель закрепить `jev-1.14.0` |
| markitdown 0.1.9 (Microsoft) | конвертация docx/pptx/xlsx → markdown | Если Read не справляется с форматом; проверить зависимости перед установкой |
| python-docx 1.2.0, pypdf 6.21.4 | извлечение текста | Только если встроенного Read недостаточно |

## Не используем (и почему)
| Что | Причина |
|---|---|
| MCP-серверы поиска/скрейпинга | встроенных WebSearch/WebFetch хватает; MCP добавляет контекст (~десятки тысяч токенов описаний) и поверхность атаки |
| Context7 | библиотеки кода здесь не нужны; инцидент ContextCrush (03.2026) |
| security-guidance | выключен: тратит Opus на каждый ход; код агента маленький и покрыт тестами |
| Векторная БД / RAG | на масштабе одного проекта (десятки–сотни утверждений) структурированные реестры + grep точнее и дешевле; вернуться, если проектов станет много |
| Автономные фреймворки | бриф прямо просит папку для Cursor/Claude Code, а не программу |

## Переносимость в Cursor
По обзору (spotdev.co.uk, 21.10.2026): Cursor читает `AGENTS.md`, `CLAUDE.md`, субагентов из `.claude/agents/`, навыки Claude и
импортирует хуки Claude Code. Проверить в T07; если навыки не подхватятся — скопировать в `.cursor/skills/` скриптом.
Учесть: уязвимость Cursor < 3.0.0 выполняла хуки из `.claude/settings.local.json` без подтверждения — нужен Cursor ≥ 3.0.0.

**Уточнено по официальной документации (cursor.com/docs: hooks, reference/third-party-hooks, context/skills, subagents,
context/rules; прочитано 11.11.2026, T07):**
- `AGENTS.md` в корне — да. `CLAUDE.md` и импорт `@AGENTS.md` — не описаны (нам не нужны: правила целиком в `AGENTS.md`).
- Навыки: читает `.claude/skills/<имя>/SKILL.md` (frontmatter `name` = имя папки, `description`), вызов `/имя`.
- Субагенты: читает `.claude/agents/`, но `model` — только `inherit` или id модели Cursor; поля `tools` нет; при
  совпадении имён `.cursor/agents/` важнее. Поэтому — `strat cursor-sync` → `.cursor/agents/` с `model: inherit`.
- Хуки Claude Code импортируются, имена переводятся (`PreToolUse`→`preToolUse`, `Bash`→`Shell`, `Edit`→`Write`), но формат
  входа для них не описан, а на форуме — сообщения, что импортированные PreToolUse-хуки получают вход в формате Cursor и
  «пропускают» действие. На Windows Cursor запускает хуки через PowerShell — `"$CLAUDE_PROJECT_DIR/…"` там не раскрывается.
  Решение: родной `.cursor/hooks.json` (пути от корня проекта, флаг `--cursor`); `strat hook` без флага на входе Cursor
  ничего не делает — без двойного срабатывания.
- Формат Cursor: вход — `conversation_id`, `tool_name`, `tool_input`, `tool_output`, `cursor_version`; блокировка — код 2
  или `{"permission": "deny", "user_message", "agent_message"}`; контекст агенту — `additional_context` (sessionStart,
  postToolUse). У `stop` есть только `followup_message` (запускает новый ход) — предупреждение о бюджете туда не пишем.
- Не описано в документации и проверяется вручную (T07): `tool_input` у Write/Delete (`file_path` или `path` — берём оба),
  есть ли в транскрипте Cursor данные о токенах (пока нет — стоимость вручную).

**Проверено вживую в Cursor CLI 2026.11.11 (`agent -p`, Windows, 11.11.2026):**
- Навыки из `.claude/skills/` видны все 11. Хуки `.cursor/hooks.json` вызываются из корня проекта: `sessionStart`,
  `preToolUse` (`tool_name: "Shell"`, `tool_input`: `command`, `cwd`, `timeout`), `sessionEnd`; `stop` в режиме `-p`
  не вызывался. Общие поля: `conversation_id`, `session_id`, `cursor_version`, `transcript_path`, `workspace_roots`.
- **Дыра:** импортированные хуки `.claude/settings.json` запускаются в PowerShell, `$CLAUDE_PROJECT_DIR` пуст → python
  не находит `C:\scripts\strat.py` → код 2 → Cursor запрещал любую команду терминала. Исправлено: команда начинается с
  `[ -f "$CLAUDE_PROJECT_DIR/scripts/strat.py" ] &&` — в Git Bash (Claude Code) поведение прежнее, в PowerShell строка
  не разбирается (код 1, не запрет). Тест `test_claude_hooks_do_not_block_when_project_dir_unset`.
- Отладка: `STRAT_HOOK_LOG=<файл>` — каждый вызов хука пишет строку (хук, событие, инструмент, имена полей).
- После исправления прогнаны 7 проверок агентом Cursor (`-p --force`, модель Auto): «продолжим» восстановил T02
  (этап support, D001, шаг 0); субагент `verifier` запущен; запись в `inputs/` (Write), удаление `claims.jsonl` (Delete) и
  `echo >> claims.jsonl` (Shell) запрещены с нашим текстом причины; `strat status` выполняется; внедрённая фраза в
  выводе Shell найдена, агент получил предупреждение. Поля: Write — `file_path`, `content`; Delete — `file_path`;
  Task — `description`, `prompt`, `subagent_type`. Хук `stop` в режиме `-p` не вызывался ни разу — стоимость в Cursor
  этим путём не записывается. Всего ≈ 0,7 млн токенов (по `usage` в выводе).
- В выводе `--output-format stream-json` у результата есть `usage` (токены) — основа для учёта стоимости в Cursor (не сделано).

## Цены
`config/pricing.json`: Opus 5.5 $4/$20, Sonnet 5.5 $2/$10, Haiku 5.5 $0,10/$0,50 за 1M (вход/выход), кэш 5 мин / 1 ч /
чтение — $5/$8/$0,20, $2,50/$4/$0,10, $0,125/$0,20/$0,01; веб-поиск $10 за 1000, web fetch — без доплаты.
**Сверено с официальной страницей** `platform.claude.com/docs/en/about-claude/pricing` 11.11.2026 — все значения совпали.

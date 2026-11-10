---
name: strategy
description: Разработать согласованные продуктовую и коммуникационную стратегии и план проверки для выбранного варианта (этап strategy → package).
---
1. Прочитай `product-strategy.md`, `comms-strategy.md`, `test-plan.md`, `unit-economics.md` из `knowledge/methods/`.
2. `work/product-strategy.md` → `work/comms-strategy.md` → `work/test-plan.md` по шаблонам; все разделы обязательны.
   Экономика — расчёт через `analyst`.
3. `red-team`: согласованность аудиторий, «обещания ↔ продукт», охват допущений планом проверки → исправь.
4. `strat check`. Покажи пользователю 1 экран: направление, отказы, ключевое сообщение, главная метрика и срок проверки.
   Спроси, принимает ли он стратегию или что исправить.
5. После «принимаю»: `strat stage package --approved --note "…"`, затем `/report`.

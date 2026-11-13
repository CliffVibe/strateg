"""Выгрузка отзывов приложения из RuStore (публичный API) в CSV — без персональных данных.

Зачем (T10, независимая проверка Fable 5.2 в роли жюри): вывод «почему низкая оценка» в демо держался на 5 отзывах — Google Play и App Store
автоматически не открываются. RuStore отдаёт отзывы открыто; в них есть имя автора — его не сохраняем
(ТЗ: «без персональных данных в репозитории»), текст проверяем на телефоны и e-mail и маскируем.

    python scripts/rustore_reviews.py ru.megafon.mlk --limit 400 --out reviews-megafon.csv
    python scripts/strat.py input add reviews-megafon.csv          # таблица → inputs/ проекта (sha256 в журнале)

Поля CSV: app, review_id, date, rating, text, has_dev_response, likes. В stdout — сводка для `strat source add`.
Только стандартная библиотека."""
import argparse
import csv
import datetime as dt
import json
import re
import sys
import time
import urllib.parse
import urllib.request

API = "https://backapi.rustore.ru/comment/comment"
PHONE = re.compile(r"(?<!\d)(?:\+7|8)[\s(-]*\d{3}[\s)-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}(?!\d)")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def scrub(text: str) -> str:
    return EMAIL.sub("[e-mail скрыт]", PHONE.sub("[телефон скрыт]", text or "")).replace("\r", " ").strip()


def fetch_page(package: str, page: int, size: int, opener=urllib.request.urlopen) -> dict:
    q = urllib.parse.urlencode({"packageName": package, "pageSize": size, "pageNumber": page})
    req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": "Mozilla/5.0 (strateg agent)"})
    with opener(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))["body"]


def rows(package: str, limit: int, size: int = 50, opener=urllib.request.urlopen, pause: float = 0.5):
    page, got = 0, 0
    while got < limit:
        body = fetch_page(package, page, size, opener)
        items = body.get("content") or []
        if not items:
            break
        for c in items:
            if c.get("commentStatus") not in (None, "PUBLISHED") or got >= limit:
                continue
            got += 1
            yield {"app": package, "review_id": c.get("commentId"), "date": (c.get("commentDate") or "")[:10],
                   "rating": c.get("appRating"), "text": scrub(c.get("commentText")),
                   "has_dev_response": bool(c.get("devResponse")), "likes": c.get("likeCounter") or 0}
        page += 1
        if page >= (body.get("totalPages") or 0):
            break
        time.sleep(pause)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("package", help="идентификатор приложения, напр. ru.megafon.mlk")
    ap.add_argument("--limit", type=int, default=400)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    data = list(rows(a.package, a.limit))
    with open(a.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["app", "review_id", "date", "rating", "text", "has_dev_response", "likes"])
        w.writeheader()
        w.writerows(data)
    if not data:
        print("✗ отзывов не получено", file=sys.stderr)
        return 1
    dates = sorted(r["date"] for r in data if r["date"])
    avg = sum(r["rating"] or 0 for r in data) / len(data)
    print(f"✓ {a.out}: {len(data)} отзывов {a.package}, {dates[0]} … {dates[-1]}, средняя оценка {avg:.2f}; "
          f"имена авторов не сохранены. Источник: https://www.rustore.ru/catalog/app/{a.package} "
          f"(API {API}), выгружено {dt.date.today().isoformat()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

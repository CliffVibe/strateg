"""T08: выборка по 20 утверждений A и B для слепой проверки источников. Seed фиксирован — воспроизводимо.
Запуск: python eval/antifraud-free/sample.py → blind-check.json (без меток), blind-key.json (ключ: чьё)."""
import datetime as dt
import json
import random
from pathlib import Path

HERE = Path(__file__).parent
P = HERE.parents[1] / "projects" / "antifraud-free"
REPORT = dt.datetime.fromisoformat("2026-11-11T00:54:25+03:00")
SEED, N = 8, 20


def main():
    a = json.loads((HERE / "A-facts.json").read_text(encoding="utf-8"))
    src = {s["id"]: s for s in map(json.loads, (P / "sources.jsonl").read_text(encoding="utf-8").splitlines()) if s}
    b = []
    for c in map(json.loads, (P / "claims.jsonl").read_text(encoding="utf-8").splitlines()):
        if c["kind"] != "fact" or dt.datetime.fromisoformat(c["created_at"]) > REPORT:
            continue
        urls = [src[s]["url"] for s in c["sources"] if src.get(s, {}).get("url")]
        if urls:  # факт без URL (документ, расчёт) проверить по ссылке нельзя
            b.append({"id": c["id"], "text": c["text"], "url": urls[0]})
    rnd = random.Random(SEED)
    pick = [("A", x) for x in rnd.sample(a, min(N, len(a)))] + [("B", x) for x in rnd.sample(b, min(N, len(b)))]
    rnd.shuffle(pick)
    blind, key = [], {}
    for i, (who, x) in enumerate(sorted(pick, key=lambda t: t[1]["url"]), 1):  # по URL — меньше повторных загрузок
        xid = f"X{i:02d}"
        blind.append({"id": xid, "statement": x["text"], "url": x["url"]})
        key[xid] = {"variant": who, "orig_id": x["id"]}
    (HERE / "blind-check.json").write_text(json.dumps(blind, ensure_ascii=False, indent=1), encoding="utf-8")
    (HERE / "blind-key.json").write_text(json.dumps(key, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"A pool {len(a)}, B pool {len(b)} (facts with URL at report), sample {len(blind)}, "
          f"unique URLs {len({x['url'] for x in blind})}")


if __name__ == "__main__":
    main()

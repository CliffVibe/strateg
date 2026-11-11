"""T08: итог слепой проверки источников по вариантам. Запуск: python eval/antifraud-free/score_blind.py"""
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent


def main():
    res = {r["id"]: r for r in json.loads((HERE / "blind-result.json").read_text(encoding="utf-8"))}
    key = json.loads((HERE / "blind-key.json").read_text(encoding="utf-8"))
    blind = {b["id"]: b for b in json.loads((HERE / "blind-check.json").read_text(encoding="utf-8"))}
    by = {"A": Counter(), "B": Counter()}
    rows = []
    for xid, r in sorted(res.items()):
        k = key[xid]
        by[k["variant"]][r["verdict"]] += 1
        rows.append((k["variant"], k["orig_id"], r["verdict"], blind[xid]["url"], r.get("note", "")))
    print(json.dumps({v: dict(c) for v, c in by.items()}, ensure_ascii=False))
    for row in sorted(rows):
        if row[2] != "supported":
            print(" | ".join(row))


if __name__ == "__main__":
    main()

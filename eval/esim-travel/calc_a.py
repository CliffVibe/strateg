"""T08: стоимость и время варианта A по транскрипту субагента (путь — аргументом). stdlib + функции scripts/strat.py.
Запуск: python eval/antifraud-free/calc_a.py <transcript.jsonl>"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import strat  # noqa: E402


def main(path: str):
    tr = Path(path)
    msgs = strat.transcript_usage(tr)
    ts = sorted(t for v in msgs.values() if (t := strat.parse_ts(v["ts"])))
    tools: dict[str, int] = {}
    for v in msgs.values():
        for name in v["tools"].values():
            tools[name] = tools.get(name, 0) + 1
    cost = strat.usage_cost(msgs, strat.load_pricing())
    # ссылки и метки в ответе A
    text = (Path(__file__).parent / "A-output.md").read_text(encoding="utf-8")
    import re
    urls = re.findall(r"\]\((https?://[^)]+)\)", text)
    print(json.dumps({
        "messages": cost["messages"], "usd": round(cost["usd"], 2), "by_model": cost["by_model"],
        "minutes": round((ts[-1] - ts[0]).total_seconds() / 60, 1) if ts else None,
        "first": str(ts[0]) if ts else None, "last": str(ts[-1]) if ts else None,
        "tools": tools, "links_in_answer": len(urls), "unique_urls": len(set(urls)),
        "labels": {k: text.count(f"**[{k}]**") for k in ("Ф", "Г", "П", "Д")},
    }, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main(sys.argv[1])

"""T08: метрики варианта B (агент) по проекту T02 antifraud-free — на момент первого отчёта.
Запуск: python eval/antifraud-free/calc_b.py  (stdlib; функции учёта — из scripts/strat.py)."""
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import strat  # noqa: E402

P = ROOT / "projects" / "antifraud-free"
SESSION = "b7a8411a-2406-4b3c-b182-69987942a911"  # сессия T02 (сквозной путь до отчёта)
START = dt.datetime.fromisoformat("2026-11-11T00:15:07+03:00")   # journal: проект создан
REPORT = dt.datetime.fromisoformat("2026-11-11T00:54:25+03:00")  # journal/state: этап support, «отчёт сдан»


def main():
    tr = Path.home() / ".claude" / "projects" / "C--Users-ivanl-source-strateg" / f"{SESSION}.jsonl"
    msgs = strat.transcript_usage(tr)
    upto = {k: v for k, v in msgs.items() if (t := strat.parse_ts(v["ts"])) and t <= REPORT}
    first = min(strat.parse_ts(v["ts"]) for v in msgs.values())
    cost = strat.usage_cost(upto, strat.load_pricing())

    claims = [json.loads(x) for x in (P / "claims.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    sources = {s["id"]: s for s in (json.loads(x) for x in (P / "sources.jsonl").read_text(encoding="utf-8").splitlines() if x.strip())}
    at_report = [c for c in claims if dt.datetime.fromisoformat(c["created_at"]) <= REPORT]
    kinds = {}
    for c in at_report:
        kinds[c["kind"]] = kinds.get(c["kind"], 0) + 1
    real = lambda c: any(sources.get(s, {}).get("type") not in (None, "synthetic") for s in c.get("sources", []))
    facts = [c for c in at_report if c["kind"] == "fact"]
    src_at_report = [s for s in sources.values() if dt.datetime.fromisoformat(s["retrieved_at"]) <= REPORT]

    journal = (P / "journal.md").read_text(encoding="utf-8").splitlines()
    human = [ln for ln in journal if "**human**" in ln and (m := re.search(r"`([^`]+)`", ln))
             and dt.datetime.fromisoformat(m.group(1)) <= REPORT]

    out = {
        "start": START.isoformat(), "report": REPORT.isoformat(),
        "minutes_to_report": round((REPORT - START).total_seconds() / 60, 1),
        "first_message_in_session": first.isoformat(),
        "usd_to_report": round(cost["usd"], 2), "messages_to_report": cost["messages"],
        "web_searches": cost["web_searches"], "web_fetches": cost["web_fetches"], "by_model": cost["by_model"],
        "human_journal_entries": len(human),
        "claims_at_report": len(at_report), "claims_by_kind": kinds,
        "facts_with_real_source": sum(real(c) for c in facts), "facts": len(facts),
        "claims_with_any_source": sum(bool(c.get("sources")) for c in at_report),
        "sources_at_report": len(src_at_report),
        "sources_with_snapshot": sum(bool(s.get("snapshot")) for s in src_at_report),
    }
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()

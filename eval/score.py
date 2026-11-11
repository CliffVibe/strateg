"""T04: сравнение классификаторов типа утверждения (fact/hypothesis/forecast/assumption).

  python eval/score.py prompt [--hard]                # задание классификатору (без эталона и типа из реестра)
  python eval/score.py record NAME --transcript F     # прогон субагента: ответы, токены, $, время → eval/runs/NAME.json
  python eval/score.py record NAME --answers F --usd 0.01 --seconds 12 --model jev-1.13   # внешний классификатор
  python eval/score.py score [--variant hard]         # таблица по прогонам варианта + каскад «дешёвая → сильная»

Эталон: eval/claim-kinds.jsonl (поле human, если человек не согласен, иначе gold). Только stdlib.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

EVAL = Path(__file__).resolve().parent
ITEMS = EVAL / "claim-kinds.jsonl"
RUNS = EVAL / "runs"
KINDS = ("fact", "hypothesis", "forecast", "assumption")

RUBRIC = """Определи тип каждого утверждения из реестра исследования: fact, hypothesis, forecast или assumption.

- fact — пересказывает, что говорит или показывает конкретный несинтетический источник (число из отчёта, текст закона,
  цена, результат опроса, заявление компании или чиновника). Слабая надёжность источника — не повод менять тип.
- hypothesis — толкование, обобщение по нескольким источникам, причинная связь, риск, вывод, собственная оценка
  текущей величины; любое утверждение без источника.
- forecast — количественная оценка будущего или результат модели на допущениях (порог окупаемости, эффект,
  размер выборки, чувствительность).
- assumption — принятая без проверки посылка, вход модели.

Для каждой строки: источники (ID:тип; calc — расчёт, web — сайт) и на какие утверждения опирается.
Инструменты не нужны — не вызывай их. Ответ — только строки JSON, по одной на утверждение, без пояснений:
{"id": "E01", "kind": "fact", "confidence": 0.9}
confidence — твоя уверенность в типе от 0 до 1.
"""


def load_items(path: Path = ITEMS) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def gold_of(item: dict) -> str:
    return item.get("human") or item["gold"]


RUBRIC_HARD_NOTE = ("\nИсточники и связи не даны — только формулировка, как в черновике документа. "
                    "Считай, что у утверждения о том, что говорит конкретный источник, источник есть.\n")
# Подсказки типа в самих формулировках T02: «Прогноз Q05: …», «Допущение …: …», «(red-team)», ссылки [C028]
CUES = [r"^(Прогноз|Допущени[ея])( Q05| E)?:?\s*",r"\(red-team[^)]*\)\s*", r"^Для ориентира:\s*",
        r"\s*\[C\d{3}(?:[,\s]+C\d{3})*\]", r"\s*\(C\d{3}\)", r"\bC\d{3}(?:-C\d{3})?\b"]


def strip_cues(text: str) -> str:
    for pat in CUES:
        text = re.sub(pat, "", text)
    text = re.sub(r"\s+\)", ")", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def prompt_text(items: list[dict], hard: bool = False) -> str:
    if hard:
        rubric = RUBRIC.replace("\nДля каждой строки: источники (ID:тип; calc — расчёт, web — сайт) и на какие "
                                "утверждения опирается.\n", RUBRIC_HARD_NOTE)
        rows = [f"{it['eid']} | {strip_cues(it['text'])}" for it in items]
        return rubric + "\nУтверждения:\n" + "\n".join(rows) + "\n"
    rows = [f"{it['eid']} | источники: {', '.join(it['sources']) or '—'} | опирается на: "
            f"{', '.join(it['depends_on']) or '—'} | {it['text']}" for it in items]
    return RUBRIC + "\nУтверждения:\n" + "\n".join(rows) + "\n"


def parse_answers(text: str) -> dict[str, dict]:
    """Строки JSON из ответа модели (терпимо к ```-блокам и мусору между строками)."""
    out = {}
    for m in re.finditer(r"\{[^{}]*\}", text):
        try:
            d = json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
        eid, kind = str(d.get("id", "")).strip(), str(d.get("kind", "")).strip().lower()
        if re.fullmatch(r"E\d{2}", eid) and kind in KINDS:
            try:
                conf = float(d.get("confidence", 1.0))
            except (TypeError, ValueError):
                conf = 1.0
            out[eid] = {"kind": kind, "confidence": conf}
    return out


def score(items: list[dict], preds: dict[str, dict]) -> dict:
    n = len(items)
    ok = sum(preds.get(it["eid"], {}).get("kind") == gold_of(it) for it in items)
    clear = [it for it in items if not it.get("ambiguous")]
    ok_clear = sum(preds.get(it["eid"], {}).get("kind") == gold_of(it) for it in clear)
    per_kind = {}
    for k in KINDS:
        ks = [it for it in items if gold_of(it) == k]
        if ks:
            per_kind[k] = sum(preds.get(it["eid"], {}).get("kind") == k for it in ks) / len(ks)
    errors = [(it["eid"], it["claim_id"], gold_of(it), preds.get(it["eid"], {}).get("kind", "—"))
              for it in items if preds.get(it["eid"], {}).get("kind") != gold_of(it)]
    # «Фактом назвали не факт» — самая дорогая ошибка: гипотеза получает вес доказательства
    false_fact = sum(1 for _, _, g, p in errors if p == "fact" and g != "fact")
    return {"n": n, "accuracy": ok / n if n else 0.0, "clear_n": len(clear),
            "clear_accuracy": ok_clear / len(clear) if clear else 0.0, "per_kind": per_kind,
            "missing": sum(it["eid"] not in preds for it in items), "false_fact": false_fact, "errors": errors}


def cascade(cheap: dict[str, dict], strong: dict[str, dict], threshold: float) -> tuple[dict[str, dict], list[str]]:
    """Ответ дешёвой модели; при уверенности ниже порога (или без ответа) — ответ сильной."""
    out, escalated = {}, []
    for eid in sorted(set(cheap) | set(strong)):
        c = cheap.get(eid)
        if c and c["confidence"] >= threshold:
            out[eid] = c
        else:
            escalated.append(eid)
            if eid in strong:
                out[eid] = strong[eid]
            elif c:
                out[eid] = c
    return out, escalated


def _strat():
    sys.path.insert(0, str(EVAL.parent / "scripts"))
    import strat  # noqa: E402 — переиспользуем подсчёт токенов и цен
    return strat


def transcript_run(path: Path) -> dict:
    """Токены, $, время и текст последнего ответа из транскрипта субагента."""
    strat = _strat()
    msgs = strat.transcript_usage(path)
    cost = strat.usage_cost(msgs, strat.load_pricing())
    stamps, last_text = [], ""
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get("timestamp"):
            stamps.append(d["timestamp"])
        m = d.get("message")
        if d.get("type") == "assistant" and isinstance(m, dict):
            texts = []
            for b in m.get("content") or []:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "text":
                    texts.append(b.get("text", ""))
                elif b.get("type") == "tool_use" and b.get("name") == "SubagentHandback":
                    # итог субагента приходит вызовом SubagentHandback, а не текстом
                    texts += [v for v in (b.get("input") or {}).values() if isinstance(v, str)]
            if any(t.strip() for t in texts):
                last_text = "\n".join(texts)
    secs = 0.0
    if len(stamps) >= 2:
        ts = sorted(datetime.fromisoformat(s.replace("Z", "+00:00")) for s in stamps)
        secs = (ts[-1] - ts[0]).total_seconds()
    models = sorted(cost["by_model"]) or ["unknown"]
    return {"model": ",".join(models), "usd": round(cost["usd"], 6), "input": cost["input"], "output": cost["output"],
            "cache_write": cost["cache_write"], "cache_read": cost["cache_read"], "seconds": round(secs, 1),
            "tool_calls": sum(len(v.get("tools") or {}) for v in msgs.values()), "answer": last_text}


def load_runs() -> dict[str, dict]:
    return {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in sorted(RUNS.glob("*.json"))}


def cmd_record(a):
    if a.transcript:
        run = transcript_run(Path(a.transcript))
        if a.model:
            run["model"] = a.model
    else:
        run = {"model": a.model or "unknown", "usd": a.usd, "seconds": a.seconds,
               "answer": Path(a.answers).read_text(encoding="utf-8")}
    run["predictions"] = parse_answers(run.pop("answer"))
    run["note"] = a.note
    run["variant"] = a.variant
    RUNS.mkdir(exist_ok=True)
    (RUNS / f"{a.name}.json").write_text(json.dumps(run, ensure_ascii=False, indent=1), encoding="utf-8")
    s = score(load_items(), run["predictions"])
    print(f"{a.name}: {len(run['predictions'])} ответов, точность {s['accuracy']:.0%}, ${run['usd']:.4f}, {run['seconds']} с")


def table(items, runs: dict[str, dict]) -> str:
    head = ("| Прогон | Модель | Точность (40) | Однозначные | fact | hyp | fcst | asm | «факт» вместо не-факта "
            "| $ за 40 | Время, с |\n|---|---|---|---|---|---|---|---|---|---|---|")
    rows = []
    for name, r in runs.items():
        s = score(items, r["predictions"])
        pk = [f"{s['per_kind'].get(k, 0):.0%}" for k in KINDS]
        rows.append(f"| {name} | {r['model']} | {s['accuracy']:.0%} | {s['clear_accuracy']:.0%} | {' | '.join(pk)} "
                    f"| {s['false_fact']} | {r['usd']:.4f} | {r['seconds']:.0f} |")
    return head + "\n" + "\n".join(rows)


def cmd_score(a):
    items = load_items()
    runs = {n: r for n, r in load_runs().items() if r.get("variant", "base") == a.variant}
    print(f"Вариант задания: {a.variant}\n")
    if not runs:
        sys.exit("нет прогонов в eval/runs/")
    print(table(items, runs))
    print()
    for name, r in runs.items():
        errs = score(items, r["predictions"])["errors"]
        print(f"{name}: ошибки — " + (", ".join(f"{e}/{c} {g}→{p}" for e, c, g, p in errs) or "нет"))
    cheap = [n for n in runs if a.cheap in n]
    strong = [n for n in runs if a.strong in n]
    if cheap and strong:
        print(f"\nКаскад {a.cheap}→{a.strong} (эскалация при уверенности < порога):")
        print("| Пара | Порог | Эскалировано | Точность | $ (дешёвая + сильная на эскалированных, оценка) |\n|---|---|---|---|---|")
        for c in cheap:
            for s_ in strong:
                rc, rs = runs[c], runs[s_]
                for t in a.threshold:
                    pr, esc = cascade(rc["predictions"], rs["predictions"], t)
                    sc = score(items, pr)
                    usd = rc["usd"] + rs["usd"] * len(esc) / max(len(items), 1)
                    print(f"| {c}+{s_} | {t} | {len(esc)} | {sc['accuracy']:.0%} | {usd:.4f} |")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    pp = sub.add_parser("prompt")
    pp.add_argument("--hard", action="store_true", help="без источников, ссылок и меток типа в тексте")
    r = sub.add_parser("record")
    r.add_argument("name")
    r.add_argument("--transcript")
    r.add_argument("--answers")
    r.add_argument("--model")
    r.add_argument("--usd", type=float, default=0.0)
    r.add_argument("--seconds", type=float, default=0.0)
    r.add_argument("--note", default="")
    r.add_argument("--variant", choices=["base", "hard"], default="base")
    s = sub.add_parser("score")
    s.add_argument("--threshold", type=float, nargs="*", default=[0.7, 0.8, 0.9])
    s.add_argument("--cheap", default="haiku")
    s.add_argument("--strong", default="sonnet")
    s.add_argument("--variant", choices=["base", "hard"], default="base")
    a = ap.parse_args(argv)
    if a.cmd == "prompt":
        sys.stdout.reconfigure(encoding="utf-8")
        print(prompt_text(load_items(), hard=a.hard))
    elif a.cmd == "record":
        if not (a.transcript or a.answers):
            sys.exit("нужен --transcript или --answers")
        cmd_record(a)
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        cmd_score(a)


if __name__ == "__main__":
    main()

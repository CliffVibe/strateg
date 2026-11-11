"""T04: подсчёт точности классификатора типа утверждения и каскад «дешёвая модель → сильная»."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("score", REPO / "eval" / "score.py")
score = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score)


def item(eid, gold, human=None, ambiguous=False):
    return {"eid": eid, "claim_id": "C" + eid[1:], "text": "t", "sources": [], "depends_on": [],
            "gold": gold, "human": human, "ambiguous": ambiguous}


class EvalRoutingTest(unittest.TestCase):
    def test_dataset_is_40_blind_items_of_all_kinds(self):
        items = score.load_items()
        self.assertEqual(len(items), 40)
        self.assertEqual({score.gold_of(i) for i in items}, set(score.KINDS))
        prompt = score.prompt_text(items)
        rows = {r.split(" | ")[0]: r for r in prompt.splitlines() if r.startswith("E")}
        self.assertEqual(len(rows), 40)
        for it in items:  # в строке нет собственного ID реестра — тип не подсмотреть
            self.assertNotIn(it["claim_id"], rows[it["eid"]])
        self.assertNotIn("registry_kind", prompt)
        self.assertNotIn('"gold"', prompt)

    def test_hard_prompt_has_no_type_cues(self):
        hard = score.prompt_text(score.load_items(), hard=True)
        rows = [r for r in hard.splitlines() if r.startswith("E")]
        self.assertEqual(len(rows), 40)
        self.assertNotRegex(hard, r"C\d{3}")
        self.assertNotIn("источники:", hard)
        for r in rows:
            self.assertNotRegex(r, r"^E\d\d \| (Прогноз|Допущени)|red-team")
        self.assertEqual(score.strip_cues("Прогноз Q05 (при допущениях C027-C029): порог [C030]; см. (C025)"),
                         "(при допущениях): порог; см.")

    def test_parse_answers_tolerates_fences_and_junk(self):
        text = 'Вот:\n```json\n{"id": "E01", "kind": "Fact", "confidence": 0.9}\n{"id":"E02","kind":"guess"}\n' \
               '{"id": "E03", "kind": "forecast", "confidence": "high"}\n```'
        p = score.parse_answers(text)
        self.assertEqual(p["E01"], {"kind": "fact", "confidence": 0.9})
        self.assertNotIn("E02", p)  # неизвестный тип — не ответ
        self.assertEqual(p["E03"]["confidence"], 1.0)

    def test_score_uses_human_over_gold_and_counts_false_facts(self):
        items = [item("E01", "fact"), item("E02", "hypothesis", human="fact"), item("E03", "forecast", ambiguous=True),
                 item("E04", "hypothesis")]
        preds = {"E01": {"kind": "fact", "confidence": 1}, "E02": {"kind": "fact", "confidence": 1},
                 "E03": {"kind": "hypothesis", "confidence": 1}, "E04": {"kind": "fact", "confidence": 1}}
        s = score.score(items, preds)
        self.assertAlmostEqual(s["accuracy"], 0.5)
        self.assertAlmostEqual(s["clear_accuracy"], 2 / 3)
        self.assertEqual(s["false_fact"], 1)  # E04: гипотеза названа фактом
        self.assertEqual([e[0] for e in s["errors"]], ["E03", "E04"])

    def test_cascade_escalates_low_confidence_and_missing(self):
        cheap = {"E01": {"kind": "fact", "confidence": 0.95}, "E02": {"kind": "fact", "confidence": 0.5}}
        strong = {"E01": {"kind": "hypothesis", "confidence": 0.9}, "E02": {"kind": "hypothesis", "confidence": 0.9},
                  "E03": {"kind": "forecast", "confidence": 0.9}}
        out, esc = score.cascade(cheap, strong, 0.8)
        self.assertEqual(esc, ["E02", "E03"])
        self.assertEqual(out["E01"]["kind"], "fact")
        self.assertEqual(out["E02"]["kind"], "hypothesis")

    def test_transcript_run_reads_usage_time_and_answer(self):
        with tempfile.TemporaryDirectory() as d:
            tp = Path(d) / "agent-x.jsonl"
            lines = [
                {"type": "user", "timestamp": "2026-11-11T10:00:00Z", "message": {"role": "user", "content": "q"}},
                {"type": "assistant", "timestamp": "2026-11-11T10:00:12Z",
                 "message": {"id": "m1", "model": "claude-haiku-5-5", "content": [
                     {"type": "text", "text": '{"id": "E01", "kind": "fact", "confidence": 0.8}'}],
                     "usage": {"input_tokens": 1000, "output_tokens": 200}}},
            ]
            tp.write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")
            r = score.transcript_run(tp)
        self.assertEqual(r["seconds"], 12.0)
        self.assertEqual((r["input"], r["output"]), (1000, 200))
        self.assertAlmostEqual(r["usd"], (1000 * 0.1 + 200 * 0.5) / 1e6)
        self.assertEqual(score.parse_answers(r["answer"])["E01"]["kind"], "fact")

    def test_transcript_run_reads_subagent_handback(self):
        with tempfile.TemporaryDirectory() as d:
            tp = Path(d) / "agent-y.jsonl"
            line = {"type": "assistant", "timestamp": "2026-11-11T10:00:05Z",
                    "message": {"id": "m2", "model": "claude-sonnet-5-5", "usage": {"input_tokens": 10, "output_tokens": 5},
                                "content": [{"type": "tool_use", "id": "t1", "name": "SubagentHandback",
                                             "input": {"report": '{"id": "E02", "kind": "forecast", "confidence": 0.7}'}}]}}
            tp.write_text(json.dumps(line), encoding="utf-8")
            r = score.transcript_run(tp)
        self.assertEqual(score.parse_answers(r["answer"])["E02"], {"kind": "forecast", "confidence": 0.7})


if __name__ == "__main__":
    unittest.main()

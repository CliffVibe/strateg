"""T06 — устойчивость: параллельные сессии, обрыв хода, продолжение. Запуск: python -m unittest discover -s tests -v"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STRAT = REPO / "scripts" / "strat.py"
SESSION_VARS = ("CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID", "STRAT_SESSION")


class ResilienceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="strat-t06-"))
        shutil.copytree(REPO / "templates", self.tmp / "templates")
        shutil.copytree(REPO / "config", self.tmp / "config")
        (self.tmp / "projects").mkdir()
        base = {k: v for k, v in os.environ.items() if k not in SESSION_VARS and k != "STRAT_DEV"}
        self.env = {**base, "STRAT_ROOT": str(self.tmp), "PYTHONIOENCODING": "utf-8"}
        self.tdir = self.tmp / "transcripts"  # как ~/.claude/projects/<папка>/: транскрипты всех сессий папки
        self.tdir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_cli(self, *args, session=None, stdin=None):
        env = {**self.env, "CLAUDE_CODE_SESSION_ID": session} if session else self.env
        return subprocess.run([sys.executable, str(STRAT), *args], env=env, input=stdin,
                              capture_output=True, text=True, encoding="utf-8")

    def ok(self, *args, session=None, stdin=None):
        r = self.run_cli(*args, session=session, stdin=stdin)
        self.assertEqual(r.returncode, 0, f"{args}: {r.stdout}{r.stderr}")
        return r.stdout

    def hook(self, name, session, **extra):
        d = {"session_id": session, "transcript_path": str(self.tdir / f"{session}.jsonl"), **extra}
        return self.ok("hook", name, stdin=json.dumps(d))  # хук узнаёт сессию из входа, а не из окружения

    def transcript(self, session, msgs, append=False):
        """msgs: [(id, ts, output_tokens)] — по $10 за 1 млн выходных токенов sonnet."""
        t = self.tdir / f"{session}.jsonl"
        with t.open("a" if append else "w", encoding="utf-8") as f:
            for mid, ts, out in msgs:
                u = {"input_tokens": 0, "output_tokens": out, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}
                f.write(json.dumps({"type": "assistant", "timestamp": ts, "message": {
                    "id": mid, "model": "claude-sonnet-5-5", "usage": u, "content": []}}) + "\n")
        return t

    def cost(self, slug, session):
        f = self.tmp / "projects" / slug / "costs" / f"{session}.json"
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None

    def state(self, slug):
        return json.loads((self.tmp / "projects" / slug / "state.json").read_text(encoding="utf-8"))

    def activity(self, *events):
        (self.tmp / "projects" / ".activity.jsonl").write_text(
            "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in events), encoding="utf-8")

    # ── параллельные сессии в одной папке ──
    def test_session_keeps_its_project_when_another_session_switches(self):
        # T06: песочница создана в сессии A, пока сессия B работала над antifraud-free, — активный проект был один
        # на всю папку, и команды, хуки и бюджет B переключились бы на чужой проект
        self.ok("new", "main", "--title", "Основной", session="B")
        self.hook("session-start", "B")                       # B закрепила за собой main
        self.ok("new", "sandbox", "--title", "Песочница", session="A")  # A переключила папку на sandbox
        self.assertIn("(main)", self.ok("status", session="B"))
        self.ok("q", "add", "--text", "Вопрос B", session="B")
        self.assertEqual(len(json.loads((self.tmp / "projects" / "main" / "plan.json").read_text(encoding="utf-8"))["questions"]), 1)
        self.assertIn("(sandbox)", self.ok("status", session="A"))
        self.transcript("B", [])
        self.hook("stop", "B")
        self.assertIn("last_turn_at", self.state("main"))
        self.assertNotIn("last_turn_at", self.state("sandbox"))
        # новая сессия берёт проект, активный в папке на момент старта (так /resume находит прерванную работу)
        self.assertIn("(sandbox)", self.hook("session-start", "C"))
        self.assertIn("(sandbox)", self.ok("status", session="C"))

    def test_session_cost_follows_its_own_project_not_the_folder(self):
        # T06: сессия разработки T06 переключила папку → стоимость параллельной сессии ушла бы в чужой проект
        self.ok("new", "main", "--title", "Основной")
        self.ok("new", "sandbox", "--title", "Песочница")
        self.activity({"at": "2026-01-01T00:00:00+00:00", "slug": "main", "session": "B"},
                      {"at": "2026-02-01T00:00:00+00:00", "slug": "sandbox", "session": "A"})
        self.transcript("B", [("b1", "2026-03-01T00:00:00Z", 1000)])
        self.hook("stop", "B")
        self.assertEqual(self.cost("main", "B")["messages"], 1)
        self.assertIsNone(self.cost("sandbox", "B"))
        # старые сессии без своих активаций — как раньше, по истории папки
        self.transcript("old", [("o1", "2026-03-01T00:00:00Z", 1000)])
        self.hook("stop", "old")
        self.assertEqual(self.cost("sandbox", "old")["messages"], 1)

    def test_prelude_before_new_project_goes_to_new_project(self):
        # T10, задача 2: сессия закрепила проект папки (demo) при старте, затем /start создал новый — первые ответы
        # ($1,42) ушли в чужой проект
        self.ok("new", "demo", "--title", "Демо")
        self.ok("new", "esim", "--title", "eSIM")
        self.activity({"at": "2026-01-01T00:00:00+00:00", "slug": "demo", "session": "C", "how": "pin"},
                      {"at": "2026-01-01T00:01:00+00:00", "slug": "esim", "session": "C", "how": "new"})
        self.transcript("C", [("c1", "2026-01-01T00:00:30Z", 1000), ("c2", "2026-01-01T00:02:00Z", 1000)])
        self.hook("stop", "C")
        self.assertEqual(self.cost("esim", "C")["messages"], 2)
        self.assertIsNone(self.cost("demo", "C"))
        # закреплённый проект, в котором сессия продолжила работу (use), остаётся за ним
        self.activity({"at": "2026-02-01T00:00:00+00:00", "slug": "demo", "session": "D", "how": "pin"},
                      {"at": "2026-02-01T00:05:00+00:00", "slug": "esim", "session": "D", "how": "use"})
        self.transcript("D", [("d1", "2026-02-01T00:01:00Z", 1000)])
        self.hook("stop", "D")
        self.assertEqual(self.cost("demo", "D")["messages"], 1)

    # ── обрыв хода ──
    def test_interrupted_turn_is_costed_at_next_session_start(self):
        # Stop-хук не вызывается, если ход прерван (Ctrl+C, «Стоп») или окно закрыто: последний ход терялся
        self.ok("new", "demo", "--title", "Демо")
        self.transcript("A", [("a1", "2099-01-01T00:00:00Z", 1000)])
        self.hook("stop", "A")
        self.assertAlmostEqual(self.cost("demo", "A")["usd"], 0.01, places=6)
        self.transcript("A", [("a2", "2099-01-01T00:01:00Z", 2000)], append=True)  # ход прерван — Stop не было
        self.assertAlmostEqual(self.cost("demo", "A")["usd"], 0.01, places=6)
        self.transcript("B", [])
        self.hook("session-start", "B")  # новая сессия в той же папке досчитывает прерванную
        self.assertAlmostEqual(self.cost("demo", "A")["usd"], 0.03, places=6)
        before = (self.tmp / "projects" / "demo" / "costs" / "A.json").read_text(encoding="utf-8")
        self.hook("session-start", "B")  # повтор ничего не меняет
        self.hook("stop", "A")
        self.assertEqual(json.loads(before)["usd"], self.cost("demo", "A")["usd"])

    def test_session_end_records_cost(self):
        self.ok("new", "demo", "--title", "Демо")
        self.transcript("A", [("a1", "2099-01-01T00:00:00Z", 1000)])
        self.hook("session-end", "A")
        self.assertEqual(self.cost("demo", "A")["messages"], 1)

    def test_retried_question_done_drops_stale_error(self):
        # T06 вживую: Q01 упал (404), повтор с другим источником — done, а в plan.json висела старая ошибка
        self.ok("new", "demo", "--title", "Демо")
        self.ok("q", "add", "--text", "Вопрос")
        self.ok("q", "start", "Q01")
        self.ok("q", "fail", "Q01", "--text", "404")
        self.ok("q", "start", "Q01")
        self.ok("q", "done", "Q01", "--claims", "C001")
        plan = json.loads((self.tmp / "projects" / "demo" / "plan.json").read_text(encoding="utf-8"))
        q = plan["questions"][0]
        self.assertEqual((q["status"], q["attempts"]), ("done", 2))
        self.assertNotIn("error", q)
        journal = (self.tmp / "projects" / "demo" / "journal.md").read_text(encoding="utf-8")
        self.assertIn("Q01 → failed: 404", journal)  # история сбоя не теряется


if __name__ == "__main__":
    unittest.main()

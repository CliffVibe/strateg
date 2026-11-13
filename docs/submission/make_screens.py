"""Скриншоты для описания работы (T10): настоящие выводы команд strat и отчёт демо, отрисованные Edge headless.
Запуск из корня репозитория: python docs/submission/make_screens.py  (stdlib; нужен Microsoft Edge)."""
import html
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "submission" / "screens"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}


def run(args: list[str], stdin: str | None = None) -> tuple[str, int]:
    r = subprocess.run([sys.executable, "scripts/strat.py", *args], cwd=ROOT, input=stdin, capture_output=True,
                       text=True, encoding="utf-8", env=ENV)
    return (r.stdout + r.stderr).rstrip(), r.returncode


def shot(page: Path, png: Path, w: int, h: int):
    """Edge headless иногда завершается, не записав файл (когда открыт обычный Edge) — повторяем до трёх раз."""
    import time
    tmp = page.with_suffix(".tmp.png")
    for _ in range(3):
        subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        f"--user-data-dir={Path(__import__('tempfile').gettempdir()) / 'strateg-edge'}",
                        f"--window-size={w},{h}", f"--screenshot={tmp}", page.as_uri()], capture_output=True)
        for _ in range(20):
            if tmp.exists() and tmp.stat().st_size:
                tmp.replace(png)
                return
            time.sleep(0.25)
    raise RuntimeError(f"Edge не сохранил скриншот {png.name}")

def terminal(name: str, blocks: list[tuple[str, str]], w: int = 1100):
    body = "".join(f'<div class="cmd">$ {html.escape(c)}</div><pre>{html.escape(o)}</pre>' for c, o in blocks)
    per_line = (w - 40) // 8.4  # символов в строке Consolas 15px — длинные строки переносятся
    lines = sum(2 + sum(max(1, -(-len(x) // int(per_line))) for x in o.splitlines()) for _, o in blocks)
    page = OUT / f"{name}.html"
    page.write_text(f"""<!doctype html><meta charset="utf-8"><style>
body{{margin:0;background:#0c0c0c;color:#d6d6d6;font:15px/1.45 Consolas,'Cascadia Mono',monospace;padding:14px 18px}}
.cmd{{color:#7fd4ff;margin-top:6px}} pre{{margin:2px 0 8px;white-space:pre-wrap}}</style>{body}""", encoding="utf-8")
    shot(page, OUT / f"{name}.png", w, 40 + lines * 22)
    page.unlink()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    demo = ["-p", "demo-app-retention"]
    terminal("t-status-cost", [("python scripts/strat.py status", run([*demo, "status"])[0]),
                               ("python scripts/strat.py cost", run([*demo, "cost"])[0].split("\nЦены:")[0])])
    blk = '{"tool_name":"Write","tool_input":{"file_path":"projects/demo-app-retention/inputs/brief.md"}}'
    out, code = run(["hook", "protect"], stdin=blk)
    sh = '{"tool_name":"Bash","tool_input":{"command":"echo x >> projects/demo-app-retention/claims.jsonl"}}'
    out2, code2 = run(["hook", "protect"], stdin=sh)
    terminal("t-guard", [("hook protect ← Write projects/demo-app-retention/inputs/brief.md", f"{out}\n(код {code} — действие запрещено)"),
                         ("hook protect ← Bash: echo x >> projects/demo-app-retention/claims.jsonl", f"{out2}\n(код {code2})")])
    terminal("t-impact", [("python scripts/strat.py impact S026", run([*demo, "impact", "S026"])[0]),
                          ("python scripts/strat.py decision review", run([*demo, "decision", "review"])[0])])
    chk = run([*demo, "check"])[0].splitlines()
    terminal("t-check", [("python scripts/strat.py check   (первые строки из " + str(len(chk)) + ")",
                          "\n".join(chk[:9]) + f"\n…\nИтог: ошибок {sum(x.startswith('✗') for x in chk)}, "
                          f"предупреждений {sum(x.startswith('⚠') for x in chk)}")])
    shot(ROOT / "projects" / "demo-app-retention" / "report.html", OUT / "report-demo.png", 1200, 1500)
    shot(ROOT / "projects" / "esim-travel" / "report.html", OUT / "report-esim.png", 1200, 1300)
    print("\n".join(sorted(p.name for p in OUT.glob("*.png"))))


if __name__ == "__main__":
    main()

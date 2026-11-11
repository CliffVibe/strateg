"""T08: обезличенный пакет для слепой оценки полезности (docs/05-evaluation.md, шаг 3).
B — report.md на момент сдачи T02 (коммит 61ba0f2), ссылки [C…]/[S…] заменены ссылками на источники, как у A;
убраны признаки агента: номера решений, пути work/…, раздел «Как получен результат».
Запуск: python eval/antifraud-free/make_blind.py → blind/doc-1.md, blind/doc-2.md, blind/form.md; ключ — blind-key.json."""
import json
import random
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
COMMIT = "61ba0f2"
KIND_WORD = {"assumption": "допущение", "forecast": "прогноз", "hypothesis": "гипотеза", "fact": "факт"}


def git_show(path: str) -> str:
    return subprocess.run(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT, capture_output=True, check=True).stdout.decode("utf-8")


def expand(ids: str) -> list[str]:
    out = []
    for part in re.split(r",\s*", ids):
        m = re.fullmatch(r"([CS])(\d{3})\s*[–-]\s*[CS]?(\d{3})", part.strip())
        if m:
            out += [f"{m.group(1)}{n:03d}" for n in range(int(m.group(2)), int(m.group(3)) + 1)]
        elif part.strip():
            out.append(part.strip())
    return out


def main():
    report = git_show("projects/antifraud-free/report.md")
    (HERE / "B-report-v1.md").write_text(report, encoding="utf-8")  # как было сдано — для протокола
    claims = {c["id"]: c for c in map(json.loads, git_show("projects/antifraud-free/claims.jsonl").splitlines()) if c}
    sources = {s["id"]: s for s in map(json.loads, git_show("projects/antifraud-free/sources.jsonl").splitlines()) if s}

    def link_for(ids: str) -> str:
        urls, words = [], []
        for i in expand(ids):
            if i.startswith("S"):
                srcs = [i]
            else:
                c = claims.get(i, {})
                srcs = c.get("sources", [])
                if not any(sources.get(s, {}).get("url") for s in srcs):
                    words.append(KIND_WORD.get(c.get("kind"), "оценка"))
            for s in srcs:
                u = sources.get(s, {}).get("url")
                if u and u not in urls:
                    urls.append(u)
        parts = [f"[{urlparse(u).netloc.removeprefix('www.')}]({u})" for u in urls]
        parts += sorted(set(words))
        return f"({', '.join(parts)})" if parts else ""

    text = re.sub(r"\[((?:[CS]\d{3}(?:\s*[–-]\s*[CS]?\d{3})?(?:,\s*)?)+)\]", lambda m: link_for(m.group(1)), report)
    text = re.sub(r"\n*Подробно: `work/[^`]+`\.?", "", text)
    text = re.sub(r"\s*\(выбрана руководителем, D001\)", "", text)
    text = re.sub(r"\*\*D\d{3}:\*\*\s*", "", text)
    text = re.split(r"\n## 7\. Как получен результат", text)[0].rstrip() + "\n"
    a = (HERE / "A-output.md").read_text(encoding="utf-8")

    rnd = random.Random(2211)
    order = ["A", "B"] if rnd.random() < 0.5 else ["B", "A"]
    out = HERE / "blind"
    out.mkdir(exist_ok=True)
    docs = {"A": a, "B": text}
    for n, who in enumerate(order, 1):
        (out / f"doc-{n}.md").write_text(docs[who], encoding="utf-8")
    key_path = HERE / "blind-key.json"
    key = json.loads(key_path.read_text(encoding="utf-8")) if key_path.exists() else {}
    key["usefulness_docs"] = {f"doc-{n}": who for n, who in enumerate(order, 1)}
    key_path.write_text(json.dumps(key, ensure_ascii=False, indent=1), encoding="utf-8")
    print("B blind chars:", len(text), "· A chars:", len(a), "· leftover refs:", re.findall(r"\[[CSD]\d{3}", text))


if __name__ == "__main__":
    main()

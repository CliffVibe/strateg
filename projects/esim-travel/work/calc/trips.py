"""Q04: динамика выездов, туристических поездок, топ-5, потолок eSIM-аудитории 2027.
Читает только inputs/trips-outbound.csv. Python stdlib. Запуск: python trips.py
Единицы: поездки (пересечения границы по ФСБ), НЕ люди."""
import csv, re, sys, io
from pathlib import Path
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
SRC = Path(__file__).resolve().parents[2] / "inputs" / "trips-outbound.csv"
# В inputs/ 6 строк с неэкранированными запятыми внутри полей metric/note (поле значения сдвигается).
# Файл менять нельзя -> читаем толерантно: значение = первое чисто числовое поле после 4-го, metric = склейка до него.
rows, repaired = [], 0
for i, f in enumerate(csv.reader(open(SRC, encoding="utf-8"))):
    if i == 0:
        continue
    k = next(j for j in range(4, len(f)) if re.fullmatch(r"\d+", f[j].strip()))
    if len(f) != 9:
        repaired += 1
    rows.append(dict(period=f[0], period_type=f[1], geography=f[2], metric=",".join(f[3:k]).strip(),
                     value=float(f[k]), unit=f[k + 1], source=f[k + 2], claim=f[k + 3], note=",".join(f[k + 4:])))
print("строк прочитано:", len(rows), "| из них с неэкранированными запятыми (починено при чтении):", repaired)
assert all(len(r["metric"]) > 5 for r in rows)


def get(period, geo, metric_start, ptype="year"):
    m = [r for r in rows if r["period"] == str(period) and r["geography"] == geo
         and r["metric"].startswith(metric_start) and r["period_type"] == ptype]
    assert len(m) == 1, (period, geo, metric_start, len(m))
    return m[0]["value"]


ALL = "выезды граждан РФ (ФСБ, все цели"
TOUR = "туристические поездки (ФСБ"
checks = []


def check(name, ok, detail=""):
    checks.append(ok)
    print(("[OK]  " if ok else "[FAIL] ") + name, detail)


print("== 1. Качество данных ==")
print("строк:", len(rows), "| единицы:", dict(Counter(r["unit"] for r in rows)))
keys = Counter((r["period"], r["period_type"], r["geography"], r["metric"]) for r in rows)
check("дубликатов ключа нет", max(keys.values()) == 1)
no_claim = [f'{r["period"]} {r["geography"]} {r["metric"][:22]}' for r in rows if not r["claim"]]
print("строк без ссылки на утверждение (claim пусто):", len(no_claim), "->", no_claim)
check("значения > 0", all(r["value"] > 0 for r in rows))

print("\n== 2. Динамика (поездок, годы) ==")
res = {}
for label, pref in (("все цели", ALL), ("туризм", TOUR)):
    v = {y: get(y, "Всего", pref) for y in (2023, 2024, 2025)}
    g24, g25 = v[2024] / v[2023] - 1, v[2025] / v[2024] - 1
    cagr = (v[2025] / v[2023]) ** 0.5 - 1
    res[label] = (v, g24, g25, cagr)
    print(f"{label}: 2023 {v[2023]/1e6:.1f} -> 2024 {v[2024]/1e6:.1f} -> 2025 {v[2025]/1e6:.1f} млн поездок; "
          f"г/г 2024 {g24:+.1%}, 2025 {g25:+.1%}; CAGR 2023-25 {cagr:+.1%}")
va, vt = res["все цели"][0], res["туризм"][0]
for y in (2023, 2024, 2025):
    print(f"  доля туризма в выездах {y}: {vt[y]/va[y]:.1%}")
check("заявленный рост 2024 (все цели) +7,8%", abs(res["все цели"][1] - 0.078) < 0.003, f'расчёт {res["все цели"][1]:+.2%}')
check("заявленный рост 2025 (все цели) +8%", abs(res["все цели"][2] - 0.08) < 0.005, f'расчёт {res["все цели"][2]:+.2%}')
check("заявленный рост туризма 2025 +15,6%", abs(res["туризм"][2] - 0.156) < 0.005, f'расчёт {res["туризм"][2]:+.2%} (округление млн)')
d_all, d_tour = (va[2025] - va[2023]) / 1e6, (vt[2025] - vt[2023]) / 1e6
print(f"прирост 2023->2025, млн поездок: все цели {d_all:+.1f}; туризм {d_tour:+.1f} -> {d_tour/d_all:.0%} прироста выездов дал туризм")

print("\n== 3. Топ-5 стран, туристические поездки 2025 ==")
countries = {r["geography"]: r["value"] for r in rows
             if r["period"] == "2025" and r["period_type"] == "year" and r["metric"].startswith(TOUR) and r["geography"] != "Всего"}
ranked = sorted(countries.items(), key=lambda kv: -kv[1])
for i, (c, v) in enumerate(ranked, 1):
    print(f"  {i:2d}. {c:11s} {v/1e6:6.3f} млн  {v/vt[2025]:5.1%} от 13,4 млн")
top5 = sum(v for _, v in ranked[:5])
top10 = sum(v for _, v in ranked)
print(f"топ-5 = {top5/1e6:.2f} млн = {top5/vt[2025]:.1%}; в таблице 10 стран = {top10/1e6:.2f} млн = {top10/vt[2025]:.1%}; прочие = {(vt[2025]-top10)/1e6:.2f} млн")
check("сумма стран <= итога", top10 <= vt[2025])
check("топ-5 из C090 = Турция, ОАЭ, Египет, Китай, Таиланд", [c for c, _ in ranked[:5]] == ["Турция", "ОАЭ", "Египет", "Китай", "Таиланд"])
growth = {}
top5d = dict(ranked[:5])
for r in rows:
    if r["period"] == "2025" and r["metric"].startswith(TOUR) and r["geography"] in top5d:
        m = re.search(r"([+-]\d+[.,]?\d*)%", r["note"])
        growth[r["geography"]] = float(m.group(1).replace(",", ".")) / 100
base24 = sum(top5d[c] / (1 + g) for c, g in growth.items())
print(f"оценка топ-5 в 2024 по г/г из примечаний: {base24/1e6:.2f} млн = {base24/vt[2024]:.1%} от 11,6 млн (оценка, округления источника)")

print("\n== 4. Единицы: туристические vs все цели, 2025 ==")
for c in ("Турция", "Таиланд", "Вьетнам"):
    a = [r["value"] for r in rows if r["period"] == "2025" and r["geography"] == c and r["metric"] == "выезды (ФСБ все цели)"]
    t = countries.get(c)
    if a:
        print(f"  {c}: все цели {a[0]/1e6:.2f} млн, туризм {t/1e6:.2f} млн -> туризм = {t/a[0]:.0%} поездок в страну")
print("  Абхазия 2024: все цели 5,9 млн (маятниковые пересечения) vs туризм 2025 0,87 млн -> 'все цели' включает не-туризм; для eSIM берём только туризм")
print("  ФСБ считает пересечения: один человек = несколько поездок; уникальных путешественников в данных нет (C096).")

print("\n== 5. Расхождение 2025: Ведомости 29,4 vs ФСБ 31,5 млн ==")
ved = None
for r in rows:
    m = re.search(r"Ведомости.*?пишут (\d+[.,]\d+) млн", r["note"])
    if m:
        ved = float(m.group(1).replace(",", ".")) * 1e6
assert ved
fsb = va[2025]
print(f"Ведомости {ved/1e6:.1f} vs ФСБ {fsb/1e6:.1f}: разница {(fsb-ved)/1e6:.1f} млн = {(fsb-ved)/fsb:.1%} от ФСБ")
print(f"Ведомости пишут +7%: при базе ФСБ 2024 ({va[2024]/1e6:.1f}) 29,4 дало бы {ved/va[2024]-1:+.1%}, а не +7% -> внутренняя несогласованность; "
      f"+7% подразумевает базу {ved/1.07/1e6:.1f} млн (ближе к 2023 = 27,1) -> вероятно иная методика/период.")
share_9m = {y: get(y, "Всего", ALL, "9 месяцев") / get(y, "Всего", ALL) for y in (2023, 2024)}
print("доля 9 месяцев в году (все цели): 2023 %.1f%%, 2024 %.1f%%; для 2025 -> 9М ≈ %.1f млн (оценка), близко к 'Росстат >24 млн' (C098)." % (
    100 * share_9m[2023], 100 * share_9m[2024], fsb * share_9m[2024] / 1e6))
h1 = get(2025, "Всего", ALL, "полугодие (янв-июн)")
print(f"H1 2025 {h1/1e6:.1f} млн = {h1/fsb:.1%} от года 31,5 (H1 2024 ~12,6 из 29,2 = {12.6/29.2:.1%}; ряд H1 2024 - по поиску без снимка)")
check("31,5 согласуется с H1 (доля H1 42-45%)", 0.42 < h1 / fsb < 0.45, f"{h1/fsb:.1%}")
print("вывод: в расчёт берём ФСБ 31,5 / 13,4 (туризм); 29,4 - нижняя граница неопределённости; на туристический ряд 13,4 не влияет.")

print("\n== 6. Потолок eSIM-аудитории 2027 (туристические поездки) ==")
base = vt[2025]
print("Потолок = ВСЕ туристические поездки (100% с eSIM-совместимым телефоном и желанием) - верхняя граница, не прогноз покупок.")
print("Сценарии роста 2027 к 2025: 0 / +5% / +10% (допущение; справочно: 2025 +15,6%, CAGR 2023-25 +20% -> сценарии консервативны)")
ceil = {}
for g in (0.0, 0.05, 0.10):
    ceil[g] = base * (1 + g)
    lo, hi = ceil[g] / 1.6, ceil[g] / 1.2
    print(f"  +{g:.0%}: {ceil[g]/1e6:.2f} млн туристических поездок; в людях при 1,2-1,6 поездок/чел. (допущение) ~ {lo/1e6:.1f}-{hi/1e6:.1f} млн путешественников")
print(f"Справочно: рост как CAGR 2023-25 ({res['туризм'][3]:+.0%}/год) дал бы 2027 = {base*(1+res['туризм'][3])**2/1e6:.1f} млн (вне сценариев)")
print("Ориентир: 9%% поездок на международной eSIM (ComNews, C007) = %.2f-%.2f млн покупок/год на ВЕСЬ рынок (до выбора оператора)" % (ceil[0.0] * 0.09 / 1e6, ceil[0.10] * 0.09 / 1e6))
print("Ограничения: данные - поездки; 2026 и сезонность по месяцам в таблице отсутствуют; Абхазия/СНГ внутри туристических поездок (Абхазия 0,87 млн) - роуминг там иной.")
print("\nИТОГО проверок: %d/%d пройдено" % (sum(checks), len(checks)))

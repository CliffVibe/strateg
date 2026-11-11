"""Пересмотр (T05, 2026-11-11): фактическая цена платного уровня МегаФона по ComNews (июнь–июль 2026) —
«Моя безопасность+» / «ИИ-защита в звонках» 149 ₽ за 30 дней [S028, C075], а не base 199 ₽ из допущения C027.

Новое допущение C078: price low/base/high = 149 / 149 / 249 ₽ (наблюдаемая цена прайса МегаФона — base;
249 ₽ — верх рынка, Билайн PRO [C076]; ниже 149 ₽ не берём — промо-период 7 дней не учитываем).
Остальные допущения не меняются (C028, C029, C064).

Скрипт не правит исходные расчёты (S018, S024): он исполняет их код с заменой одной строки — цены,
так что формулы те же, а старые выводы остаются воспроизводимыми.
Запуск: python work/calc/rev_price149.py
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).parent


def run(script, old, new, extra_globals=None):
    src = (HERE / script).read_text(encoding="utf-8")
    assert src.count(old) == 1, f"{script}: не нашёл строку для замены: {old}"
    src = src.replace(old, new)
    # проверка в q05 сверяет вклад с ценой 199 — подменяем на новую базу
    src = src.replace("30_000*199*0.65", "30_000*149*0.65")
    g = {"__name__": "__main__", "__file__": str(HERE / script)}
    g.update(extra_globals or {})
    exec(compile(src, script, "exec"), g)
    return g


print("############ Q05 при цене 149 / 149 / 249 ₽ (C078) ############")
q = run("q05_breakeven.py", '"price":  (149, 199, 249)', '"price":  (149, 149, 249)')

print("\n############ E и пилот при цене 149 ₽ (C078) ############")
e = run("e_economics_pilot.py", "PAY_SHARE, PRICE, SVC_MARGIN = 0.03, 199, 0.65",
        "PAY_SHARE, PRICE, SVC_MARGIN = 0.03, 149, 0.65")

# Порог E точнее, чем печатает e_economics (там округление до 0,001 п.п.) — для выборки под порог
A = e["A_CONTRIB"]; RV = e["RETAINED_VALUE"]; N = e["N"]
need_e = (A * (1 - 0.85) + N * 0.20 * 8 * (1 - 0.3)) / RV / N * 100
p0 = e["p0_3m"]
print(f"\nВыборка под новый порог E {need_e:.3f} п.п./мес: n на группу = {e['n_per_group'](p0, p0 - need_e / 100 * 3):,}")

print("\n############ Калибровка по отчётности и масштаб на базу МегаФона (как в C073, C074) ############")
ARPU_REP, M_REP, LIFE = 468, 0.423, 18          # C071, C068; срок — допущение C028
rv_rep = ARPU_REP * M_REP * LIFE
paid = N * 0.03 * 149 * 0.65
b_eff = -(paid + N * 0.25 * 15)                 # B base: adopt 25%, 15 ₽
e_eff = -(paid * (1 - 0.85) + N * 0.20 * 8 * (1 - 0.3))
print(f"ценность удержанного по отчётности: {rv_rep:,.0f} ₽; порог B {-b_eff / rv_rep / N * 100:.3f}, "
      f"E {-e_eff / rv_rep / N * 100:.3f} п.п./мес")
BASE_MF = 79.37                                  # млн абонентов, C069
print(f"масштаб на {BASE_MF} млн: B {b_eff * BASE_MF / 1e6:,.0f} млн ₽/мес ({b_eff * BASE_MF * 12 / 1e9:.1f} млрд ₽/год); "
      f"E {e_eff * BASE_MF / 1e6:,.0f} млн ₽/мес ({e_eff * BASE_MF * 12 / 1e9:.1f} млрд ₽/год)")
for name, s in e["SCEN"].items():
    d = -(paid * (1 - s["keep"]) + N * s["optin"] * s["cost"] * (1 - s["partner"]))
    print(f"  E {name}: {d * BASE_MF * 12 / 1e9:.1f} млрд ₽/год")

"""Экономика варианта E (freemium + партнёр) и размер выборки пилота.

Все вводные — допущения (данных МегаФона нет). Расчёт на 1 млн абонентов, помесячно.
База A и ценность удержанного абонента — из q05_breakeven.py (base-сценарий, допущения C027–C028).
Запуск: python work/calc/e_economics_pilot.py
"""
from math import ceil, sqrt
from statistics import NormalDist

N = 1_000_000
# --- base-допущения Q05 (C027, C028)
PAY_SHARE, PRICE, SVC_MARGIN = 0.03, 199, 0.65
ARPU, CONTRIB, LIFE_M = 500, 0.38, 18
BASE_CHURN = 0.02
A_CONTRIB = N * PAY_SHARE * PRICE * SVC_MARGIN          # вклад платного уровня в A, ₽/мес
RETAINED_VALUE = ARPU * CONTRIB * LIFE_M                  # вклад одного удержанного абонента, ₽

# --- допущения E (low / base / high для E — от худшего к лучшему)
SCEN = {
    "худший":  dict(optin=0.30, cost=15, keep=0.70, partner=0.0),
    "базовый": dict(optin=0.20, cost=8,  keep=0.85, partner=0.3),
    "лучший":  dict(optin=0.15, cost=3,  keep=0.95, partner=0.5),
}

print("=== Экономика E против A (на 1 млн абонентов, ₽/мес) ===")
print(f"Вклад платного уровня в A: {A_CONTRIB/1e6:.2f} млн ₽/мес; ценность удержанного абонента: {RETAINED_VALUE:,.0f} ₽")
for name, s in SCEN.items():
    lost_paid = A_CONTRIB * (1 - s["keep"])                       # платящие, ушедшие в бесплатный уровень
    free_cost = N * s["optin"] * s["cost"] * (1 - s["partner"])   # затраты на бесплатное предупреждение после доли партнёра
    delta = -(lost_paid + free_cost)                              # без эффекта на отток
    need_pp = -delta / RETAINED_VALUE / N * 100                   # требуемое снижение оттока, п.п./мес по всей базе
    print(f"{name:8s}: потеря платного {lost_paid/1e6:5.2f} + затраты бесплатного {free_cost/1e6:5.2f} "
          f"= {delta/1e6:6.2f} млн ₽/мес; порог: −{need_pp:.3f} п.п./мес ({need_pp/ (BASE_CHURN*100):.0%} оттока)")
    # проверка: при пороге эффект = 0
    assert abs(delta + need_pp / 100 * N * RETAINED_VALUE) < 1e-3

print("\n=== Размер выборки пилота (двусторонний тест долей, α=5%, мощность 80%) ===")
z = NormalDist().inv_cdf(0.975) + NormalDist().inv_cdf(0.80)
def n_per_group(p0, p1):
    pbar = (p0 + p1) / 2
    return ceil((z * sqrt(2 * pbar * (1 - pbar))) ** 2 / (p0 - p1) ** 2)

p0_3m = 1 - (1 - BASE_CHURN) ** 3   # кумулятивный отток за 3 мес. ≈ 5,9%
for rel in (0.10, 0.20, 0.30):
    for uptake in (1.0, 0.30):
        p1 = p0_3m * (1 - rel * uptake)  # ITT: эффект разбавлен долей подключивших
        print(f"снижение оттока у подключивших {rel:.0%}, подключились {uptake:.0%} предложенных: "
              f"отток 3 мес {p0_3m:.2%} → {p1:.2%}; n на группу = {n_per_group(p0_3m, p1):,}")

print("\n=== Выборка под порог окупаемости E (анализ по намерению) ===")
# Порог E по всей базе −0,05 п.п./мес [C065]; при раскатке подключаются ~20–30% — как в группе предложения,
# поэтому порог сопоставим с эффектом «группа предложения против контроля».
for thr_pp_month in (0.05, 0.08):
    p1 = p0_3m - thr_pp_month / 100 * 3
    print(f"MDE {thr_pp_month} п.п./мес (за 3 мес {p0_3m:.2%} → {p1:.2%}): n на группу = {n_per_group(p0_3m, p1):,}")

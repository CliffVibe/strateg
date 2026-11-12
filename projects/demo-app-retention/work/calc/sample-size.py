"""MDE для плана проверки варианта C. Только stdlib. Входы — допущения (внутренних данных нет).
Дизайн 1: holdout — доля h пользователей приложения получает улучшения ядра на 6 мес позже;
сравниваем накопленный 6-мес. отток (две доли), alpha=0,05 двусторонний, мощность 80%.
Дизайн 2: A/B нового бота, 2 недели, метрика — доля обращений, решённых без оператора.
MDE считается по нормальному приближению с разными дисперсиями под H0/H1 (решаем итерацией).
DEFF — поправка на кластеризацию (повторные обращения одного пользователя, семьи); база 1.
Читает порог окупаемости из unit-economics.py.
"""
import importlib.util, math, os
from statistics import NormalDist

here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ue", os.path.join(here, "unit-economics.py"))
ue = importlib.util.module_from_spec(spec); spec.loader.exec_module(ue)

ALPHA, POWER = 0.05, 0.80
Z = NormalDist().inv_cdf(1 - ALPHA / 2) + NormalDist().inv_cdf(POWER)  # 2.8016

AUD = ue.ASSUME["A"]                 # 12/18/25 млн
HOLD = (0.01, 0.02, 0.05, 0.10)      # доли holdout
CHURN = ue.ASSUME["CHURN"]
BASE_SEC = (0.40, 0.50, 0.60)        # допущение: база доли «решено без оператора»
VOL_SEC = (1e6, 1.5e6, 2e6)          # допущение: обращений в месяц

def mde_abs(p0, n1, n2, deff=1.0):
    """Минимальная разница долей (p0 - p1) при p1 < p0, мощность POWER."""
    d = 0.0
    for _ in range(100):
        p1 = p0 - (d if d else 1e-4)
        se_h0 = math.sqrt(deff * ((p0 + p1) / 2) * (1 - (p0 + p1) / 2) * (1 / n1 + 1 / n2))
        se_h1 = math.sqrt(deff * (p0 * (1 - p0) / n1 + p1 * (1 - p1) / n2))
        nd = NormalDist().inv_cdf(1 - ALPHA / 2) * se_h0 + NormalDist().inv_cdf(POWER) * se_h1
        if abs(nd - d) < 1e-12: break
        d = nd
    return d

def mde_sec(p0, n1, n2, deff=1.0):  # рост доли (p1 > p0), симметрично по формуле через p0
    return mde_abs(p0, n1, n2, deff)

def monthly_from_6m(p6):  return 1 - (1 - p6) ** (1 / 6)
def six_from_monthly(c):  return 1 - (1 - c) ** 6

def mde_monthly_pp(c0, h, A, deff=1.0):
    p0 = six_from_monthly(c0)
    d6 = mde_abs(p0, h * A, (1 - h) * A, deff)   # группа holdout n1 = h*A
    c1 = monthly_from_6m(p0 - d6)
    return d6 * 100, (c0 - c1) * 100

if __name__ == "__main__":
    print(f"Z (alpha 0,05 двуст., мощность 80%) = {Z:.4f}")
    b = ue.base()
    t_base = ue.thr(b)
    best = dict(b, A=ue.ASSUME["A"][2], ARPU=ue.ASSUME["ARPU"][2], MARGIN=ue.ASSUME["MARGIN"][2], R=ue.ASSUME["R"][0])
    worst = dict(b, A=ue.ASSUME["A"][0], ARPU=ue.ASSUME["ARPU"][0], MARGIN=ue.ASSUME["MARGIN"][0], R=ue.ASSUME["R"][2])
    t_best, t_worst = ue.thr(best), ue.thr(worst)
    print(f"Порог окупаемости (п.п. месячного оттока): база {t_base:.4f}, лучший {t_best:.4f}, худший {t_worst:.4f}")

    print("\n== MDE holdout (DEFF=1), отток 2,0%%/мес (6 мес = %.2f%%): MDE за 6 мес п.п. | в пересчёте на месяц п.п. ==" % (six_from_monthly(0.02)*100))
    print("Аудитория  " + "  ".join(f"h={h:.0%}".rjust(15) for h in HOLD))
    for A in AUD:
        cells = []
        for h in HOLD:
            d6, dm = mde_monthly_pp(0.02, h, A)
            cells.append(f"{d6:.3f}|{dm:.4f}".rjust(15))
        print(f"{A/1e6:>6.0f}млн  " + "  ".join(cells))

    print("\n== Тот же расчёт при DEFF=2 и оттоке 3,0%/мес, A=18 млн: месячный MDE, п.п. ==")
    for c0 in CHURN:
        for deff in (1.0, 2.0):
            print(f"отток {c0:.1%} DEFF={deff:.0f}: " + "  ".join(f"h={h:.0%}: {mde_monthly_pp(c0, h, 18e6, deff)[1]:.4f}" for h in HOLD))

    print("\n== Видит ли тест порог? (A=18млн, отток 2%, DEFF=1 и 2); отношение MDE_мес / порог ==")
    for name, t in (("база", t_base), ("лучший", t_best), ("худший", t_worst)):
        for deff in (1.0, 2.0):
            r = "  ".join(f"h={h:.0%}: {mde_monthly_pp(0.02, h, 18e6, deff)[1]/t:.2f}" for h in HOLD)
            print(f"порог {name:7s} ({t:.4f}) DEFF={deff:.0f}: {r}")
    print("(<1: тест различает эффект на уровне порога; >1: не различает)")

    # минимальный holdout, при котором MDE <= порог (A=18млн, отток 2%)
    print("\n== Минимальная доля holdout, при которой MDE_мес <= порог (A=18млн, отток 2%) ==")
    for name, t in (("база", t_base), ("лучший", t_best), ("худший", t_worst)):
        for deff in (1.0, 2.0):
            lo, hi = 1e-5, 0.5
            if mde_monthly_pp(0.02, hi, 18e6, deff)[1] > t: print(f"{name} DEFF={deff:.0f}: недостижимо"); continue
            for _ in range(60):
                mid = (lo + hi) / 2
                if mde_monthly_pp(0.02, mid, 18e6, deff)[1] > t: lo = mid
                else: hi = mid
            print(f"{name:7s} DEFF={deff:.0f}: h >= {hi:.3%} ({hi*18e6:,.0f} пользователей)")

    print("\n== Вторичная метрика: доля обращений, решённых в приложении без оператора. A/B 50/50, 2 недели ==")
    print("(обращений за 2 недели = объём в месяц * 14/30,4 (0,46 месяца); MDE в п.п.; DEFF 1 | 2)")
    for vol in VOL_SEC:
        n = vol * 14 / 30.4
        for p0 in BASE_SEC:
            print(f"{vol/1e6:.1f} млн/мес, база {p0:.0%}: n всего {n:,.0f}; MDE {mde_sec(p0, n/2, n/2)*100:.2f} | {mde_sec(p0, n/2, n/2, 2.0)*100:.2f} п.п.")
    # проверки
    assert abs(Z - 2.8016) < 1e-3
    d6, dm = mde_monthly_pp(0.02, 0.5, 18e6)
    se = math.sqrt(0.0 + 2 * six_from_monthly(0.02) * (1 - six_from_monthly(0.02)) / 9e6)
    assert abs(d6 / 100 - Z * se) / (Z * se) < 0.02  # при 50/50 ~ Z*SE
    assert 0 < six_from_monthly(0.02) < 1 and abs(monthly_from_6m(six_from_monthly(0.02)) - 0.02) < 1e-12
    print("\nПроверки пройдены: Z, согласие с аналитической формулой при 50/50, пересчёт 6 мес <-> месяц.")

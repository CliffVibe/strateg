"""Q05: точка безубыточности бесплатного расширенного уровня защиты. На 1 млн абонентов.
Все входы - допущения (inputs/ пуст). Читает только константы ниже. stdlib."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
N = 1_000_000
# имя: (low, base, high); low/high - значения параметра, не "благоприятность"
P = {
 "pen":    (0.01, 0.03, 0.06),   # доля базы с платным уровнем сейчас
 "price":  (149, 199, 249),      # ₽/мес
 "m_svc":  (0.50, 0.65, 0.80),   # маржа услуги после затрат ИИ/партнёров
 "adopt":  (0.10, 0.25, 0.40),   # доля базы, включающая бесплатный уровень
 "c_user": (5, 15, 30),          # ₽/мес на пользователя при бесплатной модели
 "arpu":   (400, 500, 600),      # ₽/мес
 "m_arpu": (0.30, 0.38, 0.45),   # доля вклада в ARPU
 "churn":  (0.015, 0.02, 0.025), # базовый отток в мес
 "life":   (12, 18, 24),         # мес вклада удержанного абонента
 # вариант C: сегмент
 "seg":    (0.20, 0.25, 0.30),   # доля базы в сегменте
 "k_pay":  (0.7, 1.0, 1.5),      # концентрация платящих в сегменте (1 = как в среднем)
 "arpu_x": (1.0, 1.3, 1.6),      # ARPU сегмента / средний
}
def b(i=1): return {k: v[i] for k, v in P.items()}

def calc(p):
    cm = p["arpu"] * p["m_arpu"]                 # вклад абонента, ₽/мес
    ltv = cm * p["life"]                         # ₽ за удержанного абонента
    paid = N * p["pen"] * p["price"] * p["m_svc"]  # вклад платного уровня в A, ₽/мес
    # B: теряем вклад платящих, платим за обслуживание всех включивших
    cost_B = N * p["adopt"] * p["c_user"]
    effB_direct = -paid - cost_B
    dB = -effB_direct / (N * ltv)                # треб. снижение оттока по всей базе, доля/мес
    # C: сегмент seg; платящих в нём pen*k_pay*seg; включают adopt внутри сегмента
    Ns = N * p["seg"]
    paid_C = Ns * min(1, p["pen"] * p["k_pay"]) * p["price"] * p["m_svc"]
    cost_C = Ns * p["adopt"] * p["c_user"]
    effC_direct = -paid_C - cost_C
    ltv_s = ltv * p["arpu_x"]
    dC_seg = -effC_direct / (Ns * ltv_s)         # в сегменте
    dC_all = dC_seg * p["seg"]                   # в пересчёте на всю базу
    return dict(cm=cm, ltv=ltv, paid=paid, effB=effB_direct, dB=dB,
                effC=effC_direct, dC_seg=dC_seg, dC_all=dC_all,
                effD=-paid, dB_rel=dB / p["churn"], dCs_rel=dC_seg / p["churn"],
                dB_adopt=dB / p["adopt"])

def fmt(x): return f"{x:,.0f}".replace(",", " ")

if __name__ == "__main__":
    r = calc(b())
    print("=== BASE, на 1 млн абонентов, ₽/мес (эффект относительно A, без эффекта на отток) ===")
    print(f"A: вклад платного уровня (опорный) {fmt(r['paid'])}; эффект vs A = 0")
    print(f"B: {fmt(r['effB'])}  | C: {fmt(r['effC'])} | D: {fmt(r['effD'])}")
    print(f"вклад удержанного абонента {r['cm']:.0f} ₽/мес, за {b()['life']} мес = {fmt(r['ltv'])} ₽")
    print("\n=== ТРЕБУЕМОЕ СНИЖЕНИЕ ОТТОКА (вариант = A) ===")
    print(f"B: {r['dB']*100:.3f} п.п./мес по всей базе = {r['dB_rel']*100:.1f}% от базового оттока "
          f"({r['dB']*N:,.0f} удержанных на 1 млн/мес; среди включивших {r['dB_adopt']*100:.2f} п.п.)")
    print(f"C: {r['dC_seg']*100:.3f} п.п./мес внутри сегмента = {r['dCs_rel']*100:.1f}% его оттока; "
          f"на всю базу {r['dC_all']*100:.3f} п.п. ({r['dC_all']*N:,.0f} абонентов/мес на 1 млн)")
    # диапазон: все допущения в сторону выгоды бесплатной модели / против
    fav = b(); unf = b()
    for k, (lo, ba, hi) in P.items():
        # знак влияния на порог B определяется численно
        fl, fh = dict(b(), **{k: lo}), dict(b(), **{k: hi})
        if calc(fl)["dB"] <= calc(fh)["dB"]: fav[k], unf[k] = lo, hi
        else: fav[k], unf[k] = hi, lo
    f, u = calc(fav), calc(unf)
    print("\n=== ДИАПАЗОН (все допущения вместе: благоприятные / неблагоприятные для B,C) ===")
    print(f"B: {f['dB']*100:.3f} .. {u['dB']*100:.3f} п.п./мес ({f['dB_rel']*100:.1f}% .. {u['dB_rel']*100:.1f}% оттока)")
    print(f"C в сегменте: {f['dC_seg']*100:.3f} .. {u['dC_seg']*100:.3f} п.п. ({f['dCs_rel']*100:.1f}% .. {u['dCs_rel']*100:.1f}%)")
    print(f"C на всю базу: {f['dC_all']*100:.3f} .. {u['dC_all']*100:.3f} п.п.")
    print("\n=== ЧУВСТВИТЕЛЬНОСТЬ порога B (п.п./мес), по одному параметру low/base/high ===")
    rows = []
    for k in P:
        lo = calc(dict(b(), **{k: P[k][0]}))["dB"]*100; hi = calc(dict(b(), **{k: P[k][2]}))["dB"]*100
        rows.append((abs(hi-lo), k, lo, hi))
    for sw, k, lo, hi in sorted(rows, reverse=True):
        print(f"{k:7s} low->{lo:.3f}  high->{hi:.3f}  размах {sw:.3f}")
    print("\n(C, порог в сегменте; k_pay/arpu_x/seg влияют только на C)")
    rows = []
    for k in P:
        lo = calc(dict(b(), **{k: P[k][0]}))["dC_seg"]*100; hi = calc(dict(b(), **{k: P[k][2]}))["dC_seg"]*100
        rows.append((abs(hi-lo), k, lo, hi))
    for sw, k, lo, hi in sorted(rows, reverse=True)[:5]:
        print(f"{k:7s} low->{lo:.3f}  high->{hi:.3f}")
    # правдоподобие: ВЦИОМ 1% называют защиту -> верхняя граница доли оттока, связанной с защитой
    print("\n=== СРАВНЕНИЕ С ОТКРЫТЫМИ ДАННЫМИ (оценка порядка) ===")
    for share in (0.01, 0.05, 0.10, 0.20):
        d = share * b()["churn"] * 100
        print(f"если защита причина {share*100:.0f}% оттока и бесплатный уровень устраняет её полностью: "
              f"{d:.3f} п.п. -> {'покрывает' if d/100 >= r['dB'] else 'не покрывает'} порог B base ({r['dB']*100:.3f})")
    # проверки
    print("\n=== ПРОВЕРКИ ===")
    assert abs(r["paid"] - 30_000*199*0.65) < 1e-6
    chk = calc(b()); dB = chk["dB"]
    assert abs(dB*N*chk["ltv"] + chk["effB"]) < 1e-6          # при пороге эффект B = 0
    assert abs(chk["dC_seg"]*N*b()["seg"]*chk["ltv"]*b()["arpu_x"] + chk["effC"]) < 1e-6
    assert 0 < dB < b()["churn"] and 0 < chk["dC_seg"] < b()["churn"]
    assert chk["effD"] == -chk["paid"]
    print("ед.: ₽/мес на 1 млн; отток - доля/мес (печать в п.п.); порог даёт нулевой эффект: ОК")
    print("период: помесячный поток; вклад удержанного = вклад/мес x срок (без дисконта, без каннибализации на ARPU)")

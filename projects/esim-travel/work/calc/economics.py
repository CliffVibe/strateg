"""Q06: сценарная экономика туристической eSIM оператора, 2027 год. Python stdlib.
Читает только inputs/trips-outbound.csv (база туристических поездок 2025). Остальные входы — константы ниже:
(ф) = из реестра утверждений (C/S), (д) = ДОПУЩЕНИЕ без открытых данных, задано вилкой (пессим., база, оптим.).
Единицы: ₽ (с НДС для розницы, без НДС для выручки модели), ГБ, дни; период — календарный 2027, денежные суммы в млн ₽.
Запуск: python economics.py
"""
import io, re, sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
SRC = Path(__file__).resolve().parents[2] / "inputs" / "trips-outbound.csv"
T25 = None
for line in open(SRC, encoding="utf-8"):
    if line.startswith("2025,year,Всего,туристические поездки"):
        T25 = float(re.search(r",(\d{7,9}),поездок", line).group(1))
assert T25 == 13_400_000, T25  # C084

SCEN = ("пессимистичный", "базовый", "оптимистичный")
# ---- вилки допущений: (пессим., база, оптим.) -------------------------------------------------------
P = {
    # спрос
    "g":        (0.00, 0.05, 0.10),   # (д) рост туристических поездок 2027 к 2025 (по постановке; факт 2025: +15,6% C084)
    "op_share": (0.15, 0.25, 0.33),   # (д) доля поездок, где путешественник — абонент оператора (оператор не назван)
    "esim_sh":  (0.05, 0.09, 0.15),   # (д на основе ф) доля поездок на международной eSIM в 2027; 9% = ComNews C007; Opensignal C030: ~x2 за год
    "capture":  (0.20, 0.35, 0.50),   # (д) доля своих абонентов среди eSIM-поездок, купивших у своего оператора (89% "предпочли бы" - потолок, C031)
    "nonsub":   (0.00, 0.20, 0.50),   # (д) покупки не-абонентов, % к покупкам абонентов (МТС Оплата/Билайн продают любым абонентам C034/C036)
    "covA":     (0.50, 0.70, 0.85),   # (д) доля сезона 2027, покрытая продажами при своём продукте (разработка 6-8 мес.)
    "covB":     (0.75, 0.90, 1.00),   # (д) то же для white-label (запуск быстрее)
    # цена и состав
    "price_mult": (1.0, 1.0, 1.0),    # (д) множитель цен-ориентиров; в чувствительности 0,8-1,2
    "util":     (0.75, 0.75, 0.75),   # (д) доля купленных ГБ, реально потреблённых (остаток сгорает C036)
    "unl_gb":   (9.0, 6.0, 4.0),      # (д) реальный расход ГБ на пакете "безлимит/неделя" (у безлимита есть порог скорости C077)
    # издержки
    "cost_usd": (1.45, 0.85, 0.45),   # (д) оптовая стоимость ГБ у зарубежного партнёра, $/ГБ (открытых данных нет, C058)
    "fx":       (100.0, 83.09, 75.0), # (ф+д) ₽/$: 83,09 = Самокатус 07.11.2026 (C137); 2027 - вилка
    "eurusd":   (1.15, 1.15, 1.15),   # (д) для пересчёта цен в евро (Airalo, Holafly)
    "vat":      (0.22, 0.22, 0.22),   # (д) НДС в розничной цене (проверить с налоговой службой оператора)
    "acq":      (0.02, 0.02, 0.02),   # (д) эквайринг/СБП, доля от розницы
    "support":  (40.0, 25.0, 15.0),   # (д) поддержка и активация, ₽ на покупку
    "cac":      (120.0, 60.0, 30.0),  # (д) маркетинг, ₽ на покупку (свои каналы - приложение/push; чужих нет)
    # каннибализация
    "k":        (0.50, 0.30, 0.15),   # (д) доля покупок абонентов, которые иначе принесли бы оператору платный роуминг
    "R":        (3500.0, 2500.0, 1750.0),  # (д на основе ф) роуминговая выручка с такой поездки, ₽ (Турция 10 дн. от 3500 C136; Kaleido $42 C031; 350 ₽/сут. C038)
    "m_roam":   (0.65, 0.50, 0.35),   # (д) валовая маржа роуминга (доля потерянной выручки, которая была прибылью)
    # затраты запуска (млн ₽)
    "fixA_opex": (50.0, 30.0, 20.0),  # (д) A: команда, платформа eSIM, поддержка в год
    "fixA_capex": (100.0, 50.0, 25.0),  # (д) A: разовая интеграция/запуск; амортизация 3 года
    "fixB_opex": (15.0, 10.0, 5.0),   # (д) B: команда, поддержка, год
    "fixB_capex": (20.0, 10.0, 5.0),  # (д) B: разовый запуск; амортизация 1 год (нормы с 01.03.2028 C003/C049)
    "b_mult":   (2.0, 1.6, 1.3),      # (д) наценка агрегатора к оптовой стоимости ГБ в модели B
    # модель C
    "u":        (0.20, 0.20, 0.20),   # (д на основе ф) доля поездок абонентов с платным роумингом оператора (29% = 100-37-25-9 из C007 - верхняя граница)
    "a":        (0.10, 0.20, 0.30),   # (д) доля роумеров, уходящих в 2027 к сторонним eSIM/местной SIM без мер
    "r":        (0.15, 0.25, 0.35),   # (д) доля уходящих, удержанная пакетами
    "phi":      (0.15, 0.10, 0.05),   # (д) доля остающихся роумеров, переходящих на пакет (теряем разницу цены)
    "priceC_x": (1.5, 1.5, 1.5),      # (д) цена пакета на роуминге = средняя цена A x1,5 (роуминговая закупка дороже; 350 ₽/сут. = 2450 ₽/нед.)
    "fixC":     (12.0, 6.0, 3.0),     # (д) C: настройка биллинга, тарифы, маркетинг, год
    "covC":     (0.90, 0.90, 0.90),   # (д) доля сезона для C
}
# цены-ориентиры 3 пакетов (розница с НДС, ₽) и вилка объёмов
PK = [  # имя, ГБ, дней, цена ₽, обоснование
    ("P1 3 ГБ / 7 дн", 3.0, 7, 590.0, "МТС 3 ГБ/30 дн = 622 (C034): -5%; 1 ГБ/7 дн у МТС 413"),
    ("P2 10 ГБ / 30 дн", 10.0, 30, 1190.0, "МТС 1301 (C034): -9%; Yesim $17,90 и eSIM365 $18,90 (C077,C078) + комиссия посредника"),
    ("P3 безлимит / 7 дн", None, 7, 1890.0, "Yesim безлимит 7 дн $22,80 (C077) ~ 1894 ₽ по C137"),
]
# доли пакетов: безлимит 15% (Kaleido C031); остальные 85% по Cellesim C028: <=5 ГБ 61,2% (24,6+36,6), >5 ГБ 38,8% (в т.ч. 12% покупок без объёма - см. секцию 9)
MIX = [0.85 * 0.612, 0.85 * 0.388, 0.15]


def sc(i, over=None):
    d = {k: v[i] for k, v in P.items()}
    if over:
        d.update(over)
    return d


def pack_econ(p, cost_mult=1.0, include_cac=True):
    """Юнит-экономика на одну покупку (микс пакетов), ₽."""
    cgb = p["cost_usd"] * p["fx"] * cost_mult
    out = []
    for (name, gb, days, price, _), w in zip(PK, MIX):
        gross = price * p["price_mult"]
        net = gross / (1 + p["vat"])
        used = p["unl_gb"] if gb is None else gb * p["util"]
        cost = used * cgb
        other = p["acq"] * gross + p["support"] + (p["cac"] if include_cac else 0)
        out.append(dict(name=name, w=w, gross=gross, net=net, cost=cost, other=other, cm=net - cost - other))
    return dict(
        pk=out,
        gross=sum(o["w"] * o["gross"] for o in out), net=sum(o["w"] * o["net"] for o in out),
        cost=sum(o["w"] * o["cost"] for o in out), other=sum(o["w"] * o["other"] for o in out),
        cm=sum(o["w"] * o["cm"] for o in out), cgb=cgb)


def model_AB(p, which):
    mult = p["b_mult"] if which == "B" else 1.0
    cov = p["covB"] if which == "B" else p["covA"]
    fixed = (p["fixB_opex"] + p["fixB_capex"] / 1.0) if which == "B" else (p["fixA_opex"] + p["fixA_capex"] / 3.0)
    e = pack_econ(p, mult)
    trips = T25 * (1 + p["g"])
    sub = trips * p["op_share"] * cov * p["esim_sh"] * p["capture"]
    total = sub * (1 + p["nonsub"])
    sub_frac = sub / total if total else 1.0
    cann_per = sub_frac * p["k"] * p["R"] * p["m_roam"]  # потерянная маржа роуминга на одну покупку
    res = dict(trips=trips, sub=sub, total=total, e=e, fixed=fixed, cann_per=cann_per)
    res["gross_rev"] = total * e["gross"] / 1e6
    res["net_rev"] = total * e["net"] / 1e6
    res["contrib"] = total * e["cm"] / 1e6
    res["cann_loss"] = total * cann_per / 1e6
    res["lost_roam_rev"] = sub * p["k"] * p["R"] / 1e6
    res["result"] = res["contrib"] - res["cann_loss"] - fixed
    res["result_nocann"] = res["contrib"] - fixed
    res["be_total"] = fixed * 1e6 / (e["cm"] - cann_per) if e["cm"] - cann_per > 0 else float("inf")
    res["be_total_nocann"] = fixed * 1e6 / e["cm"] if e["cm"] > 0 else float("inf")
    mkt = trips * p["esim_sh"]
    res["be_share_of_mkt"] = res["be_total"] / mkt
    # критическая доля каннибализации k*: результат = 0 при данных объёмах
    lost_per_k = sub * p["R"] * p["m_roam"] / 1e6
    res["k_crit"] = (res["contrib"] - fixed) / lost_per_k if lost_per_k else float("inf")
    res["lost_rev_at_kcrit_share"] = (sub * res["k_crit"] * p["R"] / 1e6) / res["gross_rev"] if res["gross_rev"] else 0
    return res


def model_C(p):
    trips = T25 * (1 + p["g"])
    N = trips * p["op_share"] * p["u"] * p["covC"]  # роумеры-абоненты
    pr = sum(w * pk[3] for pk, w in zip(PK, MIX)) * p["priceC_x"] * p["price_mult"]
    e = pack_econ(p, p["b_mult"], include_cac=False)
    m_pkg = pr / (1 + p["vat"]) - e["cost"] - p["acq"] * pr - p["support"]
    base_margin = p["R"] * p["m_roam"]
    switch = p["phi"] * (1 - p["a"]) * N
    retained = p["r"] * p["a"] * N
    d_switch = switch * (m_pkg - base_margin) / 1e6
    d_ret = retained * m_pkg / 1e6
    res = dict(N=N, price=pr, m_pkg=m_pkg, switch=switch, retained=retained, d_switch=d_switch, d_ret=d_ret,
               fixed=p["fixC"], result=d_switch + d_ret - p["fixC"], purchases=switch + retained,
               gross_rev=(switch + retained) * pr / 1e6,
               base_roam_rev=N * (1 - p["a"]) * p["R"] / 1e6)
    # порог: при какой доле удержания r результат = 0
    per_r = p["a"] * N * m_pkg / 1e6
    res["r_crit"] = (p["fixC"] - d_switch) / per_r if per_r > 0 else float("inf")
    return res


checks = []


def check(name, ok, detail=""):
    checks.append(bool(ok))
    print(("[OK]   " if ok else "[FAIL] ") + name, detail)


def f(x, n=1):
    return f"{x:,.{n}f}".replace(",", " ")


# ================================ 0. входы и ориентиры рынка ==========================================
b = sc(1)
eur = b["fx"] * b["eurusd"]
print("== 0. Ценовые ориентиры (₽ по курсу %.2f ₽/$, %.1f ₽/€ - допущение) ==" % (b["fx"], eur))
ref = [
    ("МТС Оплата, Европа 1 ГБ/7 дн (C034)", 413, 1), ("МТС 3 ГБ/30 дн (C034)", 622, 3),
    ("МТС 10 ГБ/30 дн (C034)", 1301, 10), ("МТС 20 ГБ/30 дн (C034)", 1998, 20),
    ("Билайн 30 ГБ/30 дн от 1050 (C132, реклама, 'от', low)", 1050, 30),
    ("Yesim 10 ГБ/30 дн $17,90 (C077)", 17.90 * b["fx"], 10), ("eSIM365 10 ГБ/30 дн $18,90 (C078)", 18.90 * b["fx"], 10),
    ("eSIM365 1 ГБ/7 дн $2,20 (C078)", 2.20 * b["fx"], 1), ("Yesim безлимит 7 дн $22,80 (C077)", 22.80 * b["fx"], None),
    ("Airalo Турция 'от 4,00 €' (C087, мин. пакет)", 4.0 * eur, None),  # Holafly 3,79 € (C138): период цены не указан - не сравниваем с пакетами
]
for n, pr, gb in ref:
    print(f"  {n:58s} {pr:7.0f} ₽" + (f"  = {pr/gb:5.0f} ₽/ГБ" if gb else ""))
print("  + комиссия посредника при оплате российской картой иностранного сайта: от 350 ₽ до 1299 ₽ (C075, low) -> 10 ГБ у Yesim/eSIM365 'на руки' ~ %.0f-%.0f ₽"
      % (17.90 * b["fx"] + 350, 18.90 * b["fx"] + 350))
print("  Роуминг: Европа 350 ₽/сут. за 1 ГБ (C038, low) => 7 сут. = 2450 ₽; Турция 10 дн. 3500-13000 ₽ (C136, low); Kaleido (C031): роуминг $42 = %.0f ₽, eSIM $28 = %.0f ₽ в среднем на поездку" % (42 * b["fx"], 28 * b["fx"]))
print("  ВНИМАНИЕ: C136 даёт 10 ГБ у сторонних eSIM 520-820 ₽, C077/C078 - 1490-1570 ₽: расхождение в 2-3 раза (разные источники, продавец-блог, даты) - цены-ориентиры берём по более высоким и по МТС (official).")
print("  Доли способов связи (C007): местная SIM 37%, местная eSIM 25%, международная eSIM 9% => остаток 29% (роуминг/прочее, оценка = 100-37-25-9); 64% решают в поездке.")
print("\n== 1. Цены-ориентиры оператора для 3 пакетов и миксы ==")
for (n, gb, d, pr, why), w in zip(PK, MIX):
    print(f"  {n:20s} {pr:6.0f} ₽ (с НДС), доля в покупках {w:.1%}; основание: {why}" + (f"; = {pr/gb:.0f} ₽/ГБ" if gb else ""))
check("доли микса = 100%", abs(sum(MIX) - 1) < 1e-9, f"{sum(MIX):.4f}")

# ================================ 2. юнит-экономика =====================================================
print("\n== 2. Маржа на покупку, ₽ (модель A, свой продукт) ==")
for i, s in enumerate(SCEN):
    e = pack_econ(sc(i))
    print(f"  [{s}] ₽/ГБ закупки {e['cgb']:.0f}; на покупку: розница {e['gross']:.0f}, без НДС {e['net']:.0f}, трафик {e['cost']:.0f}, прочее {e['other']:.0f} -> маржа {e['cm']:.0f} ₽ ({e['cm']/e['net']:.0%} от выручки без НДС)")
    if i == 1:
        for o in e["pk"]:
            print(f"        {o['name']:20s} доля {o['w']:.0%}: без НДС {o['net']:.0f}, трафик {o['cost']:.0f}, прочее {o['other']:.0f}, маржа {o['cm']:.0f} ₽")
        for o in e["pk"]:
            check(f"{o['name']} маржа > 0 в базе", o["cm"] > 0)
        check("маржа микса = сумма долей x маржа", abs(e["cm"] - sum(o["w"] * o["cm"] for o in e["pk"])) < 1e-9)
        check("выручка - затраты = маржа", abs(e["net"] - e["cost"] - e["other"] - e["cm"]) < 1e-9)

# ================================ 3. сценарии, модели A/B/C =============================================
print("\n== 3. Сценарии 2027 (все допущения сдвигаются вместе; это границы, а не вероятности) ==")
RES = {}
for i, s in enumerate(SCEN):
    p = sc(i)
    A, B, C = model_AB(p, "A"), model_AB(p, "B"), model_C(p)
    RES[s] = (A, B, C)
    mkt = A["trips"] * p["esim_sh"]
    print(f"\n[{s}] поездок туристических {A['trips']/1e6:.2f} млн; рынок международной eSIM {mkt/1e3:.0f} тыс. покупок; доля поездок абонентов {p['op_share']:.0%}")
    for nm, R_ in (("A свой продукт ", A), ("B white-label  ", B)):
        print(f"  {nm}: покупок {R_['total']/1e3:6.1f} тыс. (абоненты {R_['sub']/1e3:.1f}), выручка розн. {f(R_['gross_rev'])} млн ₽ (без НДС {f(R_['net_rev'])}), "
              f"маржа {f(R_['contrib'])}, каннибализация -{f(R_['cann_loss'])} (потеряно роуминг. выручки {f(R_['lost_roam_rev'])}), затраты запуска -{f(R_['fixed'])} => РЕЗУЛЬТАТ {f(R_['result'])} млн ₽")
        be = "нет (маржа на покупку <= потерь роуминга)" if R_["be_total"] == float("inf") else f"{f(R_['be_total']/1e3)} тыс. покупок/год ({R_['be_share_of_mkt']:.0%} всего рынка межд. eSIM)"
        ben = "нет (маржа <= 0)" if R_["be_total_nocann"] == float("inf") else f"{f(R_['be_total_nocann']/1e3)} тыс."
        kc = f"{R_['k_crit']:.0%}" if R_["k_crit"] >= 0 else "нет (не окупается и при k=0)"
        print(f"        порог окупаемости: {be} с учётом каннибализации; без неё {ben}; k* (макс. доля каннибализации) = {kc} при k допущ. {p['k']:.0%}")
    print(f"  C роуминг-пакеты: покупок пакетов {C['purchases']/1e3:.1f} тыс. (переходят {C['switch']/1e3:.1f}, удержано {C['retained']/1e3:.1f}), выручка пакетов {f(C['gross_rev'])} млн ₽; "
          f"потеря на переходящих {f(C['d_switch'])}, удержанная маржа {C['d_ret']:+.1f}, затраты -{f(C['fixed'])} => РЕЗУЛЬТАТ {f(C['result'])} млн ₽ (безубыточная доля удержания r* = {('%.0f%%' % (100*C['r_crit'])) if 0 <= C['r_crit'] <= 1 else ('нет (>100%)' if C['r_crit'] > 1 else '0: окупается без удержания')} при r допущ. {p['r']:.0%}); "
          f"база роуминга абонентов (без мер) {f(C['base_roam_rev'],0)} млн ₽ выручки")
    check(f"[{s}] выручка A = покупки x средняя розница", abs(A["gross_rev"] - A["total"] * A["e"]["gross"] / 1e6) < 1e-9)
    check(f"[{s}] результат A = маржа - каннибализация - затраты", abs(A["result"] - (A["contrib"] - A["cann_loss"] - A["fixed"])) < 1e-9)
    check(f"[{s}] покупки A <= рынок eSIM x (1+доля не-абонентов)", A["total"] <= mkt * (1 + p["nonsub"]) + 1e-6)
    # точность порога: на пороге результат = 0
    if A["be_total"] < 1e12:
        chk = A["be_total"] * (A["e"]["cm"] - A["cann_per"]) / 1e6 - A["fixed"]
        check(f"[{s}] на пороге A результат = 0", abs(chk) < 1e-6)
rs = [RES[s][0]["result"] for s in SCEN]
check("A: пессим. < база < оптим.", rs[0] < rs[1] < rs[2], [round(x, 1) for x in rs])
rs = [RES[s][1]["result"] for s in SCEN]
check("B: пессим. < база < оптим.", rs[0] < rs[1] < rs[2], [round(x, 1) for x in rs])

# ================================ 4. сравнение моделей =================================================
print("\n== 4. Сравнение моделей, результат 2027 (млн ₽) ==")
print(f"  {'':16s}" + "".join(f"{s:>18s}" for s in SCEN))
for nm, idx in (("A свой продукт", 0), ("B white-label", 1), ("C пакеты роуминга", 2)):
    print(f"  {nm:16s}" + "".join(f"{f(RES[s][idx]['result']):>18s}" for s in SCEN))
print("  без каннибализации (A/B):")
for nm, idx in (("A", 0), ("B", 1)):
    print(f"  {nm:16s}" + "".join(f"{f(RES[s][idx]['result_nocann']):>18s}" for s in SCEN))
print("  Риск B: нормы проекта о запрете торговли SIM через агрегаторы - с 01.03.2028, если примут (C003, C033, C049): в 2027 продажи возможны; капзатраты B уже отнесены на 1 год (не на 3). "
      "Для A и C таких ограничений в источниках нет (C048). Скорость: A покрывает %.0f%% сезона, B %.0f%% (допущения)." % (100 * b["covA"], 100 * b["covB"]))

# ================================ 5. чувствительность (база A) ==========================================
print("\n== 5. Чувствительность результата A (млн ₽), по одному допущению, остальные - база ==")
base_res = model_AB(sc(1), "A")["result"]
print(f"  база A: {f(base_res)}")
RANGES = {k: (v[0], v[2]) for k, v in P.items() if v[0] != v[2]}
RANGES["price_mult"] = (0.8, 1.2)
RANGES["vat"] = (0.22, 0.0)
rows = []
for k, (lo, hi) in RANGES.items():
    if k in ("a", "r", "phi", "priceC_x", "fixC", "covC", "u", "b_mult", "covB", "fixB_opex", "fixB_capex", "eurusd"):
        continue
    ra = model_AB(sc(1, {k: lo}), "A")["result"]
    rb = model_AB(sc(1, {k: hi}), "A")["result"]
    rows.append((abs(rb - ra), k, lo, hi, ra, rb))
rows.sort(reverse=True)
for sw, k, lo, hi, ra, rb in rows:
    print(f"  {k:11s} {lo:>8g} -> {f(ra):>8s} | {hi:>8g} -> {f(rb):>8s}  размах {f(sw)}")
print("  (в 'price_mult' объём покупок не меняется - эластичность спроса по цене в открытых данных не найдена; размах цены завышен)")

print("\n== 6. Порог окупаемости A: тыс. покупок/год при затратах запуска (млн ₽/год) и каннибализации k (R, m_roam - база) ==")
print("   доля абонентов в покупках - база (1/(1+не-абоненты)); ₽/ГБ закупки - база")
pb = sc(1)
eb = pack_econ(pb)
sub_frac = 1 / (1 + pb["nonsub"])
print(f"  маржа на покупку до каннибализации {eb['cm']:.0f} ₽; потеря роуминга на покупку при k=30%: {sub_frac*0.3*pb['R']*pb['m_roam']:.0f} ₽")
print(f"  {'затраты, млн ₽':>16s}" + "".join(f"   k={k:.0%}" for k in (0, .15, .30, .50)))
for F_ in (28.0, 47.0, 83.0):
    cells = []
    for k in (0, .15, .30, .50):
        den = eb["cm"] - sub_frac * k * pb["R"] * pb["m_roam"]
        cells.append(f"{F_*1e3/den:7.0f}" if den > 0 else "   нет ")
    print(f"  {F_:>16.0f}" + "".join(f"{c:>8s}" for c in cells))
print("  (28 / 47 / 83 млн = затраты A при вилке пессим.-оптим. допущений: opex + капзатраты/3; 'нет' = маржа не покрывает потерю роуминга)")
print("\n  порог по каннибализации k* (макс. доля покупок абонентов, замещающих платный роуминг) при затратах A=47 млн ₽, ₽/ГБ закупки разные и объёмах базы:")
A0 = model_AB(pb, "A")
for cgb_usd in (0.45, 0.85, 1.45):
    pp = sc(1, {"cost_usd": cgb_usd})
    A_ = model_AB(pp, "A")
    print(f"   {cgb_usd*pp['fx']:.0f} ₽/ГБ: маржа/покупку {A_['e']['cm']:.0f} ₽, результат без каннибализации {f(A_['result_nocann'])} млн, k* = {A_['k_crit']:.0%} (отрицательное = не окупается даже при k=0)")
print("  k* при R (₽/поездку) и m_roam, база A:")
for R_ in (1750, 2500, 3500):
    print(f"   R={R_}: " + ", ".join(f"m={m:.0%}: k*={model_AB(sc(1, {'R': R_, 'm_roam': m}), 'A')['k_crit']:.0%}" for m in (0.35, 0.5, 0.65)))
print(f"  При m_roam=100% (потеря всей выручки): k* = {model_AB(sc(1, {'m_roam': 1.0}), 'A')['k_crit']:.0%}; отрицательное k* = цель недостижима и при нулевой каннибализации (объём ниже порога)")

print("\n== 7. Чувствительность модели C (млн ₽) ==")
cb = model_C(sc(1))["result"]
print(f"  база C: {f(cb)}")
for k in ("a", "r", "phi", "priceC_x", "u"):
    lo, hi = {"priceC_x": (1.2, 2.0), "u": (0.15, 0.29)}.get(k, (P[k][0], P[k][2]))
    print(f"  {k:9s} {lo:g} -> {f(model_C(sc(1, {k: lo}))['result'])} | {hi:g} -> {f(model_C(sc(1, {k: hi}))['result'])}")

print("\n== 8. Проверки ==")
check("доли в допущениях в диапазоне 0..1", all(0 <= x <= 1 for k in ("op_share", "esim_sh", "capture", "k", "m_roam", "util", "acq", "vat", "u", "a", "r", "phi", "covA", "covB", "covC") for x in P[k]))
check("база туристических поездок = 13,4 млн (C084)", T25 == 13_400_000)
check("рынок межд. eSIM 2027 (база) = 14,07 млн x 9% = 1,27 млн", abs(T25 * 1.05 * 0.09 - 1_266_300) < 1)
check("цена P1 < МТС 3 ГБ; P2 < МТС 10 ГБ", PK[0][3] < 622 and PK[1][3] < 1301)
print("\n== 9. Чувствительность к миксу: 12% покупок Cellesim без объёма (C028) ==")
print("  база: >5 ГБ = 38,8% = 15,4% + 11,4% + 12% без объёма; альтернатива - нормировка на 88% с известным объёмом: <=5 ГБ 69,5%, >5 ГБ 30,5%")
MIX_BASE = list(MIX)
for lab, mx in (("база 52,0/33,0/15,0", MIX_BASE), ("нормировка 59,1/25,9/15,0", [0.85 * 0.612 / 0.88, 0.85 * 0.268 / 0.88, 0.15])):
    MIX[:] = mx
    rr = [model_AB(sc(i), "A")["result"] for i in range(3)]
    rb_ = [model_AB(sc(i), "B")["result"] for i in range(3)]
    rc_ = [model_C(sc(i))["result"] for i in range(3)]
    A1 = model_AB(sc(1), "A")
    print(f"  {lab}: A {[round(x,1) for x in rr]}; B {[round(x,1) for x in rb_]}; C {[round(x,1) for x in rc_]}; маржа/покупку A база {A1['e']['cm']:.0f} ₽; порог A без каннибализации {A1['be_total_nocann']/1e3:.0f} тыс.; с k=30% {A1['be_total']/1e3:.0f} тыс.")
MIX[:] = MIX_BASE
print("итого проверок: %d/%d" % (sum(checks), len(checks)))

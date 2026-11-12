"""Пересчёт порога окупаемости C после red-team (12.11.2026). Опирается на unit-economics.py.
Добавлено:
- START: месяц, с которого действует снижение оттока (по графику плана: разбор отзывов в январе,
  выпуск бота февраль–март, A/B 2 недели, выкатка -> база апрель). Абоненто-месяцев = sum_{m=START..12}(12-m+0.5).
- LOSS: потеря ARPU у пользователей с улучшениями из-за кнопок «отключить»/«оспорить» (доля ARPU, в год, по 95% аудитории).
- SAVE: экономия поддержки = обращений, ушедших от оператора, в год x стоимость обращения.
Чистый порог: d * A * SM(START) * ARPU * MARGIN = R + LOSS*A*0.95*ARPU*12*MARGIN*(SM(START)/72 доли года не учитываем: потеря — с выпуска) - SAVE.
Для простоты потерю и экономию считаем с месяца выпуска: множитель (13-START)/12.
"""
import importlib.util, pathlib
spec = importlib.util.spec_from_file_location("ue", pathlib.Path(__file__).with_name("unit-economics.py"))
ue = importlib.util.module_from_spec(spec); spec.loader.exec_module(ue)

EXTRA = {
    "START":  (3, 4, 6),                 # месяц начала эффекта (март / апрель / июнь)
    "LOSS":   (0.0, 0.001, 0.003),        # потеря ARPU от отключений, доля (0 / 0,1% / 0,3%)
    "CONTACTS_SAVED": (1e6, 3e6, 6e6),    # обращений к оператору в год, ушедших в бот (полный год)
    "COST_CONTACT":   (50.0, 100.0, 150.0),  # стоимость обращения к оператору, руб.
}
HOLDIN = 0.95

def sm(start):
    return sum(12 - m + 0.5 for m in range(start, 13))

def net_threshold(p):
    frac = (13 - p["START"]) / 12
    loss = p["LOSS"] * p["A"] * HOLDIN * p["ARPU"] * 12 * frac * p["MARGIN"]
    save = p["CONTACTS_SAVED"] * p["COST_CONTACT"] * frac
    need = p["R"] + loss - save
    return need / (p["A"] * HOLDIN * sm(p["START"]) * p["ARPU"] * p["MARGIN"]) * 100, loss, save

if __name__ == "__main__":
    b = ue.base(); b.update({k: v[1] for k, v in EXTRA.items()})
    print("Абоненто-месяцев: март", sm(3), "апрель", sm(4), "июнь", sm(6))
    for s in EXTRA["START"]:
        p = dict(b, LOSS=0.0, CONTACTS_SAVED=0.0, START=s)
        t, _, _ = net_threshold(p)
        print(f"Только сдвиг старта, START={s}: порог {t:.3f} п.п./мес ({t/100/b['CHURN']:.1%} от оттока)")
    t, loss, save = net_threshold(b)
    print(f"\nБаза чистая (апрель, потеря ARPU 0,1%, экономия 3 млн обр. x 100 руб.): порог {t:.3f} п.п. "
          f"({t/100/b['CHURN']:.1%}); потеря маржи {loss/1e6:.0f} млн, экономия {save/1e6:.0f} млн")
    for L in EXTRA["LOSS"]:
        tt, ll, _ = net_threshold(dict(b, LOSS=L))
        print(f"  LOSS={L:.1%}: порог {tt:.3f} п.п., потеря маржи {ll/1e6:.0f} млн руб.")
    # окупается ли C только экономией поддержки (ветка «ноль»)?
    for c in EXTRA["CONTACTS_SAVED"]:
        for cc in EXTRA["COST_CONTACT"]:
            s = c * cc * (13 - b["START"]) / 12
            print(f"  экономия {c/1e6:.0f} млн обр. x {cc:.0f} руб. = {s/1e6:.0f} млн руб. "
                  f"{'>=' if s >= b['R'] else '<'} R={b['R']/1e6:.0f} млн")
    # потеря ARPU, которая съедает весь ресурс R при нулевом эффекте
    be_loss = b["R"] / (b["A"] * HOLDIN * b["ARPU"] * 12 * (13 - b["START"]) / 12 * b["MARGIN"])
    print(f"\nПотеря ARPU, равная по марже всему R: {be_loss:.2%} -> guardrail ниже этого")
    assert sm(1) == 72
    print("Проверки пройдены.")

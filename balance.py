import math

def solve_balance(p):
    keys = ["Q_kw", "G1", "t1_in", "t1_out", "G2", "t2_in", "t2_out"]
    v = {k: (None if p.get(k) in (None, "") else float(p[k])) for k in keys}
    known = sum(x is not None for x in v.values())
    if known < 5:
        return None, f"Недостаточно данных: введено {known} из 7 параметров баланса (нужно минимум 5)."
    cp1, cp2 = float(p["cp1"]), float(p["cp2"])
    flow = p.get("flow_type", "counter")
    Q = None if v["Q_kw"] is None else v["Q_kw"] * 1000.0
    G1, t1i, t1o, G2, t2i, t2o = v["G1"], v["t1_in"], v["t1_out"], v["G2"], v["t2_in"], v["t2_out"]

    for _ in range(4):
        if Q is None and None not in (G1, t1i, t1o): Q = G1 * cp1 * (t1i - t1o)
        if Q is None and None not in (G2, t2i, t2o): Q = G2 * cp2 * (t2o - t2i)
        if Q is not None:
            if G1 is None and None not in (t1i, t1o) and abs(t1i - t1o) > 1e-6: G1 = Q / (cp1 * (t1i - t1o))
            if t1o is None and None not in (G1, t1i) and G1 > 0: t1o = t1i - Q / (G1 * cp1)
            if t1i is None and None not in (G1, t1o) and G1 > 0: t1i = t1o + Q / (G1 * cp1)
            if G2 is None and None not in (t2i, t2o) and abs(t2o - t2i) > 1e-6: G2 = Q / (cp2 * (t2o - t2i))
            if t2o is None and None not in (G2, t2i) and G2 > 0: t2o = t2i + Q / (G2 * cp2)
            if t2i is None and None not in (G2, t2o) and G2 > 0: t2i = t2o - Q / (G2 * cp2)

    if any(x is None for x in (Q, G1, t1i, t1o, G2, t2i, t2o)):
        return None, "Невозможно замкнуть баланс: задайте 2 параметра на одной стороне и 3 на другой (или Q + 4 параметра)."
    if Q <= 0 or G1 <= 0 or G2 <= 0:
        return None, "Ошибка: тепловая нагрузка Q и расходы G1, G2 должны быть > 0."
    q1, q2 = G1 * cp1 * (t1i - t1o), G2 * cp2 * (t2o - t2i)
    if abs(q1 - q2) / max(Q, 1.0) > 0.02:
        return None, f"Невязка баланса > 2%: Q1={q1/1000:.2f} кВт, Q2={q2/1000:.2f} кВт, Q={Q/1000:.2f} кВт."

    if flow == "co":
        if t1i <= t2i or t1o <= t2o:
            return None, f"Температурный пересек при прямотоке: выход горячего ({t1o:.1f}°C) <= выхода холодного ({t2o:.1f}°C)."
    else:
        if t1i <= t2o or t1o <= t2i:
            return None, f"Температурный пересек при противотоке: t1=({t1i:.1f}->{t1o:.1f}°C), t2=({t2i:.1f}->{t2o:.1f}°C)."

    Ch, Cc = G1 * cp1, G2 * cp2
    pts_tx = []
    for i in range(41):
        xi = i / 40.0
        if flow == "co":
            r = Ch / Cc
            ntu_h = math.log((t1i - t2i) / (t1o - t2o)) / (1.0 + r)
            Th = t1i - (t1i - t2i) * (1.0 - math.exp(-ntu_h * (1.0 + r) * xi)) / (1.0 + r)
            Tc = t2i + r * (t1i - Th)
        else:
            if abs(Ch - Cc) / max(Ch, Cc) < 1e-4:
                Th, Tc = t1i - (t1i - t1o) * xi, t2o - (t2o - t2i) * xi
            else:
                r = Ch / Cc
                ntu_h = math.log((t1i - t2o) / (t1o - t2i)) / (1.0 - r)
                Th = t1i - (t1i - t2i) * (1.0 - math.exp(-ntu_h * (1.0 - r) * xi)) / (1.0 - r * math.exp(-ntu_h * (1.0 - r)))
                Tc = t2o - r * (t1i - Th)
        pts_tx.append([round(xi, 3), round(Th, 2), round(Tc, 2)])

    return dict(Q_kw=round(Q/1000.0, 3), G1=round(G1, 4), t1_in=round(t1i, 2), t1_out=round(t1o, 2),
                G2=round(G2, 4), t2_in=round(t2i, 2), t2_out=round(t2o, 2),
                flow_type=flow, tx=pts_tx), None

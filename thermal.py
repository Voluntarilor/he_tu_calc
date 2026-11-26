import math
from rules import MATERIALS, TK_MAX_SHELL_P, check_table11, format_tu_name
from fluids import get_props

def lmtd_ft(t1i, t1o, t2i, t2o, z, flow="counter"):
    if flow == "co":
        dtb, dtm = max(t1i - t2i, 1e-6), max(t1o - t2o, 1e-6)
        lmtd = dtb if abs(dtb - dtm) < 1e-4 else (dtb - dtm) / math.log(dtb / dtm)
        return lmtd, 1.0
    dtb, dtm = max(t1i - t2o, 1e-6), max(t1o - t2i, 1e-6)
    lmtd = dtb if abs(dtb - dtm) < 1e-4 else (dtb - dtm) / math.log(dtb / dtm)
    if z == 1: return lmtd, 1.0
    P, R = (t2o - t2i) / (t1i - t2i), (t1i - t1o) / (t2o - t2i)
    eta = math.sqrt(R * R + 1.0)
    if P >= 2.0 / (1.0 + R + eta) - 1e-4: return lmtd, 0.0
    dlt = (1.0 - P)/P if abs(R - 1.0) < 1e-5 else (R - 1.0)/math.log((1.0 - P)/(1.0 - R*P))
    den = math.log((2.0 - P * (1.0 + R - eta)) / (2.0 - P * (1.0 + R + eta)))
    return lmtd, max(0.0, min(1.0, (eta / dlt) / den if den > 0 else 0.0))

def calc_hydraulics_and_k(u, p, G1, t1i, t1o, G2, t2i, t2o):
    if p["hot_side"] == "tube":
        Gt, tti, tto, rhot, cpt, mut, kt, rft = G1, t1i, t1o, p["rho1"], p["cp1"], p["mu1"], p["k1"], p["rf1"]
        Gs, tsi, tso, rhos, cps, mus, ks, rfs = G2, t2i, t2o, p["rho2"], p["cp2"], p["mu2"], p["k2"], p["rf2"]
        flt, fls, pt_op, ps_op, ct, cs = p.get("fl1",""), p.get("fl2",""), p.get("pop1",0.6), p.get("pop2",0.6), p.get("c1",30), p.get("c2",30)
    else:
        Gs, tsi, tso, rhos, cps, mus, ks, rfs = G1, t1i, t1o, p["rho1"], p["cp1"], p["mu1"], p["k1"], p["rf1"]
        Gt, tti, tto, rhot, cpt, mut, kt, rft = G2, t2i, t2o, p["rho2"], p["cp2"], p["mu2"], p["k2"], p["rf2"]
        fls, flt, ps_op, pt_op, cs, ct = p.get("fl1",""), p.get("fl2",""), p.get("pop1",0.6), p.get("pop2",0.6), p.get("c1",30), p.get("c2",30)

    dout, din, L, z = u["dt"] / 1000.0, (u["dt"] - 2 * u["w"]) / 1000.0, u["L"], u["z"]
    wt = Gt / (rhot * u["At"])
    Ret, Prt = rhot * wt * din / mut, cpt * mut / kt
    if Ret >= 2300:
        Nut0 = 0.023 * (Ret ** 0.8) * (Prt ** 0.4)
        lf = 0.25 * (math.log10(0.2e-3 / (3.7 * din) + (6.81 / Ret) ** 0.9)) ** -2
    else:
        gz = Ret * Prt * (din / L)
        Nut0, lf = (1.61 * (gz ** (1.0 / 3.0)) if gz > 12 else 3.66), 64.0 / max(Ret, 1.0)
    wtn = 4.0 * Gt / (math.pi * (u["dyt"] / 1000.0) ** 2 * rhot)
    dpt = (lf*(L*z/din) + 2.5*(z-1) + 2.0*z)*(rhot*wt**2/2.0) + 3.0*(rhot*wtn**2/2.0)

    ws = Gs / (rhos * u["Ac"])
    Res, Prs = rhos * ws * dout / mus, cps * mus / ks
    wsn = 4.0 * Gs / (math.pi * (u["dys"] / 1000.0) ** 2 * rhos)
    mr = u["nr"] if p["use_tu_rows"] else math.ceil(math.sqrt((u["N"] - 1)/3.0 + 0.25))
    bd_frac = dict(A=0.0, B=1.0, C=0.0, E=0.0, F=0.0)

    if p["method"] == "dytnerskiy":
        Nus0 = 0.24*(Res**0.6)*(Prs**0.36) if Res >= 1000 else 0.34*(Res**0.5)*(Prs**0.36)
        dps = (3.0*mr*(u["nb"]+1)/(max(Res,10.0)**0.2))*(rhos*ws**2/2.0) + 1.5*u["nb"]*(rhos*ws**2/2.0) + 3.0*(rhos*wsn**2/2.0)
    else:
        Nus0 = 0.27 * (Res ** 0.63) * (Prs ** 0.36)
        rlm, rs, Jc, Js = 0.18, 0.35, 1.02, 0.92
        Jl = 0.44 * (1.0 - rs) + (1.0 - 0.44 * (1.0 - rs)) * math.exp(-2.2 * rlm)
        Fbp = 0.14 + (0.04 if z > 1 else 0.0)
        Jb = math.exp(-1.35 * Fbp)
        Jr = 1.0 if Res >= 100 else (10.0 / max(mr * (u["nb"] + 1), 1)) ** 0.18
        Nus0 *= Jc * Jl * Jb * Js * Jr
        dpbi = 4.0 * (0.35 * (Res ** -0.2)) * mr * (rhos * ws ** 2 / 2.0)
        Rl, Rb = math.exp(-1.33 * (1.0 + rs) * (rlm ** 0.8)), math.exp(-3.7 * Fbp)
        ww = Gs / (rhos * math.sqrt(u["Ac"] * u["Aw"]))
        dpw = (2.0 + 0.6 * mr) * (rhos * ww ** 2 / 2.0) * Rl
        dps = ((u["nb"]-1)*dpbi*Rb*Rl + u["nb"]*dpw + 2.0*dpbi*Rb*0.92) + 3.0*(rhos*wsn**2/2.0)
        bd_frac = dict(A=0.04, B=round(1.0 - Fbp - 0.18, 3), C=0.06, E=0.08, F=round(Fbp, 3))

    at, as_ = Nut0 * kt / din, Nus0 * ks / dout
    _, k_wall, _ = MATERIALS.get(p["mat"], ("", 45.0, 1.0))

    if p.get("use_visc_corr") and flt and fls and not flt.startswith("0") and not fls.startswith("0"):
        K0 = 1.0 / (1.0 / as_ + (u["w"] / 1000.0) / k_wall + rft + rfs + (1.0 / at) * (dout / din))
        tm_t, tm_s = 0.5 * (tti + tto), 0.5 * (tsi + tso)
        q_fl = K0 * abs(tm_t - tm_s)
        tw_t = tm_t - q_fl / at if tm_t > tm_s else tm_t + q_fl / at
        tw_s = tm_s + q_fl / as_ if tm_t > tm_s else tm_s - q_fl / as_
        pwt, pws = get_props(flt, tw_t, pt_op, ct), get_props(fls, tw_s, ps_op, cs)
        at *= max(0.6, min(1.4, (Prt / (pwt["cp"] * pwt["mu"] / pwt["k"])) ** 0.25))
        as_ *= max(0.6, min(1.4, (Prs / (pws["cp"] * pws["mu"] / pws["k"])) ** 0.25))

    rs_th, rt_th, rm_th, rf_th = 1.0 / as_, (1.0 / at) * (dout / din), (u["w"] / 1000.0) / k_wall, rft + rfs
    R_tot = rs_th + rt_th + rm_th + rf_th
    K = 1.0 / R_tot
    K_clean = 1.0 / (rs_th + rt_th + rm_th)
    extra = dict(
        K_clean=round(K_clean, 1), r_pct=dict(s=round(rs_th/R_tot*100,1), t=round(rt_th/R_tot*100,1), f=round(rf_th/R_tot*100,1), m=round(rm_th/R_tot*100,1)),
        rv2_t=round(rhot * wtn**2, 1), rv2_s=round(rhos * wsn**2, 1), bd=bd_frac,
        Gt=round(Gt, 3), Gs=round(Gs, 3), rhot=rhot, rhos=rhos, cpt=cpt, cps=cps, mut=mut, mus=mus, kt=kt, ks=ks, rft=rft, rfs=rfs
    )
    return K, at, as_, wt, ws, dpt, dps, tti, tto, tsi, tso, extra

def solve_unit(u, p, bal, rating_mode=False):
    flow = p.get("flow_type", "counter")
    if flow == "co" and u["z"] > 1 and not rating_mode: return None
    p_req = max(p["p_des_t"], p["p_des_s"])
    valid_pys = [py for py in u["pys"] if py >= p_req - 1e-6]
    if not valid_pys and not rating_mode: return None
    Py = next(iter(valid_pys)) if valid_pys else max(u["pys"])

    Q = bal["Q_kw"] * 1000.0
    lmtd, ft = lmtd_ft(bal["t1_in"], bal["t1_out"], bal["t2_in"], bal["t2_out"], u["z"], flow)
    if ft < 0.75 and not rating_mode: return None
    ft = max(ft, 0.5)

    K, at, as_, wt, ws, dpt, dps, tti, tto, tsi, tso, extra = calc_hydraulics_and_k(
        u, p, bal["G1"], bal["t1_in"], bal["t1_out"], bal["G2"], bal["t2_in"], bal["t2_out"]
    )
    Freq = Q / (K * lmtd * ft)
    mrg = (u["F"] - Freq) / Freq * 100.0

    if not rating_mode:
        if not (p["min_margin"] <= mrg <= p["max_margin"]): return None
        if dpt / 1000.0 > p["max_dp_t"] or dps / 1000.0 > p["max_dp_s"]: return None

    tm_t, tm_s = 0.5 * (tti + tto), 0.5 * (tsi + tso)
    q_flux = K * lmtd * ft
    t_tube_wall = tm_t - q_flux / at if tm_t > tm_s else tm_t + q_flux / at
    ok_t11, dt_allow, dt_act = check_table11(u["D"], Py, p["mat"], t_tube_wall, tm_s)

    req_type, warns = p["unit_type"], []
    if req_type in ("AUTO_T", "AUTO_X"):
        base_n, base_k = ("ТН", "ТК") if req_type == "AUTO_T" else ("ХН", "ХК")
        if ok_t11: chosen_type = base_n
        elif p["p_des_s"] <= TK_MAX_SHELL_P + 1e-6: chosen_type = base_k
        else:
            chosen_type = base_k
            warns.append(f"⚠ Δt_ст={dt_act}°C > доп. и P_корп={p['p_des_s']}>{TK_MAX_SHELL_P} МПа: нужен ТП (ГОСТ 15119 / ТУ 3612-024, Табл. 11)")
    else:
        chosen_type = req_type
        if chosen_type in ("ТН", "ХН") and not ok_t11:
            warns.append(f"⚠ Δt_ст={dt_act}°C > доп.{dt_allow}°C: нужен ТК/ХК или ТП (ТУ 3612-024-00220302-02, Табл. 11)")
        if chosen_type in ("ТК", "ХК") and p["p_des_s"] > TK_MAX_SHELL_P + 1e-6:
            warns.append(f"⚠ Для ТК/ХК макс P_корп={TK_MAX_SHELL_P} МПа: нужен ТП (ТУ 3612-024-00220302-02, Табл. 1 / ГОСТ 15119)")

    if flow == "co" and u["z"] > 1: warns.append("⚠ Прямоток допустим только при z=1 (Дытнерский, гл. 2)")
    if chosen_type not in u["types"]:
        if not rating_mode: return None
        warns.append(f"⚠ Типоразмер не входит в сортамент {chosen_type} (ТУ 3612-024-00220302-02, Табл. 2–6)")
    if chosen_type in ("ТК", "ХК") and p["orient"] == "В":
        warns.append("⚠ Аппараты ТК/ХК с компенсатором изготавливаются только горизонтальными Г (ТУ 3612-024-00220302-02, п. 1.2)")
    if not valid_pys: warns.append(f"⚠ P_расч={p_req} МПа > макс Py={Py} МПа (ТУ 3612-024-00220302-02, Табл. 1)")

    model, ins_warn = format_tu_name(u["D"], chosen_type, p["orient"], Py, p["mat"], u["dt"], u["L"], u["z"], p["climate"], p.get("ins_mode", "auto"), max(tsi, tso), min(tsi, tso))
    if ins_warn: warns.append(ins_warn)

    return dict(idx=u["idx"], model=model, F_cat=u["F"], F_req=round(Freq, 2), margin=round(mrg, 1), K=round(K, 1),
                lmtd_corr=round(lmtd * ft, 2), alpha_t=round(at, 0), alpha_s=round(as_, 0), wt=round(wt, 2), ws=round(ws, 2),
                dp_t=round(dpt / 1000.0, 2), dp_s=round(dps / 1000.0, 2), dt_wall=f"{dt_act}/{dt_allow}", warn="; ".join(warns),
                tti=tti, tto=tto, tsi=tsi, tso=tso, geo=u, extra=extra)

def simulate_unit(u, p):
    flow = p.get("flow_type", "counter")
    G1, t1i, G2, t2i = float(p["G1"]), float(p["t1_in"]), float(p["G2"]), float(p["t2_in"])
    C1, C2 = G1 * float(p["cp1"]), G2 * float(p["cp2"])
    Cmin, Cmax = min(C1, C2), max(C1, C2)
    Cr = Cmin / Cmax
    t1o, t2o = t1i - 0.5 * (t1i - t2i) * (Cmin / C1), t2i + 0.5 * (t1i - t2i) * (Cmin / C2)

    for _ in range(15):
        K, at, as_, wt, ws, dpt, dps, _, _, _, _, _ = calc_hydraulics_and_k(u, p, G1, t1i, t1o, G2, t2i, t2o)
        _, ft = lmtd_ft(t1i, t1o, t2i, t2o, u["z"], flow)
        ft = max(ft, 0.6)
        ntu = (K * u["F"] * ft) / Cmin
        if flow == "co": eps = (1.0 - math.exp(-ntu * (1.0 + Cr))) / (1.0 + Cr)
        elif abs(1.0 - Cr) < 1e-4: eps = ntu / (1.0 + ntu)
        else:
            e_term = math.exp(-ntu * (1.0 - Cr))
            eps = (1.0 - e_term) / (1.0 - Cr * e_term)
        Q = eps * Cmin * (t1i - t2i)
        t1o, t2o = t1i - Q / C1, t2i + Q / C2

    bal = dict(Q_kw=round(Q/1000.0, 3), G1=G1, t1_in=round(t1i, 2), t1_out=round(t1o, 2),
               G2=G2, t2_in=round(t2i, 2), t2_out=round(t2o, 2))
    res = solve_unit(u, p, bal, rating_mode=True)
    res["margin"], res["F_req"] = 0.0, u["F"]
    return bal, res

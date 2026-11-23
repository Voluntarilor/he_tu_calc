import math
from rules import MATERIALS, check_table11, format_tu_name

def lmtd_ft(t1i, t1o, t2i, t2o, z):
    dtb, dtm = max(t1i - t2o, 1e-6), max(t1o - t2i, 1e-6)
    lmtd = dtb if abs(dtb - dtm) < 1e-4 else (dtb - dtm) / math.log(dtb / dtm)
    if z == 1: return lmtd, 1.0
    P, R = (t2o - t2i) / (t1i - t2i), (t1i - t1o) / (t2o - t2i)
    eta = math.sqrt(R * R + 1.0)
    if P >= 2.0 / (1.0 + R + eta) - 1e-4: return lmtd, 0.0
    dlt = (1.0 - P)/P if abs(R - 1.0) < 1e-5 else (R - 1.0)/math.log((1.0 - P)/(1.0 - R*P))
    den = math.log((2.0 - P * (1.0 + R - eta)) / (2.0 - P * (1.0 + R + eta)))
    return lmtd, max(0.0, min(1.0, (eta / dlt) / den if den > 0 else 0.0))

def solve_unit(u, p, bal, rating_mode=False):
    if p["hot_side"] == "tube":
        Gt, tti, tto, rhot, cpt, mut, kt, rft = bal["G1"],bal["t1_in"],bal["t1_out"],p["rho1"],p["cp1"],p["mu1"],p["k1"],p["rf1"]
        Gs, tsi, tso, rhos, cps, mus, ks, rfs = bal["G2"],bal["t2_in"],bal["t2_out"],p["rho2"],p["cp2"],p["mu2"],p["k2"],p["rf2"]
    else:
        Gs, tsi, tso, rhos, cps, mus, ks, rfs = bal["G1"],bal["t1_in"],bal["t1_out"],p["rho1"],p["cp1"],p["mu1"],p["k1"],p["rf1"]
        Gt, tti, tto, rhot, cpt, mut, kt, rft = bal["G2"],bal["t2_in"],bal["t2_out"],p["rho2"],p["cp2"],p["mu2"],p["k2"],p["rf2"]

    p_req = max(p["p_des_t"], p["p_des_s"])
    valid_pys = [py for py in u["pys"] if py >= p_req - 1e-6]
    if not valid_pys:
        if not rating_mode: return None
        Py = max(u["pys"])
    else:
        Py = next(iter(valid_pys))

    Q = bal["Q_kw"] * 1000.0
    lmtd, ft = lmtd_ft(bal["t1_in"], bal["t1_out"], bal["t2_in"], bal["t2_out"], u["z"])
    if ft < 0.75 and not rating_mode: return None
    ft = max(ft, 0.5)

    dout, din, L, z = u["dt"] / 1000.0, (u["dt"] - 2 * u["w"]) / 1000.0, u["L"], u["z"]
    wt = Gt / (rhot * u["At"])
    Ret, Prt = rhot * wt * din / mut, cpt * mut / kt
    if Ret >= 2300:
        Nut = 0.023 * (Ret ** 0.8) * (Prt ** 0.4)
        lf = 0.25 * (math.log10(0.2e-3 / (3.7 * din) + (6.81 / Ret) ** 0.9)) ** -2
    else:
        gz = Ret * Prt * (din / L)
        Nut, lf = (1.61 * (gz ** (1.0 / 3.0)) if gz > 12 else 3.66), 64.0 / max(Ret, 1.0)
    at = Nut * kt / din
    wtn = 4.0 * Gt / (math.pi * (u["dyt"] / 1000.0) ** 2 * rhot)
    dpt = (lf*(L*z/din) + 2.5*(z-1) + 2.0*z)*(rhot*wt**2/2.0) + 3.0*(rhot*wtn**2/2.0)

    ws = Gs / (rhos * u["Ac"])
    Res, Prs = rhos * ws * dout / mus, cps * mus / ks
    wsn = 4.0 * Gs / (math.pi * (u["dys"] / 1000.0) ** 2 * rhos)
    mr = u["nr"] if p["use_tu_rows"] else math.ceil(math.sqrt((u["N"] - 1)/3.0 + 0.25))

    if p["method"] == "dytnerskiy":
        Nus = 0.24*(Res**0.6)*(Prs**0.36) if Res >= 1000 else 0.34*(Res**0.5)*(Prs**0.36)
        as_ = Nus * ks / dout
        dps = (3.0*mr*(u["nb"]+1)/(max(Res,10.0)**0.2))*(rhos*ws**2/2.0) + 1.5*u["nb"]*(rhos*ws**2/2.0) + 3.0*(rhos*wsn**2/2.0)
    else:
        aid = 0.27 * (Res ** 0.63) * (Prs ** 0.36) * ks / dout
        rlm, rs, Jc, Js = 0.18, 0.35, 1.02, 0.92
        Jl = 0.44 * (1.0 - rs) + (1.0 - 0.44 * (1.0 - rs)) * math.exp(-2.2 * rlm)
        Fbp = 0.14 + (0.04 if z > 1 else 0.0)
        Jb = math.exp(-1.35 * Fbp)
        Jr = 1.0 if Res >= 100 else (10.0 / max(mr * (u["nb"] + 1), 1)) ** 0.18
        as_ = aid * Jc * Jl * Jb * Js * Jr
        dpbi = 4.0 * (0.35 * (Res ** -0.2)) * mr * (rhos * ws ** 2 / 2.0)
        Rl, Rb = math.exp(-1.33 * (1.0 + rs) * (rlm ** 0.8)), math.exp(-3.7 * Fbp)
        ww = Gs / (rhos * math.sqrt(u["Ac"] * u["Aw"]))
        dpw = (2.0 + 0.6 * mr) * (rhos * ww ** 2 / 2.0) * Rl
        dps = ((u["nb"]-1)*dpbi*Rb*Rl + u["nb"]*dpw + 2.0*dpbi*Rb*0.92) + 3.0*(rhos*wsn**2/2.0)

    _, k_wall, _ = MATERIALS.get(p["mat"], ("", 45.0, 1.0))
    K = 1.0 / (1.0 / as_ + (u["w"] / 1000.0) / k_wall + rft + rfs + (1.0 / at) * (dout / din))
    Freq = Q / (K * lmtd * ft)
    mrg = (u["F"] - Freq) / Freq * 100.0

    if not rating_mode:
        if not (p["min_margin"] <= mrg <= p["max_margin"]): return None
        if dpt / 1000.0 > p["max_dp_t"] or dps / 1000.0 > p["max_dp_s"]: return None

    tm_t, tm_s = 0.5 * (tti + tto), 0.5 * (tsi + tso)
    q_flux = K * lmtd * ft
    t_tube_wall = tm_t - q_flux / at if tm_t > tm_s else tm_t + q_flux / at
    t_shell_wall = tm_s
    ok_t11, dt_allow, dt_act = check_table11(u["D"], Py, p["mat"], t_tube_wall, t_shell_wall)

    req_type = p["unit_type"]
    warn = ""
    if req_type == "AUTO_T":
        chosen_type = "ТН" if ok_t11 else "ТК"
    elif req_type == "AUTO_X":
        chosen_type = "ХН" if ok_t11 else "ХК"
    else:
        chosen_type = req_type
        if chosen_type in ("ТН", "ХН") and not ok_t11:
            warn = f"⚠ Δt_ст={dt_act}°C > доп.{dt_allow}°C (нужен ТК/ХК)"
    if chosen_type not in u["types"]:
        if not rating_mode: return None
        warn = f"⚠ Типоразмер не входит в ТУ для {chosen_type}"
    if chosen_type in ("ТК", "ХК") and p["orient"] == "В":
        warn = "⚠ Аппараты с линз. компенсатором (ТК/ХК) по ТУ только горизонтальные (Г)"
    if not valid_pys:
        warn = f"⚠ P_расч={p_req} МПа > макс Py={Py} МПа"

    model = format_tu_name(u["D"], chosen_type, p["orient"], Py, p["mat"], u["dt"], L, z, p["climate"], max(tsi, tso))
    return dict(model=model, F_cat=u["F"], F_req=round(Freq, 2), margin=round(mrg, 1), K=round(K, 1),
                alpha_t=round(at, 0), alpha_s=round(as_, 0), wt=round(wt, 2), ws=round(ws, 2),
                dp_t=round(dpt / 1000.0, 2), dp_s=round(dps / 1000.0, 2), dt_wall=f"{dt_act}/{dt_allow}", warn=warn)

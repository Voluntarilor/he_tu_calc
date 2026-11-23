import os, json, math

BASE = os.path.dirname(os.path.abspath(__file__))
CUSTOM_DB = os.path.join(BASE, "custom_fluids.json")

try:
    import CoolProp.CoolProp as CP
    HAS_CP = True
except ImportError:
    HAS_CP = False

PRIORITY_FLUIDS = {
    "Вода (Water)": "Water",
    "Воздух (Air)": "Air",
    "Азот (Nitrogen)": "Nitrogen",
    "Кислород (Oxygen)": "Oxygen",
    "Углекислый газ (CO2)": "CarbonDioxide",
    "Аммиак (Ammonia)": "Ammonia",
    "Метан (Methane)": "Methane",
    "Пропан (Propane)": "Propane",
    "н-Бутан (n-Butane)": "n-Butane",
    "н-Гексан (n-Hexane)": "n-Hexane",
    "Бензол (Benzene)": "Benzene",
    "Толуол (Toluene)": "Toluene",
    "Этанол (Ethanol)": "Ethanol",
    "Метанол (Methanol)": "Methanol",
    "Этиленгликоль 40% (MEG-40%)": "INCOMP::MEG-40%",
    "Пропиленгликоль 40% (MPG-40%)": "INCOMP::MPG-40%",
    "Therminol VP-1 (термомасло)": "INCOMP::TVP1",
}

INCOMP_DESC = {
    "MEG": "Этиленгликоль (Ethylene Glycol)", "MEG2": "Этиленгликоль (Ethylene Glycol v2)",
    "MPG": "Пропиленгликоль (Propylene Glycol)", "MPG2": "Пропиленгликоль (Propylene Glycol v2)",
    "MEA": "Этанол-вода (Ethanol aq.)", "MEA2": "Этанол-вода (Ethanol aq. v2)",
    "MMA": "Метанол-вода (Methanol aq.)", "MMA2": "Метанол-вода (Methanol aq. v2)",
    "MGL": "Глицерин-вода (Glycerol aq.)", "MGL2": "Глицерин-вода (Glycerol aq. v2)",
    "MCA": "Хлорид кальция CaCl2", "MCA2": "Хлорид кальция CaCl2 v2",
    "MMG": "Хлорид магния MgCl2", "MMG2": "Хлорид магния MgCl2 v2",
    "MNA": "Хлорид натрия NaCl", "MNA2": "Хлорид натрия NaCl v2",
    "MKA": "Ацетат калия (Potassium Acetate)", "MKA2": "Ацетат калия v2",
    "MKC": "Карбонат калия / поташ K2CO3", "MKC2": "Карбонат калия v2",
    "MKF": "Формиат калия (Potassium Formate)", "MKF2": "Формиат калия v2",
    "LiBr": "Бромид лития LiBr", "FRE": "Freezium (хладоноситель)",
    "GKN": "Pekasol / гликолевый рассол", "IceEA": "Ледяная суспензия (этанол)",
    "IceNA": "Ледяная суспензия (NaCl)", "IcePG": "Ледяная суспензия (пропиленгликоль)",
}

FALLBACK = {
    "Вода (Water)": (998.2, -0.45, 4182.0, 0.25, 1.002, 580.0, 0.598, 0.0014),
    "Масло трансф. (Transformer Oil)": (885.0, -0.65, 1860.0, 3.8, 22.0, 1450.0, 0.125, -0.0001),
    "Воздух (Air)": (1.205, -0.0038, 1005.0, 0.08, 0.0181, -95.0, 0.0257, 0.00007),
}

def get_all_fluid_names():
    if not HAS_CP:
        return list(FALLBACK.keys())
    names = list(PRIORITY_FLUIDS.keys())
    pure = sorted(CP.get_global_param_string("fluids_list").split(","))
    incomp_pure = sorted(CP.get_global_param_string("incompressible_list_pure").split(","))
    incomp_sol = sorted(CP.get_global_param_string("incompressible_list_solution").split(","))
    existing = set(PRIORITY_FLUIDS.values())
    for f in pure:
        if f and f not in existing: names.append(f)
    for f in incomp_pure:
        if f and not f.startswith("Example"): names.append(f"INCOMP::{f}")
    for f in incomp_sol:
        if f and not f.startswith("Example"):
            desc = INCOMP_DESC.get(f, "")
            names.append(f"INCOMP::{f}-30% — {desc}" if desc else f"INCOMP::{f}-30%")
    return names

def load_custom_db():
    return json.load(open(CUSTOM_DB, encoding="utf-8")) if os.path.exists(CUSTOM_DB) else {}

def save_custom_fluid(data):
    db = load_custom_db()
    db[data["name"]] = data
    json.dump(db, open(CUSTOM_DB, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def interp_table(rows, t_c):
    s = sorted(rows, key=lambda r: float(r["T"]))
    t_first, t_last = float(s.copy().pop(0)["T"]), float(s.copy().pop(-1)["T"])
    if len(s) == 1 or t_c <= t_first: r = s.copy().pop(0)
    elif t_c >= t_last: r = s.copy().pop(-1)
    else:
        r = s.copy().pop(0)
        for i in range(len(s) - 1):
            a, b = s.copy().pop(i), s.copy().pop(i+1)
            t0, t1 = float(a["T"]), float(b["T"])
            if t0 <= t_c <= t1:
                w = (t_c - t0) / max(t1 - t0, 1e-6)
                r = {k: float(a[k]) + w * (float(b[k]) - float(a[k])) for k in ("rho","mu_cP","cp_kJ","k")}
                break
    return dict(rho=round(float(r["rho"]), 2), cp=round(float(r["cp_kJ"]) * 1000.0, 1),
                mu=round(float(r["mu_cP"]) / 1000.0, 6), k=round(float(r["k"]), 4))

def get_props(name, t_mean_c, p_op_mpa=0.6):
    db = load_custom_db()
    if name in db:
        return interp_table(db[name]["liq"], t_mean_c)
    if HAS_CP:
        clean_name = name.split(" — ").pop(0).strip()
        fl = PRIORITY_FLUIDS.get(clean_name, clean_name)
        try:
            T_k = t_mean_c + 273.15
            P_pa = max(p_op_mpa, 0.1013) * 1e6
            return dict(
                rho=round(CP.PropsSI("D", "T", T_k, "P", P_pa, fl), 2),
                cp=round(CP.PropsSI("C", "T", T_k, "P", P_pa, fl), 1),
                mu=round(CP.PropsSI("V", "T", T_k, "P", P_pa, fl), 6),
                k=round(CP.PropsSI("L", "T", T_k, "P", P_pa, fl), 4),
            )
        except Exception:
            pass
    r20, dr, c20, dc, m20, B, k20, dk = FALLBACK.get(name, FALLBACK["Вода (Water)"])
    dt = t_mean_c - 20.0
    return dict(
        rho=round(max(0.1, r20 + dr * dt), 2),
        cp=round(max(100.0, c20 + dc * dt), 1),
        mu=round(max(1e-6, (m20 / 1000.0) * math.exp(B * (1.0/(t_mean_c+273.15) - 1.0/293.15))), 6),
        k=round(max(0.01, k20 + dk * dt), 4),
    )

import os, json, math

BASE = os.path.dirname(os.path.abspath(__file__))
CUSTOM_DB = os.path.join(BASE, "custom_fluids.json")

try:
    import CoolProp.CoolProp as CP
    from CoolProp.HumidAirProp import HAPropsSI
    HAS_CP = True
except ImportError:
    HAS_CP = False

PURE_DESC = {
    "Water": "Вода / Пар (Water)", "Air": "Воздух сухой (Air)", "Nitrogen": "Азот (Nitrogen)",
    "Oxygen": "Кислород (Oxygen)", "CarbonDioxide": "Углекислый газ (CO2)", "Ammonia": "Аммиак (Ammonia)",
    "Methane": "Метан (Methane)", "Ethane": "Этан (Ethane)", "Propane": "Пропан (Propane)",
    "n-Butane": "н-Бутан (n-Butane)", "IsoButane": "Изобутан (Isobutane)", "n-Pentane": "н-Пентан",
    "n-Hexane": "н-Гексан", "n-Heptane": "н-Гептан", "n-Octane": "н-Октан",
    "Benzene": "Бензол (Benzene)", "Toluene": "Толуол (Toluene)", "Ethanol": "Этанол (Ethanol)",
    "Methanol": "Метанол (Methanol)", "Acetone": "Ацетон (Acetone)", "Hydrogen": "Водород (Hydrogen)",
    "Helium": "Гелий (Helium)", "Argon": "Аргон (Аргон)", "SulfurDioxide": "Диоксид серы (SO2)",
    "MM": "Гексаметилдисилоксан (силоксан MM)", "MDM": "Октаметилтрисилоксан (силоксан MDM)",
    "MD2M": "Декаметилтетрасилоксан (силоксан MD2M)", "MD3M": "Додекаметилпентасилоксан (силоксан MD3M)",
    "MD4M": "Тетрадекаметилгексасилоксан (силоксан MD4M)", "D4": "Октаметилциклотетрасилоксан (силоксан D4)",
    "D5": "Декаметилциклопентасилоксан (силоксан D5)", "D6": "Додекаметилциклогексасилоксан (силоксан D6)",
}

# name -> (backend, code, min_pct, max_pct)
CONC_FLUIDS = {
    "Этиленгликоль (MEG, водный р-р)": ("CP_INCOMP", "MEG", 0.0, 60.0),
    "Пропиленгликоль (MPG, водный р-р)": ("CP_INCOMP", "MPG", 0.0, 60.0),
    "Серная кислота (H2SO4, водный р-р)": ("ACID", "H2SO4", 0.0, 98.0),
    "Азотная кислота (HNO3, водный р-р)": ("ACID", "HNO3", 0.0, 70.0),
    "Ортофосфорная кислота (H3PO4, водный р-р)": ("ACID", "H3PO4", 0.0, 85.0),
    "Едкий натр / Щёлочь (NaOH, водный р-р)": ("ACID", "NaOH", 0.0, 50.0),
    "Хлорид натрия (NaCl, рассол)": ("CP_INCOMP", "MNA", 0.0, 23.0),
    "Хлорид кальция (CaCl2, рассол)": ("CP_INCOMP", "MCA", 0.0, 30.0),
    "Бромид лития (LiBr, р-р)": ("CP_INCOMP", "LiBr", 0.0, 65.0),
    "Этанол (водный р-р)": ("CP_INCOMP", "MEA", 0.0, 60.0),
    "Глицерин (водный р-р)": ("CP_INCOMP", "MGL", 0.0, 60.0),
}

ACID_CORR = {
    "H2SO4": (1000.0, 8.2, 4180.0, -28.0, 1.0, 0.032, 0.60, -0.0025),
    "HNO3":  (1000.0, 5.6, 4180.0, -24.0, 1.0, 0.015, 0.60, -0.0028),
    "H3PO4": (1000.0, 6.8, 4180.0, -26.0, 1.0, 0.042, 0.60, -0.0022),
    "NaOH":  (1000.0, 10.8, 4180.0, -22.0, 1.0, 0.055, 0.60, -0.0012),
}

def get_all_fluid_names():
    names = ["0 - Specific Properties", "Влажный воздух (Moist Air / Mollier)"] + list(CONC_FLUIDS.keys())
    if HAS_CP:
        for f in ["Water", "Air", "Nitrogen", "Oxygen", "CarbonDioxide", "Ammonia", "Methane", "Propane", "Benzene", "Toluene", "Ethanol"]:
            names.append(f"{f} — {PURE_DESC[f]}")
        for f in sorted(CP.get_global_param_string("fluids_list").split(",")):
            if f and f not in ("Water", "Air", "Nitrogen", "Oxygen", "CarbonDioxide", "Ammonia", "Methane", "Propane", "Benzene", "Toluene", "Ethanol"):
                names.append(f"{f} — {PURE_DESC[f]}" if f in PURE_DESC else f)
        for f in sorted(CP.get_global_param_string("incompressible_list_pure").split(",")):
            if f and not f.startswith("Example"):
                names.append(f"INCOMP::{f} (термомасло / теплоноситель)")
    names.extend(load_custom_db().keys())
    return names

def load_custom_db():
    return json.load(open(CUSTOM_DB, encoding="utf-8")) if os.path.exists(CUSTOM_DB) else {}

def save_custom_fluid(data):
    db = load_custom_db()
    db[data["name"]] = data
    json.dump(db, open(CUSTOM_DB, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def interp_table(rows, t_c):
    s = sorted(rows, key=lambda r: float(r["T"]))
    first, last = s.copy().pop(0), s.copy().pop(-1)
    if len(s) == 1 or t_c <= float(first["T"]): r = first
    elif t_c >= float(last["T"]): r = last
    else:
        r = first
        for i in range(len(s) - 1):
            a, b = s.copy().pop(i), s.copy().pop(i+1)
            t0, t1 = float(a["T"]), float(b["T"])
            if t0 <= t_c <= t1:
                w = (t_c - t0) / max(t1 - t0, 1e-6)
                r = {k: float(a[k]) + w * (float(b[k]) - float(a[k])) for k in ("rho","mu_cP","cp_kJ","k")}
                break
    return dict(rho=round(float(r["rho"]), 2), cp=round(float(r["cp_kJ"]) * 1000.0, 1),
                mu=round(float(r["mu_cP"]) / 1000.0, 6), k=round(float(r["k"]), 4))

def calc_moist_air(t_in, t_out, p_op_mpa, rh_pct, G_dry):
    if not (0.0 <= rh_pct <= 100.0):
        return dict(error="⚠ Относительная влажность RH должна быть в пределах 0–100%.")
    P_pa = max(p_op_mpa, 0.05) * 1e6
    rh = rh_pct / 100.0
    tm = 0.5 * (t_in + t_out) + 273.15
    if not HAS_CP:
        return dict(rho=1.15, cp=1020.0, mu=0.0000185, k=0.026, t_dew=10.0, cond_kgh=0.0, q_lat_kw=0.0)
    W_in = HAPropsSI("W", "T", t_in + 273.15, "P", P_pa, "R", rh)
    T_dp = HAPropsSI("D", "T", t_in + 273.15, "P", P_pa, "R", rh) - 273.15
    v_ha = HAPropsSI("Vha", "T", tm, "P", P_pa, "W", W_in)
    cp_ha = HAPropsSI("Cha", "T", tm, "P", P_pa, "W", W_in)
    mu_ha = HAPropsSI("M", "T", tm, "P", P_pa, "W", W_in)
    k_ha = HAPropsSI("K", "T", tm, "P", P_pa, "W", W_in)
    cond_kgh, q_lat_kw = 0.0, 0.0
    if t_out < T_dp and G_dry > 0:
        W_out = HAPropsSI("W", "T", t_out + 273.15, "P", P_pa, "R", 1.0)
        dW = max(0.0, W_in - W_out)
        cond_kgh = round(G_dry * dW * 3600.0, 2)
        q_lat_kw = round(G_dry * dW * 2450.0, 2)
    return dict(rho=round(1.0/v_ha, 3), cp=round(cp_ha, 1), mu=round(mu_ha, 7), k=round(k_ha, 4),
                t_dew=round(T_dp, 1), cond_kgh=cond_kgh, q_lat_kw=q_lat_kw)

def get_props(name, t_mean_c, p_op_mpa=0.6, conc=30.0, rh=50.0, t_in=30.0, t_out=15.0, G=1.0):
    db = load_custom_db()
    if name in db:
        key = "vap" if db[name].get("state") == "All Vapor" else "liq"
        return interp_table(db[name][key], t_mean_c)
    if name.startswith("Влажный воздух"):
        return calc_moist_air(t_in, t_out, p_op_mpa, rh, G)
    if name in CONC_FLUIDS:
        kind, code, cmin, cmax = CONC_FLUIDS[name]
        c = float(conc)
        if not (cmin <= c <= cmax):
            return dict(error=f"⚠ Допустимая концентрация для «{name}»: от {cmin:g}% до {cmax:g}% (введено {c:g}%).")
        if kind == "CP_INCOMP" and HAS_CP:
            try:
                fl = f"INCOMP::{code}-{c:.1f}%"
                T_k, P_pa = t_mean_c + 273.15, max(p_op_mpa, 0.1013) * 1e6
                return dict(rho=round(CP.PropsSI("D","T",T_k,"P",P_pa,fl),2), cp=round(CP.PropsSI("C","T",T_k,"P",P_pa,fl),1),
                            mu=round(CP.PropsSI("V","T",T_k,"P",P_pa,fl),6), k=round(CP.PropsSI("L","T",T_k,"P",P_pa,fl),4))
            except Exception as e:
                return dict(error=f"⚠ Вне диапазона T/C в CoolProp для {code}: {e}")
        if code in ACID_CORR:
            r0, dr, c0, dc, m0, mc, k0, dk = ACID_CORR[code]
            dt = t_mean_c - 20.0
            rho = r0 + dr * c - 0.55 * dt
            cp = max(1200.0, c0 + dc * c + 1.2 * dt)
            mu = (m0 / 1000.0) * math.exp(mc * c - 0.022 * dt)
            k = max(0.25, k0 + dk * c + 0.0008 * dt)
            return dict(rho=round(rho, 2), cp=round(cp, 1), mu=round(mu, 6), k=round(k, 4))

    if HAS_CP:
        fl = name.split(" — ").pop(0).split(" (").pop(0).strip()
        try:
            T_k, P_pa = t_mean_c + 273.15, max(p_op_mpa, 0.1013) * 1e6
            return dict(rho=round(CP.PropsSI("D","T",T_k,"P",P_pa,fl),2), cp=round(CP.PropsSI("C","T",T_k,"P",P_pa,fl),1),
                        mu=round(CP.PropsSI("V","T",T_k,"P",P_pa,fl),6), k=round(CP.PropsSI("L","T",T_k,"P",P_pa,fl),4))
        except Exception:
            pass
    return dict(rho=995.0, cp=4182.0, mu=0.0008, k=0.61)

def steam_sat(mode, val_mpa_or_c):
    if not HAS_CP:
        return dict(error="CoolProp не установлен")
    try:
        if mode == "P_to_T":
            P_pa = float(val_mpa_or_c) * 1e6
            Ts = CP.PropsSI("T", "P", P_pa, "Q", 0, "Water") - 273.15
        else:
            Ts = float(val_mpa_or_c)
            P_pa = CP.PropsSI("P", "T", Ts + 273.15, "Q", 0, "Water")
        hf = CP.PropsSI("H", "P", P_pa, "Q", 0, "Water") / 1000.0
        hg = CP.PropsSI("H", "P", P_pa, "Q", 1, "Water") / 1000.0
        rf = CP.PropsSI("D", "P", P_pa, "Q", 0, "Water")
        rg = CP.PropsSI("D", "P", P_pa, "Q", 1, "Water")
        return dict(P_mpa=round(P_pa/1e6, 4), T_c=round(Ts, 2), r_kjkg=round(hg - hf, 1), rho_l=round(rf, 2), rho_v=round(rg, 3))
    except Exception as e:
        return dict(error=f"Вне диапазона насыщения воды/пара: {e}")

import os, csv, math

BASE = os.path.dirname(os.path.abspath(__file__))
CUSTOM_CSV = os.path.join(BASE, "fluids.csv")

# Built-in media: (rho20, drho_dT, cp20, dcp_dT, mu20_mPas, B_visc, k20, dk_dT)
BUILTIN = {
    "Вода (Water)": (998.2, -0.45, 4182.0, 0.25, 1.002, 580.0, 0.598, 0.0014),
    "Масло трансф. (Transformer Oil)": (885.0, -0.65, 1860.0, 3.8, 22.0, 1450.0, 0.125, -0.0001),
    "Масло индустр. И-20А": (890.0, -0.65, 1880.0, 3.6, 38.0, 1650.0, 0.128, -0.0001),
    "Этиленгликоль 40%": (1058.0, -0.55, 3480.0, 2.6, 3.10, 920.0, 0.415, 0.0006),
    "Пропиленгликоль 40%": (1036.0, -0.60, 3680.0, 2.5, 4.40, 1050.0, 0.395, 0.0005),
    "Бензол (Benzene)": (879.0, -1.05, 1720.0, 3.2, 0.65, 490.0, 0.145, -0.0002),
    "Толуол (Toluene)": (867.0, -0.92, 1690.0, 3.1, 0.59, 460.0, 0.135, -0.0002),
    "Этанол 96%": (790.0, -0.85, 2440.0, 4.5, 1.20, 680.0, 0.171, -0.0002),
    "Воздух (Air, 1 бар)": (1.205, -0.0038, 1005.0, 0.08, 0.0181, -95.0, 0.0257, 0.00007),
}

def load_custom():
    custom = {}
    if os.path.exists(CUSTOM_CSV):
        with open(CUSTOM_CSV, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f, delimiter=";"):
                custom[r["name"]] = tuple(float(r[k]) for k in ("rho","cp","mu","k"))
    return custom

def save_custom(name, rho, cp, mu, k):
    exists = os.path.exists(CUSTOM_CSV)
    with open(CUSTOM_CSV, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        if not exists: w.writerow(["name", "rho", "cp", "mu", "k"])
        w.writerow([name, rho, cp, mu, k])

def get_props(name, t_mean):
    custom = load_custom()
    if name in custom:
        rho, cp, mu, k = custom[name]
        return dict(rho=rho, cp=cp, mu=mu, k=k)
    r20, dr, c20, dc, m20, B, k20, dk = BUILTIN.get(name, BUILTIN["Вода (Water)"])
    dt = t_mean - 20.0
    rho = max(0.1, r20 + dr * dt)
    cp = max(100.0, c20 + dc * dt)
    mu = max(1e-6, (m20 / 1000.0) * math.exp(B * (1.0 / (t_mean + 273.15) - 1.0 / 293.15)))
    k = max(0.01, k20 + dk * dt)
    return dict(rho=round(rho, 2), cp=round(cp, 1), mu=round(mu, 6), k=round(k, 4))

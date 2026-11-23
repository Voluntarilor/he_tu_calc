import os, glob, csv

BASE = os.path.dirname(os.path.abspath(__file__))
def num(v): return float(str(v).strip().replace(",", "."))

def read_csv_auto(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp1251"):
        try: text = raw.decode(enc); break
        except UnicodeDecodeError: pass
    lines = text.splitlines()
    first = next(iter(lines), "")
    delim = ";" if first.count(";") > first.count(",") else ","
    return list(csv.DictReader(lines, delimiter=delim))

def load_catalog():
    p_map, cat_rows = {}, []
    for f in glob.glob(os.path.join(BASE, "*.csv")):
        if "results" in f or "fluids" in f: continue
        data = read_csv_auto(f)
        if not data: continue
        cols = next(iter(data)).keys()
        if "D_кожуха_мм" in cols:
            for r in data:
                p_map.setdefault(int(num(r["D_кожуха_мм"])), []).append(num(r["P_rasc_korp_МПа"]))
        elif "D_shell_mm" in cols:
            cat_rows = data
    if not cat_rows:
        raise FileNotFoundError(f"Put your geometry CSV (with D_shell_mm) inside {BASE}")
    for D in p_map: p_map[D] = sorted(set(p_map[D]))

    rows = []
    for r in cat_rows:
        D, dt, z = int(num(r["D_shell_mm"])), int(num(r["D_tube_mm"])), int(num(r["pass_number_z"]))
        w, L, F = num(r["Tube_thickness_mm"]), num(r["L_tubes_mm"]), num(r["F_HE_m2"])
        At, Aw, Ac = num(r["A_passage of one pass tube side_m2"]), num(r["A_passage area in cut region_m2"]), num(r["A_passage area between baffles_m2"])
        nb, N, nr = int(num(r["number of baffles_x"])), int(num(r["tube number_N"])), int(num(r["tube rows nrows number_n"]))
        if D in (600, 630) and dt == 25 and Ac == 0.45: Ac = 0.045
        if D == 1000 and dt == 25 and Aw == 0.0662: Aw = 0.1062
        dyt = {159:80,273:100,325:100,400:150,426:150,600:(150 if z==4 else 200),630:(150 if z==4 else 200),800:(200 if z==4 else 250),1000:(200 if z==4 else 300),1200:(250 if z==4 else 350)}[D]
        dys = {159:80,273:100,325:100,400:150,426:150,600:200,630:200,800:250,1000:300,1200:350}[D]
        types = ["ТН"] + (["ТК"] if D >= 325 or z == 1 else [])
        if dt == 25 and ((D in (159, 273) and z == 1) or (D >= 325 and z in (2, 4))): types += ["ХН", "ХК"]
        pys = p_map.get(D, [0.6, 1.0, 1.6, 2.5, 4.0])
        rows.append(dict(D=D, dt=dt, w=w, z=z, L=L, F=F, At=At, Aw=Aw, Ac=Ac, nb=nb, N=N, nr=nr, dyt=dyt, dys=dys, types=types, pys=pys))
    return rows

CATALOG = load_catalog()

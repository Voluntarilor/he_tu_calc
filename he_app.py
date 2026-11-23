import os, json
from http.server import HTTPServer, BaseHTTPRequestHandler
from catalog import CATALOG
from balance import solve_balance
from thermal import solve_unit, simulate_unit
from fluids import get_all_fluid_names, HAS_CP, load_custom_db, save_custom_fluid, get_props
from rules import MATERIALS, TEMA_FOULING, test_pressure_gost34347

BASE = os.path.dirname(os.path.abspath(__file__))

class Handler(BaseHTTPRequestHandler):
    def send_json(self, obj):
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(json.dumps(obj).encode("utf-8"))
    def do_GET(self):
        if self.path == "/meta":
            fluids = ["0 - Specific Properties"] + get_all_fluid_names() + list(load_custom_db().keys())
            units_list = [f"{u['D']}-{u['dt']}x{int(u['w'])}-{u['L']}-{u['z']} (F={u['F']} м²)" for u in CATALOG]
            return self.send_json(dict(fluids=fluids, materials=list(MATERIALS.keys()), fouling=TEMA_FOULING, units=units_list))
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
        with open(os.path.join(BASE, "index.html"), "rb") as f: self.wfile.write(f.read())
    def do_POST(self):
        p = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/props":
            return self.send_json(get_props(p["name"], float(p["t_mean"]), float(p.get("p_op", 0.6))))
        if self.path == "/save_fluid":
            save_custom_fluid(p)
            return self.send_json(dict(ok=True))
        p_test = test_pressure_gost34347(max(p["p_des_t"], p["p_des_s"]), p["t_des"], p["mat"])
        mode = p.get("calc_mode", "design")
        if mode == "sim":
            if any(p.get(k) is None for k in ("G1", "t1_in", "G2", "t2_in")):
                return self.send_json(dict(error="Для режима Симуляции задайте G1, T1 вход, G2 и t2 вход."))
            idx = int(p.get("unit_idx", 0))
            u = next((x for i, x in enumerate(CATALOG) if i == idx), None)
            sim_bal, r = simulate_unit(u, p)
            p_sim = {**p, "Q_kw": None, "t1_out": sim_bal["t1_out"], "t2_out": sim_bal["t2_out"]}
            bal, _ = solve_balance(p_sim)
            return self.send_json(dict(balance=bal, p_test=p_test, units=[r]))
        bal, err = solve_balance(p)
        if err: return self.send_json(dict(error=err))
        if mode == "rating":
            idx = int(p.get("unit_idx", 0))
            u = next((x for i, x in enumerate(CATALOG) if i == idx), None)
            out = [solve_unit(u, p, bal, True)] if u else []
        else:
            out = sorted([r for u in CATALOG if (r := solve_unit(u, p, bal, False))], key=lambda x: x["F_cat"])
        self.send_json(dict(balance=bal, p_test=p_test, units=out))

if __name__ == "__main__":
    print(f"Loaded {len(CATALOG)} units (CoolProp={HAS_CP}). Starting server on 0.0.0.0:8050...")
    HTTPServer(("0.0.0.0", 8050), Handler).serve_forever()

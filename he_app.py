import os, json
from http.server import HTTPServer, BaseHTTPRequestHandler
from catalog import CATALOG
from balance import solve_balance
from thermal import solve_unit, simulate_unit
from fluids import get_all_fluid_names, CONC_FLUIDS, HAS_CP, load_custom_db, save_custom_fluid, get_props, steam_sat
from rules import MATERIALS, TEMA_FOULING, test_pressure_gost34347
from datasheet import render_datasheet
from calcsheet import render_calcsheet

BASE = os.path.dirname(os.path.abspath(__file__))

class Handler(BaseHTTPRequestHandler):
    def send_json(self, obj):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode("utf-8"))

    def send_html(self, html_str):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html_str.encode("utf-8"))

    def do_GET(self):
        if self.path == "/meta":
            cat_meta = [dict(idx=u["idx"], D=u["D"], dt=u["dt"], w=int(u["w"]), L=u["L"], z=u["z"], F=u["F"], types=u["types"]) for u in CATALOG]
            return self.send_json(dict(
                fluids=get_all_fluid_names(), conc_fluids=list(CONC_FLUIDS.keys()),
                materials=list(MATERIALS.keys()), fouling=TEMA_FOULING, cat=cat_meta
            ))
        with open(os.path.join(BASE, "index.html"), "rb") as f:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(f.read())

    def do_POST(self):
        p = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/props":
            return self.send_json(get_props(
                p["name"], float(p["t_mean"]), float(p.get("p_op", 0.6)),
                float(p.get("conc", 30.0)), float(p.get("rh", 50.0)),
                float(p.get("t_in", 30.0)), float(p.get("t_out", 15.0)), float(p.get("G", 1.0))
            ))
        if self.path == "/steam":
            return self.send_json(steam_sat(p["mode"], float(p["val"])))
        if self.path == "/save_fluid":
            save_custom_fluid(p)
            return self.send_json(dict(ok=True))

        p_test = test_pressure_gost34347(max(p["p_des_t"], p["p_des_s"]), p["t_des"], p["mat"])
        mode = p.get("calc_mode", "design")

        if self.path in ("/datasheet", "/calcsheet"):
            if self.path == "/calcsheet":
                p = dict(p, method="dytnerskiy")
            idx = int(p.get("unit_idx", 0))
            u = next((x for x in CATALOG if x["idx"] == idx), None)
            if not u:
                return self.send_html("<h3>Unit not found</h3>")
            if mode == "sim":
                sim_bal, r = simulate_unit(u, p)
                p_sim = dict(p)
                p_sim.update(Q_kw=None, t1_out=sim_bal["t1_out"], t2_out=sim_bal["t2_out"])
                bal, _ = solve_balance(p_sim)
            else:
                bal, err = solve_balance(p)
                if err:
                    return self.send_html(f"<h3>{err}</h3>")
                r = solve_unit(u, p, bal, rating_mode=True)
            fn = render_datasheet if self.path == "/datasheet" else render_calcsheet
            return self.send_html(fn(p, bal, r, p_test))

        if mode == "sim":
            if any(p.get(k) is None for k in ("G1", "t1_in", "G2", "t2_in")):
                return self.send_json(dict(error="Для режима Симуляции задайте G1, T1 вход, G2 и t2 вход."))
            idx = int(p.get("unit_idx", 0))
            u = next((x for x in CATALOG if x["idx"] == idx), None)
            sim_bal, r = simulate_unit(u, p)
            p_sim = dict(p)
            p_sim.update(Q_kw=None, t1_out=sim_bal["t1_out"], t2_out=sim_bal["t2_out"])
            bal, _ = solve_balance(p_sim)
            return self.send_json(dict(balance=bal, p_test=p_test, units=[r]))

        bal, err = solve_balance(p)
        if err:
            return self.send_json(dict(error=err))

        if mode == "rating":
            idx = int(p.get("unit_idx", 0))
            u = next((x for x in CATALOG if x["idx"] == idx), None)
            out = [solve_unit(u, p, bal, True)] if u else []
        else:
            out = sorted([r for u in CATALOG if (r := solve_unit(u, p, bal, False))], key=lambda x: x["F_cat"])
        self.send_json(dict(balance=bal, p_test=p_test, units=out))

if __name__ == "__main__":
    print(f"Loaded {len(CATALOG)} units (CoolProp={HAS_CP}). Starting server on 0.0.0.0:8050...")
    HTTPServer(("0.0.0.0", 8050), Handler).serve_forever()

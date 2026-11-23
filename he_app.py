import os, json, webbrowser, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from catalog import CATALOG
from balance import solve_balance
from thermal import solve_unit
from fluids import BUILTIN, load_custom, save_custom, get_props
from rules import MATERIALS, test_pressure_gost34347

BASE = os.path.dirname(os.path.abspath(__file__))

class Handler(BaseHTTPRequestHandler):
    def send_json(self, obj):
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(json.dumps(obj).encode("utf-8"))
    def do_GET(self):
        if self.path == "/meta":
            fluids = ["0 - Ручной ввод"] + list(BUILTIN.keys()) + list(load_custom().keys())
            units_list = [f"{u['D']}-{u['dt']}x{int(u['w'])}-{u['L']}-{u['z']} (F={u['F']} м²)" for u in CATALOG]
            return self.send_json(dict(fluids=fluids, materials=list(MATERIALS.keys()), units=units_list))
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
        with open(os.path.join(BASE, "index.html"), "rb") as f: self.wfile.write(f.read())
    def do_POST(self):
        p = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/props":
            return self.send_json(get_props(p["name"], float(p["t_mean"])))
        if self.path == "/save_fluid":
            save_custom(p["name"], float(p["rho"]), float(p["cp"]), float(p["mu"]), float(p["k"]))
            return self.send_json(dict(ok=True))
        bal, err = solve_balance(p)
        if err: return self.send_json(dict(error=err))
        p_test = test_pressure_gost34347(max(p["p_des_t"], p["p_des_s"]), p["t_des"], p["mat"])
        if p.get("calc_mode") == "rating":
            idx = int(p.get("unit_idx", 0))
            u = next((x for i, x in enumerate(CATALOG) if i == idx), None)
            r = solve_unit(u, p, bal, rating_mode=True) if u else None
            out = [r] if r else []
        else:
            out = sorted([r for u in CATALOG if (r := solve_unit(u, p, bal, False))], key=lambda x: x["F_cat"])
        self.send_json(dict(balance=bal, p_test=p_test, units=out))

if __name__ == "__main__":
    print(f"Loaded {len(CATALOG)} units. Opening browser...")
    threading.Timer(1.0, lambda: webbrowser.open("http://127.0.0.1:8050")).start()
    HTTPServer(("0.0.0.0", 8050), Handler).serve_forever()

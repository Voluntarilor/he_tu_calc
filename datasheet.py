from rules import MATERIALS, MAT_PARTS

def render_datasheet(p, bal, r, p_test):
    u, ex = r["geo"], r["extra"]
    hot_in_tube = (p["hot_side"] == "tube")
    fl_s = p["fl2"] if hot_in_tube else p["fl1"]
    fl_t = p["fl1"] if hot_in_tube else p["fl2"]
    pop_s = p["pop2"] if hot_in_tube else p["pop1"]
    pop_t = p["pop1"] if hot_in_tube else p["pop2"]
    dp_al_s = p["max_dp_s"]
    dp_al_t = p["max_dp_t"]
    mat_ru, mat_en = MAT_PARTS.get(p["mat"], (p["mat"], p["mat"]))
    or_en = "Horizontal" if p["orient"] == "Г" else "Vertical"
    or_ru = "Горизонтальный" if p["orient"] == "Г" else "Вертикальный"

    if p["flow_type"] == "co":
        fl_dir_en, fl_dir_ru = "Co-current", "Прямоток"
    elif u["z"] > 1:
        fl_dir_en, fl_dir_ru = f"Mixed flow (1–{u['z']})", f"Смешанный ток (1–{u['z']})"
    else:
        fl_dir_en, fl_dir_ru = "Counter-current", "Противоток"

    passes_svg = '<line x1="35" y1="45" x2="215" y2="45" stroke="#555" stroke-width="1.5"/>' if u["z"] > 1 else ''
    svg_sketch = f'''<svg viewBox="0 0 260 90" width="240" height="82">
      <rect x="35" y="22" width="180" height="46" fill="#f8f9fa" stroke="#000" stroke-width="1.5"/>
      <path d="M35,22 Q12,45 35,68 M215,22 Q238,45 215,68" fill="#e9ecef" stroke="#000" stroke-width="1.5"/>
      <line x1="42" y1="22" x2="42" y2="68" stroke="#000" stroke-width="2"/>
      <line x1="208" y1="22" x2="208" y2="68" stroke="#000" stroke-width="2"/>
      <line x1="42" y1="33" x2="208" y2="33" stroke="#666"/><line x1="42" y1="57" x2="208" y2="57" stroke="#666"/>
      {passes_svg}
      <line x1="65" y1="8" x2="65" y2="22" stroke="#000" stroke-width="2"/><text x="69" y="16" font-size="9">↓</text>
      <line x1="185" y1="68" x2="185" y2="82" stroke="#000" stroke-width="2"/><text x="189" y="81" font-size="9">↓</text>
      <line x1="22" y1="33" x2="35" y2="33" stroke="#000" stroke-width="2"/><text x="10" y="36" font-size="9">→</text>
      <line x1="22" y1="57" x2="35" y2="57" stroke="#000" stroke-width="2"/><text x="10" y="60" font-size="9">←</text>
    </svg>'''
    return f'''<!doctype html><html><head><meta charset="utf-8"><title>Datasheet — {r["model"]}</title>
<style>
body{{font-family:Arial,sans-serif;font-size:11px;margin:12px;color:#000}}
.bar{{margin-bottom:8px;display:flex;gap:8px}}
.bar button{{padding:6px 14px;font-weight:bold;cursor:pointer;border:1px solid #333;background:#0b5ed7;color:#fff;border-radius:4px}}
table.ds{{width:100%;max-width:960px;border-collapse:collapse;border:2px solid #000}}
table.ds td,table.ds th{{border:1px solid #555;padding:4px 6px}}
.hdr{{font-size:15px;font-weight:bold;text-align:center;background:#e9ecef}}
.sec{{font-weight:bold;text-align:center;background:#dee2e6;letter-spacing:.5px}}
.r{{text-align:right;font-family:Consolas,monospace;font-size:11.5px}}.c{{text-align:center}}
@media print{{.bar{{display:none}}body{{margin:0}}}}
</style></head><body>
<div class="bar">
  <button onclick="setLang('en')">English (TEMA / HTRI)</button>
  <button onclick="setLang('ru')">Русский (Опросный лист ТУ)</button>
  <button onclick="window.print()" style="background:#198754">Print / Save PDF</button>
</div>
<table class="ds">
<tr><td colspan="7" class="hdr" data-en="HEAT EXCHANGER SPECIFICATION &amp; RATING SHEET" data-ru="РАСЧЕТНЫЙ ЛИСТ ТЕПЛООБМЕННОГО АППАРАТА">HEAT EXCHANGER SPECIFICATION &amp; RATING SHEET</td></tr>
<tr><td data-en="Service of Unit" data-ru="Назначение аппарата">Service of Unit</td><td colspan="3"><b>{p.get("service","Process Heat Exchanger")}</b></td><td data-en="Item No." data-ru="Позиция">Item No.</td><td colspan="2"><b>{p.get("item_no","E-101")}</b></td></tr>
<tr><td data-en="Model / Type" data-ru="Обозначение по ТУ">Model / Type</td><td colspan="2"><b>{r["model"]}</b></td><td data-en="Orientation" data-ru="Исполнение">Orientation</td><td class="c" data-en="{or_en}" data-ru="{or_ru}">{or_en}</td><td data-en="Shells / Unit" data-ru="Корпусов">Shells / Unit</td><td class="c">1</td></tr>
<tr><td data-en="Surf/Unit (Gross / Req)" data-ru="Поверхность (Кат / Расч)">Surf/Unit (Gross / Req)</td><td class="c" data-en="m²" data-ru="м²">m²</td><td colspan="2" class="r">{r["F_cat"]} / {r["F_req"]}</td><td data-en="Overdesign" data-ru="Запас поверхности">Overdesign</td><td colspan="2" class="r"><b>{r["margin"]} %</b></td></tr>
<tr><td colspan="7" class="sec" data-en="PERFORMANCE OF ONE UNIT" data-ru="РАБОЧИЕ ХАРАКТЕРИСТИКИ АППАРАТА">PERFORMANCE OF ONE UNIT</td></tr>
<tr><th colspan="2" data-en="Fluid Allocation" data-ru="Распределение потоков">Fluid Allocation</th><th colspan="2" data-en="Shell Side" data-ru="Межтрубное пространство">Shell Side</th><th colspan="3" data-en="Tube Side" data-ru="Трубное пространство">Tube Side</th></tr>
<tr><td colspan="2" data-en="Fluid Name" data-ru="Наименование среды">Fluid Name</td><td colspan="2" class="c"><b>{fl_s}</b></td><td colspan="3" class="c"><b>{fl_t}</b></td></tr>
<tr><td data-en="Fluid Quantity, Total" data-ru="Массовый расход">Fluid Quantity, Total</td><td class="c" data-en="kg/s" data-ru="кг/с">kg/s</td><td colspan="2" class="r">{ex["Gs"]}</td><td colspan="3" class="r">{ex["Gt"]}</td></tr>
<tr><td data-en="Liquid / Vapor" data-ru="Фазовое состояние">Liquid / Vapor</td><td class="c" data-en="wt%" data-ru="% масс.">wt%</td><td class="c">100 / 0</td><td class="c">100 / 0</td><td colspan="2" class="c">100 / 0</td><td class="c">100 / 0</td></tr>
<tr><td data-en="Temperature (In / Out)" data-ru="Температура (Вход / Выход)">Temperature (In / Out)</td><td class="c">°C</td><td class="r">{r["tsi"]:.2f}</td><td class="r">{r["tso"]:.2f}</td><td colspan="2" class="r">{r["tti"]:.2f}</td><td class="r">{r["tto"]:.2f}</td></tr>
<tr><td data-en="Density" data-ru="Плотность">Density</td><td class="c" data-en="kg/m³" data-ru="кг/м³">kg/m³</td><td colspan="2" class="r">{ex["rhos"]}</td><td colspan="3" class="r">{ex["rhot"]}</td></tr>
<tr><td data-en="Viscosity" data-ru="Динамическая вязкость">Viscosity</td><td class="c" data-en="mPa·s" data-ru="мПа·с">mPa·s</td><td colspan="2" class="r">{ex["mus"]*1000:.4f}</td><td colspan="3" class="r">{ex["mut"]*1000:.4f}</td></tr>
<tr><td data-en="Specific Heat" data-ru="Удельная теплоемкость">Specific Heat</td><td class="c" data-en="kJ/(kg·K)" data-ru="кДж/(кг·К)">kJ/(kg·K)</td><td colspan="2" class="r">{ex["cps"]/1000:.4f}</td><td colspan="3" class="r">{ex["cpt"]/1000:.4f}</td></tr>
<tr><td data-en="Thermal Conductivity" data-ru="Теплопроводность">Thermal Conductivity</td><td class="c" data-en="W/(m·K)" data-ru="Вт/(м·К)">W/(m·K)</td><td colspan="2" class="r">{ex["ks"]}</td><td colspan="3" class="r">{ex["kt"]}</td></tr>
<tr><td data-en="Operating Pressure" data-ru="Рабочее давление">Operating Pressure</td><td class="c" data-en="MPa" data-ru="МПа">MPa</td><td colspan="2" class="r">{pop_s}</td><td colspan="3" class="r">{pop_t}</td></tr>
<tr><td data-en="Velocity" data-ru="Скорость потока">Velocity</td><td class="c" data-en="m/s" data-ru="м/с">m/s</td><td colspan="2" class="r">{r["ws"]}</td><td colspan="3" class="r">{r["wt"]}</td></tr>
<tr><td data-en="Pressure Drop, Allow / Calc" data-ru="Перепад давления (Доп / Расч)">Pressure Drop, Allow / Calc</td><td class="c" data-en="kPa" data-ru="кПа">kPa</td><td class="r">{dp_al_s}</td><td class="r"><b>{r["dp_s"]}</b></td><td colspan="2" class="r">{dp_al_t}</td><td class="r"><b>{r["dp_t"]}</b></td></tr>
<tr><td data-en="Average Film Coefficient" data-ru="Коэффициент теплоотдачи α">Average Film Coefficient</td><td class="c" data-en="W/(m²·K)" data-ru="Вт/(м²·К)">W/(m²·K)</td><td colspan="2" class="r">{r["alpha_s"]}</td><td colspan="3" class="r">{r["alpha_t"]}</td></tr>
<tr><td data-en="Fouling Resistance" data-ru="Терм. сопротивление загрязн.">Fouling Resistance</td><td class="c" data-en="m²·K/W" data-ru="м²·К/Вт">m²·K/W</td><td colspan="2" class="r">{ex["rfs"]}</td><td colspan="3" class="r">{ex["rft"]}</td></tr>
<tr><td data-en="Heat Exchanged" data-ru="Тепловая нагрузка Q">Heat Exchanged</td><td class="c" data-en="kW" data-ru="кВт">kW</td><td class="r"><b>{bal["Q_kw"]}</b></td><td data-en="MTD (Corrected)" data-ru="Ср. разность Δt_ср">MTD (Corrected)</td><td class="r"><b>{r["lmtd_corr"]} °C</b></td><td data-en="Wall Δt / Allow" data-ru="Δt_ст / доп.">Wall Δt / Allow</td><td class="r">{r["dt_wall"]} °C</td></tr>
<tr><td data-en="Transfer Rate, Service" data-ru="Коэф. теплопередачи K">Transfer Rate, Service</td><td class="c" data-en="W/(m²·K)" data-ru="Вт/(м²·К)">W/(m²·K)</td><td class="r"><b>{r["K"]}</b></td><td data-en="Clean K" data-ru="Чистый K_чист">Clean K</td><td colspan="3" class="r">{ex["K_clean"]} <span data-en="W/(m²·K)" data-ru="Вт/(м²·К)">W/(m²·K)</span></td></tr>
<tr><td colspan="7" class="sec" data-en="CONSTRUCTION OF ONE SHELL" data-ru="КОНСТРУКТИВНЫЕ ДАННЫЕ АППАРАТА">CONSTRUCTION OF ONE SHELL</td></tr>
<tr><td data-en="Design Pressure" data-ru="Расчетное давление">Design Pressure</td><td class="c" data-en="MPa" data-ru="МПа">MPa</td><td colspan="2" class="r">{p["p_des_s"]}</td><td class="r">{p["p_des_t"]}</td><td colspan="2" rowspan="5" class="c">{svg_sketch}</td></tr>
<tr><td data-en="Test Pressure (GOST 34347)" data-ru="Пробное давление (ГОСТ 34347)">Test Pressure (GOST 34347)</td><td class="c" data-en="MPa" data-ru="МПа">MPa</td><td colspan="3" class="c"><b>{p_test}</b></td></tr>
<tr><td data-en="Design Temperature" data-ru="Расчетная температура">Design Temperature</td><td class="c">°C</td><td colspan="3" class="c">{p["t_des"]}</td></tr>
<tr><td data-en="No Passes per Shell" data-ru="Число ходов по трубам">No Passes per Shell</td><td class="c">-</td><td colspan="2" class="c">1</td><td class="c">{u["z"]}</td></tr>
<tr><td data-en="Flow Direction" data-ru="Схема движения">Flow Direction</td><td class="c">-</td><td colspan="3" class="c" data-en="{fl_dir_en}" data-ru="{fl_dir_ru}">{fl_dir_en}</td></tr>
<tr><td data-en="Connections Size (Dy)" data-ru="Условный проход штуцеров Dy">Connections Size (Dy)</td><td class="c" data-en="mm" data-ru="мм">mm</td><td colspan="2" class="c">Dy {ex["dys_eff"]}</td><td colspan="3" class="c">Dy {ex["dyt_eff"]}</td></tr>
<tr><td data-en="Tubes: Qty / OD×Thk / Length" data-ru="Трубы: Кол-во / d×s / L">Tubes: Qty / OD×Thk / Length</td><td colspan="6" class="c" data-en="{u['N']} pcs | {u['dt']} × {u['w']} mm | L = {u['L']} m" data-ru="{u['N']} шт. | {u['dt']} × {u['w']} мм | L = {u['L']} м">{u['N']} pcs | {u['dt']} × {u['w']} mm | L = {u['L']} m</td></tr>
<tr><td data-en="Shell ID / Baffles" data-ru="Диаметр кожуха / Перегородки">Shell ID / Baffles</td><td colspan="6" class="c" data-en="D = {u['D']} mm | {u['nb']} baffles | Climate: {p['climate']}" data-ru="D = {u['D']} мм | {u['nb']} перег. | Климат: {p['climate']}">D = {u['D']} mm | {u['nb']} baffles | Climate: {p['climate']}</td></tr>
<tr><td data-en="Materials (TU 3612-024)" data-ru="Материалы (ТУ 3612-024)">Materials (TU 3612-024)</td><td colspan="6" class="c" data-en="{p['mat']} — {mat_en}" data-ru="{p['mat']} — {mat_ru}">{p['mat']} — {mat_en}</td></tr>
<tr><td colspan="7"><b data-en="Notes / Normative Warnings:" data-ru="Примечания / Нормативные проверки:">Notes / Normative Warnings:</b> {r["warn"] or "OK (ТУ 3612-024-00220302-02 / ГОСТ 34347)"}</td></tr>
</table>
<script>
function setLang(l){{document.querySelectorAll("[data-"+l+"]").forEach(el=>el.textContent=el.getAttribute("data-"+l));}}
</script></body></html>'''

def render_calcsheet(p, bal, r, p_test):
    u, ex = r["geo"], r["extra"]
    st = ex["steps"]
    hot_tube = (p["hot_side"] == "tube")
    fl_t = p["fl1"] if hot_tube else p["fl2"]
    fl_s = p["fl2"] if hot_tube else p["fl1"]

    nu_t_eq = f"0.023 · {st['Ret']:.0f}⁰·⁸ · {st['Prt']:.2f}⁰·⁴" if st["Ret"] >= 2300 else f"1.61 · (Re·Pr·d/L)¹/³ (ламинарный режим)"
    nu_s_eq = f"0.24 · {st['Res']:.0f}⁰·⁶ · {st['Prs']:.2f}⁰·³⁶" if st["Res"] >= 1000 else f"0.34 · {st['Res']:.0f}⁰·⁵ · {st['Prs']:.2f}⁰·³⁶"

    return f'''<!doctype html><html><head><meta charset="utf-8"><title>Расчет по шагам — {r["model"]}</title>
<style>
body{{font-family:Arial,sans-serif;font-size:12px;margin:16px;color:#111;max-width:880px}}
h2{{margin:0 0 6px;border-bottom:2px solid #000;padding-bottom:4px}}
h3{{background:#e9ecef;padding:5px 8px;margin:12px 0 6px;border-left:4px solid #0b5ed7}}
table{{width:100%;border-collapse:collapse;margin-bottom:8px}}
td,th{{border:1px solid #bbb;padding:4px 7px;text-align:left}}
td.v{{font-family:Consolas,monospace;font-weight:bold;text-align:right;width:140px}}
td.f{{color:#444;font-size:11.5px}}
@media print{{button{{display:none}}}}
</style></head><body>
<button onclick="window.print()" style="padding:7px 14px;background:#198754;color:#fff;border:none;border-radius:4px;font-weight:bold;cursor:pointer;margin-bottom:10px">Печать / Сохранить в PDF</button>
<h2>ПРОВЕРОЧНЫЙ ТЕПЛОВОЙ И ГИДРАВЛИЧЕСКИЙ РАСЧЕТ (по Дытнерскому Ю.И.)</h2>
<p><b>Аппарат по ТУ 3612-024-00220302-02:</b> {r["model"]} | <b>Позиция:</b> {p.get("item_no","E-101")}<br>
<b>Геометрия:</b> D = {u["D"]} мм; трубы {u["dt"]}×{u["w"]} мм (d_вн = {st["din"]*1000:.1f} мм), L = {u["L"]} м, N = {u["N"]} шт., z = {u["z"]}, перегородок = {u["nb"]}, рядов n = {st["mr"]}, F_кат = {u["F"]} м²</p>

<h3>1. Тепловой баланс и средняя разность температур</h3>
<table>
<tr><th>Величина</th><th>Формула / Подстановка</th><th>Значение</th></tr>
<tr><td>Тепловая нагрузка Q</td><td class="f">Q = G₁·c₁·|t₁' - t₁''| = {bal["G1"]}·{p["cp1"]}·|{bal["t1_in"]} - {bal["t1_out"]}|</td><td class="v">{bal["Q_kw"]} кВт</td></tr>
<tr><td>Большая / малая разность Δt_б / Δt_м</td><td class="f">Разности температур на концах аппарата</td><td class="v">{st["dtb"]:.2f} / {st["dtm"]:.2f} °C</td></tr>
<tr><td>Среднелогарифмическая Δt_л</td><td class="f">Δt_л = (Δt_б - Δt_м) / ln(Δt_б / Δt_м)</td><td class="v">{st["lmtd"]:.2f} °C</td></tr>
<tr><td>Параметры P, R и поправка ε_Δt</td><td class="f">P = {st["P"]:.3f}, R = {st["R"]:.3f} (для z = {u["z"]})</td><td class="v">ε_Δt = {st["ft"]:.3f}</td></tr>
<tr><td>Расчетная разность температур Δt_ср</td><td class="f">Δt_ср = Δt_л · ε_Δt = {st["lmtd"]:.2f} · {st["ft"]:.3f}</td><td class="v">{r["lmtd_corr"]} °C</td></tr>
</table>
<h3>2. Трубное пространство — {fl_t} (t_ср = {0.5*(r["tti"]+r["tto"]):.1f} °C)</h3>
<table>
<tr><th>Величина</th><th>Формула / Подстановка</th><th>Значение</th></tr>
<tr><td>Свойства среды (ρ / c_p / μ / λ)</td><td class="f">При рабочих T и P</td><td class="v">{ex["rhot"]} / {ex["cpt"]} / {ex["mut"]} / {ex["kt"]}</td></tr>
<tr><td>Скорость в трубах w_тр</td><td class="f">w_тр = G_тр / (ρ_тр · A_тр) = {ex["Gt"]} / ({ex["rhot"]} · {u["At"]})</td><td class="v">{r["wt"]} м/с</td></tr>
<tr><td>Критерии Re_тр и Pr_тр</td><td class="f">Re = ρ·w·d_вн/μ; Pr = c_p·μ/λ</td><td class="v">{st["Ret"]:.0f} / {st["Prt"]:.2f}</td></tr>
<tr><td>Критерий Нуссельта Nu_тр</td><td class="f">Nu₀ = {nu_t_eq} (поправка вязк. φ_тр = {st["phi_t"]:.3f})</td><td class="v">{st["Nut0"]*st["phi_t"]:.1f}</td></tr>
<tr><td>Коэффициент теплоотдачи α_тр</td><td class="f">α_тр = Nu_тр · λ_тр / d_вн</td><td class="v">{r["alpha_t"]:.0f} Вт/(м²·К)</td></tr>
<tr><td>Потери давления ΔP_тр (трение / местн. / штуц.)</td><td class="f">λ_тр = {st["lf"]:.4f}; w_шт = {st["wtn"]:.2f} м/с (Dy {ex["dyt_eff"]})</td><td class="v">{st["dpt_tr"]/1000:.2f} / {st["dpt_loc"]/1000:.2f} / {st["dpt_noz"]/1000:.2f} кПа</td></tr>
<tr><td>Суммарное сопротивление ΔP_тр</td><td class="f">ΔP_тр = ΔP_тр.лин + ΔP_местн + ΔP_шт</td><td class="v">{r["dp_t"]} кПа</td></tr>
</table>

<h3>3. Межтрубное пространство — {fl_s} (t_ср = {0.5*(r["tsi"]+r["tso"]):.1f} °C)</h3>
<table>
<tr><th>Величина</th><th>Формула / Подстановка</th><th>Значение</th></tr>
<tr><td>Свойства среды (ρ / c_p / μ / λ)</td><td class="f">При рабочих T и P</td><td class="v">{ex["rhos"]} / {ex["cps"]} / {ex["mus"]} / {ex["ks"]}</td></tr>
<tr><td>Скорость в межтрубном w_мтр</td><td class="f">w_мтр = G_мтр / (ρ_мтр · A_мтр) = {ex["Gs"]} / ({ex["rhos"]} · {u["Ac"]})</td><td class="v">{r["ws"]} м/с</td></tr>
<tr><td>Критерии Re_мтр и Pr_мтр</td><td class="f">Re = ρ·w·d_нар/μ; Pr = c_p·μ/λ</td><td class="v">{st["Res"]:.0f} / {st["Prs"]:.2f}</td></tr>
<tr><td>Критерий Нуссельта Nu_мтр</td><td class="f">Nu₀ = {nu_s_eq} (поправка вязк. φ_мтр = {st["phi_s"]:.3f})</td><td class="v">{st["Nus0"]*st["phi_s"]:.1f}</td></tr>
<tr><td>Коэффициент теплоотдачи α_мтр</td><td class="f">α_мтр = Nu_мтр · λ_мтр / d_нар</td><td class="v">{r["alpha_s"]:.0f} Вт/(м²·К)</td></tr>
<tr><td>Потери давления ΔP_мтр (пучок / перег. / штуц.)</td><td class="f">Рядов n = {st["mr"]}, перег. = {u["nb"]}; w_шт = {st["wsn"]:.2f} м/с (Dy {ex["dys_eff"]})</td><td class="v">{st["dps_bun"]/1000:.2f} / {st["dps_baf"]/1000:.2f} / {st["dps_noz"]/1000:.2f} кПа</td></tr>
<tr><td>Суммарное сопротивление ΔP_мтр</td><td class="f">ΔP_мтр = ΔP_пуч + ΔP_перег + ΔP_шт</td><td class="v">{r["dp_s"]} кПа</td></tr>
</table>

<h3>4. Теплопередача, площадь поверхности и прочностные проверки</h3>
<table>
<tr><th>Величина</th><th>Формула / Подстановка</th><th>Значение</th></tr>
<tr><td>Термические сопротивления (мтр / стенка / загр / тр)</td><td class="f">λ_ст = {st["k_wall"]} Вт/(м·К), s = {u["w"]} мм</td><td class="v">{st["rs_th"]:.5f} / {st["rm_th"]:.5f} / {st["rf_th"]:.5f} / {st["rt_th"]:.5f}</td></tr>
<tr><td>Коэффициент теплопередачи K</td><td class="f">K = 1 / ΣR = 1 / {st["R_tot"]:.5f}</td><td class="v">{r["K"]} Вт/(м²·К)</td></tr>
<tr><td>Расчетная поверхность F_расч</td><td class="f">F_расч = Q / (K · Δt_ср) = {bal["Q_kw"]*1000:.0f} / ({r["K"]} · {r["lmtd_corr"]})</td><td class="v">{r["F_req"]} м²</td></tr>
<tr><td>Запас поверхности (сравнение с F_кат = {u["F"]} м²)</td><td class="f">(F_кат - F_расч) / F_расч · 100%</td><td class="v">{r["margin"]} %</td></tr>
<tr><td>Разность температур стенки Δt_ст / доп. (Табл. 11)</td><td class="f">Проверка необходимости компенсатора (ТК/ХК)</td><td class="v">{r["dt_wall"]} °C</td></tr>
<tr><td>Пробное гидравлическое давление P_исп (ГОСТ 34347)</td><td class="f">P_исп = 1.25 · P_расч · ([σ]₂₀/[σ]_t)</td><td class="v">{p_test} МПа</td></tr>
</table>
</body></html>'''

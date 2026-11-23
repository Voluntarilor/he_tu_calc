MATERIALS = {
    "М1": ("Ст3сп / Сталь 20", 47.0, 1.00),
    "М3": ("09Г2С (хладостойкая)", 45.0, 1.00),
    "М6": ("12Х18Н10Т / Ст3", 17.5, 1.12),
    "М8": ("12Х18Н10Т (нерж.)", 17.5, 1.14),
    "М10": ("10Х17Н13М2Т", 16.5, 1.14),
    "М11": ("Латунь Л68 / Ст3", 105.0, 1.05),
    "М19": ("Титан ВТ1-0", 21.0, 1.15),
}

# ТУ 3612-024-00220302-02 Table 11: max allowable |t_shell - t_tube| (°C) for ТН/ХН
# Key: (material_group, temp_band) -> {D: {Py: dt_max}}
TABLE_11 = {
    ("CS", "low"): {
        159:{1.6:50,2.5:45,4.0:35}, 273:{1.6:50,2.5:45,4.0:35}, 325:{1.6:50,2.5:40,4.0:30},
        400:{1.6:45,2.5:35,4.0:25}, 426:{1.6:45,2.5:35,4.0:25}, 600:{1.6:40,2.5:35,4.0:25},
        630:{1.6:40,2.5:35,4.0:25}, 800:{1.0:55,1.6:40,2.5:30,4.0:20},
        1000:{0.6:60,1.0:55,1.6:35,2.5:30,4.0:20}, 1200:{0.6:60,1.0:50,1.6:35,2.5:25}
    },
    ("SS", "low"): {
        159:{1.6:40,2.5:35,4.0:25}, 273:{1.6:40,2.5:35,4.0:25}, 325:{1.6:40,2.5:30,4.0:25},
        400:{1.6:35,2.5:30,4.0:20}, 426:{1.6:35,2.5:30,4.0:20}, 600:{1.6:35,2.5:25,4.0:20},
        630:{1.6:35,2.5:25,4.0:20}, 800:{1.0:45,1.6:30,2.5:25,4.0:None},
        1000:{0.6:50,1.0:45,1.6:30,2.5:20,4.0:None}, 1200:{0.6:50,1.0:40,1.6:25,2.5:20}
    }
}

def test_pressure_gost34347(p_des_mpa, t_des_c, mat_code):
    _, _, s_ratio_base = MATERIALS.get(mat_code, ("Сталь", 45.0, 1.0))
    t_factor = 1.0 if t_des_c <= 50 else min(1.25, s_ratio_base + max(0.0, (t_des_c - 100.0) * 0.0007))
    return round(1.25 * p_des_mpa * t_factor, 2)

def check_table11(D, Py, mat_code, t_tube_wall, t_shell_wall):
    grp = "CS" if mat_code in ("М1", "М3") else "SS"
    dt_allow = TABLE_11[(grp, "low")].get(D, {}).get(Py, 25)
    dt_actual = abs(t_shell_wall - t_tube_wall)
    if dt_allow is None:
        return False, None, round(dt_actual, 1)
    return (dt_actual <= dt_allow), dt_allow, round(dt_actual, 1)

def format_tu_name(D, utype, orient, Py, mat_code, dt, L, z, climate, t_shell_max):
    py_str = str(Py).replace(".", ",")
    L_str = str(int(L)) if float(L).is_integer() else str(L).replace(".", ",")
    ins = "-И" if (t_shell_max > 50.0 or t_shell_max < 5.0) else ""
    return f"{D} {utype}{orient}-{py_str}-{mat_code}/{dt}Г-{L_str}-{z}-{climate}{ins}"

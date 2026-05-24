import math

MU = 0.15

def modulus_of_elasticity(fc: float) -> float:
    return 4700 * math.sqrt(fc)

def modulus_of_rupture(fc: float) -> float:
    return 0.62 * math.sqrt(fc)

def radius_of_stiffness(Ec: float, t: float, k: float) -> float:
    D = Ec * t**3 / (12 * (1 - MU**2))
    return (D / k) ** 0.25

def equivalent_radius(b: float) -> float:
    return math.sqrt(b / math.pi)

def flexural_stress_interior(P: float, Lr: float, t: float, b: float) -> float:
    a = equivalent_radius(b)
    return 0.316 * P / t**2 * (4 * math.log10(Lr / a) + 1.069)

def flexural_stress_edge(P: float, Lr: float, t: float, b: float) -> float:
    a = equivalent_radius(b)
    return 0.529 * P / t**2 * (4 * math.log10(Lr / a) + 0.359)

def flexural_stress_corner(P: float, Lr: float, t: float, b: float) -> float:
    a = equivalent_radius(b)
    return 3 * P / t**2 * (1 - (a * math.sqrt(2) / Lr) ** 0.6)

def bearing_stress(P: float, Ac: float) -> float:
    return P / Ac

def punching_shear(V: float, b: float, d: float) -> float:
    return V / (2 * (b + d) * d)

def min_slab_thickness_interior(P: float, k: float, fr: float, b: float) -> float:
    lo = 1.0
    for _ in range(50):
        t = lo
        Ec = modulus_of_elasticity(30)
        Lr = radius_of_stiffness(Ec, t, k)
        si = flexural_stress_interior(P, Lr, t, b)
        tn = math.sqrt(0.316 * P / fr * (4 * math.log10(Lr / equivalent_radius(b)) + 1.069))
        if abs(tn - t) < 0.5:
            return tn
        lo = tn
    return lo

def min_slab_thickness_corner(P: float, k: float, fr: float, b: float) -> float:
    lo = 1.0
    for _ in range(50):
        t = lo
        Ec = modulus_of_elasticity(30)
        Lr = radius_of_stiffness(Ec, t, k)
        a = equivalent_radius(b)
        tn = math.sqrt(3 * P / fr * (1 - (a * math.sqrt(2) / Lr) ** 0.6))
        if abs(tn - t) < 0.5:
            return tn
        lo = tn
    return lo

def crack_width(stress: float, fr: float, t: float) -> float:
    if stress <= fr:
        return 0.0
    ratio = stress / fr
    return 0.01 * (ratio - 1) * t * 0.001

def calculate_full(P_kN: float, t_mm: float, fc_MPa: float,
                   k_kPa_mm: float, b_mm: float, Ac_mm2: float) -> dict:
    P = P_kN * 1000
    t = t_mm
    fc = fc_MPa
    k = k_kPa_mm * 0.001
    b = b_mm
    Ac = Ac_mm2

    Ec = modulus_of_elasticity(fc)
    fr = modulus_of_rupture(fc)
    Lr = radius_of_stiffness(Ec, t, k)

    si = flexural_stress_interior(P, Lr, t, b)
    se = flexural_stress_edge(P, Lr, t, b)
    sc = flexural_stress_corner(P, Lr, t, b)
    sb = bearing_stress(P, Ac)
    v = punching_shear(P, b, t)

    t_min_int = min_slab_thickness_interior(P, k, fr, b)
    t_min_cor = min_slab_thickness_corner(P, k, fr, b)

    cw_int = crack_width(si, fr, t)
    cw_edge = crack_width(se, fr, t)
    cw_cor = crack_width(sc, fr, t)

    return {
        "inputs": {
            "load_kN": P_kN,
            "thickness_mm": t_mm,
            "concrete_strength_MPa": fc_MPa,
            "subgrade_modulus_kPa_mm": k_kPa_mm,
            "contact_width_mm": b_mm,
            "contact_area_mm2": Ac_mm2
        },
        "material_properties": {
            "modulus_of_elasticity_MPa": round(Ec, 1),
            "modulus_of_rupture_MPa": round(fr, 3)
        },
        "slab_properties": {
            "radius_of_stiffness_mm": round(Lr, 1),
            "min_thickness_interior_mm": round(t_min_int, 1),
            "min_thickness_corner_mm": round(t_min_cor, 1)
        },
        "stresses": {
            "interior_flexural_MPa": round(si, 3),
            "edge_flexural_MPa": round(se, 3),
            "corner_flexural_MPa": round(sc, 3),
            "bearing_MPa": round(sb, 3),
            "punching_shear_MPa": round(v, 3)
        },
        "crack_widths_mm": {
            "interior": round(cw_int, 4),
            "edge": round(cw_edge, 4),
            "corner": round(cw_cor, 4)
        },
        "status": {
            "interior_ok": si <= fr,
            "edge_ok": se <= fr,
            "corner_ok": sc <= fr,
            "bearing_ok": sb <= fc * 0.45,
            "punching_ok": v <= 0.17 * math.sqrt(fc)
        }
    }

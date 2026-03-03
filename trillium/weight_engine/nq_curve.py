"""
Trillium V2 — Curva Nq–b2/D2 e Calcolo Spessori
Fonte: Curva nq-D2-b2.xlsx (Standards), SOP-569, SOP-546
Aggiornamento: 26 febbraio 2026

Calcola:
 - b2 (larghezza uscita girante) dato Nq e D2
 - Spessore corpo pompa (SOP-569 semplificato)
 - Spessore disco girante (SOP-546 semplificato)
"""

import math

# ============================================================
# CURVA Nq → b2/D2  (da Curva nq-D2-b2.xlsx, Dashed Curve)
# ============================================================
# Coppia (nq, b2/D2) — 26 punti empirici
# Interpolazione lineare tra i punti.

NQ_B2D2_CURVE = [
    (10, 0.037),
    (12, 0.044),
    (15, 0.053),
    (18, 0.062),
    (20, 0.068),
    (25, 0.080),
    (30, 0.091),
    (35, 0.102),
    (40, 0.112),
    (50, 0.130),
    (60, 0.149),
    (70, 0.165),
    (80, 0.180),
    (90, 0.194),
    (100, 0.206),
    (120, 0.228),
    (140, 0.247),
    (160, 0.264),
    (180, 0.279),
    (200, 0.293),
    (250, 0.324),
    (300, 0.350),
    (350, 0.374),
    (400, 0.395),
    (450, 0.414),
    (500, 0.432),
]


def get_b2_d2_ratio(nq: float) -> float:
    """
    Dato il numero specifico di giri (Nq), restituisce il rapporto b2/D2
    interpolando linearmente dalla curva empirica.

    Esempio: Nq=30 → b2/D2 = 0.091
             Nq=45 → b2/D2 ≈ 0.121 (interpolato tra 40 e 50)

    Args:
        nq: Numero specifico di giri [giri/min]

    Returns:
        Rapporto b2/D2 (adimensionale)
    """
    if nq <= NQ_B2D2_CURVE[0][0]:
        return NQ_B2D2_CURVE[0][1]
    if nq >= NQ_B2D2_CURVE[-1][0]:
        return NQ_B2D2_CURVE[-1][1]

    for i in range(len(NQ_B2D2_CURVE) - 1):
        nq_lo, ratio_lo = NQ_B2D2_CURVE[i]
        nq_hi, ratio_hi = NQ_B2D2_CURVE[i + 1]
        if nq_lo <= nq <= nq_hi:
            t = (nq - nq_lo) / (nq_hi - nq_lo)
            return ratio_lo + t * (ratio_hi - ratio_lo)

    return NQ_B2D2_CURVE[-1][1]


def calc_b2(nq: float, d2_mm: float) -> float:
    """
    Calcola b2 (larghezza uscita girante) in mm.

    b2 = D2 × (b2/D2 ratio dalla curva Nq)

    Esempio: Nq=30, D2=350mm → b2/D2=0.091 → b2 = 350 × 0.091 = 31.85 mm

    Args:
        nq: Numero specifico di giri
        d2_mm: Diametro esterno girante in mm

    Returns:
        b2 in mm
    """
    ratio = get_b2_d2_ratio(nq)
    return round(d2_mm * ratio, 1)


# ============================================================
# SPESSORE CORPO POMPA — SOP-569 (semplificato)
# ============================================================
# Formula: t = (P × D_i) / (2 × S × E - 1.2 × P) + sovrametallo
# dove:
#   P = MAWP (pressione max ammissibile, bar → MPa)
#   D_i = diametro interno corpo (mm)
#   S = tensione ammissibile materiale (MPa)
#   E = efficienza giunto saldato (0.85 per casting)
#   sovrametallo = 3.0 mm (tipico per fonderia)
#
# Spessore minimo fondibile:
#   < 200mm diametro:  6 mm
#   200-400mm:         8 mm
#   400-800mm:        10 mm
#   > 800mm:          12 mm

MIN_CASTABLE_THICKNESS = [
    (200, 6.0),
    (400, 8.0),
    (800, 10.0),
    (9999, 12.0),
]


def calc_casing_thickness(
    mawp_bar: float,
    d_internal_mm: float,
    yield_strength_mpa: float,
    joint_efficiency: float = 0.85,
    corrosion_allowance_mm: float = 3.0,
) -> dict:
    """
    Calcola lo spessore corpo pompa secondo SOP-569 (semplificato).

    Args:
        mawp_bar: MAWP in bar
        d_internal_mm: Diametro interno corpo in mm
        yield_strength_mpa: Tensione di snervamento materiale (MPa)
        joint_efficiency: Efficienza giunto (default 0.85 per casting)
        corrosion_allowance_mm: Sovrametallo corrosione (default 3.0 mm)

    Returns:
        dict con t_calc (mm), t_min_castable (mm), t_final (mm)

    Esempio:
        MAWP=40 bar, D_i=300mm, Yield=250 MPa
        → t_calc = 3.5mm + 3.0mm sovrametallo = 6.5mm
        → t_min_fondibile = 8.0mm (per D_i 200-400)
        → t_final = 8.0mm
    """
    p_mpa = mawp_bar * 0.1  # bar → MPa
    s = yield_strength_mpa / 1.5  # fattore sicurezza 1.5

    denominator = 2 * s * joint_efficiency - 1.2 * p_mpa
    if denominator <= 0:
        t_calc = 999.0  # pressione troppo alta per il materiale
    else:
        t_calc = (p_mpa * d_internal_mm) / (2 * denominator)

    t_with_corrosion = t_calc + corrosion_allowance_mm

    # Spessore minimo fondibile
    t_min_cast = 6.0
    for d_limit, t_min in MIN_CASTABLE_THICKNESS:
        if d_internal_mm <= d_limit:
            t_min_cast = t_min
            break

    t_final = max(t_with_corrosion, t_min_cast)

    return {
        "t_calc_mm": round(t_calc, 1),
        "t_with_corrosion_mm": round(t_with_corrosion, 1),
        "t_min_castable_mm": t_min_cast,
        "t_final_mm": round(t_final, 1),
        "controlling": "pressure" if t_with_corrosion >= t_min_cast else "castability",
    }


# ============================================================
# SPESSORE DISCO GIRANTE — SOP-546 (semplificato)
# ============================================================
# Formula semplificata: t_disc = k × D2 × √(P / S)
# dove:
#   k = coefficiente empirico (0.02 per disco posteriore, 0.015 per anteriore)
#   D2 = diametro esterno girante (mm)
#   P = MAWP (MPa)
#   S = tensione ammissibile (MPa)
#
# Spessori minimi:
#   D2 < 200:  4 mm
#   D2 200-400: 5 mm
#   D2 > 400:  6 mm

MIN_IMPELLER_THICKNESS = [
    (200, 4.0),
    (400, 5.0),
    (9999, 6.0),
]


def calc_impeller_disc_thickness(
    mawp_bar: float,
    d2_mm: float,
    yield_strength_mpa: float,
) -> dict:
    """
    Calcola lo spessore disco girante secondo SOP-546 (semplificato).

    Args:
        mawp_bar: MAWP in bar
        d2_mm: Diametro esterno girante in mm
        yield_strength_mpa: Tensione di snervamento materiale (MPa)

    Returns:
        dict con t_rear (mm), t_front (mm), t_min (mm)

    Esempio:
        MAWP=40 bar, D2=350mm, Yield=450 MPa
        → t_rear = 0.02 × 350 × √(4.0/300) = 0.81mm
        → t_min = 5.0mm (per D2 200-400)
        → t_final_rear = 5.0mm
    """
    p_mpa = mawp_bar * 0.1
    s = yield_strength_mpa / 1.5

    if s <= 0:
        return {"t_rear_mm": 6.0, "t_front_mm": 6.0, "t_min_mm": 6.0}

    factor = math.sqrt(p_mpa / s) if p_mpa > 0 else 0

    t_rear = 0.020 * d2_mm * factor
    t_front = 0.015 * d2_mm * factor

    t_min = 4.0
    for d_limit, t_val in MIN_IMPELLER_THICKNESS:
        if d2_mm <= d_limit:
            t_min = t_val
            break

    return {
        "t_rear_mm": round(max(t_rear, t_min), 1),
        "t_front_mm": round(max(t_front, t_min), 1),
        "t_min_mm": t_min,
        "controlling_rear": "pressure" if t_rear >= t_min else "minimum",
        "controlling_front": "pressure" if t_front >= t_min else "minimum",
    }


# ============================================================
# FORMULE DI SCALING (da Flusso stima pesi.docx)
# ============================================================

def scaling_impeller(
    weight_ref_kg: float,
    d2_new: float, d2_ref: float,
    rho_new: float, rho_ref: float,
    t_new: float = 1.0, t_ref: float = 1.0,
) -> float:
    """
    Scaling peso girante: W_new = W_ref × (D2_new/D2_ref)² × (ρ_new/ρ_ref) × (t_new/t_ref)

    Esponente 2 perché la girante è un disco: volume ∝ D²×t
    """
    return weight_ref_kg * (d2_new / d2_ref) ** 2 * (rho_new / rho_ref) * (t_new / t_ref)


def scaling_casing(
    weight_ref_kg: float,
    d2_new: float, d2_ref: float,
    rho_new: float, rho_ref: float,
    t_new: float = 1.0, t_ref: float = 1.0,
) -> float:
    """
    Scaling peso corpo: W_new = W_ref × (D2_new/D2_ref)² × (ρ_new/ρ_ref) × (t_new/t_ref)

    Esponente 2 perché il corpo è approssimato come shell cilindrica
    Lo spessore influenza linearmente (se cambia pressione/materiale)
    """
    return weight_ref_kg * (d2_new / d2_ref) ** 2 * (rho_new / rho_ref) * (t_new / t_ref)


def scaling_cover(
    weight_ref_kg: float,
    d2_new: float, d2_ref: float,
    rho_new: float, rho_ref: float,
) -> float:
    """
    Scaling peso coperchio: W_new = W_ref × (D2_new/D2_ref)³ × (ρ_new/ρ_ref)

    Esponente 3 perché il coperchio scala come un solido tridimensionale
    """
    return weight_ref_kg * (d2_new / d2_ref) ** 3 * (rho_new / rho_ref)


def scaling_shaft(
    length_mm: float,
    diameter_mm: float,
    rho_kg_m3: float,
) -> float:
    """
    Peso barra grezza albero: W = π/4 × D² × L × ρ

    Esempio: L=600mm, D=70mm, ρ=7850 → W = 18.1 kg
    """
    d_m = diameter_mm / 1000.0
    l_m = length_mm / 1000.0
    return math.pi / 4.0 * d_m ** 2 * l_m * rho_kg_m3


# ============================================================
# SELEZIONE NOZZLE (da Mod.463 — Flange Nozzle Selection)
# ============================================================
# Formula: V = Q / (π/4 × D²)
# Limiti velocità (API 610):
#   Aspirazione: ≤ 4.6 m/s
#   Mandata:     ≤ 7.6 m/s

STANDARD_NOZZLE_SIZES_MM = [
    25, 50, 75, 100, 125, 150, 200, 250, 300, 350, 400, 450, 500, 600,
    700, 800, 900, 1000,
]

NOZZLE_MM_TO_INCH = {
    25: 1, 50: 2, 75: 3, 100: 4, 125: 5, 150: 6, 200: 8, 250: 10,
    300: 12, 350: 14, 400: 16, 450: 18, 500: 20, 600: 24,
    700: 28, 800: 32, 900: 36, 1000: 40,
}


def calc_nozzle_velocity(q_m3h: float, d_mm: float) -> float:
    """Velocità fluido nel nozzle (m/s). V = Q / (π/4 × D²)"""
    if d_mm <= 0 or q_m3h <= 0:
        return 0.0
    d_m = d_mm / 1000.0
    q_m3s = q_m3h / 3600.0
    return q_m3s / (math.pi / 4.0 * d_m ** 2)


def select_nozzle_size(
    q_m3h: float,
    v_max_suction: float = 4.6,
    v_max_discharge: float = 7.6,
) -> dict:
    """
    Seleziona DN ottimale aspirazione/mandata dalla portata (Mod.463).

    Esempio: Q=500 m³/h → Aspiraz. DN=200mm (8"), Mandata DN=150mm (6")

    Args:
        q_m3h: Portata volumetrica (m³/h)
        v_max_suction: Vel. max aspirazione (m/s), default 4.6
        v_max_discharge: Vel. max mandata (m/s), default 7.6

    Returns:
        dict con suction/discharge DN (mm, inch), velocità
    """
    suction_mm = STANDARD_NOZZLE_SIZES_MM[-1]
    discharge_mm = STANDARD_NOZZLE_SIZES_MM[-1]
    v_suction = v_discharge = 0.0

    for dn in STANDARD_NOZZLE_SIZES_MM:
        v = calc_nozzle_velocity(q_m3h, dn)
        if v <= v_max_suction:
            suction_mm = dn
            v_suction = v
            break

    for dn in STANDARD_NOZZLE_SIZES_MM:
        v = calc_nozzle_velocity(q_m3h, dn)
        if v <= v_max_discharge:
            discharge_mm = dn
            v_discharge = v
            break

    return {
        "suction_mm": suction_mm,
        "suction_inch": NOZZLE_MM_TO_INCH.get(suction_mm, suction_mm // 25),
        "suction_velocity": round(v_suction, 1),
        "discharge_mm": discharge_mm,
        "discharge_inch": NOZZLE_MM_TO_INCH.get(discharge_mm, discharge_mm // 25),
        "discharge_velocity": round(v_discharge, 1),
    }


# ============================================================
# DIMENSIONAMENTO ALBERO (da Mod.496 — API 610 / Duncan-Hood)
# ============================================================
# d_min = k × (P / n)^(1/3)
#   k ≈ 85 (OH), 72 (BB), 78 (VS)
#   P = potenza assorbita (kW)
#   n = velocità (rpm)

SHAFT_K_FACTOR = {
    "OH": 85, "OH1": 85, "OH2": 85, "OH3": 85, "OH4": 85, "OH5": 85,
    "BB": 72, "BB1": 72, "BB2": 72, "BB3": 72, "BB4": 72, "BB5": 72,
    "VS": 78, "VS1": 78, "VS4": 78, "VS6": 78, "VS7": 78,
}


def calc_shaft_diameter(
    power_kw: float = None,
    speed_rpm: float = 3000,
    pump_family: str = "BB1",
    q_m3h: float = None,
    head_m: float = None,
    density_kg_m3: float = 1000,
    efficiency: float = 0.80,
) -> dict:
    """
    Diametro minimo albero (API 610 / Mod.496).

    Esempio: Q=500 m³/h, H=80m, n=1450 rpm, BB1
        → P≈136 kW, d_min=33mm, d_standard=35mm

    Args:
        power_kw: Potenza assorbita (kW). Se None, calcolata da Q×H
        speed_rpm: Velocità rotazione (rpm)
        pump_family: Famiglia pompa
        q_m3h, head_m: Portata e prevalenza (se power_kw=None)
        density_kg_m3: Densità fluido (default 1000 kg/m³)
        efficiency: Rendimento pompa (default 0.80)

    Returns:
        dict con d_min_mm, d_standard_mm, power_kw, torque_nm
    """
    if power_kw is None:
        if q_m3h and head_m and density_kg_m3 > 0:
            power_kw = density_kg_m3 * 9.81 * (q_m3h / 3600.0) * head_m / (efficiency * 1000)
        else:
            return {"d_min_mm": 0, "d_standard_mm": 0, "power_kw": 0, "torque_nm": 0}

    if power_kw <= 0 or speed_rpm <= 0:
        return {"d_min_mm": 0, "d_standard_mm": 0, "power_kw": 0, "torque_nm": 0}

    torque_nm = power_kw * 1000 * 60 / (2 * math.pi * speed_rpm)

    family_upper = pump_family.upper()
    k = SHAFT_K_FACTOR.get(family_upper, 78)
    d_min = k * (power_kw / speed_rpm) ** (1.0 / 3.0)

    # Arrotonda a diametri standard ISO
    standard_d = [
        20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95,
        100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200,
    ]
    d_std = standard_d[-1]
    for d in standard_d:
        if d >= d_min:
            d_std = d
            break

    return {
        "d_min_mm": round(d_min, 1),
        "d_standard_mm": d_std,
        "power_kw": round(power_kw, 1),
        "torque_nm": round(torque_nm, 1),
        "k_factor": k,
        "family": family_upper,
    }


# ============================================================
# PART CODES STANDARD (da Standard Part List OH2.xls)
# ============================================================

STANDARD_PART_CODES = {
    "102": {"name_it": "Corpo con voluta", "name_en": "Casing with volute", "group": "casing"},
    "161": {"name_it": "Coperchio corpo", "name_en": "Casing cover", "group": "cover"},
    "230": {"name_it": "Girante", "name_en": "Impeller", "group": "impeller"},
    "210": {"name_it": "Albero", "name_en": "Shaft", "group": "shaft"},
    "330": {"name_it": "Supporto", "name_en": "Bearing bracket", "group": "support"},
    "360.1": {"name_it": "Coperchio supp. int.", "name_en": "Inner bearing cover", "group": "cover"},
    "360.2": {"name_it": "Coperchio supp. est.", "name_en": "Outer bearing cover", "group": "cover"},
    "452": {"name_it": "Premitreccia", "name_en": "Gland", "group": "seal"},
    "461": {"name_it": "Anello baderna", "name_en": "Packing ring", "group": "seal"},
    "542": {"name_it": "Boccola di tenuta", "name_en": "Throttle bushing", "group": "seal"},
    "525": {"name_it": "Boccola di fondo", "name_en": "Bottom bushing", "group": "seal"},
    "502": {"name_it": "Anello usura fisso", "name_en": "Stationary wear ring", "group": "wear_ring"},
    "503": {"name_it": "Anello usura rotante", "name_en": "Rotating wear ring", "group": "wear_ring"},
    "320": {"name_it": "Cuscinetto", "name_en": "Bearing", "group": "bearing"},
    "524": {"name_it": "Camicia prot. albero", "name_en": "Shaft sleeve", "group": "shaft"},
    "681": {"name_it": "Protezione giunto", "name_en": "Coupling guard", "group": "accessory"},
    "890": {"name_it": "Piastra di base", "name_en": "Baseplate", "group": "baseplate"},
    "918": {"name_it": "Bulloni fondazione", "name_en": "Foundation bolts", "group": "bolting"},
    "900": {"name_it": "Viteria corpo", "name_en": "Casing bolting", "group": "bolting"},
    "900.10": {"name_it": "Viteria coperchi", "name_en": "Cover bolting", "group": "bolting"},
}


def get_part_code(component_name: str) -> str | None:
    """Dato il nome componente, restituisce il codice parte standard."""
    name_lower = component_name.lower()
    for code, info in STANDARD_PART_CODES.items():
        if (info["name_it"].lower() in name_lower
                or name_lower in info["name_it"].lower()
                or info["name_en"].lower() in name_lower
                or name_lower in info["name_en"].lower()):
            return code
    return None


def get_part_info(code: str) -> dict | None:
    """Restituisce le info del componente dato il codice."""
    return STANDARD_PART_CODES.get(code)

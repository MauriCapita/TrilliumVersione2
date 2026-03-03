"""
Trillium V2 — Parts List Templates
Template standard per la parts list di ogni famiglia di pompa.
Definisce i componenti tipici e il metodo di calcolo del peso per ciascuno.
"""


# ============================================================
# METODI DI CALCOLO PESO
# ============================================================
# Ogni componente ha un metodo di calcolo associato:
#   - "scaling_complex": formula pnew = pref × f^(2.3÷2.4) × ρnew/ρref
#     (per componenti di fusione: corpi diffusore, bowl, giranti, volute)
#   - "scaling_pressure": formula pnew = pref × f^2 × ρnew/ρref × Snew/Sref
#     (per componenti pressurizzati dove lo spessore è critico)
#   - "geometric": calcolo da geometrie elementari (cilindri, coni, anelli)
#     (per componenti semplici: colonne, gomiti, telai motore)
#   - "lookup_flange": peso da tabella ASME B16.5 per size e rating
#   - "lookup_standard": peso da tabella standard interna
#   - "ai_estimate": stima AI quando non si hanno dati sufficienti

CALC_METHODS = {
    "scaling_complex": {
        "description": "Scaling con formula f^(2.3÷2.4) per componenti di fusione",
        "formula": "pnew = pref × f^exp × ρnew/ρref",
        "exponent_range": (2.3, 2.4),
        "default_exponent": 2.35,
    },
    "scaling_pressure": {
        "description": "Scaling con spessore per componenti pressurizzati",
        "formula": "pnew = pref × f^2 × ρnew/ρref × Snew/Sref",
        "exponent": 2.0,
    },
    "geometric": {
        "description": "Calcolo da geometrie elementari (cilindri, coni, anelli)",
        "formula": "Calcolo volumetrico × densità materiale",
    },
    "lookup_flange": {
        "description": "Peso flange da tabella ASME B16.5",
        "formula": "Tabella (size, rating) × ρnew/ρcarbon_steel",
    },
    "lookup_standard": {
        "description": "Peso da tabella standard interna",
        "formula": "Peso tabulato, eventualmente scalato per materiale",
    },
    "ai_estimate": {
        "description": "Stima AI quando dati insufficienti per altri metodi",
        "formula": "AI analizza documenti storici e propone stima",
    },
}


# ============================================================
# TEMPLATE PARTS LIST PER FAMIGLIA POMPA
# ============================================================
# Ogni famiglia ha una lista di componenti tipici.
# I componenti sono organizzati per sottogruppo funzionale.

# --- Pompe orizzontali OH2 (da Standard part list OH2.xls) ---
# "Calcolo peso" = True per i componenti con "x" nell'XLS
PARTS_OH = [
    # Idraulica
    {"component": "Corpo con voluta", "component_en": "Casing (Volute)",
     "tpi_code": "102", "group": "Idraulica",
     "calc_method": "scaling_pressure", "is_critical": True,
     "needs_weight_calc": True, "qty": 1,
     "notes": "Componente pressurizzato, spessore critico (SOP-569)"},

    {"component": "Coperchio corpo", "component_en": "Casing Cover",
     "tpi_code": "161", "group": "Idraulica",
     "calc_method": "scaling_pressure", "is_critical": True,
     "needs_weight_calc": True, "qty": 1,
     "notes": "Coperchio corpo pompa, pressurizzato"},

    {"component": "Viteria corpo", "component_en": "Casing Bolts",
     "tpi_code": "900.00", "group": "Idraulica",
     "calc_method": "geometric", "is_critical": False,
     "needs_weight_calc": False, "qty": 1,
     "notes": "Bulloneria cassa"},

    # Supporto e coperchi supporto
    {"component": "Supporto", "component_en": "Bearing Support",
     "tpi_code": "330", "group": "Supporto",
     "calc_method": "scaling_complex", "is_critical": True,
     "needs_weight_calc": True, "qty": 1,
     "notes": "Supporto cuscinetti, peso da tabella per DN albero"},

    {"component": "Coperchio supp. int.", "component_en": "Support Cover (Inboard)",
     "tpi_code": "360.1", "group": "Supporto",
     "calc_method": "scaling_complex", "is_critical": False,
     "needs_weight_calc": False, "qty": 1,
     "notes": "Coperchio supporto lato interno"},

    {"component": "Coperchio supp. est.", "component_en": "Support Cover (Outboard)",
     "tpi_code": "360.2", "group": "Supporto",
     "calc_method": "scaling_complex", "is_critical": False,
     "needs_weight_calc": False, "qty": 1,
     "notes": "Coperchio supporto lato esterno"},

    {"component": "Viteria per coperchi", "component_en": "Cover Bolts",
     "tpi_code": "900.10", "group": "Supporto",
     "calc_method": "geometric", "is_critical": False,
     "needs_weight_calc": False, "qty": 1,
     "notes": "Bulloneria coperchi supporto"},

    # Girante
    {"component": "Girante", "component_en": "Impeller",
     "tpi_code": "230", "group": "Idraulica",
     "calc_method": "scaling_complex", "is_critical": True,
     "needs_weight_calc": True, "qty": 1,
     "notes": "Fusione, scaling con (D2/D2')² × ρ/ρ' × t/t' (SOP-546)"},

    # Anelli usura
    {"component": "Anello usura fisso", "component_en": "Wear Ring (Stationary)",
     "tpi_code": "502", "group": "Idraulica",
     "calc_method": "geometric", "is_critical": False,
     "needs_weight_calc": False, "qty": 2,
     "notes": "Anello anti-usura stazionario"},

    {"component": "Anello usura rotante", "component_en": "Wear Ring (Rotating)",
     "tpi_code": "503", "group": "Idraulica",
     "calc_method": "geometric", "is_critical": False,
     "needs_weight_calc": False, "qty": 2,
     "notes": "Anello anti-usura rotante"},

    # Albero e parti meccaniche
    {"component": "Albero", "component_en": "Shaft",
     "tpi_code": "210", "group": "Meccanica",
     "calc_method": "geometric", "is_critical": True,
     "needs_weight_calc": True, "qty": 1,
     "notes": "Barra grezza: W = π/4 × D² × L × ρ"},

    {"component": "Camicia prot. albero", "component_en": "Shaft Sleeve",
     "tpi_code": "524", "group": "Meccanica",
     "calc_method": "geometric", "is_critical": False,
     "needs_weight_calc": False, "qty": 1,
     "notes": "Camicia protezione albero, cilindro cavo"},

    # Cuscinetti
    {"component": "Cuscinetto lato int.", "component_en": "Bearing (Inboard)",
     "tpi_code": "320", "group": "Cuscinetti",
     "calc_method": "lookup_standard", "is_critical": False,
     "needs_weight_calc": False, "qty": 1,
     "notes": "Peso da catalogo cuscinetti"},

    {"component": "Cuscinetto lato mot.", "component_en": "Bearing (Motor Side)",
     "tpi_code": "320", "group": "Cuscinetti",
     "calc_method": "lookup_standard", "is_critical": False,
     "needs_weight_calc": False, "qty": 1,
     "notes": "Peso da catalogo cuscinetti"},

    # Tenute
    {"component": "Premitreccia", "component_en": "Stuffing Box / Gland",
     "tpi_code": "452", "group": "Tenute",
     "calc_method": "scaling_complex", "is_critical": False,
     "needs_weight_calc": False, "qty": 1,
     "notes": "Qty 1/0 — presente solo se pompa con baderna"},

    {"component": "Anello baderna", "component_en": "Packing Ring",
     "tpi_code": "461", "group": "Tenute",
     "calc_method": "lookup_standard", "is_critical": False,
     "needs_weight_calc": False, "qty": 1,
     "notes": "Qty 1/0 — presente solo se pompa con baderna"},

    {"component": "Boccola di tenuta", "component_en": "Seal Bushing",
     "tpi_code": "542", "group": "Tenute",
     "calc_method": "scaling_complex", "is_critical": False,
     "needs_weight_calc": False, "qty": 1,
     "notes": "Boccola sede tenuta"},

    {"component": "Boccola di fondo", "component_en": "Bottom Bushing",
     "tpi_code": "525", "group": "Tenute",
     "calc_method": "scaling_complex", "is_critical": False,
     "needs_weight_calc": False, "qty": 1,
     "notes": "Boccola fondo camera tenuta"},

    # Accoppiamento
    {"component": "Protezione giunto", "component_en": "Coupling Guard",
     "tpi_code": "681", "group": "Accoppiamento",
     "calc_method": "lookup_standard", "is_critical": False,
     "needs_weight_calc": False, "qty": 1,
     "notes": "Protezione/carter accoppiamento"},

    # Basamento
    {"component": "Piastra di base", "component_en": "Baseplate",
     "tpi_code": "890", "group": "Basamento",
     "calc_method": "geometric", "is_critical": False,
     "needs_weight_calc": False, "qty": 1,
     "notes": "Telaio base, calcolo strutturale"},

    {"component": "Bulloni fondazione", "component_en": "Foundation Bolts",
     "tpi_code": "918", "group": "Basamento",
     "calc_method": "geometric", "is_critical": False,
     "needs_weight_calc": False, "qty": 1,
     "notes": "Bulloneria fissaggio a fondazione"},

    # Voci accessorie
    {"component": "Viteria varia 2%", "component_en": "Miscellaneous Bolts (2%)",
     "tpi_code": "900.20", "group": "Accessori",
     "calc_method": "ai_estimate", "is_critical": False,
     "needs_weight_calc": False, "qty": 1,
     "notes": "2% del peso totale per viteria minuta"},

    {"component": "Varie 2%", "component_en": "Miscellaneous (2%)",
     "tpi_code": "099", "group": "Accessori",
     "calc_method": "ai_estimate", "is_critical": False,
     "needs_weight_calc": False, "qty": 1,
     "notes": "2% del peso totale per voci varie"},

    {"component": "Conservazione", "component_en": "Preservation",
     "tpi_code": "091", "group": "Accessori",
     "calc_method": "ai_estimate", "is_critical": False,
     "needs_weight_calc": False, "qty": 1,
     "notes": "Qty 1/0 — conservazione/imballaggio"},
]


# --- Pompe Between-Bearing (BB) ---
PARTS_BB = [
    # Idraulica
    {"component": "Casing (Barrel/Corpo)", "group": "Idraulica",
     "calc_method": "scaling_pressure", "is_critical": True,
     "notes": "Barrel pressurizzato (BB5) o cassa assiale (BB3)"},
    {"component": "Impeller (Girante) - per stadio", "group": "Idraulica",
     "calc_method": "scaling_complex", "is_critical": True,
     "notes": "Moltiplicare per numero stadi"},
    {"component": "Diffuser / Guide Vane", "group": "Idraulica",
     "calc_method": "scaling_complex", "is_critical": True,
     "notes": "Corpo diffusore, fusione"},
    {"component": "Bowl / Stage Casing", "group": "Idraulica",
     "calc_method": "scaling_complex", "is_critical": True,
     "notes": "Corpo stadio"},
    {"component": "Crossover / Return Channel", "group": "Idraulica",
     "calc_method": "scaling_complex", "is_critical": True,
     "notes": "Canale di ritorno tra stadi"},
    {"component": "Wear Rings - per stadio", "group": "Idraulica",
     "calc_method": "scaling_complex", "is_critical": False,
     "notes": "Per ogni stadio"},
    {"component": "Balance Drum / Disc", "group": "Idraulica",
     "calc_method": "scaling_complex", "is_critical": True,
     "notes": "Compensazione spinta assiale"},

    # Coperchi
    {"component": "Head Cover (Suction Side)", "group": "Coperchi",
     "calc_method": "scaling_pressure", "is_critical": True,
     "notes": "Coperchio lato aspirazione"},
    {"component": "Head Cover (Discharge Side)", "group": "Coperchi",
     "calc_method": "scaling_pressure", "is_critical": True,
     "notes": "Coperchio lato mandata"},

    # Albero e Meccanica
    {"component": "Shaft (Albero)", "group": "Meccanica",
     "calc_method": "geometric", "is_critical": True,
     "notes": "Albero più lungo dei OH, calcolo diametro × lunghezza"},
    {"component": "Shaft Sleeves", "group": "Meccanica",
     "calc_method": "geometric", "is_critical": False,
     "notes": ""},
    {"component": "Coupling Hub", "group": "Meccanica",
     "calc_method": "lookup_standard", "is_critical": False,
     "notes": ""},

    # Tenute
    {"component": "Mechanical Seal (Drive End)", "group": "Tenute",
     "calc_method": "lookup_standard", "is_critical": False,
     "notes": ""},
    {"component": "Mechanical Seal (Non-Drive End)", "group": "Tenute",
     "calc_method": "lookup_standard", "is_critical": False,
     "notes": ""},

    # Cuscinetti
    {"component": "Bearing Housing (Drive End)", "group": "Cuscinetti",
     "calc_method": "scaling_complex", "is_critical": False,
     "notes": ""},
    {"component": "Bearing Housing (Non-Drive End)", "group": "Cuscinetti",
     "calc_method": "scaling_complex", "is_critical": False,
     "notes": ""},
    {"component": "Thrust Bearing", "group": "Cuscinetti",
     "calc_method": "lookup_standard", "is_critical": False,
     "notes": ""},
    {"component": "Radial Bearings", "group": "Cuscinetti",
     "calc_method": "lookup_standard", "is_critical": False,
     "notes": ""},

    # Flangiatura
    {"component": "Suction Flange / Nozzle", "group": "Flangiatura",
     "calc_method": "lookup_flange", "is_critical": False,
     "notes": ""},
    {"component": "Discharge Flange / Nozzle", "group": "Flangiatura",
     "calc_method": "lookup_flange", "is_critical": False,
     "notes": ""},

    # Bulloneria cassa
    {"component": "Casing Bolts / Studs", "group": "Bulloneria",
     "calc_method": "geometric", "is_critical": False,
     "notes": "Peso bulloneria cassa"},

    # Basamento
    {"component": "Baseplate/Support", "group": "Basamento",
     "calc_method": "geometric", "is_critical": False,
     "notes": ""},
]


# --- Pompe Verticali (VS) ---
PARTS_VS = [
    # Idraulica (Bowl Assembly)
    {"component": "Suction Bell / Suction Can", "group": "Idraulica",
     "calc_method": "scaling_complex", "is_critical": True,
     "notes": "Campana aspirazione o can (VS6/VS7)"},
    {"component": "Bowl (Corpo stadio) - per stadio", "group": "Idraulica",
     "calc_method": "scaling_complex", "is_critical": True,
     "notes": "Fusione, moltiplicare per numero stadi"},
    {"component": "Impeller (Girante) - per stadio", "group": "Idraulica",
     "calc_method": "scaling_complex", "is_critical": True,
     "notes": "Moltiplicare per numero stadi"},
    {"component": "Diffuser - per stadio", "group": "Idraulica",
     "calc_method": "scaling_complex", "is_critical": True,
     "notes": ""},
    {"component": "Wear Rings - per stadio", "group": "Idraulica",
     "calc_method": "scaling_complex", "is_critical": False,
     "notes": ""},

    # Colonna (Geometrie semplici)
    {"component": "Column Pipe - per sezione", "group": "Colonna",
     "calc_method": "geometric", "is_critical": True,
     "notes": "Cilindro: diametro, lunghezza, spessore"},
    {"component": "Column Flange - per sezione", "group": "Colonna",
     "calc_method": "lookup_flange", "is_critical": False,
     "notes": ""},
    {"component": "Line Shaft - per sezione", "group": "Colonna",
     "calc_method": "geometric", "is_critical": True,
     "notes": "Albero di trasmissione, cilindro"},
    {"component": "Line Shaft Bearings", "group": "Colonna",
     "calc_method": "lookup_standard", "is_critical": False,
     "notes": "Cuscinetti intermedi"},
    {"component": "Shaft Coupling - per sezione", "group": "Colonna",
     "calc_method": "lookup_standard", "is_critical": False,
     "notes": ""},

    # Testa di scarico
    {"component": "Discharge Elbow / Head", "group": "Testa",
     "calc_method": "scaling_pressure", "is_critical": True,
     "notes": "Gomito di scarico, componente pressurizzato"},
    {"component": "Motor Frame / Stool", "group": "Testa",
     "calc_method": "geometric", "is_critical": True,
     "notes": "Supporto motore, geometria cilindrica/conica"},
    {"component": "Tension Plate", "group": "Testa",
     "calc_method": "geometric", "is_critical": False,
     "notes": ""},

    # Flangiatura
    {"component": "Discharge Flange", "group": "Flangiatura",
     "calc_method": "lookup_flange", "is_critical": False,
     "notes": "ASME B16.5"},

    # Sole Plate
    {"component": "Sole Plate", "group": "Basamento",
     "calc_method": "geometric", "is_critical": False,
     "notes": ""},
]


# ============================================================
# MAPPATURA FAMIGLIA → TEMPLATE
# ============================================================

# ============================================================
# MAPPING MODELLI: API → TPI → LEGACY
# ============================================================
# Fonte: disegni OH2 database e nomenclatura Trillium Pumps

PUMP_MODELS = {
    "OH1": {
        "tpi": ["65AP", "80AP"],
        "legacy": ["B", "BM", "BH"],
        "notes": "End suction overhung, monostadio",
    },
    "OH2": {
        "tpi": ["100AP", "125AP", "150AP", "200AP", "250AP", "300AP"],
        "legacy": ["A", "AM", "AH", "AL"],
        "notes": "Between bearings overhung, design TMP",
    },
    "OH3": {
        "tpi": ["100VP", "125VP"],
        "legacy": ["V", "VM"],
        "notes": "Vertical inline",
    },
    "OH4": {
        "tpi": [],
        "legacy": ["RV"],
        "notes": "Rigid coupled vertical",
    },
    "OH5": {
        "tpi": [],
        "legacy": [],
        "notes": "Close-coupled",
    },
    "OH6": {
        "tpi": [],
        "legacy": [],
        "notes": "High speed integrally geared",
    },
    "BB1": {
        "tpi": ["200BB", "250BB", "300BB"],
        "legacy": ["D", "DH", "DL"],
        "notes": "Axially split single/two stage",
    },
    "BB2": {
        "tpi": ["150BB", "200BB"],
        "legacy": ["E", "EH"],
        "notes": "Radially split single stage",
    },
    "BB3": {
        "tpi": ["100MS", "150MS", "200MS"],
        "legacy": ["M", "MH", "ML"],
        "notes": "Axially split multistage",
    },
    "BB5": {
        "tpi": ["100BF", "150BF"],
        "legacy": ["F", "FH"],
        "notes": "Barrel multistage alta pressione",
    },
    "VS1": {
        "tpi": ["200VS"],
        "legacy": ["VS"],
        "notes": "Vertical suspended single stage",
    },
    "VS4": {
        "tpi": ["150VT", "200VT"],
        "legacy": ["VT"],
        "notes": "Vertical turbine",
    },
    "VS6": {
        "tpi": ["100VC", "150VC"],
        "legacy": ["VC"],
        "notes": "Vertical can",
    },
    "VS7": {
        "tpi": ["100VD", "150VD"],
        "legacy": ["VD"],
        "notes": "Vertical double case",
    },
}

PUMP_FAMILIES = {
    # Overhung
    "OH1": {"name": "OH1 - End Suction Overhung", "type": "OH",
            "template": PARTS_OH, "description": "Pompa centrifuga a sbalzo monostadio"},
    "OH2": {"name": "OH2 - Between Bearings Overhung", "type": "OH",
            "template": PARTS_OH, "description": "Pompa centrifuga a sbalzo con supporti"},
    "OH3": {"name": "OH3 - Vertical Inline", "type": "OH",
            "template": PARTS_OH, "description": "Pompa centrifuga in linea verticale"},
    "OH4": {"name": "OH4 - Rigid Coupling Overhung", "type": "OH",
            "template": PARTS_OH, "description": "Pompa overhung accoppiamento rigido"},
    "OH5": {"name": "OH5 - Close Coupled", "type": "OH",
            "template": PARTS_OH, "description": "Pompa close-coupled"},

    # Between Bearings
    "BB1": {"name": "BB1 - Axially Split Single Stage", "type": "BB",
            "template": PARTS_BB, "description": "Pompa a cassa bipartita assialmente monostadio"},
    "BB2": {"name": "BB2 - Axially Split Multi Stage", "type": "BB",
            "template": PARTS_BB, "description": "Pompa a cassa bipartita assialmente multistadio"},
    "BB3": {"name": "BB3 - Axially Split Multi Stage", "type": "BB",
            "template": PARTS_BB, "description": "Pompa barrel multistadio alta pressione"},
    "BB4": {"name": "BB4 - Single Stage", "type": "BB",
            "template": PARTS_BB, "description": "Pompa between-bearings monostadio"},
    "BB5": {"name": "BB5 - Barrel Multi Stage", "type": "BB",
            "template": PARTS_BB, "description": "Pompa barrel multistadio"},

    # Vertical Suspended
    "VS1": {"name": "VS1 - Vertical Single Stage", "type": "VS",
            "template": PARTS_VS, "description": "Pompa verticale monostadio sospesa"},
    "VS4": {"name": "VS4 - Vertical Multi Stage", "type": "VS",
            "template": PARTS_VS, "description": "Pompa verticale multistadio"},
    "VS6": {"name": "VS6 - Vertical Canned", "type": "VS",
            "template": PARTS_VS, "description": "Pompa verticale a can"},
    "VS7": {"name": "VS7 - Vertical Double Casing", "type": "VS",
            "template": PARTS_VS, "description": "Pompa verticale a doppia cassa"},
}


def get_parts_template(pump_family: str) -> list[dict] | None:
    """Restituisce il template dei componenti per una famiglia pompa."""
    family_info = PUMP_FAMILIES.get(pump_family.upper())
    if family_info:
        return family_info["template"]
    return None


def get_family_info(pump_family: str) -> dict | None:
    """Restituisce le informazioni sulla famiglia pompa."""
    return PUMP_FAMILIES.get(pump_family.upper())


def list_pump_families() -> list[str]:
    """Restituisce lista ordinata delle famiglie pompa disponibili."""
    return sorted(PUMP_FAMILIES.keys())


def get_family_names() -> dict[str, str]:
    """Restituisce dizionario famiglia → nome completo."""
    return {k: v["name"] for k, v in PUMP_FAMILIES.items()}


def get_pump_models(pump_family: str) -> dict | None:
    """Restituisce modelli TPI e legacy per una famiglia pompa.

    Returns:
        dict con chiavi 'tpi' (list[str]), 'legacy' (list[str]), 'notes' (str)
        o None se famiglia non trovata.
    """
    return PUMP_MODELS.get(pump_family.upper())


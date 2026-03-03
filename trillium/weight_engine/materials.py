"""
Trillium V2 — Database Materiali
Fonte: Material_Database.xlsm (Trillium Pumps Italy — Standards)
114 materiali reali con Yield, UTS, densità, tipo fornitura.
Aggiornamento: 26 febbraio 2026
"""


# ============================================================
# DATABASE DENSITÀ MATERIALI (kg/m³)
# ============================================================
# Fonte: standard industriali pompe centrifughe (API 610, ASME)

MATERIAL_DENSITY = {
    # --- Acciai al carbonio ---
    "Carbon Steel": 7850,
    "A216 WCB": 7850,
    "ASTM A216 WCB": 7850,
    "ASTM A216 WCB (HRC<22)": 7850,
    "A105": 7850,
    "A106 Gr.B": 7850,
    "SA-216 WCB": 7850,
    "SA-105": 7850,
    "ASTM A352 LCC": 7850,
    "ASTM A352 LCB": 7850,
    "ASTM A352 LCB (HRC<22)": 7850,
    "ASTM A352 LC1": 7850,
    "ASTM A352 Gr. LC2": 7850,
    "ASTM A36": 7850,
    "EN10250-3 36CrNiMo4": 7850,
    "AISI 4140": 7850,
    "ASTM A576 Gr.1045": 7850,
    "C45 UNI 7845": 7850,
    "Fe 60 UNI 7230": 7850,
    "42CrMo4 UNI7845": 7850,
    "C15 UNI 7846": 7850,
    "ASTM A434 Cl.BC": 7850,
    "ASTM A434 Cl.BB": 7850,
    "ASTM A434 Cl.BB (HRC<22)": 7850,
    "ASTM A434 cl. BB/BC": 7850,
    "ASTM A322 Gr. 4140 class P3": 7850,
    "ASTM A322 Gr. 4140 class Q4": 7850,

    # --- Acciai inossidabili austenitici ---
    "SS 316": 7960,
    "SS 316L": 7960,
    "SS 304": 7930,
    "SS 304L": 7930,
    "AISI 316L": 7960,
    "ASTM A479 Tp.316": 7960,
    "ASTM A479 Tp.316L": 7960,
    "ASTM A479 Tp.316L (HRC<22)": 7960,
    "ASTM A276 Tp.316 HOT-FINISHED": 7960,
    "ASTM A276 Tp.316 COLD FINISHED": 7960,
    "ASTM A276 Tp.316L HOT-FINISHED": 7960,
    "ASTM A276 Tp.316L COLD FINISHED": 7960,
    "ASTM A276 Tp.316/316L (HRC<22)": 7960,
    "ASTM A479 Tp. XM19": 7880,
    "ASTM A479 Tp. XM19 (HRC<22)": 7880,
    "X10 Cr Ni 1809 UNI 6900": 7930,
    "A351 CF8M": 7960,
    "A351 CF8": 7930,
    "A351 CF3M": 7960,
    "A182 F316": 7960,
    "A182 F304": 7930,
    "SA-351 CF8M": 7960,
    "SA-351 CF8": 7930,
    "ASTM A351 CF8M": 7960,
    "ASTM A351 CF8M (HRC<22)": 7960,
    "ASTM A351 CF3M": 7960,
    "ASTM A351 CF3M (HRC<22)": 7960,
    "ASTM A743 CF3M": 7960,
    "ASTM A743 CF3M (HRC<22)": 7960,
    "ASTM A743 CF8M": 7960,
    "ASTM A743 CF8M (HRC<22)": 7960,
    "A4 ISO 3506": 7960,
    "A2 ISO 3506": 7930,

    # --- Acciai inossidabili duplex ---
    "Duplex 2205": 7820,
    "A890 Gr.4A": 7820,
    "SA-890 4A": 7820,
    "Super Duplex 2507": 7850,
    "A890 Gr.5A": 7850,
    "ASTM A479 UNS S31803": 7820,
    "ASTM A276 UNS S31803": 7820,
    "ASTM A276 UNS S31803 (HRC<25)": 7820,
    "ASTM A479 UNS S32760": 7850,
    "ASTM A276 UNS S32760": 7850,
    "ASTM A276 UNS S32760 (PREN>40)": 7850,
    "ASTM A276 UNS S32750": 7850,
    "ASTM A182 F55": 7850,
    "ASTM A182 Tp. F51": 7820,
    "ASTM A890 Gr.1B": 7820,
    "ASTM A890 Gr.1B (HRC<25)": 7820,
    "ASTM A890 Gr.5A": 7850,
    "ASTM A890 Gr.6A": 7850,
    "ASTM A890 Gr. 4A": 7820,
    "ASTM A995 Gr.4A": 7820,
    "ASTM A995 Gr.4A (HRC<28)": 7820,
    "ASTM A995 Gr.5A": 7850,
    "ASTM A995 Gr.6A": 7850,
    "ASTM A995 Gr. 1B (CD4MCuN)": 7820,

    # --- Acciai inossidabili martensitici ---
    "SS 410": 7740,
    "SS 420": 7740,
    "A217 CA15": 7740,
    "13Cr-4Ni": 7740,
    "A743 CA6NM": 7740,
    "ASTM A743 CA6NM": 7740,
    "ASTM A743 CA6NM (HRC<22)": 7740,
    "ASTM A487 CA6NM class B": 7740,
    "ASTM A487 CA6NM class B (HRC<22)": 7740,
    "ASTM A473 Tp.420": 7740,
    "ASTM A276 Tp.420": 7740,
    "ASTM A276 Tp.420 (HRC<22)": 7740,
    "ASTM A276 Tp.410": 7740,
    "ASTM A182 F6NM": 7740,
    "X30 Cr13 UNI 6900 (AISI 420)": 7740,

    # --- Leghe di nichel ---
    "Monel 400": 8830,
    "Monel K-500": 8440,
    "Inconel 625": 8440,
    "Inconel 718": 8190,
    "Hastelloy C-276": 8890,
    "Hastelloy B-2": 9220,
    "Alloy 20 (CN-7M)": 8080,
    "Incoloy 825": 8140,
    "Incoloy 925": 8140,
    "ASTM B425 UNS N08825": 8140,
    "ASTM B424 UNS N08825": 8140,
    "ASTM B425 N08825": 8140,
    "UNS N05500 (HRC<29)": 8440,
    "ASTM A494 Gr. Cu5MCuC": 8830,
    "ASTM A494 Gr.M30C": 8830,
    "Alloy 400 (Monel)": 8830,
    "Alloy 625 (Inconel)": 8440,
    "CW-12MW": 8690,

    # --- Leghe di rame ---
    "Bronze": 8800,
    "Leaded Bronze": 8930,
    "Tin Bronze C90300": 8800,
    "Aluminum Bronze": 7600,
    "Nickel Aluminum Bronze": 7600,
    "NAB C95800": 7640,
    "ASTM B148 C95800": 7640,
    "ASTM B148 C95500": 7640,
    "Gunmetal": 8700,
    "PCUZN40 UNI4891": 8500,

    # --- Titanio ---
    "Titanium Gr.2": 4510,
    "Titanium Gr.5": 4430,
    "Ti-6Al-4V": 4430,

    # --- Ghisa ---
    "Cast Iron": 7200,
    "Ductile Iron": 7100,
    "A48 Class 30": 7200,
    "A536 60-40-18": 7100,
    "ASTM A536 65.45.12": 7100,
    "Ni-Resist": 7400,

    # --- Alluminio ---
    "GAlSi9Cu1 EN AB 46400": 2750,
    "AlSi7Mg EN AB 42000": 2680,

    # --- Speciali ---
    "Zirconium": 6510,
    "Stellite 6": 8380,
}


# ============================================================
# PROPRIETÀ MECCANICHE MATERIALI
# ============================================================
# Fonte: Material_Database.xlsm (Trillium Pumps Italy — Standards)
# 114 materiali con Yield e Tensile reali da database aziendale

MATERIAL_PROPERTIES = {
    # === CASTING (corpo, coperchi, voluta) ===
    "ASTM A216 WCB": {"yield_strength": 250, "tensile_strength": 485, "supply": "casting", "temperature_limit": 425},
    "ASTM A216 WCB (HRC<22)": {"yield_strength": 250, "tensile_strength": 485, "supply": "casting", "temperature_limit": 425},
    "ASTM A352 LCC": {"yield_strength": 275, "tensile_strength": 485, "supply": "casting", "temperature_limit": -46},
    "ASTM A352 LCB": {"yield_strength": 240, "tensile_strength": 450, "supply": "casting", "temperature_limit": -46},
    "ASTM A352 LCB (HRC<22)": {"yield_strength": 240, "tensile_strength": 450, "supply": "casting", "temperature_limit": -46},
    "ASTM A352 LC1": {"yield_strength": 240, "tensile_strength": 450, "supply": "casting", "temperature_limit": -59},
    "ASTM A352 Gr. LC2": {"yield_strength": 275, "tensile_strength": 485, "supply": "casting", "temperature_limit": -73},
    "ASTM A743 CA6NM": {"yield_strength": 550, "tensile_strength": 755, "supply": "casting", "temperature_limit": 400},
    "ASTM A743 CA6NM (HRC<22)": {"yield_strength": 550, "tensile_strength": 755, "supply": "casting", "temperature_limit": 400},
    "ASTM A743 CF3M": {"yield_strength": 205, "tensile_strength": 485, "supply": "casting", "temperature_limit": 815},
    "ASTM A743 CF3M (HRC<22)": {"yield_strength": 205, "tensile_strength": 485, "supply": "casting", "temperature_limit": 815},
    "ASTM A743 CF8M": {"yield_strength": 205, "tensile_strength": 485, "supply": "casting", "temperature_limit": 815},
    "ASTM A743 CF8M (HRC<22)": {"yield_strength": 205, "tensile_strength": 485, "supply": "casting", "temperature_limit": 815},
    "ASTM A351 CF8M": {"yield_strength": 205, "tensile_strength": 485, "supply": "casting", "temperature_limit": 815},
    "ASTM A351 CF8M (HRC<22)": {"yield_strength": 205, "tensile_strength": 485, "supply": "casting", "temperature_limit": 815},
    "ASTM A351 CF3M": {"yield_strength": 205, "tensile_strength": 485, "supply": "casting", "temperature_limit": 815},
    "ASTM A351 CF3M (HRC<22)": {"yield_strength": 205, "tensile_strength": 485, "supply": "casting", "temperature_limit": 815},
    "ASTM A487 CA6NM class B": {"yield_strength": 515, "tensile_strength": 690, "supply": "casting", "temperature_limit": 400},
    "ASTM A487 CA6NM class B (HRC<22)": {"yield_strength": 515, "tensile_strength": 690, "supply": "casting", "temperature_limit": 400},
    "ASTM A494 Gr. Cu5MCuC": {"yield_strength": 240, "tensile_strength": 520, "supply": "casting", "temperature_limit": 480},
    "ASTM A494 Gr.M30C": {"yield_strength": 225, "tensile_strength": 450, "supply": "casting", "temperature_limit": 480},
    "ASTM A536 65.45.12": {"yield_strength": 310, "tensile_strength": 448, "supply": "casting", "temperature_limit": 345},
    "GAlSi9Cu1 EN AB 46400": {"yield_strength": 140, "tensile_strength": 240, "supply": "casting", "temperature_limit": 200},
    "AlSi7Mg EN AB 42000": {"yield_strength": 0, "tensile_strength": 127, "supply": "casting", "temperature_limit": 200},
    "ASTM B148 C95500": {"yield_strength": 275, "tensile_strength": 620, "supply": "casting", "temperature_limit": 288},
    "ASTM B148 C95800": {"yield_strength": 240, "tensile_strength": 585, "supply": "casting", "temperature_limit": 288},

    # === PRESSURE CASTING (pompe alta pressione) ===
    "ASTM A890 Gr.1B": {"yield_strength": 485, "tensile_strength": 690, "supply": "pressure casting", "temperature_limit": 315},
    "ASTM A890 Gr.1B (HRC<25)": {"yield_strength": 485, "tensile_strength": 690, "supply": "pressure casting", "temperature_limit": 315},
    "ASTM A890 Gr.5A": {"yield_strength": 515, "tensile_strength": 690, "supply": "pressure casting", "temperature_limit": 315},
    "ASTM A890 Gr.6A": {"yield_strength": 450, "tensile_strength": 690, "supply": "pressure casting", "temperature_limit": 315},
    "ASTM A890 Gr. 4A": {"yield_strength": 415, "tensile_strength": 620, "supply": "pressure casting", "temperature_limit": 315},
    "ASTM A995 Gr.4A": {"yield_strength": 415, "tensile_strength": 620, "supply": "pressure casting", "temperature_limit": 315},
    "ASTM A995 Gr.4A (HRC<28)": {"yield_strength": 415, "tensile_strength": 620, "supply": "pressure casting", "temperature_limit": 315},
    "ASTM A995 Gr.5A": {"yield_strength": 515, "tensile_strength": 690, "supply": "pressure casting", "temperature_limit": 315},
    "ASTM A995 Gr.6A": {"yield_strength": 450, "tensile_strength": 690, "supply": "pressure casting", "temperature_limit": 315},
    "ASTM A995 Gr. 1B (CD4MCuN)": {"yield_strength": 485, "tensile_strength": 690, "supply": "pressure casting", "temperature_limit": 315},

    # === DUPLEX / SUPER DUPLEX (bar) ===
    "ASTM A479 UNS S31803": {"yield_strength": 450, "tensile_strength": 620, "supply": "bar", "temperature_limit": 315},
    "ASTM A276 UNS S31803": {"yield_strength": 448, "tensile_strength": 620, "supply": "bar", "temperature_limit": 315},
    "ASTM A276 UNS S31803 (HRC<25)": {"yield_strength": 448, "tensile_strength": 620, "supply": "bar", "temperature_limit": 315},
    "ASTM A479 UNS S32760": {"yield_strength": 550, "tensile_strength": 750, "supply": "bar", "temperature_limit": 315},
    "ASTM A276 UNS S32760": {"yield_strength": 550, "tensile_strength": 750, "supply": "bar", "temperature_limit": 315},
    "ASTM A276 UNS S32760 (PREN>40)": {"yield_strength": 550, "tensile_strength": 750, "supply": "bar", "temperature_limit": 315},
    "ASTM A276 UNS S32750": {"yield_strength": 515, "tensile_strength": 760, "supply": "bar", "temperature_limit": 315},
    "ASTM A182 F55": {"yield_strength": 550, "tensile_strength": 750, "supply": "forging", "temperature_limit": 315},
    "ASTM A182 Tp. F51": {"yield_strength": 450, "tensile_strength": 620, "supply": "forging", "temperature_limit": 315},

    # === INOX AUSTENITICO (bar/forging) ===
    "ASTM A479 Tp.316": {"yield_strength": 205, "tensile_strength": 515, "supply": "bar", "temperature_limit": 815},
    "ASTM A479 Tp.316L": {"yield_strength": 170, "tensile_strength": 485, "supply": "bar", "temperature_limit": 815},
    "ASTM A479 Tp.316L (HRC<22)": {"yield_strength": 170, "tensile_strength": 485, "supply": "bar", "temperature_limit": 815},
    "ASTM A276 Tp.316 HOT-FINISHED": {"yield_strength": 205, "tensile_strength": 515, "supply": "bar", "temperature_limit": 815},
    "ASTM A276 Tp.316 COLD FINISHED": {"yield_strength": 310, "tensile_strength": 620, "supply": "bar", "temperature_limit": 815},
    "ASTM A276 Tp.316L HOT-FINISHED": {"yield_strength": 170, "tensile_strength": 485, "supply": "bar", "temperature_limit": 815},
    "ASTM A276 Tp.316L COLD FINISHED": {"yield_strength": 310, "tensile_strength": 620, "supply": "bar", "temperature_limit": 815},
    "ASTM A276 Tp.316/316L (HRC<22)": {"yield_strength": 170, "tensile_strength": 485, "supply": "bar", "temperature_limit": 815},
    "ASTM A479 Tp. XM19": {"yield_strength": 380, "tensile_strength": 690, "supply": "bar", "temperature_limit": 400},
    "ASTM A479 Tp. XM19 (HRC<22)": {"yield_strength": 380, "tensile_strength": 690, "supply": "bar", "temperature_limit": 400},
    "AISI 316L": {"yield_strength": 170, "tensile_strength": 485, "supply": "bar", "temperature_limit": 815},

    # === MARTENSITICO / CROMO (bar/forging) ===
    "ASTM A473 Tp.420": {"yield_strength": 640, "tensile_strength": 850, "supply": "bar", "temperature_limit": 400},
    "ASTM A276 Tp.420": {"yield_strength": 640, "tensile_strength": 850, "supply": "bar", "temperature_limit": 400},
    "ASTM A276 Tp.420 (HRC<22)": {"yield_strength": 640, "tensile_strength": 850, "supply": "bar", "temperature_limit": 400},
    "ASTM A276 Tp.410": {"yield_strength": 275, "tensile_strength": 480, "supply": "bar", "temperature_limit": 400},
    "ASTM A182 F6NM": {"yield_strength": 620, "tensile_strength": 795, "supply": "forging", "temperature_limit": 400},
    "X30 Cr13 UNI 6900 (AISI 420)": {"yield_strength": 590, "tensile_strength": 785, "supply": "bar", "temperature_limit": 400},

    # === ACCIAIO AL CARBONIO / LEGATO ===
    "EN10250-3 36CrNiMo4": {"yield_strength": 320, "tensile_strength": 400, "supply": "plate", "temperature_limit": 425},
    "AISI 4140": {"yield_strength": 862, "tensile_strength": 862, "supply": "bar", "temperature_limit": 425},
    "ASTM A576 Gr.1045": {"yield_strength": 585, "tensile_strength": 655, "supply": "bar", "temperature_limit": 425},
    "ASTM A36": {"yield_strength": 240, "tensile_strength": 585, "supply": "bar", "temperature_limit": 425},
    "C45 UNI 7845": {"yield_strength": 335, "tensile_strength": 590, "supply": "bar", "temperature_limit": 425},
    "Fe 60 UNI 7230": {"yield_strength": 304, "tensile_strength": 588, "supply": "bar", "temperature_limit": 425},
    "42CrMo4 UNI7845": {"yield_strength": 510, "tensile_strength": 740, "supply": "bar", "temperature_limit": 425},
    "C15 UNI 7846": {"yield_strength": 440, "tensile_strength": 740, "supply": "bar", "temperature_limit": 425},
    "X10 Cr Ni 1809 UNI 6900": {"yield_strength": 370, "tensile_strength": 680, "supply": "bar", "temperature_limit": 400},
    "ASTM A434 Cl.BC": {"yield_strength": 550, "tensile_strength": 720, "supply": "bar", "temperature_limit": 425},
    "ASTM A434 Cl.BB": {"yield_strength": 450, "tensile_strength": 620, "supply": "bar", "temperature_limit": 425},
    "ASTM A434 Cl.BB (HRC<22)": {"yield_strength": 450, "tensile_strength": 620, "supply": "bar", "temperature_limit": 425},
    "ASTM A434 cl. BB/BC": {"yield_strength": 450, "tensile_strength": 620, "supply": "bar", "temperature_limit": 425},
    "ASTM A322 Gr. 4140 class P3": {"yield_strength": 1034, "tensile_strength": 1172, "supply": "bar", "temperature_limit": 425},
    "ASTM A322 Gr. 4140 class Q4": {"yield_strength": 517, "tensile_strength": 655, "supply": "bar", "temperature_limit": 425},

    # === LEGHE DI NICHEL ===
    "ASTM B425 UNS N08825": {"yield_strength": 240, "tensile_strength": 585, "supply": "bar", "temperature_limit": 540},
    "ASTM B424 UNS N08825": {"yield_strength": 240, "tensile_strength": 585, "supply": "plate", "temperature_limit": 540},
    "ASTM B425 N08825": {"yield_strength": 240, "tensile_strength": 585, "supply": "bar", "temperature_limit": 540},
    "UNS N05500 (HRC<29)": {"yield_strength": 585, "tensile_strength": 895, "supply": "bar", "temperature_limit": 480},
    "Incoloy 925": {"yield_strength": 271, "tensile_strength": 685, "supply": "bar", "temperature_limit": 540},

    # === BOLTING (bulloneria) ===
    "ASTM A193 grade B7": {"yield_strength": 515, "tensile_strength": 690, "supply": "bolting", "temperature_limit": 425},
    "ASTM A193 grade B8M": {"yield_strength": 205, "tensile_strength": 515, "supply": "bolting", "temperature_limit": 815},
    "ASTM A193 Gr.B8MA Cl. 1A": {"yield_strength": 205, "tensile_strength": 515, "supply": "bolting", "temperature_limit": 815},
    "ASTM A193 B8M Cl.2": {"yield_strength": 345, "tensile_strength": 620, "supply": "bolting", "temperature_limit": 815},
    "ASTM A193 B8 Cl.2": {"yield_strength": 345, "tensile_strength": 690, "supply": "bolting", "temperature_limit": 815},
    "ASTM A193 B6": {"yield_strength": 585, "tensile_strength": 760, "supply": "bolting", "temperature_limit": 400},
    "ASTM A193 Gr. B7M": {"yield_strength": 550, "tensile_strength": 690, "supply": "bolting", "temperature_limit": 425},
    "ASTM A193 Gr.B16": {"yield_strength": 585, "tensile_strength": 690, "supply": "bolting", "temperature_limit": 425},
    "ASTM A325M Tp. 1": {"yield_strength": 560, "tensile_strength": 725, "supply": "bolting", "temperature_limit": 425},
    "ASTM A320 Gr. L7": {"yield_strength": 725, "tensile_strength": 860, "supply": "bolting", "temperature_limit": -101},
    "ASTM A320 Gr. L7M": {"yield_strength": 550, "tensile_strength": 600, "supply": "bolting", "temperature_limit": -101},
    "ASTM A320 B8M Cl.2": {"yield_strength": 345, "tensile_strength": 620, "supply": "bolting", "temperature_limit": -196},
    "ASTM F1554 Gr.36": {"yield_strength": 284, "tensile_strength": 400, "supply": "bolting", "temperature_limit": 200},
    "A4 ISO 3506": {"yield_strength": 205, "tensile_strength": 515, "supply": "bar", "temperature_limit": 400},
    "A2 ISO 3506": {"yield_strength": 205, "tensile_strength": 515, "supply": "bar", "temperature_limit": 400},
    "8.8 UNI 3740": {"yield_strength": 640, "tensile_strength": 800, "supply": "bolting", "temperature_limit": 300},
    "10.9 UNI 3740": {"yield_strength": 940, "tensile_strength": 1040, "supply": "bolting", "temperature_limit": 300},
    "12.9 UNI 3740": {"yield_strength": 1100, "tensile_strength": 1220, "supply": "bolting", "temperature_limit": 300},

    # === ALIAS SEMPLIFICATI (compatibilità con form) ===
    "Carbon Steel": {"yield_strength": 250, "tensile_strength": 485, "supply": "casting", "temperature_limit": 425},
    "A216 WCB": {"yield_strength": 250, "tensile_strength": 485, "supply": "casting", "temperature_limit": 425},
    "SS 316": {"yield_strength": 205, "tensile_strength": 515, "supply": "bar", "temperature_limit": 815},
    "SS 316L": {"yield_strength": 170, "tensile_strength": 485, "supply": "bar", "temperature_limit": 815},
    "SS 304": {"yield_strength": 205, "tensile_strength": 515, "supply": "bar", "temperature_limit": 815},
    "Duplex 2205": {"yield_strength": 450, "tensile_strength": 620, "supply": "bar", "temperature_limit": 315},
    "Super Duplex 2507": {"yield_strength": 550, "tensile_strength": 795, "supply": "bar", "temperature_limit": 315},
    "13Cr-4Ni": {"yield_strength": 550, "tensile_strength": 760, "supply": "casting", "temperature_limit": 400},
    "Monel 400": {"yield_strength": 240, "tensile_strength": 550, "supply": "bar", "temperature_limit": 480},
    "Inconel 625": {"yield_strength": 415, "tensile_strength": 830, "supply": "bar", "temperature_limit": 980},
    "Hastelloy C-276": {"yield_strength": 310, "tensile_strength": 690, "supply": "bar", "temperature_limit": 675},
    "Cast Iron": {"yield_strength": 210, "tensile_strength": 210, "supply": "casting", "temperature_limit": 230},
    "Ductile Iron": {"yield_strength": 275, "tensile_strength": 415, "supply": "casting", "temperature_limit": 345},
    "Titanium Gr.2": {"yield_strength": 275, "tensile_strength": 345, "supply": "bar", "temperature_limit": 315},
    "Bronze": {"yield_strength": 125, "tensile_strength": 275, "supply": "casting", "temperature_limit": 260},
    "NAB C95800": {"yield_strength": 240, "tensile_strength": 585, "supply": "casting", "temperature_limit": 288},
    "PCUZN40 UNI4891": {"yield_strength": 147, "tensile_strength": 353, "supply": "bar", "temperature_limit": 260},
}


# ============================================================
# COSTO INDICATIVO MATERIALI (€/kg)
# ============================================================
# Fonte: valori medi di mercato industriale pompe (indicativi, configurabili)
# Aggiornamento: 27 febbraio 2026

MATERIAL_COST_EUR_KG = {
    # --- Acciai al carbonio ---
    "Carbon Steel": 3.0,
    "A216 WCB": 3.0,
    "ASTM A216 WCB": 3.0,
    "A105": 3.2,
    "A106 Gr.B": 3.2,
    "ASTM A352 LCC": 4.0,
    "ASTM A352 LCB": 4.0,
    "ASTM A36": 2.5,
    "AISI 4140": 4.5,
    "ASTM A576 Gr.1045": 3.5,

    # --- Acciai inossidabili austenitici ---
    "SS 316": 8.0,
    "SS 316L": 8.5,
    "SS 304": 7.0,
    "SS 304L": 7.5,
    "AISI 316L": 8.5,
    "ASTM A351 CF8M": 9.0,
    "ASTM A351 CF3M": 9.5,
    "ASTM A743 CF8M": 9.0,
    "ASTM A743 CF3M": 9.5,

    # --- Duplex / Super Duplex ---
    "Duplex 2205": 12.0,
    "Super Duplex 2507": 18.0,
    "ASTM A890 Gr.5A": 20.0,
    "ASTM A890 Gr. 4A": 14.0,
    "ASTM A995 Gr.4A": 14.0,
    "ASTM A995 Gr.5A": 20.0,

    # --- Martensitici ---
    "13Cr-4Ni": 7.0,
    "A743 CA6NM": 7.0,
    "ASTM A743 CA6NM": 7.0,
    "SS 410": 6.0,
    "SS 420": 6.5,

    # --- Leghe di nichel ---
    "Monel 400": 35.0,
    "Monel K-500": 45.0,
    "Inconel 625": 45.0,
    "Inconel 718": 50.0,
    "Hastelloy C-276": 55.0,
    "Hastelloy B-2": 60.0,
    "Alloy 20 (CN-7M)": 25.0,
    "Incoloy 825": 28.0,
    "Incoloy 925": 30.0,

    # --- Leghe di rame ---
    "Bronze": 10.0,
    "Aluminum Bronze": 11.0,
    "Nickel Aluminum Bronze": 12.0,
    "NAB C95800": 12.0,
    "ASTM B148 C95800": 12.0,

    # --- Titanio ---
    "Titanium Gr.2": 60.0,
    "Titanium Gr.5": 75.0,

    # --- Ghisa ---
    "Cast Iron": 1.8,
    "Ductile Iron": 2.2,

    # --- Speciali ---
    "Zirconium": 120.0,
    "Stellite 6": 90.0,
}


def get_cost_per_kg(material_name: str) -> float | None:
    """
    Restituisce il costo indicativo €/kg del materiale.
    Cerca match esatto, poi case-insensitive, poi parziale.
    """
    if material_name in MATERIAL_COST_EUR_KG:
        return MATERIAL_COST_EUR_KG[material_name]

    name_lower = material_name.lower()
    for key, value in MATERIAL_COST_EUR_KG.items():
        if key.lower() == name_lower:
            return value

    # Match parziale (es. "Carbon Steel" matcha "ASTM A216 WCB" → no, ma "Carbon" matcha "Carbon Steel")
    for key, value in MATERIAL_COST_EUR_KG.items():
        if name_lower in key.lower() or key.lower() in name_lower:
            return value

    # Fallback: stima basata sulla categoria di materiale
    for key, value in MATERIAL_COST_EUR_KG.items():
        if name_lower.startswith(key.lower()[:4]):
            return value

    return None


# ============================================================
# PESI STANDARD FLANGE (kg) PER RATING E DIMENSIONE
# ============================================================
# Fonte: ASME B16.5 (Pipe Flanges and Flanged Fittings)

FLANGE_WEIGHTS = {
    # (size_inch, rating): weight_kg
    # Rating 150
    (1, 150): 1.0, (1.5, 150): 1.5, (2, 150): 2.5, (3, 150): 4.5,
    (4, 150): 6.8, (6, 150): 11.5, (8, 150): 17.5, (10, 150): 25.0,
    (12, 150): 34.0, (14, 150): 41.0, (16, 150): 52.0, (18, 150): 63.0,
    (20, 150): 77.0, (24, 150): 108.0,
    # Rating 300
    (1, 300): 1.5, (1.5, 300): 2.2, (2, 300): 3.8, (3, 300): 7.2,
    (4, 300): 10.5, (6, 300): 19.0, (8, 300): 30.0, (10, 300): 45.0,
    (12, 300): 60.0, (14, 300): 75.0, (16, 300): 95.0, (18, 300): 115.0,
    (20, 300): 140.0, (24, 300): 190.0,
    # Rating 600
    (1, 600): 2.0, (1.5, 600): 3.0, (2, 600): 5.0, (3, 600): 9.5,
    (4, 600): 14.5, (6, 600): 27.0, (8, 600): 44.0, (10, 600): 65.0,
    (12, 600): 88.0, (14, 600): 110.0, (16, 600): 140.0, (18, 600): 175.0,
    (20, 600): 210.0, (24, 600): 290.0,
    # Rating 900
    (1, 900): 3.5, (1.5, 900): 5.0, (2, 900): 8.0, (3, 900): 15.0,
    (4, 900): 22.0, (6, 900): 42.0, (8, 900): 68.0, (10, 900): 100.0,
    (12, 900): 135.0, (14, 900): 165.0, (16, 900): 210.0, (18, 900): 260.0,
    (20, 900): 320.0, (24, 900): 440.0,
    # Rating 1500
    (1, 1500): 5.0, (1.5, 1500): 7.5, (2, 1500): 12.0, (3, 1500): 22.0,
    (4, 1500): 34.0, (6, 1500): 65.0, (8, 1500): 105.0, (10, 1500): 155.0,
    (12, 1500): 210.0, (14, 1500): 260.0, (16, 1500): 330.0, (18, 1500): 410.0,
    (20, 1500): 500.0, (24, 1500): 680.0,
    # Rating 2500
    (1, 2500): 7.5, (1.5, 2500): 11.0, (2, 2500): 18.0, (3, 2500): 33.0,
    (4, 2500): 52.0, (6, 2500): 100.0, (8, 2500): 165.0, (10, 2500): 245.0,
    (12, 2500): 340.0,
}


# ============================================================
# FUNZIONI HELPER
# ============================================================

def get_density(material_name: str) -> float | None:
    """
    Restituisce la densità del materiale (kg/m³).
    Cerca match esatto o parziale (case-insensitive).
    """
    if material_name in MATERIAL_DENSITY:
        return MATERIAL_DENSITY[material_name]

    name_lower = material_name.lower()
    for key, value in MATERIAL_DENSITY.items():
        if key.lower() == name_lower:
            return value

    for key, value in MATERIAL_DENSITY.items():
        if name_lower in key.lower() or key.lower() in name_lower:
            return value

    return None


def get_properties(material_name: str) -> dict | None:
    """Restituisce le proprietà meccaniche del materiale."""
    if material_name in MATERIAL_PROPERTIES:
        return MATERIAL_PROPERTIES[material_name]

    name_lower = material_name.lower()
    for key, value in MATERIAL_PROPERTIES.items():
        if key.lower() == name_lower:
            return value
        if name_lower in key.lower() or key.lower() in name_lower:
            return value

    return None


def get_flange_weight(size_inch: float, rating: int, material: str = "Carbon Steel") -> float | None:
    """
    Peso flange per dimensione e rating.
    Se il materiale non è acciaio al carbonio, scala per rapporto densità.
    """
    key = (int(size_inch), int(rating))
    base_weight = FLANGE_WEIGHTS.get(key)

    if base_weight is None:
        return None

    if material != "Carbon Steel":
        rho_mat = get_density(material)
        rho_cs = MATERIAL_DENSITY["Carbon Steel"]
        if rho_mat:
            base_weight = base_weight * rho_mat / rho_cs

    return round(base_weight, 1)


def density_ratio(material_new: str, material_ref: str) -> float | None:
    """Calcola il rapporto densità ρnew/ρref."""
    rho_new = get_density(material_new)
    rho_ref = get_density(material_ref)
    if rho_new and rho_ref:
        return rho_new / rho_ref
    return None


def list_materials() -> list[str]:
    """Restituisce la lista ordinata di tutti i materiali con proprietà meccaniche."""
    return sorted(MATERIAL_PROPERTIES.keys())


def list_material_categories() -> dict[str, list[str]]:
    """Restituisce i materiali raggruppati per tipo di fornitura."""
    categories = {}
    for mat, props in MATERIAL_PROPERTIES.items():
        supply = props.get("supply", "altro")
        cat_name = {
            "casting": "Casting (corpo, coperchi, voluta)",
            "pressure casting": "Pressure Casting (alta pressione)",
            "bar": "Bar / Barre",
            "forging": "Forging / Fucinati",
            "bolting": "Bolting / Bulloneria",
            "plate": "Plate / Lamiere",
        }.get(supply, supply.title())
        categories.setdefault(cat_name, []).append(mat)

    return {k: sorted(v) for k, v in sorted(categories.items()) if v}

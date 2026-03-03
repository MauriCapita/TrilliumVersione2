"""
Trillium V2 — Pump Data Extractor
Estrae automaticamente dati strutturati dai testi dei disegni tecnici:
peso, materiale, dimensioni, part number, famiglia, componente.
"""

import re
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ============================================================
# PATTERN DI ESTRAZIONE
# ============================================================

# Peso: cattura valore + tipo (finished, raw, premachined)
WEIGHT_PATTERNS = [
    # --- Peso finito ---
    (r"[Ff]inish(?:ed)?\s+[Ww]eight\s*\(?(?:calculated|calcolato)?\)?\s*[:=]\s*(\d+[\.,]?\d*)\s*[Kk]g",
     "finished"),
    (r"[Pp]eso\s+finito\s*\(?(?:calcolato)?\)?\s*[:=]\s*(\d+[\.,]?\d*)\s*[Kk]g",
     "finished"),
    # --- Peso grezzo ---
    (r"[Rr]aw\s+(?:casting\s+)?[Ww]eight\s*[:=]\s*(\d+[\.,]?\d*)\s*[Kk]g",
     "raw"),
    (r"[Pp]eso\s+getto\s+grezzo\s*[:=]\s*(\d+[\.,]?\d*)\s*[Kk]g",
     "raw"),
    # --- Peso sgrossato ---
    (r"[Pp]re[\-\s]?machin(?:ing|ed)\s+[Ww]eight\s*[:=]\s*(\d+[\.,]?\d*)\s*[Kk]g",
     "premachined"),
    (r"[Pp]eso\s+sgrossato\s*\(?(?:calcolato)?\)?\s*[:=]\s*(\d+[\.,]?\d*)\s*[Kk]g",
     "premachined"),
    # --- Generico ---
    (r"[Ww]eight\s*[:=]\s*(\d+[\.,]?\d*)\s*[Kk]g", "generic"),
    (r"[Pp]eso\s*[:=]\s*(\d+[\.,]?\d*)\s*[Kk]g", "generic"),
    (r"(\d+[\.,]?\d*)\s*[Kk]g\b", "generic"),
]

# Materiali comuni nei disegni Trillium
MATERIAL_PATTERNS = [
    r"\b(A216[\s\-]?WCB)\b",
    r"\b(A351[\s\-]?CF8M)\b",
    r"\b(A351[\s\-]?CF8)\b",
    r"\b(A351[\s\-]?CF3M)\b",
    r"\b(A351[\s\-]?CA6NM)\b",
    r"\b(A351[\s\-]?CA15)\b",
    r"\b(A182[\s\-]?F\d+)\b",
    r"\b(CF8M|CF8|CF3M|CA6NM|CA15|WCB|CN-7M)\b",
    r"\b(Carbon\s+Steel)\b",
    r"\b(Stainless\s+Steel)\b",
    r"\b(Duplex\s*2205)\b",
    r"\b(Super\s*Duplex\s*2507)\b",
    r"\b(Inconel\s*\d{3})\b",
    r"\b(Monel\s*\d{3})\b",
    r"\b(Hastelloy\s*[A-Z]?\d*)\b",
    r"\b(Bronze)\b",
    r"\b(Titanium)\b",
    r"\b(Cast\s+Iron)\b",
    r"\b(Ductile\s+Iron)\b",
    r"\b(13Cr[\-\s]?4Ni)\b",
    r"\b(SS\s*31[06])\b",
]

# Famiglia pompa
PUMP_FAMILY_PATTERN = re.compile(r"\b(OH[1-6]|BB[1-5]|VS[1-7])\b", re.IGNORECASE)

# Flange rating
FLANGE_PATTERNS = [
    r"(?:class|rating|#)\s*(\d{3,4})",
    r"(\d{3,4})\s*(?:#|class|lb)",
    r"ANSI\s+B16\.5\s+(\d{3,4})\s*(?:LB|#|lb)?",
    r"(\d{3,4})\s*LB\b",
]

# Diametri DN (pollici o mm)
DN_PATTERNS = [
    r"DN\s*(\d+)",
    r"(\d+)\s*[\"\u2033]\s*(?:ANSI|suction|discharge|aspirazione|mandata)",
    r"(?:suction|aspirazione|inlet)\s*[:=]?\s*(?:DN\s*)?(\d+)",
    r"(?:discharge|mandata|outlet)\s*[:=]?\s*(?:DN\s*)?(\d+)",
]

# Componente dal nome file
COMPONENT_MAP = {
    "casing": ["casing", "corpo", "body", "volute"],
    "impeller": ["impeller", "girante", "wheel"],
    "shaft": ["shaft", "albero"],
    "cover": ["cover", "coperchio", "back plate"],
    "bearing": ["bearing", "cuscinetto", "bearing housing", "bearing bracket"],
    "seal": ["seal", "tenuta", "mechanical seal"],
    "baseplate": ["baseplate", "piastra", "base plate", "base"],
    "flange": ["flange", "flangia"],
    "diffuser": ["diffuser", "diffusore"],
    "wear_ring": ["wear ring", "anello usura"],
    "coupling": ["coupling", "giunto"],
}


# ============================================================
# FUNZIONI DI PARSING
# ============================================================

def _parse_weight(text: str) -> list[dict]:
    """Estrae tutti i pesi trovati nel testo con tipo e valore."""
    weights = []
    seen_values = set()

    for pattern, weight_type in WEIGHT_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            value_str = match.group(1).replace(",", ".")
            try:
                value = float(value_str)
                if value > 0 and value < 100000 and value not in seen_values:
                    weights.append({
                        "value_kg": value,
                        "type": weight_type,
                        "raw_match": match.group(0).strip(),
                    })
                    seen_values.add(value)
            except ValueError:
                pass

    # Ordina: finished > premachined > raw > generic
    priority = {"finished": 0, "premachined": 1, "raw": 2, "generic": 3}
    weights.sort(key=lambda w: priority.get(w["type"], 99))
    return weights


def _parse_materials(text: str) -> list[str]:
    """Estrae materiali dal testo."""
    materials = set()
    for pattern in MATERIAL_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            mat = match.group(1).strip()
            if len(mat) >= 2:
                materials.add(mat)
    return sorted(materials)


def _parse_component_type(filename: str) -> str:
    """Identifica il tipo di componente dal nome file."""
    name_lower = filename.lower()
    for comp_type, keywords in COMPONENT_MAP.items():
        for kw in keywords:
            if kw in name_lower:
                return comp_type
    return "unknown"


def _parse_part_number(filename: str) -> tuple[str, str, str]:
    """Estrae part number, revisione e formato dal nome file.

    Returns:
        (part_number, revision, drawing_format)
    """
    base = os.path.splitext(filename)[0]

    # Pattern: XXXX-PARTNUMBER-REVXX-FORMATO
    # Es: MACH.CASING-102A48F30-REV02-A2
    rev_match = re.search(r"REV(\d+)", base, re.IGNORECASE)
    revision = f"REV{rev_match.group(1)}" if rev_match else ""

    format_match = re.search(r"\b(A[0-4])\b", base)
    drawing_format = format_match.group(1) if format_match else ""

    # Part number: sequenza alfanumerica principale (dopo il primo -)
    parts = re.split(r"[-_]", base)
    part_number = ""
    for p in parts:
        # Cerca pattern tipo 102A48F30 o 230A70P20
        if re.match(r"\d{2,3}[A-Z]\d{2,}", p, re.IGNORECASE):
            part_number = p
            break

    return part_number, revision, drawing_format


def _parse_pump_family(text: str) -> str:
    """Estrae la famiglia pompa dal testo."""
    match = PUMP_FAMILY_PATTERN.search(text)
    return match.group(1).upper() if match else ""


def _detect_family_from_path(source: str) -> str:
    """Rileva la famiglia pompa dal percorso cartella (fallback).

    Cerca nomi di cartella come 'OH2 database', 'BB1 drawings', ecc.
    """
    # Normalizza il percorso
    path_parts = source.replace("\\", "/").lower().split("/")
    for part in path_parts:
        match = re.search(r"\b(oh[1-6]|bb[1-5]|vs[1-7])\b", part, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    return ""


def _parse_flange_rating(text: str) -> Optional[int]:
    """Estrae il rating flange dal testo."""
    valid_ratings = {150, 300, 600, 900, 1500, 2500}
    for pattern in FLANGE_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            try:
                rating = int(match.group(1))
                if rating in valid_ratings:
                    return rating
            except ValueError:
                pass
    return None


def _parse_dimensions(text: str) -> dict:
    """Estrae dimensioni (DN aspirazione, DN mandata, diametri)."""
    dims = {}
    for pattern in DN_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            try:
                val = int(match.group(1))
                context = match.group(0).lower()
                if any(k in context for k in ["suction", "aspirazione", "inlet"]):
                    dims["DN_suction"] = val
                elif any(k in context for k in ["discharge", "mandata", "outlet"]):
                    dims["DN_discharge"] = val
                elif "DN" not in str(dims):
                    dims.setdefault("DN_generic", []).append(val)
            except ValueError:
                pass
    return dims


# ============================================================
# ESTRAZIONE GEOMETRIE DAI DISEGNI
# ============================================================

def _parse_impeller_geometry(text: str) -> dict:
    """Estrae D2, b2, spessore dischi dalla girante.

    Cerca pattern come:
    - D2=350, D2 350, Ø350, diametro 350
    - b2=32, b2 32, larghezza 32
    - spessore disco 5, disc thickness 5
    """
    geom = {}

    # D2 - diametro esterno girante
    d2_patterns = [
        r'D2\s*[=:]\s*(\d+(?:\.\d+)?)',
        r'D\s*2\s*[=:]\s*(\d+(?:\.\d+)?)',
        r'(?:impeller|girante)\s+(?:diameter|diametro)\s*[=:]\s*(\d+(?:\.\d+)?)',
        r'(?:outer|esterno)\s+(?:diameter|diametro)\s*[=:]\s*(\d+(?:\.\d+)?)',
        r'Ø\s*(\d{2,4}(?:\.\d+)?)\s*(?:mm)?',
    ]
    for pat in d2_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            if 50 <= val <= 2000:  # Plausibile per girante
                geom["d2_mm"] = val
                break

    # b2 - larghezza uscita girante
    b2_patterns = [
        r'b2\s*[=:]\s*(\d+(?:\.\d+)?)',
        r'b\s*2\s*[=:]\s*(\d+(?:\.\d+)?)',
        r'(?:outlet|uscita)\s+(?:width|larghezza)\s*[=:]\s*(\d+(?:\.\d+)?)',
    ]
    for pat in b2_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            if 5 <= val <= 500:
                geom["b2_mm"] = val
                break

    # Spessore disco
    thick_patterns = [
        r'(?:disc|disco)\s+(?:thickness|spessore)\s*[=:]\s*(\d+(?:\.\d+)?)',
        r'(?:spessore)\s+(?:disc[oh]i?)\s*[=:]\s*(\d+(?:\.\d+)?)',
        r'(?:thickness|spessore)\s*[=:]\s*(\d+(?:\.\d+)?)\s*mm',
    ]
    for pat in thick_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            if 2 <= val <= 50:
                geom["disc_thickness_mm"] = val
                break

    return geom


def _parse_casing_geometry(text: str) -> dict:
    """Estrae geometria corpo pompa OH2.

    Cerca:
    - DN flange (aspirazione/mandata)
    - Diametro interno minimo
    - Larghezza voluta
    - Diametro A (SOP-569)
    """
    geom = {}

    # Diametro interno corpo
    int_diam_patterns = [
        r'(?:internal|interno)\s+(?:diameter|diametro)\s*[=:]\s*(\d+(?:\.\d+)?)',
        r'(?:bore|alesaggio)\s*[=:]\s*(\d+(?:\.\d+)?)',
        r'D\s*i\s*[=:]\s*(\d+(?:\.\d+)?)',
    ]
    for pat in int_diam_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            if 50 <= val <= 2000:
                geom["internal_diameter_mm"] = val
                break

    # Larghezza voluta
    volute_patterns = [
        r'(?:volute|voluta)\s+(?:width|larghezza)\s*[=:]\s*(\d+(?:\.\d+)?)',
        r'(?:larghezza)\s+(?:voluta)\s*[=:]\s*(\d+(?:\.\d+)?)',
    ]
    for pat in volute_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            if 10 <= val <= 1000:
                geom["volute_width_mm"] = val
                break

    # Diametro A (SOP-569)
    dia_a_patterns = [
        r'(?:diameter|diametro)\s+A\s*[=:]\s*(\d+(?:\.\d+)?)',
        r'Diam\.?\s*A\s*[=:]\s*(\d+(?:\.\d+)?)',
    ]
    for pat in dia_a_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            if 50 <= val <= 3000:
                geom["diameter_a_mm"] = val
                break

    return geom


def _classify_drawing_component(text: str, filename: str) -> str:
    """Classifica il disegno come impeller/casing/cover/shaft/baseplate/other.

    Usa sia il testo OCR che il filename per determinare il tipo.
    """
    combined = (text[:2000] + " " + filename).lower()

    # Ordine di priorità
    component_keywords = {
        "impeller": ["impeller", "girante", "giranti"],
        "casing": ["casing", "corpo pompa", "corpo grezzo", "pump body", "voluta",
                    "case", "barrel"],
        "cover": ["cover", "coperchio", "back plate", "back-plate", "head cover"],
        "shaft": ["shaft", "albero", "albero pompa"],
        "baseplate": ["baseplate", "basamento", "base plate", "frame", "support",
                       "supporto"],
        "wear_ring": ["wear ring", "anello usura", "anello di usura"],
        "seal": ["seal", "tenuta", "mechanical seal"],
        "bearing_housing": ["bearing housing", "supporto cuscinetti",
                            "cuscinetteria"],
    }

    for comp_type, keywords in component_keywords.items():
        if any(kw in combined for kw in keywords):
            return comp_type

    return "unknown"


# ============================================================
# FUNZIONE PRINCIPALE
# ============================================================

def extract_pump_data(text: str, source: str = "") -> dict:
    """Estrae dati strutturati pompa dal testo di un documento indicizzato.

    Args:
        text: Testo completo del documento (tutti i chunk uniti)
        source: Percorso sorgente del file

    Returns:
        Dict con tutti i dati estratti
    """
    filename = os.path.basename(source) if source else ""

    # Estrai dati base
    weights = _parse_weight(text)
    materials = _parse_materials(text)
    component = _parse_component_type(filename)
    part_number, revision, drawing_format = _parse_part_number(filename)
    pump_family = _parse_pump_family(text)

    # Fallback: rileva famiglia dalla cartella sorgente
    if not pump_family and source:
        pump_family = _detect_family_from_path(source)
    flange_rating = _parse_flange_rating(text)
    dimensions = _parse_dimensions(text)

    # Estrai geometrie specifiche
    impeller_geom = _parse_impeller_geometry(text)
    casing_geom = _parse_casing_geometry(text)
    drawing_component = _classify_drawing_component(text, filename)

    # Peso principale (il primo, che ha priorita finished > raw > generic)
    main_weight = weights[0] if weights else None

    # Calcola confidenza
    confidence = _compute_confidence(
        has_weight=bool(main_weight),
        has_material=bool(materials),
        has_part_number=bool(part_number),
        has_component=component != "unknown",
        has_family=bool(pump_family),
        text_length=len(text),
    )

    result = {
        "source": source,
        "filename": filename,
        "component_type": component,
        "drawing_component": drawing_component,
        "part_number": part_number,
        "revision": revision,
        "drawing_format": drawing_format,
        "pump_family": pump_family,
        "weight_kg": main_weight["value_kg"] if main_weight else None,
        "weight_type": main_weight["type"] if main_weight else None,
        "weight_raw_match": main_weight["raw_match"] if main_weight else None,
        "all_weights": weights,
        "materials": materials,
        "material_primary": materials[0] if materials else None,
        "flange_rating": flange_rating,
        "dimensions": dimensions,
        # Geometrie girante
        "d2_mm": impeller_geom.get("d2_mm"),
        "b2_mm": impeller_geom.get("b2_mm"),
        "disc_thickness_mm": impeller_geom.get("disc_thickness_mm"),
        # Geometrie corpo
        "internal_diameter_mm": casing_geom.get("internal_diameter_mm"),
        "volute_width_mm": casing_geom.get("volute_width_mm"),
        "diameter_a_mm": casing_geom.get("diameter_a_mm"),
        # DN dalle dimensioni esistenti
        "dn_suction_mm": dimensions.get("DN_suction"),
        "dn_discharge_mm": dimensions.get("DN_discharge"),
        # Confidenza
        "confidence": confidence,
        "text_length": len(text),
    }

    logger.debug("Pump data extracted from %s: weight=%s, component=%s, drawing=%s, conf=%.2f",
                 filename, result["weight_kg"], component, drawing_component, confidence)

    return result


def _compute_confidence(has_weight, has_material, has_part_number,
                        has_component, has_family, text_length) -> float:
    """Calcola un punteggio di confidenza 0.0-1.0 per l'estrazione."""
    score = 0.0

    if has_weight:
        score += 0.35
    if has_material:
        score += 0.15
    if has_part_number:
        score += 0.15
    if has_component:
        score += 0.15
    if has_family:
        score += 0.10
    if text_length > 500:
        score += 0.05
    if text_length > 2000:
        score += 0.05

    return min(score, 1.0)

"""
Trillium V2 — AI Document Enrichment
Arricchisce ogni documento indicizzato con metadati strutturati
estratti automaticamente tramite AI. I metadati vengono salvati
come payload in Qdrant per consentire ricerche filtrate.
"""

import json
import os
import logging
import re
import sys
from typing import Optional

logger = logging.getLogger(__name__)

# Aggiungi il percorso padre per import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================
# CACHE RISULTATI (evita re-analisi)
# ============================================================

_CACHE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    ".enrichment_cache.json"
)


def _load_cache() -> dict:
    if os.path.exists(_CACHE_FILE):
        try:
            with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_cache(cache: dict):
    try:
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Errore salvataggio cache enrichment: {e}")


# ============================================================
# ENRICHMENT RAPIDO (regex + heuristic, no LLM call)
# ============================================================

def enrich_fast(text: str, source: str = "") -> dict:
    """
    Arricchimento RAPIDO basato su regex e heuristic.
    Non chiama l'LLM, quindi è gratuito e veloce.
    Viene eseguito per OGNI documento durante l'indicizzazione.

    Returns:
        dict con metadati strutturati da aggiungere al payload Qdrant
    """
    meta = {}
    filename = os.path.basename(source).lower() if source else ""

    # --- Tipo documento ---
    meta["doc_type"] = _detect_doc_type(text, filename)

    # --- Famiglia pompa ---
    pump_family = _extract_pump_family(text, filename)
    if pump_family:
        meta["pump_family"] = pump_family

    # --- Materiali ---
    materials = _extract_materials(text)
    if materials:
        meta["materials"] = list(materials)[:10]  # Max 10

    # --- Pesi ---
    weights = _extract_weights(text)
    if weights:
        meta["has_weight"] = True
        meta["max_weight_kg"] = max(w for w, _ in weights)
        meta["weight_count"] = len(weights)
    else:
        meta["has_weight"] = False

    # --- Rating flange ---
    rating = _extract_flange_rating(text)
    if rating:
        meta["flange_rating"] = rating

    # --- Normative citate ---
    standards = _extract_standards(text)
    if standards:
        meta["standards"] = list(standards)[:10]

    # --- Dimensioni (DN) ---
    dimensions = _extract_dimensions(text)
    if dimensions:
        meta["dimensions"] = dimensions

    # --- Part number dal nome file ---
    part_info = _extract_part_number(filename)
    if part_info:
        meta.update(part_info)

    # --- Ha tabella BOM? (heuristic) ---
    meta["has_bom"] = _has_bom_indicators(text)

    return meta


# ============================================================
# ENRICHMENT COMPLETO CON AI
# ============================================================

def enrich_ai(text: str, source: str = "", force: bool = False) -> dict:
    """
    Arricchimento COMPLETO con AI (GPT-4o/Claude).
    Combina enrichment rapido + AI Parts List Extraction.
    Usa cache per evitare re-analisi.

    Args:
        text: Testo completo del documento
        source: Percorso sorgente
        force: Se True, ignora la cache

    Returns:
        dict con metadati strutturati completi
    """
    # Controlla cache
    if not force:
        cache = _load_cache()
        cache_key = source or hash(text[:500])
        if str(cache_key) in cache:
            return cache[str(cache_key)]

    # Step 1: Enrichment rapido (sempre)
    meta = enrich_fast(text, source)

    # Step 2: AI extraction (solo se il documento è significativo)
    if len(text) >= 100 and meta.get("has_bom") or meta.get("has_weight"):
        try:
            from weight_engine.parts_list_extractor import extract_parts_list_ai
            ai_result = extract_parts_list_ai(text, source)

            if ai_result and ai_result.get("components"):
                # Aggiungi dati AI al metadata
                meta["ai_components_count"] = len(ai_result["components"])
                meta["ai_quality_score"] = ai_result.get("quality_score", 0)

                # Sovrascrivi con dati AI se più precisi
                if ai_result.get("pump_family"):
                    meta["pump_family"] = ai_result["pump_family"]
                if ai_result.get("document_type"):
                    meta["doc_type"] = ai_result["document_type"]
                if ai_result.get("flange_rating"):
                    meta["flange_rating"] = ai_result["flange_rating"]
                if ai_result.get("total_weight_kg"):
                    meta["total_weight_kg"] = ai_result["total_weight_kg"]
                if ai_result.get("standards_cited"):
                    meta["standards"] = ai_result["standards_cited"]
                if ai_result.get("design_pressure_bar"):
                    meta["design_pressure_bar"] = ai_result["design_pressure_bar"]
                if ai_result.get("design_temperature_c"):
                    meta["design_temperature_c"] = ai_result["design_temperature_c"]
                if ai_result.get("project_number"):
                    meta["project_number"] = ai_result["project_number"]

                # Estrai materiali dai componenti AI
                ai_materials = set()
                for comp in ai_result["components"]:
                    mat = comp.get("material", "")
                    if mat and mat != "N/A":
                        ai_materials.add(mat)
                if ai_materials:
                    existing = set(meta.get("materials", []))
                    meta["materials"] = list(existing | ai_materials)[:15]

                # Peso max dai componenti AI
                ai_weights = [c["weight_kg"] for c in ai_result["components"]
                              if c.get("weight_kg") and isinstance(c["weight_kg"], (int, float))]
                if ai_weights:
                    meta["max_weight_kg"] = max(ai_weights)
                    meta["weight_count"] = len(ai_weights)
                    meta["has_weight"] = True

                meta["ai_enriched"] = True
            else:
                meta["ai_enriched"] = False

        except Exception as e:
            logger.warning(f"AI enrichment fallito per {source}: {e}")
            meta["ai_enriched"] = False
    else:
        meta["ai_enriched"] = False

    # Salva in cache
    cache = _load_cache()
    cache_key = source or str(hash(text[:500]))
    cache[str(cache_key)] = meta
    _save_cache(cache)

    return meta


# ============================================================
# REGEX EXTRACTORS
# ============================================================

def _detect_doc_type(text: str, filename: str) -> str:
    """Classifica il tipo di documento."""
    text_lower = text[:3000].lower()
    fn = filename.lower()

    if "parts list" in text_lower or "bill of material" in text_lower or "b.o.m" in text_lower:
        return "parts_list"
    if "general arrangement" in text_lower or fn.startswith("ga") or "g.a." in text_lower:
        return "general_arrangement"
    if "cross section" in text_lower or "sezione" in text_lower:
        return "cross_section"
    if "datasheet" in text_lower or "data sheet" in text_lower:
        return "datasheet"
    if fn.startswith("sop") or "standard operating" in text_lower:
        return "procedure"
    if fn.startswith("mod.") or fn.startswith("mod "):
        return "calculation"
    if "api 610" in text_lower or "asme" in text_lower or "standard" in fn:
        return "standard"
    if "specification" in text_lower or "specifica" in text_lower:
        return "specification"
    if any(ext in fn for ext in [".tif", ".tiff", ".bmp", ".png"]):
        return "drawing"
    return "other"


def _extract_pump_family(text: str, filename: str) -> Optional[str]:
    """Estrae la famiglia pompa."""
    patterns = [
        r"\b(OH[1-5])\b",
        r"\b(BB[1-5])\b",
        r"\b(VS[1-7])\b",
    ]
    for pat in patterns:
        m = re.search(pat, text[:5000], re.IGNORECASE)
        if m:
            return m.group(1).upper()
    # Prova nel nome file
    for pat in patterns:
        m = re.search(pat, filename, re.IGNORECASE)
        if m:
            return m.group(1).upper()
    return None


_MATERIAL_PATTERNS = [
    r"\b(A216[\s\-]?WCB)\b",
    r"\b(A351[\s\-]?CF8M)\b",
    r"\b(A351[\s\-]?CF8)\b",
    r"\b(A351[\s\-]?CF3M)\b",
    r"\b(A351[\s\-]?CA6NM)\b",
    r"\b(A351[\s\-]?CA15)\b",
    r"\b(A890[\s\-]?(?:4A|5A|6A))\b",
    r"\b(A995[\s\-]?(?:4A|5A|6A))\b",
    r"\b(AISI[\s\-]?\d{3,4}[A-Z]?)\b",
    r"\b(Inconel[\s\-]?\d+)\b",
    r"\b(Monel[\s\-]?\d+)\b",
    r"\b(Hastelloy[\s\-]?[A-Z]\d*)\b",
    r"\bDuplex\b",
    r"\bSuper\s?Duplex\b",
    r"\b(Carbon\s+Steel)\b",
    r"\b(Stainless\s+Steel)\b",
    r"\b(Cast\s+Iron)\b",
]


def _extract_materials(text: str) -> set:
    """Estrae materiali dal testo."""
    materials = set()
    for pat in _MATERIAL_PATTERNS:
        for m in re.finditer(pat, text, re.IGNORECASE):
            materials.add(m.group(0).strip())
    return materials


def _extract_weights(text: str) -> list:
    """Estrae tutti i pesi in kg trovati nel testo."""
    weights = []
    patterns = [
        (r"(\d+[.,]?\d*)\s*[Kk][Gg]\b", "kg"),
        (r"[Ww]eight\s*[:=]\s*(\d+[.,]?\d*)\s*[Kk][Gg]", "kg"),
        (r"[Pp]eso\s*[:=]\s*(\d+[.,]?\d*)\s*[Kk][Gg]", "kg"),
        (r"(\d+[.,]?\d*)\s*[Ll][Bb][Ss]?\b", "lbs"),
    ]
    for pattern, unit in patterns:
        for m in re.finditer(pattern, text):
            try:
                val = float(m.group(1).replace(",", "."))
                if unit == "lbs":
                    val *= 0.4536
                if 0.1 <= val <= 100000:  # Range ragionevole
                    weights.append((round(val, 2), unit))
            except (ValueError, TypeError):
                pass
    return weights


def _extract_flange_rating(text: str) -> Optional[int]:
    """Estrae il rating flange."""
    patterns = [
        r"[Cc]lass\s*(\d+)",
        r"#\s*(\d+)",
        r"ANSI\s*(\d+)",
        r"[Rr]ating\s*[:=]?\s*(\d+)",
    ]
    valid_ratings = {150, 300, 600, 900, 1500, 2500}
    for pat in patterns:
        for m in re.finditer(pat, text[:5000]):
            try:
                val = int(m.group(1))
                if val in valid_ratings:
                    return val
            except (ValueError, TypeError):
                pass
    return None


def _extract_standards(text: str) -> set:
    """Estrae normative citate."""
    standards = set()
    patterns = [
        r"\b(API\s*6\d{2})\b",
        r"\b(ASME\s*B\d+\.\d+)\b",
        r"\b(EN\s*\d{4,5})\b",
        r"\b(ISO\s*\d{4,5})\b",
        r"\b(NACE\s*MR\d+)\b",
        r"\b(ATEX\b)",
        r"\b(PED\s*\d+/\d+)\b",
    ]
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            standards.add(m.group(0).strip().upper())
    return standards


def _extract_dimensions(text: str) -> dict:
    """Estrae dimensioni principali."""
    dims = {}
    # DN aspirazione/mandata
    m = re.search(r"(?:suction|aspirazione|inlet)\s*[:=]?\s*(?:DN\s*)?(\d+)", text, re.IGNORECASE)
    if m:
        dims["suction_dn"] = int(m.group(1))
    m = re.search(r"(?:discharge|mandata|outlet)\s*[:=]?\s*(?:DN\s*)?(\d+)", text, re.IGNORECASE)
    if m:
        dims["discharge_dn"] = int(m.group(1))
    return dims


def _extract_part_number(filename: str) -> dict:
    """Estrae part number e revisione dal nome file."""
    result = {}

    # Part number (es. "100AP40-xxxx", "PL-xxxx", "GA-xxx")
    m = re.search(r"(\d{2,4}[A-Z]{1,3}\d{1,4})", filename, re.IGNORECASE)
    if m:
        result["part_number"] = m.group(1).upper()

    # Revisione
    m = re.search(r"[Rr]ev\.?\s*(\d+|[A-Z])", filename)
    if m:
        result["revision"] = m.group(1)

    return result


def _has_bom_indicators(text: str) -> bool:
    """Verifica se il testo sembra contenere una BOM/Parts List."""
    text_lower = text[:5000].lower()
    indicators = [
        "parts list", "bill of material", "bom", "b.o.m",
        "item | ", "item no", "part no", "part number",
        "peso | ", "weight |", "material |",
        "qty", "quantity", "quantità",
        "casing", "impeller", "shaft", "bearing", "seal",
    ]
    count = sum(1 for ind in indicators if ind in text_lower)
    return count >= 3


# ============================================================
# UTILITY PER METADATA QDRANT
# ============================================================

def metadata_for_qdrant(enrichment: dict) -> dict:
    """
    Converte i metadati arricchiti in formato compatibile con il payload Qdrant.
    Qdrant accetta solo tipi primitivi, liste di primitivi, e dict flat.
    """
    safe_meta = {}
    for key, value in enrichment.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            safe_meta[key] = value
        elif isinstance(value, list):
            # Converti lista in stringa se contiene non-primitivi
            if all(isinstance(v, (str, int, float)) for v in value):
                safe_meta[key] = value
            else:
                safe_meta[key] = json.dumps(value, ensure_ascii=False)
        elif isinstance(value, dict):
            # Flatten dict semplice
            for k2, v2 in value.items():
                if isinstance(v2, (str, int, float, bool)):
                    safe_meta[f"{key}_{k2}"] = v2
        # Ignora tipi non supportati
    return safe_meta

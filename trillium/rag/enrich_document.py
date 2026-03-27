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

    # --- Pesi finish/raw (specifico disegni TPI) ---
    finish_raw = _extract_finish_raw_weight(text)
    if finish_raw:
        meta.update(finish_raw)
        if not meta.get("has_weight"):
            meta["has_weight"] = True

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

    # --- Pump size designation (es. "250 AP 63") ---
    pump_size = _extract_pump_size(text, filename)
    if pump_size:
        meta.update(pump_size)

    # --- Tipo componente dal cartiglio ---
    comp_type = _extract_component_type(text)
    if comp_type:
        meta["component_type"] = comp_type

    # --- Estrazione dati specifici per componente (Vision AI + regex) ---
    # Solo per file immagine (TIF, PNG, ecc.) — usa GPT-4o per estrarre
    # peso finito, diametri, numero pale, ecc. in base al tipo componente
    ext = os.path.splitext(source)[1].lower() if source else ""
    if ext in (".tif", ".tiff", ".png", ".jpg", ".jpeg", ".bmp") and os.path.isfile(source):
        try:
            from rag.extractors import extract_component_data
            comp_data = extract_component_data(
                image_path=source,
                ocr_text=text,
                component_type=comp_type or "",
                source_filename=filename,
            )
            if comp_data:
                # Merge: i dati componente hanno priorità (Vision AI > regex)
                for k, v in comp_data.items():
                    if v is not None and v != "" and k != "component_type":
                        meta[k] = v
                # Aggiorna component_type se rilevato
                if comp_data.get("component_type") and not comp_type:
                    meta["component_type"] = comp_data["component_type"]
                logger.info(f"Estratti {len(comp_data)} campi componente per {filename}")
        except Exception as e:
            logger.warning(f"Errore estrazione componente per {filename}: {e}")

    # --- Nozzle sizes (DN aspirazione/mandata da cartiglio) ---
    nozzles = _extract_nozzle_sizes(text)
    if nozzles:
        meta.update(nozzles)

    # --- D2 diametro girante ---
    d2 = _extract_d2(text)
    if d2:
        meta["d2_mm"] = d2

    # --- Nq velocità specifica ---
    nq_val = _extract_nq(text)
    if nq_val:
        meta["nq"] = nq_val

    # --- Bolt pattern (fori, filettature) ---
    bolts = _extract_bolt_pattern(text)
    if bolts:
        meta["bolt_patterns"] = bolts

    # --- Flange DN (diametro nominale) ---
    flange_dn = _extract_flange_dn(text)
    if flange_dn:
        meta["flange_dn"] = flange_dn

    # --- Sezioni e viste ---
    sections = _extract_sections(text)
    if sections:
        meta.update(sections)

    # --- Documenti collegati (referenced part numbers) ---
    ref_docs = _extract_referenced_docs(text)
    if ref_docs:
        meta["referenced_docs"] = ref_docs

    # --- Connessioni ausiliarie (con REF A, B, C, D, E) ---
    aux_conn = _extract_aux_connections(text)
    if aux_conn:
        meta["aux_connections"] = aux_conn

    # --- Flange face type (RF, FF, RTJ) ---
    ff_type = _extract_flange_face_type(text)
    if ff_type:
        meta["flange_face_type"] = ff_type

    # --- Alt. Sol. (soluzione alternativa lavorazione) ---
    alt_sol = _extract_alt_solution(text)
    if alt_sol:
        meta["alt_solution"] = alt_sol

    # --- F.F.F.T. (Flange Face Finish Type code) ---
    ffft = _extract_ffft(text)
    if ffft:
        meta["ffft"] = ffft

    # --- Scala disegno ---
    scale = _extract_drawing_scale(text)
    if scale:
        meta["drawing_scale"] = scale

    # --- Rugosità superficiale (Ra) ---
    roughness = _extract_surface_roughness(text)
    if roughness:
        meta["surface_roughness"] = roughness

    # --- Classe cuscinetto ---
    bearings = _extract_bearing_class(text)
    if bearings:
        meta["bearing_classes"] = bearings

    # --- Tipo tenuta ---
    seal = _extract_seal_type(text)
    if seal:
        meta["seal_type"] = seal

    # --- Data disegno ---
    draw_date = _extract_drawing_date(text)
    if draw_date:
        meta["drawing_date"] = draw_date

    # --- Descrizione disegno ---
    draw_desc = _extract_drawing_description(text)
    if draw_desc:
        meta["drawing_description"] = draw_desc

    # --- Formato foglio (A2, A1, A0, ecc.) ---
    draw_fmt = _extract_drawing_format(text)
    if draw_fmt:
        meta["drawing_format"] = draw_fmt

    # --- Tolleranze generali ---
    gen_tol = _extract_general_tolerances(text)
    if gen_tol:
        meta["general_tolerances"] = gen_tol

    # --- Fabbricante ---
    manuf = _extract_manufacturer(text)
    if manuf:
        meta["manufacturer"] = manuf

    # --- Part number pre-lavorato ---
    pre_pn = _extract_pre_machined_pn(text)
    if pre_pn:
        meta["pre_machined_pn"] = pre_pn

    # --- BOM strutturata ---
    bom = _extract_bom_structured(text)
    if bom:
        meta["bom_items"] = bom
        meta["bom_count"] = len(bom)

    # --- OCR quality score ---
    meta["ocr_quality_score"] = _calc_ocr_quality_score(meta, text)

    # --- AI interpretation del cartiglio (riempie campi mancanti) ---
    ai_fields = _ai_extract_title_block(text)
    if ai_fields:
        # Sovrascrive SOLO i campi non ancora trovati da regex
        for key, val in ai_fields.items():
            if val and key not in meta:
                meta[key] = val
            elif val and key == "drawing_description" and key not in meta:
                meta[key] = val

    return meta


# ============================================================
# AI TITLE BLOCK EXTRACTION (interpreta testo OCR con OpenAI)
# ============================================================

_TITLE_BLOCK_PROMPT = """Sei un esperto di disegni tecnici di pompe centrifughe.
Hai ricevuto il testo OCR estratto da un disegno tecnico. Il testo potrebbe avere errori, caratteri mancanti o parole frammentate.

Analizza il testo e estrai i seguenti campi dal CARTIGLIO (title block) del disegno.
Rispondi SOLO con un JSON valido, senza commenti né markdown. Se un campo non è presente, usa null.

Campi da estrarre:
{
  "drawing_description": "descrizione del componente (es. 'Finish Machined Volute Casing (ANSI 300)', 'Impeller Nut')",
  "drawing_description_it": "descrizione italiana (es. 'Corpo pompa lavorato', 'Dado Bloccaggio Girante')",
  "component_type": "tipo componente in inglese minuscolo (volute_casing, impeller, shaft, cover, bearing_housing, impeller_nut, shaft_sleeve, seal, wear_ring, gasket, key, nut, flange, etc.)",
  "pump_size": "designazione pompa (es. '250 AP 63', '300 AP 50')",
  "drawing_number": "numero disegno completo (es. '102A70F30', '922A72F10')",
  "drawing_scale": "scala (es. '1:1', '1:5')",
  "drawing_format": "formato foglio (A0, A1, A2, A3, A4)",
  "drawing_date": "data più recente in formato DD.MM.YYYY",
  "revision": "ultima revisione (es. '00', '01', '02')",
  "manufacturer": "nome fabbricante (es. 'TMP S.p.A.')",
  "general_tolerances": "norma tolleranze (es. 'ISO 2768-mK')",
  "flange_face_type": "tipo finitura flangia (RF, FF, RTJ, Stock Finish, Spiral Serrated, etc.)",
  "material_description": "descrizione materiale se presente",
  "weight_kg": peso in kg se presente (solo numero),
  "alt_solution": "codice Alt. Sol. se presente"
}"""


def _ai_extract_title_block(text: str) -> Optional[dict]:
    """
    Usa OpenAI per interpretare il testo OCR e estrarre dati strutturati
    dal cartiglio. Complementa i regex extractors riempendo i campi mancanti.
    """
    if not text or len(text) < 50:
        return None

    try:
        from config import OPENAI_API_KEY
        from rag.extractor import get_openai_client
    except ImportError:
        return None

    if not OPENAI_API_KEY:
        return None

    try:
        client = get_openai_client()

        # Manda solo gli ultimi 3000 chars (dove di solito c'è il cartiglio)
        # più i primi 500 (dove possono esserci note generali)
        text_sample = text[:500] + "\n...\n" + text[-3000:]

        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Veloce e economico
            messages=[
                {"role": "system", "content": _TITLE_BLOCK_PROMPT},
                {"role": "user", "content": f"Testo OCR dal disegno tecnico:\n\n{text_sample}"}
            ],
            temperature=0.0,
            max_tokens=500,
        )

        raw = response.choices[0].message.content.strip()
        # Pulizia: rimuovi eventuale markdown wrapping
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        data = json.loads(raw)

        # Mappa i campi AI → campi meta
        result = {}
        if data.get("drawing_description"):
            result["drawing_description"] = data["drawing_description"]
        if data.get("drawing_description_it"):
            result["drawing_description_it"] = data["drawing_description_it"]
        if data.get("component_type"):
            result["component_type"] = data["component_type"]
        if data.get("pump_size"):
            result["pump_size"] = data["pump_size"]
        if data.get("drawing_scale"):
            result["drawing_scale"] = data["drawing_scale"]
        if data.get("drawing_format"):
            result["drawing_format"] = data["drawing_format"]
        if data.get("drawing_date"):
            result["drawing_date"] = data["drawing_date"]
        if data.get("manufacturer"):
            result["manufacturer"] = data["manufacturer"]
        if data.get("general_tolerances"):
            result["general_tolerances"] = data["general_tolerances"]
        if data.get("flange_face_type"):
            result["flange_face_type"] = data["flange_face_type"]
        if data.get("material_description"):
            result["material_description"] = data["material_description"]
        if data.get("alt_solution"):
            result["alt_solution"] = data["alt_solution"]

        logger.info("AI title block: %d campi estratti", len(result))
        return result if result else None

    except json.JSONDecodeError as e:
        logger.warning("AI title block: JSON non valido: %s", str(e)[:100])
        return None
    except Exception as e:
        logger.warning("AI title block: errore %s", str(e)[:100])
        return None


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
# EXTRACTORS PERFORMANCE / DISEGNI TECNICI
# ============================================================

def _extract_pump_size(text: str, filename: str) -> dict:
    """
    Estrae la designazione dimensionale della pompa (es. '250 AP 63').
    Formato TPI: NNN AP NN dove NNN=DN mandata, NN=diametro girante (pollici).
    Anche: 8x6x13, 6x4x10, ecc.
    """
    result = {}

    # Formato TPI: "250 AP 63" o "250AP63" o "250 AP 63 /B"
    m = re.search(r"(\d{2,4})\s*AP\s*(\d{1,3})\s*(?:[/\\]([A-Z0-9]))?\b", text[:10000], re.IGNORECASE)
    if m:
        result["pump_size"] = f"{m.group(1)} AP {m.group(2)}"
        result["pump_size_dn"] = int(m.group(1))  # DN mandata (mm)
        result["pump_size_impeller"] = int(m.group(2))  # Diametro girante indicativo
        if m.group(3):
            result["pump_size_variant"] = m.group(3)

    # Formato USA: "8x6x13" o "8×6×13" (suction x discharge x impeller)
    if not result:
        m = re.search(r"(\d{1,2})\s*[x×X]\s*(\d{1,2})\s*[x×X]\s*(\d{1,3})", text[:10000])
        if m:
            result["pump_size"] = f"{m.group(1)}x{m.group(2)}x{m.group(3)}"
            result["suction_inch"] = int(m.group(1))
            result["discharge_inch"] = int(m.group(2))
            result["impeller_inch"] = int(m.group(3))

    # Prova anche nel filename
    if not result:
        m = re.search(r"(\d{2,4})\s*AP\s*(\d{1,3})", filename, re.IGNORECASE)
        if m:
            result["pump_size"] = f"{m.group(1)} AP {m.group(2)}"
            result["pump_size_dn"] = int(m.group(1))
            result["pump_size_impeller"] = int(m.group(2))

    return result


def _extract_component_type(text: str) -> Optional[str]:
    """
    Estrae il tipo di componente dal cartiglio del disegno.
    Es: 'Volute Casing', 'Impeller', 'Shaft', 'Bearing Housing'.
    """
    # Cerca nel cartiglio (di solito nelle ultime righe o in blocchi specifici)
    comp_patterns = [
        (r"(?:Volute|Spiral)\s*(?:Casing|Case)", "volute_casing"),
        (r"(?:Upper|Lower|Top|Bottom)?\s*(?:Cas(?:ing|e)|Corpo\s*pompa)", "casing"),
        (r"(?:Case\s*)?Cover|Coperchio", "cover"),
        (r"Impeller\s+Nut|Dado\s+(?:Bloccaggio\s+)?Girante", "impeller_nut"),
        (r"Impeller\s+Key|Chiavetta\s+Girante", "impeller_key"),
        (r"Impeller|Girante", "impeller"),
        (r"Shaft\s+Sleeve|Bussola\s+(?:Albero|Protezione)", "shaft_sleeve"),
        (r"Shaft|Albero", "shaft"),
        (r"Bearing\s*(?:Housing|Bracket)|Supporto\s*cuscinett", "bearing_housing"),
        (r"(?:Mech(?:anical)?\s*)?Seal|Tenuta\s*(?:meccanica)?", "seal"),
        (r"Wear\s*Ring|Anello\s*(?:di\s*)?usura", "wear_ring"),
        (r"Diffuser|Diffusore", "diffuser"),
        (r"Base(?:plate)?|Basamento", "baseplate"),
        (r"Coupling|Giunto", "coupling"),
        (r"Suction\s*(?:Bell|Barrel)|Campana\s*aspira", "suction_bell"),
        (r"Flange|Flangia", "flange"),
        (r"Throttle\s*Bush|Bussola\s*(?:di\s*)?Strozzamento", "throttle_bushing"),
        (r"Balance\s*Dis[ck]|Disco\s*(?:di\s*)?Equilibr", "balance_disc"),
        (r"Balance\s*Drum|Tamburo\s*(?:di\s*)?Equilibr", "balance_drum"),
        (r"Stuffing\s*Box|Premistoppa", "stuffing_box"),
        (r"Pressure\s*Casing|Corpo\s*(?:di\s*)?Pressione", "pressure_casing"),
        (r"Deflector|Deflettore", "deflector"),
        (r"Spacer|Distanziale", "spacer"),
        (r"Gasket|Guarnizione", "gasket"),
        (r"\bNut\b|\bDado\b", "nut"),
        (r"\bKey\b|\bChiavetta\b", "key"),
        (r"\bSleeve\b|\bBussola\b", "sleeve"),
        (r"\bPlug\b|\bTappo\b", "plug"),
        (r"\bRing\b|\bAnello\b", "ring"),
        (r"General\s*Arrangement|G\.?A\.?", "general_arrangement"),
        (r"Cross\s*Section|Sezione", "cross_section"),
    ]
    for pat, comp_name in comp_patterns:
        if re.search(pat, text[:8000], re.IGNORECASE):
            return comp_name
    return None


def _extract_finish_raw_weight(text: str) -> dict:
    """
    Estrae pesi finish (lavorato) e raw (grezzo) dal cartiglio dei disegni TPI.
    Es: 'Finish weight (calculated): 864 kg' / 'Peso finito: 860 kg'
        'Raw casting: 102A70RH3'
    """
    result = {}

    # Finish weight / Peso finito
    patterns_finish = [
        r"[Ff]inish\s*(?:weight|wt)\s*(?:\([^)]*\))?\s*[:=]?\s*(\d+[.,]?\d*)\s*[Kk][Gg]",
        r"[Pp]eso\s*finit[oa]\s*(?:\([^)]*\))?\s*[:=]?\s*(\d+[.,]?\d*)\s*[Kk][Gg]",
        r"[Ff]inished\s*(?:weight|wt)\s*[:=]?\s*(\d+[.,]?\d*)\s*[Kk][Gg]",
        r"[Nn]et\s*(?:weight|wt)\s*[:=]?\s*(\d+[.,]?\d*)\s*[Kk][Gg]",
    ]
    for pat in patterns_finish:
        m = re.search(pat, text)
        if m:
            try:
                result["finish_weight_kg"] = float(m.group(1).replace(",", "."))
            except ValueError:
                pass
            break

    # Raw weight / Peso grezzo
    patterns_raw = [
        r"[Rr]aw\s*(?:weight|wt|casting)?\s*(?:\([^)]*\))?\s*[:=]?\s*(\d+[.,]?\d*)\s*[Kk][Gg]",
        r"[Pp]eso\s*grezzoo?\s*(?:\([^)]*\))?\s*[:=]?\s*(\d+[.,]?\d*)\s*[Kk][Gg]",
        r"[Gg]ross\s*(?:weight|wt)\s*[:=]?\s*(\d+[.,]?\d*)\s*[Kk][Gg]",
    ]
    for pat in patterns_raw:
        m = re.search(pat, text)
        if m:
            try:
                result["raw_weight_kg"] = float(m.group(1).replace(",", "."))
            except ValueError:
                pass
            break

    # Raw casting part number (es. "Grezzo: 102A70RH3")
    m = re.search(r"(?:[Rr]aw\s*casting|[Gg]rezzo)\s*[:=]?\s*([A-Z0-9]{6,})", text)
    if m:
        result["raw_casting_pn"] = m.group(1).upper()

    return result


def _extract_nozzle_sizes(text: str) -> dict:
    """
    Estrae le dimensioni dei bocchelli (nozzle) dal disegno.
    Es: 'DN 10" ANSI B16.5 300 LB', '8" suction', '6" discharge'
    """
    result = {}

    # Pattern: N" ANSI B16.5 NNN LB (tipico cartiglio TPI)
    nozzles = re.findall(r"(?:DN\s*)?(\d{1,2})\"?\s*(?:ANSI|ASME)?\s*(?:B16[.]5)?\s*(\d+)\s*(?:LB|#)",
                         text[:10000], re.IGNORECASE)
    if nozzles:
        sizes = sorted(set(int(n[0]) for n in nozzles), reverse=True)
        if len(sizes) >= 2:
            result["nozzle_suction_inch"] = sizes[0]  # Più grande = aspirazione
            result["nozzle_discharge_inch"] = sizes[1]  # Più piccolo = mandata
        elif len(sizes) == 1:
            result["nozzle_size_inch"] = sizes[0]
        # Rating dal nozzle
        ratings = set(int(n[1]) for n in nozzles)
        valid_ratings = {150, 300, 600, 900, 1500, 2500}
        valid_found = ratings & valid_ratings
        if valid_found:
            result["nozzle_rating"] = max(valid_found)

    # Pattern alternativo: "8x6" o "aspirazione 8" / mandata 6"
    if not result:
        m = re.search(r"(\d{1,2})\s*[x×X]\s*(\d{1,2})\s*(?:inch|pollici|\"|'')", text[:10000], re.IGNORECASE)
        if m:
            result["nozzle_suction_inch"] = int(m.group(1))
            result["nozzle_discharge_inch"] = int(m.group(2))

    return result


def _extract_d2(text: str) -> Optional[float]:
    """
    Estrae il diametro girante D2 dal testo.
    Cerca patterns come: 'D2 = 350', 'D2: 350 mm', 'diametro girante: 350mm',
    'impeller diameter: 13.78"', 'Ø girante 350'
    """
    # Cerca D2 esplicito
    patterns = [
        r"[Dd]2\s*[=:]\s*(\d+[.,]?\d*)\s*(?:mm)?",
        r"[Dd]iametr[oa]\s*(?:della?\s*)?girant[ei]\s*[=:]?\s*(\d+[.,]?\d*)\s*(?:mm)?",
        r"[Ii]mpeller\s*(?:outer\s*)?[Dd]iameter\s*[=:]?\s*(\d+[.,]?\d*)\s*(?:mm)?",
        r"[Øø]\s*(?:girant[ei]|impeller)\s*[=:]?\s*(\d+[.,]?\d*)\s*(?:mm)?",
    ]
    for pat in patterns:
        m = re.search(pat, text[:15000])
        if m:
            try:
                val = float(m.group(1).replace(",", "."))
                if 50 <= val <= 2000:  # Range ragionevole per D2 in mm
                    return val
            except ValueError:
                pass
    return None


def _extract_nq(text: str) -> Optional[float]:
    """
    Estrae la velocità specifica Nq dal testo.
    Cerca patterns come: 'Nq = 30', 'Nq: 45.2', 'Ns = 1200' (convertito)
    """
    # Nq diretto
    m = re.search(r"[Nn][Qq]\s*[=:]\s*(\d+[.,]?\d*)", text[:15000])
    if m:
        try:
            val = float(m.group(1).replace(",", "."))
            if 5 <= val <= 500:  # Range ragionevole
                return val
        except ValueError:
            pass

    # Ns (velocità specifica USA) → Nq ≈ Ns / 51.6
    m = re.search(r"[Nn][Ss]\s*[=:]\s*(\d+[.,]?\d*)", text[:15000])
    if m:
        try:
            ns = float(m.group(1).replace(",", "."))
            if 100 <= ns <= 25000:
                return round(ns / 51.6, 1)
        except ValueError:
            pass

    return None


# ============================================================
# EXTRACTORS AVANZATI — DISEGNI TECNICI
# ============================================================

def _extract_bolt_pattern(text: str) -> Optional[list]:
    """
    Estrae i pattern di bullonatura dal disegno.
    Es: 'N.16 holes Φ32' → [{"count": 16, "diameter": 32, "type": "through"}]
         'N.24 fori M30'  → [{"count": 24, "diameter": 30, "type": "tapped"}]
         'N.4 spot-faces Φ60' → [{"count": 4, "diameter": 60, "type": "spot_face"}]
    """
    patterns = [
        # N.16 EQUALLY-SPACED HOLES Φ32 / N.16 holes Φ32
        (r'N[.\s]*(\d+)\s+(?:EQUALLY[- ]SPACED\s+)?(?:holes?|HOLES?|fori|FORI)\s*[ΦΦ$#]?\s*(\d+)', 'through'),
        # N.16 SPOT-FACES Φ55 / N.4 LAMATURE Φ60
        (r'N[.\s]*(\d+)\s+(?:EQUALLY[- ]SPACED\s+)?(?:SPOT[- ]FACES?|LAMATURE)\s*[ΦΦ$#]?\s*(\d+)', 'spot_face'),
        # N.24 fori M30 (filettatura)
        (r'N[.\s]*(\d+)\s+(?:EQUALLY[- ]SPACED\s+)?(?:holes?|HOLES?|fori|FORI)\s+M(\d+)', 'tapped'),
    ]
    results = []
    seen = set()
    for pattern, bolt_type in patterns:
        for m in re.finditer(pattern, text[:15000], re.IGNORECASE):
            count = int(m.group(1))
            diameter = int(m.group(2))
            key = (count, diameter, bolt_type)
            if key not in seen and 1 <= count <= 100 and 3 <= diameter <= 200:
                seen.add(key)
                results.append(f"N.{count} {bolt_type} Φ{diameter}")
    return results if results else None


def _extract_flange_dn(text: str) -> Optional[str]:
    """
    Estrae il DN (diametro nominale) flangia.
    Es: 'DN 10" ANSI B16.5' → '10"'
        'DN250' → 'DN250'
    """
    # DN 10" o DN 250
    m = re.search(r'DN\s*(\d+)["\s]', text[:15000], re.IGNORECASE)
    if m:
        val = m.group(1)
        return f"DN{val}"
    return None


def _extract_sections(text: str) -> Optional[dict]:
    """
    Conta le sezioni e viste nel disegno.
    Es: 'Section A-A', 'Sezione C-C', 'View from D'
    """
    sections = set()
    views = set()
    # Section A-A / Sezione B-B
    for m in re.finditer(r'(?:Section|Sezione)\s+([A-Z])\s*[-–]\s*\1', text[:15000], re.IGNORECASE):
        sections.add(m.group(1))
    # View from D / Vista da D
    for m in re.finditer(r'(?:View\s+from|Vista\s+da)\s+([A-Z])', text[:15000], re.IGNORECASE):
        views.add(m.group(1))
    result = {}
    if sections:
        result["n_sections"] = len(sections)
        result["section_labels"] = ", ".join(sorted(sections))
    if views:
        result["n_views"] = len(views)
    return result if result else None


def _extract_referenced_docs(text: str) -> Optional[list]:
    """
    Estrae i numeri di disegno/documento referenziati.
    Pattern TPI: 102A70RM3, 102A70P30, 102A70F30
    Formato: NNNANNxy[N] dove NNN=numero, A=lettera, NN=numero, xy=tipo, N=opzionale
    """
    # Pattern per codici TPI (es. 102A70RM3, 102A70P30, 102A70F30)
    refs = set()
    for m in re.finditer(r'\b(\d{2,4}[A-Z]\d{2,3}[A-Z]{1,2}\d{0,2})\b', text[:15000]):
        code = m.group(1)
        if len(code) >= 7:  # Minimo 7 caratteri (es. 102A70P)
            refs.add(code)
    # Pattern per codici disegno standard (es. D260629)
    for m in re.finditer(r'\b(D\d{5,7})\b', text[:15000]):
        refs.add(m.group(1))
    return sorted(refs)[:10] if refs else None


def _extract_aux_connections(text: str) -> Optional[list]:
    """
    Estrae connessioni ausiliarie strutturate dal cartiglio.
    Cerca la tabella con REF (A, B, C, D, E) e i dettagli foro.
    Output: ['REF A: 1/2" NPT', 'REF C: 3/4" S.W.', ...]
    """
    connections = []
    seen = set()

    # Pattern 1: REF lettera + Hole/Foro + dimensione + tipo
    # Es: testo tabellare dove A) Hole 1/2" NPT o simile
    for m in re.finditer(
        r'(?:(?:REF\.?\s*)?([A-E])\s*[)\]]?\s*)?'
        r'(?:Hole|Foro)\s+(\d+/\d+)["\s]*(?:inch|in)?\s*'
        r'(NPT|S\.?W\.?|B\.?W\.?|SW|BW|R\.?F\.?|F\.?F\.?)',
        text[:20000], re.IGNORECASE
    ):
        ref = m.group(1).upper() if m.group(1) else ""
        size = m.group(2)
        conn_type = m.group(3).upper().replace(" ", "")
        # Normalizza tipi
        if conn_type in ("SW", "S.W", "SW."): conn_type = "S.W."
        if conn_type in ("BW", "B.W", "BW."): conn_type = "B.W."
        if conn_type in ("RF", "R.F", "RF."): conn_type = "R.F."
        if conn_type in ("FF", "F.F", "FF."): conn_type = "F.F."

        if ref:
            key = f"REF {ref}: {size}\" {conn_type}"
        else:
            key = f"{size}\" {conn_type}"
        if key not in seen:
            seen.add(key)
            connections.append(key)

    # Pattern 2: sequenza nella tabella connessioni
    # A  1/2"  NPT   B  3/4"  S.W.   C  1/2"  B.W.
    for m in re.finditer(
        r'([A-E])\s+(\d+/\d+)["\s]*(NPT|S\.?W\.?|B\.?W\.?|SW|BW)',
        text[:20000], re.IGNORECASE
    ):
        ref = m.group(1).upper()
        size = m.group(2)
        conn_type = m.group(3).upper().replace(" ", "")
        if conn_type in ("SW", "S.W", "SW."): conn_type = "S.W."
        if conn_type in ("BW", "B.W", "BW."): conn_type = "B.W."
        key = f"REF {ref}: {size}\" {conn_type}"
        if key not in seen:
            seen.add(key)
            connections.append(key)

    return sorted(connections)[:15] if connections else None


def _extract_flange_face_type(text: str) -> Optional[str]:
    """
    Estrae il tipo di finitura flangia.
    RF = Raised Face, FF = Flat Face, RTJ = Ring Type Joint
    Anche: Stock Finish, Spiral Serrated, Concentric Serrated, Smooth Finish
    """
    patterns = [
        (r'(?:Flange\s+Face|Tipo\s+Finit)[^\n]{0,30}(RF|R\.F\.|Raised\s+Face)', 'RF'),
        (r'(?:Flange\s+Face|Tipo\s+Finit)[^\n]{0,30}(FF|F\.F\.|Flat\s+Face)', 'FF'),
        (r'(?:Flange\s+Face|Tipo\s+Finit)[^\n]{0,30}(RTJ|Ring\s+Type)', 'RTJ'),
        (r'\bRaised\s+Face\b', 'RF'),
        (r'\bFlat\s+Face\b', 'FF'),
        (r'\bRing\s+Type\s+Joint\b', 'RTJ'),
        (r'\bStock\s+Finish\b', 'Stock Finish'),
        (r'\bSpiral\s+Serrated\b', 'Spiral Serrated'),
        (r'\bConcentric\s+Serrated\b', 'Concentric Serrated'),
        (r'\bSmooth\s+Finish\b', 'Smooth Finish'),
        (r'\bCold\s+[Ww]ater\s+Finish\b', 'Cold Water Finish'),
    ]
    # Cerca tutti i tipi trovati
    found = []
    for pattern, face_type in patterns:
        if re.search(pattern, text[:20000], re.IGNORECASE):
            if face_type not in found:
                found.append(face_type)
    if found:
        return ", ".join(found) if len(found) > 1 else found[0]
    return None


def _extract_alt_solution(text: str) -> Optional[str]:
    """
    Estrae il codice Alt. Sol. (Alternative Machining Solution)
    dal Part Identification Code nel cartiglio.
    Il codice è tipicamente 1-4 caratteri alfanumerici (es. 'A', '01', 'B2').
    """
    # Pattern diretto: "Alt. Sol." seguito da codice corto
    m = re.search(
        r'Alt\.?\s*Sol\.?\s*[:\s]+([A-Z0-9]{1,4})\b',
        text[:15000], re.IGNORECASE
    )
    if m:
        val = m.group(1).strip()
        if val and val.upper() not in ('X', 'NA', 'N', 'NONE', 'FFFT', 'SOL'):
            return val
    return None


def _extract_ffft(text: str) -> Optional[str]:
    """
    Estrae il codice F.F.F.T. (Flange Face Finish Type)
    dal cartiglio del disegno.
    """
    m = re.search(
        r'F\.?F\.?F\.?T\.?[^\n]{0,10}[:\s]+(\w+)',
        text[:15000], re.IGNORECASE
    )
    if m:
        val = m.group(1).strip()
        if val and val.upper() not in ('X', 'NA', 'N/A', 'NONE', '-', 'PRIMING', 'MATERIAL', 'SOL', 'ALT'):
            return val
    return None


def _extract_drawing_date(text: str) -> Optional[str]:
    """
    Estrae la data del disegno dal cartiglio.
    Formati: DD.MM.YYYY, DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD
    """
    # DD.MM.YYYY o DD/MM/YYYY
    m = re.search(r'\b(\d{1,2})[./\-](\d{1,2})[./\-]((?:19|20)\d{2})\b', text[:20000])
    if m:
        return f"{m.group(1).zfill(2)}.{m.group(2).zfill(2)}.{m.group(3)}"
    # YYYY-MM-DD
    m = re.search(r'\b((?:19|20)\d{2})[./\-](\d{1,2})[./\-](\d{1,2})\b', text[:20000])
    if m:
        return f"{m.group(3).zfill(2)}.{m.group(2).zfill(2)}.{m.group(1)}"
    return None


def _extract_drawing_description(text: str) -> Optional[str]:
    """
    Estrae la descrizione del disegno dal cartiglio.
    Es: 'Finish Machined Volute Casing (ANSI 300)'
        'Impeller Nut', 'Corpo pompa lavorato (ANSI 300)'
    """
    # Pattern 1: DESCRIZIONE/DESCRIPTION seguito dalla vera descrizione componente
    # Cattura tutto il testo dopo il campo fino a newline o TAVOLA
    m = re.search(
        r'DESCRI[ZS]IONE/DESCRIPTION[\s\n]+(.+?)(?:\n|TAVOLA|$)',
        text[:20000], re.IGNORECASE
    )
    if m:
        desc = m.group(1).strip()
        # Escludi header della tabella (parole chiave delle colonne)
        skip_words = {'COMPILATO', 'COMPILED', 'CONTROLLATO', 'CHECKED',
                      'APPROVATO', 'APPROVED', 'DATA', 'DATE', 'EMISSIONE',
                      'REVISIONE', 'REV'}
        first_word = desc.split()[0].upper() if desc.split() else ''
        if len(desc) > 5 and first_word not in skip_words:
            return desc[:200]

    # Pattern 2: nomi componente espliciti
    for pattern in [
        r'((?:Finish|Raw)\s+(?:Machined\s+)?(?:Volute|Impeller|Shaft|Cover|Bearing|Case|Casing)\s+\w+(?:\s*\([^)]+\))?)',
        r'(Impeller\s+(?:Nut|Key|Sleeve|Ring|Disc)(?:\s*\([^)]+\))?)',
        r'(Shaft\s+(?:Sleeve|Key|Nut|Spacer)(?:\s*\([^)]+\))?)',
        r'((?:Volute|Impeller|Shaft|Cover|Bearing|Seal|Wear)\s+(?:Casing|Housing|Assembly|Ring|Nut|Key|Sleeve)\s*(?:\([^)]+\))?)',
        r'(Corpo\s+pompa\s+\w+(?:\s*\([^)]+\))?)',
        r'(Dado\s+(?:Bloccaggio\s+)?Girante)',
        r'(Bussola\s+(?:Albero|Protezione|Strozzamento))',
        r'(Anello\s+(?:di\s+)?(?:Usura|Tenuta))',
    ]:
        m = re.search(pattern, text[:20000], re.IGNORECASE)
        if m:
            return m.group(1).strip()[:200]
    return None


def _extract_drawing_format(text: str) -> Optional[str]:
    """
    Estrae il formato del foglio (A0, A1, A2, A3, A4).
    """
    # Cerca nel cartiglio: F.to A2 o formato A1, o standalone
    m = re.search(r'(?:F\.?to|Formato|Format)\s*(A[0-4])\b', text[:20000], re.IGNORECASE)
    if m:
        return m.group(1).upper()
    # Pattern: lettera A seguita da numero foglio dopo drawing number
    m = re.search(r'\b(A[0-4])\s*$', text[:20000], re.MULTILINE)
    if m:
        return m.group(1).upper()
    return None


def _extract_general_tolerances(text: str) -> Optional[str]:
    """
    Estrae la norma tolleranze generali.
    Es: 'ISO 2768-mK', 'ISO 2768-fH', 'ISO 8015'
    """
    # ISO 2768 con classe
    m = re.search(r'ISO\s*2768\s*[-–]\s*([a-zA-Z]{1,2}[A-Z]?)', text[:20000])
    if m:
        return f"ISO 2768-{m.group(1)}"
    # Solo ISO 2768
    m = re.search(r'(ISO\s*2768)', text[:20000])
    if m:
        return "ISO 2768"
    # ISO 8015
    if re.search(r'ISO\s*8015', text[:20000]):
        return "ISO 8015"
    return None


def _extract_manufacturer(text: str) -> Optional[str]:
    """
    Estrae il fabbricante dal cartiglio.
    Es: 'TMP S.p.A.', 'Termomeccanica Pompe'
    """
    manufacturers = [
        (r'T\.?M\.?P\.?\s*S\.?p\.?A\.?', 'TMP S.p.A.'),
        (r'Termomeccanica\s+Pompe', 'Termomeccanica Pompe'),
        (r'Flowserve', 'Flowserve'),
        (r'Sulzer', 'Sulzer'),
        (r'KSB', 'KSB'),
        (r'Grundfos', 'Grundfos'),
        (r'Ruhrpumpen', 'Ruhrpumpen'),
    ]
    for pattern, name in manufacturers:
        if re.search(pattern, text[:20000], re.IGNORECASE):
            return name
    return None


def _extract_pre_machined_pn(text: str) -> Optional[str]:
    """
    Estrae il codice del pezzo pre-lavorato / sgrossato.
    Es: 'Pre machined: 102A70P30', 'Sgrossato: 102A70P30'
    """
    m = re.search(
        r'(?:Pre\s*machined|Sgrossato|Semi[- ]?lavorato)\s*[:\s]+(\d{2,4}[A-Z]\d{2,3}[A-Z]{1,3}\d{0,2})',
        text[:20000], re.IGNORECASE
    )
    if m:
        return m.group(1).strip()
    return None


def _extract_drawing_scale(text: str) -> Optional[str]:
    """
    Estrae la scala del disegno.
    Es: 'SCALE 1:5', 'SCALA 1:10', 'Scale: 1/2'
    """
    m = re.search(r'(?:SCALE|SCALA|Scale)[:\s]+\s*(\d+)\s*[:/]\s*(\d+)', text[:15000], re.IGNORECASE)
    if m:
        return f"{m.group(1)}:{m.group(2)}"
    return None


def _extract_surface_roughness(text: str) -> Optional[list]:
    """
    Estrae i valori di rugosità superficiale Ra.
    Es: 'Ra 3.2', '3.2/1.6' (rugosità diverse per superfici),
    'surface finish 0.8', 'finitura 1.6'
    """
    values = set()
    # Ra N.N
    for m in re.finditer(r'Ra\s*(\d+[.,]\d+)', text[:15000], re.IGNORECASE):
        values.add(m.group(1).replace(',', '.'))
    # Pattern N.N/N.N (due rugosità) — comune nei disegni tecnici
    for m in re.finditer(r'\b(\d+[.,]\d)\s*/\s*(\d+[.,]\d)\b', text[:15000]):
        v1 = m.group(1).replace(',', '.')
        v2 = m.group(2).replace(',', '.')
        try:
            f1, f2 = float(v1), float(v2)
            # Valori Ra tipici: 0.1 - 25.0
            if 0.1 <= f1 <= 25.0:
                values.add(v1)
            if 0.1 <= f2 <= 25.0:
                values.add(v2)
        except ValueError:
            pass
    return sorted(values)[:5] if values else None


def _extract_bearing_class(text: str) -> Optional[list]:
    """
    Estrae le classi di cuscinetto dal testo.
    Es: '6305', '7312', '22316', 'NU 316', 'bearing 6312'
    Pattern SKF/FAG: NNNNN o NN NNN
    """
    bearings = set()
    # Pattern cuscinetti radiali: 6NNN, 62NN, 63NN (escludi se preceduto da D → doc number)
    for m in re.finditer(r'(?<!D)(?<!\d)\b(6[0-3]\d{2})\b(?!\d)', text[:15000]):
        bearings.add(m.group(1))
    # Cuscinetti obliqui: 7NNN
    for m in re.finditer(r'\b(7[0-3]\d{2}(?:\.?\d+)?)\b', text[:15000]):
        bearings.add(m.group(1))
    # Cuscinetti a rulli: 22NNN, 23NNN, NU NNN, NJ NNN
    for m in re.finditer(r'\b(2[23]\d{3})\b', text[:15000]):
        bearings.add(m.group(1))
    for m in re.finditer(r'\b(N[UJ]\s*\d{3,4})\b', text[:15000]):
        bearings.add(m.group(1).replace(' ', ''))
    return sorted(bearings)[:5] if bearings else None


def _extract_seal_type(text: str) -> Optional[str]:
    """
    Estrae il tipo di tenuta meccanica.
    Es: 'mechanical seal', 'packing', 'lip seal', 'labyrinth seal'
    """
    text_lower = text[:15000].lower()
    seal_types = [
        ('mechanical seal', 'mechanical_seal'),
        ('tenuta meccanica', 'mechanical_seal'),
        ('packing', 'packing'),
        ('baderna', 'packing'),
        ('lip seal', 'lip_seal'),
        ('labyrinth seal', 'labyrinth'),
        ('tenuta a labirinto', 'labyrinth'),
        ('floating ring', 'floating_ring'),
        ('dry gas seal', 'dry_gas'),
        ('o-ring', 'o_ring'),
    ]
    for pattern, seal_id in seal_types:
        if pattern in text_lower:
            return seal_id
    return None


def _extract_bom_structured(text: str) -> Optional[list]:
    """
    Estrae la Bill of Materials (Parts List) strutturata dal testo OCR.
    Cerca righe con: Item | Part Number | Descrizione | Materiale | Qty
    Pattern: numero item + codice + descrizione
    """
    bom_items = []
    # Pattern: numero item (1-99) seguito da codice alfanumerico e descrizione
    # Es: "1  102A70F30  VOLUTE CASING  A216-WCB  1"
    # Es: "3  102A70P30  IMPELLER  A351-CF8M  1"
    for m in re.finditer(
        r'^\s*(\d{1,2})\s+(\d{2,4}[A-Z]\d{2,3}[A-Z]{1,3}\d{0,2})\s+(.+?)(?:\s+(\d+)\s*$|\s*$)',
        text[:20000], re.MULTILINE
    ):
        item_no = int(m.group(1))
        part_num = m.group(2).strip()
        desc_raw = m.group(3).strip()
        qty = m.group(4) if m.group(4) else "1"
        if 1 <= item_no <= 99 and len(part_num) >= 7:
            # Prova a separare descrizione e materiale
            desc_parts = desc_raw.rsplit("  ", 1)
            if len(desc_parts) == 2:
                description, material = desc_parts[0].strip(), desc_parts[1].strip()
            else:
                description, material = desc_raw, ""
            bom_items.append(f"Item {item_no}: {part_num} - {description}" +
                           (f" [{material}]" if material else "") +
                           f" x{qty}")
    # Pattern alternativo semplice: solo codice + descrizione
    if not bom_items:
        for m in re.finditer(
            r'(\d{2,4}[A-Z]\d{2,3}[A-Z]{1,3}\d{0,2})\s+(VOLUTE|IMPELLER|SHAFT|COVER|CASING|BEARING|RING|SLEEVE|NUT|BOLT|GASKET|KEY|PLUG)',
            text[:20000], re.IGNORECASE
        ):
            part = m.group(1)
            comp = m.group(2).strip()
            entry = f"{part} - {comp}"
            if entry not in bom_items:
                bom_items.append(entry)
    return bom_items[:20] if bom_items else None


def _calc_ocr_quality_score(meta: dict, text: str) -> int:
    """
    Calcola un punteggio di qualità OCR (0-100) basato su quanti
    campi aspettati sono stati estratti con successo.
    """
    # Campi importanti e il loro peso
    checks = [
        ("part_number", 10),       # Part number dal filename
        ("pump_size", 10),         # Designazione pompa
        ("component_type", 10),    # Tipo componente
        ("has_weight", 8),         # Peso trovato
        ("flange_rating", 8),      # Rating flangia
        ("standards", 5),          # Normative
        ("materials", 8),          # Materiali
        ("bolt_patterns", 7),      # Pattern bullonatura
        ("nozzle_size_inch", 7),   # Dimensione bocchelli
        ("aux_connections", 7),    # Connessioni ausiliarie
        ("referenced_docs", 5),    # Documenti collegati
        ("n_sections", 3),         # Sezioni
        ("surface_roughness", 5),  # Rugosità
        ("drawing_scale", 4),      # Scala
        ("revision", 3),           # Revisione
    ]
    score = 0
    max_score = sum(w for _, w in checks)
    for field, weight in checks:
        val = meta.get(field)
        if val and val != False and val != [] and val != {}:
            score += weight
    # Bonus per lunghezza testo (più testo = migliore estrazione)
    text_len = len(text)
    if text_len > 3000:
        score = min(score + 5, max_score)
    elif text_len > 1000:
        score = min(score + 2, max_score)
    return round(score / max_score * 100)


# ============================================================
# DESCRIZIONE AI DEL DISEGNO (Vision API — solo OpenAI)
# ============================================================

DRAWING_DESCRIPTION_PROMPT = """You are a mechanical engineer analyzing a technical engineering drawing for a centrifugal pump component.
This is an authorized internal analysis of company-owned engineering documentation.

Analyze the drawing and provide a QUALITATIVE CLASSIFICATION only.
DO NOT report any numbers, dimensions, weights, or measurements — those are extracted separately with higher accuracy.

Provide ONLY:
1. COMPONENT TYPE: What type of component is this? (volute casing, impeller, shaft, cover, bearing housing, suction bell, discharge head, etc.)
2. PUMP FAMILY: Pump type/family if visible (e.g. OH2, BB1, VS1, API 610)
3. DRAWING TYPE: Type of drawing (cross-section, assembly, machined part, raw casting, hydraulic, general arrangement)
4. KEY FEATURES: List the main construction features visible (flanges, holes pattern, O-ring grooves, keyways, wear rings, impeller vanes, volute spiral, etc.)
5. CONNECTIONS: Types of connections visible (flanged nozzles, threaded auxiliary connections, bolted joints)
6. SURFACE TREATMENTS: Any surface finish specifications or machining notes visible
7. STANDARDS: Any referenced standards (ANSI, ISO, API, ASME, DIN)

Be concise. Only report what is clearly visible. Do NOT invent data. Do NOT include any numbers or measurements."""


def describe_drawing_ai(path: str) -> Optional[str]:
    """
    Usa OpenAI Vision (GPT-4o) per analizzare un disegno tecnico e generare
    una descrizione strutturata del componente.
    Gestisce TIF bi-level convertendoli in JPEG RGB.

    Args:
        path: Percorso al file immagine (TIF, PNG, ecc.)

    Returns:
        Descrizione strutturata del disegno, o None se non disponibile
    """
    import io
    import base64
    from PIL import Image

    _IMAGE_EXTS = (".tif", ".tiff", ".bmp", ".png", ".jpg", ".jpeg", ".heic", ".heif")
    ext = os.path.splitext(path)[1].lower()
    if ext not in _IMAGE_EXTS:
        return None

    # Controlla cache
    cache = _load_cache()
    cache_key = f"drawing_desc_{os.path.basename(path)}"
    if cache_key in cache:
        logger.info("Drawing description da cache per %s", os.path.basename(path))
        return cache[cache_key]

    try:
        from config import OPENAI_API_KEY, VISION_MODEL_OPENAI
        from rag.extractor import get_openai_client
    except ImportError:
        logger.warning("Import falliti per describe_drawing_ai")
        return None

    if not OPENAI_API_KEY:
        logger.warning("OpenAI API key non configurata per describe_drawing_ai")
        return None

    # Apri immagine e converti in JPEG RGB (GPT-4o gestisce meglio JPEG che PNG bi-level)
    try:
        img = Image.open(path)
        # TIF bi-level (mode "1") o grayscale ("L") → RGB
        if img.mode in ("1", "L", "P", "LA", "PA"):
            img = img.convert("RGB")
        elif img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
        if img.mode == "RGBA":
            # Converti RGBA → RGB con sfondo bianco
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            img = bg

        # Ridimensiona a max 2048px per lato (ottimo per Vision)
        max_side = 2048
        w, h = img.size
        if max(w, h) > max_side:
            scale = max_side / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

        # Salva come JPEG in memoria
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        logger.info("Immagine preparata per Vision: %dx%d JPEG, %d KB",
                     img.size[0], img.size[1], len(buf.getvalue()) // 1024)
    except Exception as e:
        logger.warning("Errore preparazione immagine per Vision: %s", e)
        return None

    # Chiama OpenAI Vision
    description = None
    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=VISION_MODEL_OPENAI,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": DRAWING_DESCRIPTION_PROMPT},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{b64}",
                        "detail": "high"
                    }}
                ]
            }],
            temperature=0.1,
            max_tokens=2000
        )
        description = response.choices[0].message.content.strip()

        # Verifica che la risposta non sia un rifiuto
        refusal_patterns = ["i can't", "i cannot", "i'm sorry", "i am sorry", "unable to"]
        if any(rp in description.lower() for rp in refusal_patterns):
            logger.warning("OpenAI ha rifiutato l'analisi del disegno: %s", description[:100])
            description = None

        if description:
            logger.info("Drawing description OpenAI: %d chars per %s",
                        len(description), os.path.basename(path))
    except Exception as e:
        logger.warning("OpenAI Vision per drawing description fallito: %s", e)

    # Salva in cache (anche se None per evitare chiamate ripetute)
    if description:
        cache[cache_key] = description
        _save_cache(cache)

    return description


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

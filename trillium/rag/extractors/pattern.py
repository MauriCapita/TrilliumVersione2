"""
Trillium V2 — Estrattore Specifico: Modello Fusione (Pattern / Raw Casting)
============================================================================
Estrae dati tecnici da disegni di modelli fusione / getti grezzi.

Codice tipico: xxxAxxRM1 (suffisso RM = Raw Material / Pattern)

Questi disegni contengono:
    - Dimensioni getto grezzo con sovrametalli
    - Peso getto grezzo
    - Riferimenti al tracciato idraulico e template
    - Note fonderia (angoli sformo, rugosità, norme ISO 8062)
"""

import re
import logging
from rag.extractors import register_extractor, _call_vision_ai, _parse_json_response

logger = logging.getLogger(__name__)


PATTERN_VISION_PROMPT = """Sei un esperto di disegni tecnici di pompe centrifughe.
Analizza questo disegno tecnico di un MODELLO DI FUSIONE / GETTO GREZZO (Pattern / Raw Casting).
Contiene tipicamente: profilo grezzo con sovrametalli, note fonderia, e riferimenti.

DATI DA ESTRARRE:

=== TIPO COMPONENTE GREZZO ===
1. **raw_component_type**: Tipo (es. "impeller" se "Raw Casting Impeller" / "Girante grezza",
   "casing" se "Raw Casting Casing" / "Corpo grezzo").

=== PESO ===
2. **raw_weight_kg**: Peso getto grezzo / "Raw casting weight" in kg.

=== DIAMETRI ===
3. **outer_diameter_mm**: Diametro esterno massimo del grezzo.
4. **bore_diameter_mm**: Diametro alesaggio/foro grezzo.
5. **all_diameters**: TUTTI i diametri Φ visibili (es. "Φ669, Φ252, Φ189, Φ145, Φ80").

=== DIMENSIONI ===
6. **overall_width_mm**: Larghezza/altezza totale grezzo.
7. **key_dimensions**: Quote principali come stringa.

=== RAGGI ===
8. **all_radii**: Raggi di raccordo (es. "R8, R05, R187.1").

=== SOVRAMETALLI ===
9. **machining_allowance_mm**: Sovrametallo di lavorazione se specificato.

=== MODELLO / PATTERN ===
10. **pattern_code**: Codice modello (es. "M1230A74RM1").
11. **pattern_grade**: Grado finitura getto (es. "CT10", "Ra 12.5").

=== RIFERIMENTI ===
12. **hydraulic_layout_ref**: Riferimento tracciato idraulico (es. "230A79HY1").
13. **template_ref**: Riferimento template/seste (es. "230A79TE1").
14. **finished_drawing_ref**: Riferimento disegno finito (es. "230A79F10").

=== NOTE FONDERIA ===
15. **foundry_standard**: Norma fonderia (es. "ISO 8062").
16. **draft_angles**: Angoli di sformo se specificati.
17. **surface_roughness_casting**: Rugosità massima getto (es. "Ra 12.5").

=== CARTIGLIO ===
18. **pump_model**: Modello pompa (es. "100AP63").
19. **drawing_number**: Numero disegno (es. "230A79RM1").
20. **description_en**: Descrizione inglese (es. "Raw Casting Impeller").
21. **description_it**: Descrizione italiana (es. "Girante grezza").
22. **revision**: Revisione.

REGOLE:
- Restituisci SOLO un oggetto JSON valido.
- Valori numerici senza unità. Se un dato non è visibile, metti null.
"""


def _extract_from_ocr_text(text: str) -> dict:
    data = {}
    tc = text.replace("\n", " ")

    m = re.search(r'(?:raw\s*casting\s*weight|peso\s*gett[oa]\s*grezz)\s*[:\s]*(\d+[.,]?\d*)\s*kg', tc, re.I)
    if m: data["raw_weight_kg"] = float(m.group(1).replace(",", "."))

    m = re.search(r'[Pp]attern\s*[:\s]*(M\d+[A-Z]\d+[A-Z]+\d+)', tc)
    if m: data["pattern_code"] = m.group(1).upper()

    hy_m = re.search(r'(\d{3}[A-Z]\d{2}HY\d)', tc, re.I)
    if hy_m: data["hydraulic_layout_ref"] = hy_m.group(1).upper()

    te_m = re.search(r'(\d{3}[A-Z]\d{2}TE\d)', tc, re.I)
    if te_m: data["template_ref"] = te_m.group(1).upper()

    pump_m = re.search(r'(\d{2,4}\s*AP\s*\d{2,4})', tc, re.I)
    if pump_m: data["pump_model"] = pump_m.group(1).strip()

    dwg_m = re.search(r'(\d{3}[A-Z]\d{2}RM\d)', tc, re.I)
    if dwg_m: data["drawing_number"] = dwg_m.group(1).upper()

    return data


@register_extractor("pattern")
def extract_pattern(image_path: str, ocr_text: str = "") -> dict:
    result = {}

    logger.info(f"Estrazione pattern con Vision AI da {image_path}")
    resp = _call_vision_ai(image_path, PATTERN_VISION_PROMPT)
    if resp:
        vd = _parse_json_response(resp)
        for k, v in vd.items():
            if v is not None and v != "null" and v != "":
                if k.endswith(("_kg", "_mm")) and isinstance(v, str):
                    try: v = float(v.replace(",", "."))
                    except ValueError: continue
                result[k] = v

    if ocr_text:
        for k, v in _extract_from_ocr_text(ocr_text).items():
            if k not in result: result[k] = v

    # Validazione
    result["data_validation"] = "OK"
    notes = []
    if result.get("raw_weight_kg"): notes.append(f"Peso grezzo: {result['raw_weight_kg']} kg")
    if result.get("raw_component_type"): notes.append(f"Tipo: {result['raw_component_type']}")
    if result.get("pattern_code"): notes.append(f"Modello: {result['pattern_code']}")
    result["data_validation_notes"] = " | ".join(notes) if notes else "OK"

    return result

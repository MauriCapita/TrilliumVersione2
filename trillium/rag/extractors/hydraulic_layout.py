"""
Trillium V2 — Estrattore Specifico: Tracciato Idraulico (Hydraulic Layout)
==========================================================================
Estrae dati tecnici da disegni di tracciati idraulici girante.

Codice tipico: xxxAxxHY1 (suffisso HY = Hydraulic)

Questi disegni mostrano il profilo delle pale con:
    - Tabelle coordinate (TETA vs Pressure/Suction side)
    - Profilo interno ed esterno
    - Diametri e angoli
    - Numero pale
"""

import re
import logging
from rag.extractors import register_extractor, _call_vision_ai, _parse_json_response

logger = logging.getLogger(__name__)


HYDRAULIC_LAYOUT_VISION_PROMPT = """Sei un esperto di disegni tecnici di pompe centrifughe.
Analizza questo TRACCIATO IDRAULICO (Hydraulic Layout) di una girante.
Mostra il profilo delle pale con tabelle coordinate, viste interna/esterna.

DATI DA ESTRARRE:

=== GEOMETRIA PALE ===
1. **num_blades**: Numero pale (es. "Number of blades: 3" → 3).
2. **d2_mm**: Diametro esterno girante (il Φ più grande, es. Φ650 → 650).
3. **suction_diameter_mm**: Diametro ingresso/occhio (es. Φ192).
4. **eye_diameter_mm**: Altro diametro ingresso se diverso.

=== PROFILO ESTERNO (External Profile) ===
5. **external_profile_data**: Dati tabella "External Profile" come stringa.
   Formato: "TETA: 0°→210° | Pressure: 323→86.2 | Suction: 311→86.2"
   (riporta primo e ultimo valore).
6. **external_profile_points**: Numero di punti nella tabella profilo esterno.

=== PROFILO INTERNO (Internal Profile) ===
7. **internal_profile_data**: Dati tabella "Internal Profile" come stringa.
   Formato: "TETA: 0°→210° | Pressure: 310→79.2 | Suction: 310→64.6"
8. **internal_profile_points**: Numero di punti nella tabella profilo interno.

=== ANGOLI ===
9. **discharge_angle_deg**: Angolo di scarico (es. 20.8°).
10. **blade_inlet_angle_deg**: Angolo ingresso pale.
11. **teta_range**: Range TETA (es. "0° - 210°").

=== DIAMETRI ===
12. **all_diameters**: TUTTI i diametri Φ visibili (es. "Φ650, Φ192, Φ165.2, Φ669").

=== QUOTE ===
13. **overall_width_mm**: Larghezza totale (dimensione assiale).
14. **key_dimensions**: Quote principali come stringa.

=== RAGGI ===
15. **all_radii**: Tutti i raggi R visibili (es. "R291, R9.7, R187.1, R29").

=== RIFERIMENTI ===
16. **related_template**: Riferimento template/seste (es. "230A79TE1").
17. **related_impeller**: Riferimento disegno girante (es. "230A79F10").

=== CARTIGLIO ===
18. **pump_model**: Modello pompa.
19. **drawing_number**: Numero disegno (es. "230A79HY1").
20. **description_en**: Descrizione inglese (es. "Impeller Hydraulic Layout").
21. **description_it**: Descrizione italiana (es. "Tracciato idraulico Girante").
22. **revision**: Revisione.

REGOLE:
- Restituisci SOLO un oggetto JSON valido.
- Valori numerici senza unità di misura.
- Se un dato non è visibile, metti null.
"""


def _extract_from_ocr_text(text: str) -> dict:
    data = {}
    tc = text.replace("\n", " ")

    m = re.search(r'[Nn]umber.*?(\d+)\s*(?:blades|pale)', tc)
    if m: data["num_blades"] = int(m.group(1))

    diams = re.findall(r'[Φφ⌀]\s*(\d+[.,]?\d*)', tc)
    if diams: data["all_diameters"] = ", ".join(f"Φ{d}" for d in sorted(set(diams)))

    hy_m = re.search(r'(\d{3}[A-Z]\d{2}HY\d)', tc, re.I)
    if hy_m: data["drawing_number"] = hy_m.group(1).upper()

    pump_m = re.search(r'(\d{2,4}\s*AP\s*\d{2,4})', tc, re.I)
    if pump_m: data["pump_model"] = pump_m.group(1).strip()

    return data


@register_extractor("hydraulic_layout")
def extract_hydraulic_layout(image_path: str, ocr_text: str = "") -> dict:
    result = {}

    logger.info(f"Estrazione hydraulic_layout con Vision AI da {image_path}")
    resp = _call_vision_ai(image_path, HYDRAULIC_LAYOUT_VISION_PROMPT)
    if resp:
        vd = _parse_json_response(resp)
        for k, v in vd.items():
            if v is not None and v != "null" and v != "":
                if k.endswith("_mm") and isinstance(v, str):
                    try: v = float(v.replace(",", "."))
                    except ValueError: continue
                if k.endswith("_deg") and isinstance(v, str):
                    try: v = float(v.replace(",", "."))
                    except ValueError: continue
                result[k] = v

    if ocr_text:
        for k, v in _extract_from_ocr_text(ocr_text).items():
            if k not in result: result[k] = v

    result["data_validation"] = "OK"
    notes = []
    if result.get("num_blades"): notes.append(f"{result['num_blades']} pale")
    if result.get("d2_mm"): notes.append(f"D2={result['d2_mm']}mm")
    if result.get("discharge_angle_deg"): notes.append(f"β2={result['discharge_angle_deg']}°")
    result["data_validation_notes"] = " | ".join(notes) if notes else "OK"

    return result

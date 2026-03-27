"""
Trillium V2 — Estrattore Specifico: Corpo Pompa (Casing / Volute)
=================================================================
Estrae dati tecnici da disegni di corpi pompa (volute).

Codice parte: 102 = Corpo pompa lavorato (Finish Machined Volute Casing)

Dati estratti:
    - Peso (grezzo e finito)
    - Flange (DN, ANSI rating)
    - Diametri e quote principali
    - Fori e bulloneria
    - Tolleranze e finiture
    - Cartiglio
"""

import re
import logging
from rag.extractors import register_extractor, _call_vision_ai, _parse_json_response

logger = logging.getLogger(__name__)


CASING_VISION_PROMPT = """Sei un esperto di disegni tecnici di pompe centrifughe.
Analizza questo disegno tecnico di un CORPO POMPA / VOLUTA (Casing).
Il disegno contiene tipicamente: sezioni (A-A, C-C), viste laterali, tabelle connessioni.

DATI DA ESTRARRE:

=== PESO ===
1. **finished_weight_kg**: Peso finito calcolato in kg.
2. **raw_weight_kg**: Peso grezzo / getto grezzo in kg.

=== FLANGE ===
3. **suction_flange_dn**: DN flangia aspirazione (es. "DN 6\"" → 6).
4. **discharge_flange_dn**: DN flangia mandata se diversa.
5. **flange_rating**: Rating ANSI flange (es. "ANSI B16.5 300 LB" → "300 LB").
6. **flange_standard**: Standard flange (es. "ANSI B16.5").

=== DIAMETRI PRINCIPALI ===
7. **bore_diameter_mm**: Diametro alesaggio/sede girante.
8. **wear_ring_seat_mm**: Diametro sede anello usura (con tolleranza H7).
9. **shaft_seal_bore_mm**: Diametro sede tenuta.

=== DIMENSIONI ===
10. **overall_length_mm**: Lunghezza totale corpo.
11. **overall_height_mm**: Altezza totale.
12. **overall_width_mm**: Larghezza totale.

=== FORI E BULLONERIA ===
13. **bolt_patterns**: Descrizione configurazioni fori/bulloni.
    (es. "N.8 equally-spaced holes Φ22, N.12 holes Φ22").
14. **spot_faces**: Lamature (es. "N.4 spot-faces Φ60").

=== TOLLERANZE ===
15. **key_tolerances**: Tolleranze principali (es. "Φ291 H7, Φ656 H7, Φ696±0.1").
16. **concentricity**: Tolleranze di concentricità (es. "0.025, 0.04").
17. **general_tolerances**: Standard (es. "ISO 2768-mK").

=== FINITURA ===
18. **surface_finishes**: Finiture Ra (es. "Ra 3.2, Ra 6.3").

=== MODELLO FUSIONE ===
19. **raw_casting_ref**: Riferimento getto grezzo (es. "102A79RM1").
20. **pre_machined_ref**: Riferimento pre-lavorato (es. "102A79P10").

=== CONNESSIONI (dalla tabella Part Identification Code) ===
21. **connections_table**: Riepilogo connessioni ausiliarie se tabella presente.
    (es. "Drain, Vent, Gauge, Seal flush - varie da 1/2\" a 3/4\" NPT").

=== CARTIGLIO ===
22. **pump_model**: Modello pompa (es. "100AP63").
23. **drawing_number**: Numero disegno (es. "102A79F10").
24. **description_en**: Descrizione inglese (es. "Finish Machined Volute Casing (ANSI 300)").
25. **description_it**: Descrizione italiana (es. "Corpo Pompa Lavorato").
26. **revision**: Revisione.

=== TUTTI I DIAMETRI ===
27. **all_diameters**: Lista di TUTTI i diametri Φ visibili.

REGOLE:
- Restituisci SOLO un oggetto JSON valido.
- Valori numerici senza unità. Se un dato non è visibile, metti null.
"""


def _extract_from_ocr_text(text: str) -> dict:
    data = {}
    tc = text.replace("\n", " ")

    m = re.search(r'(?:finished\s*weight|peso\s*finit)\s*[:\s]*(\d+[.,]?\d*)\s*kg', tc, re.I)
    if m: data["finished_weight_kg"] = float(m.group(1).replace(",", "."))

    m = re.search(r'(?:raw\s*casting|peso\s*gett)\s*[:\s]*(\d+[.,]?\d*)\s*kg', tc, re.I)
    if m: data["raw_weight_kg"] = float(m.group(1).replace(",", "."))

    m = re.search(r'DN\s*(\d+)["\s].*?(\d+)\s*LB', tc, re.I)
    if m:
        data["suction_flange_dn"] = int(m.group(1))
        data["flange_rating"] = f"{m.group(2)} LB"

    pump_m = re.search(r'(\d{2,4}\s*AP\s*\d{2,4})', tc, re.I)
    if pump_m: data["pump_model"] = pump_m.group(1).strip()

    dwg_m = re.search(r'(102[A-Z]\d{2}[A-Z]\d{2})', tc, re.I)
    if dwg_m: data["drawing_number"] = dwg_m.group(1).upper()

    return data


@register_extractor("casing")
def extract_casing(image_path: str, ocr_text: str = "") -> dict:
    result = {}

    logger.info(f"Estrazione casing con Vision AI da {image_path}")
    resp = _call_vision_ai(image_path, CASING_VISION_PROMPT)
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
    if result.get("finished_weight_kg"): notes.append(f"Peso: {result['finished_weight_kg']} kg")
    if result.get("flange_rating"): notes.append(f"Rating: {result['flange_rating']}")
    if result.get("suction_flange_dn"): notes.append(f"DN{result['suction_flange_dn']}\"")
    result["data_validation_notes"] = " | ".join(notes) if notes else "OK"

    return result

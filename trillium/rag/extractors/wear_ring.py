"""
Trillium V2 — Estrattore Specifico: Anello Usura (Wear Ring)
=============================================================
Estrae dati tecnici da disegni di anelli di usura (sia coperchio che corpo).

Codici parte standard:
    502 = Anello usura fisso (Stationary wear ring / Casing wear ring)
    503 = Anello usura rotante (Rotating wear ring / Impeller wear ring)

Dati estratti:
    - Diametri (interno, esterno, sedi, giochi)
    - Peso finito
    - Tolleranze e accoppiamenti
    - Fori e forature
    - Finiture superficiali
    - Cartiglio (modello pompa, n. disegno, revisione)
"""

import re
import logging
from rag.extractors import register_extractor, _call_vision_ai, _parse_json_response

logger = logging.getLogger(__name__)


# ============================================================
# PROMPT VISION AI — ANELLO USURA
# ============================================================

WEAR_RING_VISION_PROMPT = """Sei un esperto di disegni tecnici di pompe centrifughe.
Analizza questo disegno tecnico di un ANELLO DI USURA (wear ring) e estrai TUTTI i seguenti dati.
L'anello di usura è un componente anulare con sezione tipicamente rettangolare o a L.
Il disegno contiene una SEZIONE (Section A-A) e una VISTA FRONTALE circolare.

DATI DA ESTRARRE:

=== TIPO ANELLO ===
1. **wear_ring_type**: Tipo di anello. Cerca nel cartiglio:
   - "Cover Wear Ring" / "Anello Usura Coperchio" → "cover"
   - "Casing Wear Ring" / "Anello Usura Corpo" → "casing"
   - "Impeller Wear Ring" / "Anello Usura Girante" → "impeller"
   Se codice parte inizia con 502 → "casing", con 503 → "impeller".

=== PESO ===
2. **finished_weight_kg**: "Finished weight calculated" / "Peso finito calcolato" in kg.

=== DIAMETRI (dalla SEZIONE) ===
3. **outer_diameter_mm**: Diametro ESTERNO dell'anello (il Φ più grande).
4. **inner_diameter_mm**: Diametro INTERNO dell'anello (il Φ più piccolo, la sede).
5. **bore_diameter_mm**: Diametro alesaggio / foro centrale se diverso dall'inner diameter.
6. **seat_diameter_mm**: Diametro della sede di montaggio (con tolleranza stretta tipo H7, B8).

=== DIMENSIONI SEZIONE ===
7. **height_mm**: Altezza assiale dell'anello (la dimensione verticale nella sezione).
8. **wall_thickness_mm**: Spessore parete radiale (differenza tra diametro esterno e interno / 2).
9. **lip_height_mm**: Altezza del labbro / bordino se presente (forma a L).
10. **lip_width_mm**: Larghezza del labbro se presente.

=== FORI ===
11. **holes_count**: Numero di fori (es. "n.4" → 4).
12. **holes_diameter_mm**: Diametro dei fori (es. "Φ11.5" → 11.5).
13. **holes_pattern**: Disposizione (es. "equally spaced" / "equidistanti").

=== TOLLERANZE ===
14. **key_tolerances**: Tutte le tolleranze dimensionali visibili.
    Restituisci come stringa (es. "Φ370 B8 H7, Φ377 H7, 30±0.1").

=== FINITURA SUPERFICIALE ===
15. **surface_finishes**: Finiture Ra indicate nel disegno.
    Restituisci come stringa (es. "Ra 3.2, Ra 1.6, Ra 6.3").

=== NOTE ===
16. **hardface_required**: true/false — cerca "hard-faced surface" / "superficie dura".
17. **general_tolerances**: Standard tolleranze generali (es. "ISO 2768-mk").

=== CARTIGLIO ===
18. **pump_model**: Modello pompa (es. "300 AP 50").
19. **drawing_number**: Numero disegno (es. "502A72F20").
20. **description_en**: Descrizione inglese (es. "Cover Wear Ring").
21. **description_it**: Descrizione italiana (es. "Anello Usura Coperchio").
22. **revision**: Revisione (es. "01").

=== TUTTI I DIAMETRI (catch-all) ===
23. **all_diameters**: Lista di TUTTI i diametri Φ visibili.
    Restituisci come stringa (es. "Φ395, Φ370, Φ377, Φ416, Φ439").

REGOLE:
- Restituisci SOLO un oggetto JSON valido, senza testo aggiuntivo.
- Per i valori numerici, restituisci solo il numero (senza unità di misura).
- Se un dato non è visibile o non sei sicuro, metti null.
- I diametri sono preceduti dal simbolo Φ.
- Leggi TUTTO il disegno incluse note laterali e cartiglio.
"""


# ============================================================
# REGEX FALLBACK — ANELLO USURA
# ============================================================

def _extract_from_ocr_text(text: str) -> dict:
    """Estrae dati da testo OCR con regex (fallback se Vision AI non disponibile)."""
    data = {}
    text_clean = text.replace("\n", " ")

    # Peso finito
    m = re.search(
        r'(?:finished\s*weight|peso\s*finit[oa])\s*(?:calculated|calcolat[oa])?\s*[:\s]*'
        r'(\d+[.,]?\d*)\s*(?:[±+\-]\s*\d+[%]?\s*)?kg',
        text_clean, re.IGNORECASE
    )
    if m:
        data["finished_weight_kg"] = float(m.group(1).replace(",", "."))

    # Tutti i diametri Φ
    diameters = re.findall(r'[Φφ⌀]\s*(\d+[.,]?\d*)', text_clean)
    if diameters:
        data["all_diameters"] = ", ".join(f"Φ{d}" for d in diameters)

    # Fori: n.4 fori Φ11.5
    holes_m = re.search(r'[Nn]\.?\s*(\d+)\s*(?:fori|holes)\s*[Φφ⌀]\s*(\d+[.,]?\d*)', text_clean)
    if not holes_m:
        holes_m = re.search(r'[Nn]\.?\s*(\d+)\s*[Φφ⌀]\s*(\d+[.,]?\d*)\s*(?:holes|fori)', text_clean)
    if holes_m:
        data["holes_count"] = int(holes_m.group(1))
        data["holes_diameter_mm"] = float(holes_m.group(2).replace(",", "."))

    # Modello pompa
    pump_m = re.search(r'(\d{2,4}\s*AP\s*\d{2,4})', text_clean, re.IGNORECASE)
    if pump_m:
        data["pump_model"] = pump_m.group(1).strip()

    # Numero disegno (502Axxxx o 503Axxxx)
    dwg_m = re.search(r'(50[23][A-Z]\d{2}[A-Z]\d{2})', text_clean, re.IGNORECASE)
    if dwg_m:
        data["drawing_number"] = dwg_m.group(1).upper()

    # Cover / Casing wear ring
    if re.search(r'cover\s*wear\s*ring|anello\s*usura\s*coperchio', text_clean, re.IGNORECASE):
        data["wear_ring_type"] = "cover"
    elif re.search(r'casing\s*wear\s*ring|anello\s*usura\s*corpo', text_clean, re.IGNORECASE):
        data["wear_ring_type"] = "casing"

    # Hard-faced
    if re.search(r'hard[- ]?face', text_clean, re.IGNORECASE):
        data["hardface_required"] = True

    return data


# ============================================================
# ESTRATTORE PRINCIPALE (registrato nel registry)
# ============================================================

@register_extractor("wear_ring")
def extract_wear_ring(image_path: str, ocr_text: str = "") -> dict:
    """
    Estrae dati specifici di un anello di usura dal disegno tecnico.
    
    Strategia:
        1. Vision AI (GPT-4o) sull'immagine completa con prompt mirato
        2. Regex fallback sul testo OCR per integrare dati mancanti
        3. Validazione base dei dati
    """
    result = {}

    # --- STEP 1: Vision AI (prioritaria) ---
    logger.info(f"Estrazione wear_ring con Vision AI da {image_path}")
    vision_response = _call_vision_ai(image_path, WEAR_RING_VISION_PROMPT)
    
    if vision_response:
        vision_data = _parse_json_response(vision_response)
        if vision_data:
            for key, value in vision_data.items():
                if value is not None and value != "null" and value != "":
                    # Converti stringhe numeriche
                    if key.endswith(("_kg", "_mm")) and isinstance(value, str):
                        try:
                            value = float(value.replace(",", "."))
                        except ValueError:
                            continue
                    if key.endswith("_count") and isinstance(value, str):
                        try:
                            value = int(value)
                        except ValueError:
                            continue
                    result[key] = value
            logger.info(f"Vision AI: estratti {len(result)} campi")

    # --- STEP 2: Regex fallback ---
    if ocr_text:
        regex_data = _extract_from_ocr_text(ocr_text)
        for key, value in regex_data.items():
            if key not in result:
                result[key] = value
                logger.info(f"Regex fallback: aggiunto {key}={value}")

    # --- STEP 3: Validazione ---
    # Diametri ragionevoli (10-2000 mm)
    for dk in ("outer_diameter_mm", "inner_diameter_mm", "bore_diameter_mm", "seat_diameter_mm"):
        if dk in result:
            d = result[dk]
            if isinstance(d, (int, float)) and not (10 <= d <= 2000):
                logger.warning(f"{dk}={d}mm fuori range, rimosso")
                del result[dk]

    # Peso ragionevole (0.1-500 kg per un anello)
    if "finished_weight_kg" in result:
        w = result["finished_weight_kg"]
        if isinstance(w, (int, float)) and not (0.1 <= w <= 500):
            logger.warning(f"finished_weight_kg={w}kg fuori range, rimosso")
            del result["finished_weight_kg"]

    # Outer > inner check
    od = result.get("outer_diameter_mm")
    iid = result.get("inner_diameter_mm")
    if od and iid and isinstance(od, (int, float)) and isinstance(iid, (int, float)):
        if od < iid:
            result["data_validation"] = "KO"
            result["data_validation_notes"] = f"ANOMALIA: OD={od}mm < ID={iid}mm"
        else:
            result["data_validation"] = "OK"
            thickness = (od - iid) / 2
            result["wall_thickness_calc_mm"] = round(thickness, 1)
            result["data_validation_notes"] = f"OK: OD={od}mm, ID={iid}mm, spessore={thickness:.1f}mm"

    return result

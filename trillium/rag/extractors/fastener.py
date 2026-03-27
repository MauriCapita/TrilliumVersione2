"""
Trillium V2 — Estrattore Specifico: Viteria Speciale (Fastener)
================================================================
Estrae dati tecnici da disegni di viteria speciale pompe.

Componenti coperti:
    922 = Dado blocaggio girante (Impeller nut)
    900 = Viteria corpo (Casing bolting)
    900.10 = Viteria coperchi (Cover bolting)
    918 = Bulloni fondazione (Foundation bolts)
    Ghiere, dadi speciali, prigionieri, ecc.

Dati estratti:
    - Filettatura (metrica, tipo, senso)
    - Diametri e dimensioni
    - Peso finito
    - Esagono / chiave
    - Tolleranze e finiture
    - Cartiglio
"""

import re
import logging
from rag.extractors import register_extractor, _call_vision_ai, _parse_json_response

logger = logging.getLogger(__name__)


# ============================================================
# PROMPT VISION AI — VITERIA SPECIALE
# ============================================================

FASTENER_VISION_PROMPT = """Sei un esperto di disegni tecnici di pompe centrifughe.
Analizza questo disegno tecnico di un componente di VITERIA SPECIALE (dado, ghiera,
bullone, prigioniero) e estrai TUTTI i seguenti dati.
Il disegno tipicamente contiene una SEZIONE e una VISTA FRONTALE.

DATI DA ESTRARRE:

=== TIPO COMPONENTE ===
1. **fastener_type**: Tipo. Cerca nel cartiglio:
   - "Impeller Nut" / "Dado Blocaggio Girante" → "impeller_nut"
   - "Lock Nut" / "Ghiera" → "lock_nut"
   - "Stud" / "Prigioniero" → "stud"
   - "Bolt" / "Bullone" → "bolt"
   - "Cap Screw" / "Vite" → "cap_screw"
   Altrimenti descrivi il tipo trovato.

=== PESO ===
2. **finished_weight_kg**: "Finished weight calculated" / "Peso finito calcolato" in kg.

=== FILETTATURA ===
3. **thread_size**: Filettatura completa (es. "M50x3", "M30x2", "M24").
4. **thread_pitch_mm**: Passo filettatura (es. M50x3 → 3).
5. **thread_direction**: Senso filettatura. Cerca "left hand" / "filettatura sinistra" → "left".
   Se non specificato o destro → "right".

=== DIAMETRI ===
6. **outer_diameter_mm**: Diametro ESTERNO massimo del componente.
7. **bore_diameter_mm**: Diametro foro interno / alesaggio.
8. **thread_diameter_mm**: Diametro nominale filettatura (es. M50 → 50).

=== DIMENSIONI ===
9. **overall_length_mm**: Lunghezza totale del componente.
10. **head_height_mm**: Altezza testa / dado.
11. **hex_size_mm**: Dimensione esagono o chiave (es. "M10" → 10, "SW36" → 36).
12. **chamfer**: Smusso (es. "3x45°").

=== TOLLERANZE ===
13. **key_tolerances**: Tolleranze principali (es. "h13, 0.02 concentricità").
14. **general_tolerances**: Standard tolleranze (es. "ISO 2768-mK").

=== FINITURA ===
15. **surface_finishes**: Finiture Ra (es. "Ra 6.3, Ra 3.2").

=== CARTIGLIO ===
16. **pump_model**: Modello pompa (es. "100AP63").
17. **drawing_number**: Numero disegno (es. "922A79F10").
18. **description_en**: Descrizione inglese (es. "Impeller Nut").
19. **description_it**: Descrizione italiana (es. "Dado Blocaggio Girante").
20. **revision**: Revisione (es. "01").

=== TUTTI I DIAMETRI ===
21. **all_diameters**: Lista di TUTTI i diametri Φ visibili.
    (es. "Φ116, Φ55").

REGOLE:
- Restituisci SOLO un oggetto JSON valido, senza testo aggiuntivo.
- Per i valori numerici, restituisci solo il numero (senza unità).
- Se un dato non è visibile o non sei sicuro, metti null.
- I diametri sono preceduti dal simbolo Φ.
- Leggi TUTTO il disegno incluse note e cartiglio.
"""


# ============================================================
# REGEX FALLBACK
# ============================================================

def _extract_from_ocr_text(text: str) -> dict:
    """Estrae dati da testo OCR con regex."""
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

    # Filettatura M50x3
    thread_m = re.search(r'(M\d+)\s*[xX×]\s*(\d+[.,]?\d*)', text_clean)
    if thread_m:
        data["thread_size"] = f"{thread_m.group(1)}x{thread_m.group(2)}"
        data["thread_diameter_mm"] = float(re.search(r'M(\d+)', thread_m.group(1)).group(1))
        data["thread_pitch_mm"] = float(thread_m.group(2).replace(",", "."))

    # Left hand / filettatura sinistra
    if re.search(r'left\s*hand|filettatura\s*sinistra', text_clean, re.IGNORECASE):
        data["thread_direction"] = "left"

    # Modello pompa
    pump_m = re.search(r'(\d{2,4}\s*AP\s*\d{2,4})', text_clean, re.IGNORECASE)
    if pump_m:
        data["pump_model"] = pump_m.group(1).strip()

    # Numero disegno (9xxAxxxx)
    dwg_m = re.search(r'(9\d{2}[A-Z]\d{2}[A-Z]\d{2})', text_clean, re.IGNORECASE)
    if dwg_m:
        data["drawing_number"] = dwg_m.group(1).upper()

    # Tipo dal cartiglio
    if re.search(r'impeller\s*nut|dado\s*blocca', text_clean, re.IGNORECASE):
        data["fastener_type"] = "impeller_nut"
    elif re.search(r'lock\s*nut|ghiera', text_clean, re.IGNORECASE):
        data["fastener_type"] = "lock_nut"

    return data


# ============================================================
# ESTRATTORE PRINCIPALE
# ============================================================

@register_extractor("fastener")
def extract_fastener(image_path: str, ocr_text: str = "") -> dict:
    """
    Estrae dati specifici di viteria speciale dal disegno tecnico.
    """
    result = {}

    # --- STEP 1: Vision AI ---
    logger.info(f"Estrazione fastener con Vision AI da {image_path}")
    vision_response = _call_vision_ai(image_path, FASTENER_VISION_PROMPT)

    if vision_response:
        vision_data = _parse_json_response(vision_response)
        if vision_data:
            for key, value in vision_data.items():
                if value is not None and value != "null" and value != "":
                    if key.endswith(("_kg", "_mm")) and isinstance(value, str):
                        try:
                            value = float(value.replace(",", "."))
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

    # --- STEP 3: Validazione ---
    if "finished_weight_kg" in result:
        w = result["finished_weight_kg"]
        if isinstance(w, (int, float)) and not (0.01 <= w <= 200):
            logger.warning(f"finished_weight_kg={w}kg fuori range per fastener, rimosso")
            del result["finished_weight_kg"]

    # Validazione base
    result["data_validation"] = "OK"
    notes = []
    if result.get("thread_size"):
        notes.append(f"Filettatura: {result['thread_size']}")
    if result.get("thread_direction") == "left":
        notes.append("⚠️ Filettatura SINISTRA")
    if result.get("finished_weight_kg"):
        notes.append(f"Peso: {result['finished_weight_kg']} kg")
    result["data_validation_notes"] = " | ".join(notes) if notes else "OK"

    return result

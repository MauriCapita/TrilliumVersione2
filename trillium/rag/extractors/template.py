"""
Trillium V2 — Estrattore Specifico: Template Girante (Impeller Template)
========================================================================
Estrae dati tecnici da disegni di seste/template di controllo profilo pale.

Questi sono sagome fisiche (lamiera inox/alluminio) usate in officina
per verificare il profilo delle pale della girante.

Codice tipico: 230AxxTE1 (suffisso TE = Template)

Dati estratti:
    - Lista template (inlet, outlet, discharge angle)
    - Raggi profilo pale (R202, R120, R230, ...)
    - Diametri di riferimento (Φ650, Φ192, ...)
    - Angoli scarico
    - Spessori template
    - Materiale
    - Riferimento idraulico (hydraulic layout)
    - Cartiglio
"""

import re
import logging
from rag.extractors import register_extractor, _call_vision_ai, _parse_json_response

logger = logging.getLogger(__name__)


# ============================================================
# PROMPT VISION AI — TEMPLATE GIRANTE
# ============================================================

TEMPLATE_VISION_PROMPT = """Sei un esperto di disegni tecnici di pompe centrifughe.
Analizza questo disegno tecnico di TEMPLATE/SESTE DI CONTROLLO GIRANTE.
Queste sono sagome fisiche (lamiera) per verificare il profilo delle pale.
Il disegno contiene tipicamente: sezioni di ingresso/uscita con raggi, una tabella codici componente,
e una vista d'insieme che mostra le pale della girante.

DATI DA ESTRARRE:

=== TEMPLATE ITEMS (dalla tabella in alto a destra) ===
1. **templates**: Lista dei template con i loro dettagli. Per ogni riga:
   - item: numero item (01, 02, 03)
   - name: nome (es. "Inlet Template", "Outlet Template", "Discharge Angle Template")
   - name_it: nome italiano (es. "Sesta Ingresso", "Sesta Uscita", "Sesta Angolo Uscita")
   - material: materiale (es. "inox or aluminium")
   Restituisci come lista di oggetti JSON.

=== SPESSORI TEMPLATE ===
2. **inlet_template_thickness_mm**: Spessore sesta ingresso (es. "Thickness 1mm" → 1).
3. **outlet_template_thickness_mm**: Spessore sesta uscita.
4. **discharge_template_thickness_mm**: Spessore sesta angolo uscita.

=== GEOMETRIA PALE (dalla sezione) ===
5. **all_radii**: TUTTI i raggi R visibili nel disegno (profilo pale).
   Restituisci come stringa (es. "R202.1, R120, R14.4, R201, R163.7, R97.4, R230").
6. **discharge_angle_deg**: Angolo di scarico (es. "20.8°" → 20.8).
7. **blade_inlet_angle_deg**: Angolo ingresso pale se visibile.

=== DIAMETRI ===
8. **all_diameters**: TUTTI i diametri Φ visibili (es. "Φ650, Φ192, Φ165.2").
9. **d2_mm**: Diametro massimo girante (il Φ più grande, tipicamente Φ650 → 650).
10. **suction_diameter_mm**: Diametro ingresso/occhio.

=== DIMENSIONI CHIAVE ===
11. **overall_width_mm**: Larghezza totale dalla sezione (quota orizzontale principale).
12. **b2_mm**: Larghezza uscita (b2) se visibile.
13. **key_dimensions**: Altre quote importanti come stringa (es. "224.1, 145.4, 90.3, 332, 48").

=== SUPERFICI ===
14. **pressure_side_info**: Info sulla "Pressure Side Surface" se presente.
15. **suction_side_info**: Info sulla "Suction Side Surface" se presente.

=== RIFERIMENTI ===
16. **hydraulic_layout_ref**: Riferimento tracciato idraulico (es. "230A79HY1").
17. **nq_value**: Valore Nq se menzionato (es. "NQ10" → 10).

=== CARTIGLIO ===
18. **pump_model**: Modello pompa (es. "100AP63").
19. **drawing_number**: Numero disegno (es. "230A79TE1").
20. **description_en**: Descrizione inglese (es. "Impeller Template").
21. **description_it**: Descrizione italiana (es. "Seste di controllo girante NQ10").
22. **revision**: Revisione.

REGOLE:
- Restituisci SOLO un oggetto JSON valido, senza testo aggiuntivo.
- Per i valori numerici, restituisci solo il numero.
- Se un dato non è visibile o non sei sicuro, metti null.
- Leggi TUTTO il disegno: sezioni, tabelle, note, cartiglio.
"""


# ============================================================
# REGEX FALLBACK
# ============================================================

def _extract_from_ocr_text(text: str) -> dict:
    """Estrae dati da testo OCR con regex."""
    data = {}
    text_clean = text.replace("\n", " ")

    # NQ value
    nq_m = re.search(r'NQ\s*(\d+)', text_clean, re.IGNORECASE)
    if nq_m:
        data["nq_value"] = int(nq_m.group(1))

    # Hydraulic layout reference
    hy_m = re.search(r'(\d{3}A\d{2}HY\d)', text_clean, re.IGNORECASE)
    if hy_m:
        data["hydraulic_layout_ref"] = hy_m.group(1).upper()

    # Tutti i raggi R
    radii = re.findall(r'R\s*(\d+[.,]?\d*)', text_clean)
    if radii:
        unique_r = sorted(set(f"R{r}" for r in radii))
        data["all_radii"] = ", ".join(unique_r)

    # Tutti i diametri Φ
    diameters = re.findall(r'[Φφ⌀]\s*(\d+[.,]?\d*)', text_clean)
    if diameters:
        data["all_diameters"] = ", ".join(f"Φ{d}" for d in sorted(set(diameters)))

    # Modello pompa
    pump_m = re.search(r'(\d{2,4}\s*AP\s*\d{2,4})', text_clean, re.IGNORECASE)
    if pump_m:
        data["pump_model"] = pump_m.group(1).strip()

    # Numero disegno (xxxAxxTE1)
    dwg_m = re.search(r'(\d{3}[A-Z]\d{2}TE\d)', text_clean, re.IGNORECASE)
    if dwg_m:
        data["drawing_number"] = dwg_m.group(1).upper()

    # Angolo scarico
    angle_m = re.search(r'(\d+[.,]?\d*)\s*[°]', text_clean)
    if angle_m:
        data["discharge_angle_deg"] = float(angle_m.group(1).replace(",", "."))

    return data


# ============================================================
# ESTRATTORE PRINCIPALE
# ============================================================

@register_extractor("template")
def extract_template(image_path: str, ocr_text: str = "") -> dict:
    """
    Estrae dati specifici di template/seste di controllo girante.
    """
    result = {}

    # --- STEP 1: Vision AI ---
    logger.info(f"Estrazione template con Vision AI da {image_path}")
    vision_response = _call_vision_ai(image_path, TEMPLATE_VISION_PROMPT)

    if vision_response:
        vision_data = _parse_json_response(vision_response)
        if vision_data:
            for key, value in vision_data.items():
                if value is not None and value != "null" and value != "":
                    if key.endswith(("_mm", "_deg")) and isinstance(value, str):
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
    result["data_validation"] = "OK"
    notes = []
    if result.get("nq_value"):
        notes.append(f"NQ{result['nq_value']}")
    templates = result.get("templates")
    if isinstance(templates, list):
        notes.append(f"{len(templates)} template")
    if result.get("hydraulic_layout_ref"):
        notes.append(f"Rif: {result['hydraulic_layout_ref']}")
    result["data_validation_notes"] = " | ".join(notes) if notes else "OK"

    return result

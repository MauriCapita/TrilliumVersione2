"""
Trillium V2 — Impeller (Girante) Component Extractor
=====================================================
Estrae dati specifici dai disegni tecnici delle giranti usando Vision AI.

Dati estratti:
    - finished_weight_kg: Peso finito calcolato (il dato più importante)
    - raw_weight_kg: Peso grezzo (se presente)
    - d2_mm: Diametro esterno girante
    - hub_diameter_mm: Diametro mozzo
    - shaft_bore_mm: Foro albero
    - num_blades: Numero pale
    - d2_b2_ratio: Rapporto b2/D2
    - b2_mm: Larghezza uscita
    - eye_diameter_mm: Diametro ingresso (occhio)
    - disc_thickness_at_balance_mm: Spessore disco alla sezione equilibratura
    - balance_ref_diameter_mm: Diametro di riferimento equilibratura (es. Φ650)
    - balancing_grade: Grado di equilibratura (ISO 1940)
    - surface_finish: Finitura superficiale (Ra)

Prompt template derivato dall'analisi dei template TPI:
    Template/01TemplateGiranteIntera.png → vista completa
    Template/02TemplateGiranteMezza01.png → sezione A-A
    Template/03TemplateGiranteMezza02.png → vista frontale
    Template/04TemplateGirantePrimoValore.png → zona bilanciamento
    Template/04TemplateGiranteSecondoValorePesoFinito.png → peso finito
"""

import re
import logging
from rag.extractors import register_extractor, _call_vision_ai, _parse_json_response

logger = logging.getLogger(__name__)

# ============================================================
# VISION AI PROMPT (il prompt è il cuore dell'estrazione)
# ============================================================

IMPELLER_VISION_PROMPT = """Sei un esperto di disegni tecnici di pompe centrifughe.
Analizza questo disegno tecnico di una GIRANTE (impeller) e estrai TUTTI i seguenti dati.
Il disegno tipicamente contiene: una SEZIONE (Section A-A) con il profilo interno,
una VISTA FRONTALE con pale e mozzo, e note/cartiglio con peso e specifiche.
Le viste possono essere a destra o sinistra — cerca ovunque.

DATI DA ESTRARRE:

=== PESO ===
1. **finished_weight_kg**: "Finished weight calculated" / "Peso finito calcolato" in kg.
   Se ha tolleranza (es. 86±15% kg), restituisci solo il valore base (86).

2. **raw_weight_kg**: "Raw weight" / "Peso grezzo" / "Peso di fusione" in kg.

=== DIAMETRI (dalla SEZIONE e dalla VISTA FRONTALE) ===
3. **d2_mm**: Diametro ESTERNO girante / shroud diameter (il Φ più grande nella sezione,
   es. Φ246). È il diametro dell'involucro esterno.

4. **suction_diameter_mm**: Diametro di ASPIRAZIONE / suction eye diameter
   (diametro all'ingresso della girante, nella sezione è il diametro dell'occhio).

5. **hub_diameter_mm**: Diametro del MOZZO (hub) nella vista frontale (es. Φ170).

6. **shaft_bore_mm**: Foro albero con tolleranza H (es. "25 H9" → 25).

7. **wear_ring_diameter_mm**: Diametro anello di usura / wear ring diameter.
   Nella sezione, è il diametro nella zona di tenuta, spesso con tolleranza stretta.

8. **seal_diameter_mm**: Diametro zona tenuta / seal diameter, se diverso dal wear ring.

=== GEOMETRIA SEZIONE (dalla Section A-A) ===
9. **overall_width_mm**: Larghezza assiale totale della girante (la quota orizzontale
   più grande nella sezione, es. 218±0.1).

10. **b2_mm**: Larghezza uscita girante (b2) — la distanza tra shroud e hub al bordo esterno.

11. **eye_diameter_mm**: Diametro ingresso (occhio/suction eye).

12. **vane_height_mm**: Altezza complessiva della pala nella sezione.

13. **shroud_thickness_mm**: Spessore del disco frontale (shroud).

14. **disc_thickness_mm**: Spessore EFFETTIVO del disco posteriore nella sezione.
    È una quota dimensionale (es. "15" mm) che appare nel profilo della sezione
    vicino al disco, NON è lo spessore minimo ammissibile né quello alla zona equilibratura.
    Può essere ovunque nella sezione come quota isolata.

15. **key_radii**: Raggi principali di raccordo nella sezione (es. "R190.1"). 
    Restituisci come stringa (es. "R190.1, R8").

=== DETTAGLI PALE (dalla VISTA FRONTALE) ===
15. **num_blades**: Numero di pale. Cerca "N.X blades" / "N.X pale" (es. N.3 → 3).

16. **blade_holes_diameter_mm**: Diametro fori tra le pale (es. "Φ21" → 21).

17. **blade_holes_count**: Numero fori tra le pale (es. "N.3 Φ21 holes" → 3).

=== EQUILIBRATURA ===
18. **min_disc_thickness_mm**: Spessore MINIMO disco ammissibile per equilibratura
    (es. "minimum disc allowable thickness 10 mm" → 10).

19. **disc_thickness_at_balance_mm**: Spessore EFFETTIVO del disco alla sezione equilibratura.
    Cerca "(17.8 ±0.4 at Φ650)" o "(17.8±0.4 a Φ650)". Restituisci il valore base (17.8).

20. **balance_ref_diameter_mm**: Diametro di riferimento equilibratura nella nota precedente
    (es. Φ650 → 650).

21. **balancing_grade**: Grado equilibratura ISO 1940 (es. "grade 2.5" → "G2.5").

=== FINITURA SUPERFICIALE ===
22. **surface_finishes**: Tutte le finiture superficiali indicate nel disegno.
    Restituisci come stringa (es. "Ra 6.3, Ra 3.2, Ra 1.6").

=== TOLLERANZE PRINCIPALI ===
23. **key_tolerances**: Le quote con tolleranza stretta visibili nella sezione.
    Restituisci come stringa (es. "Φ233 s6, Φ135 f8, 218±0.1, 126±0.1").

=== CARTIGLIO ===
24. **pump_model**: Modello pompa (es. "100AP63").
25. **drawing_number**: Numero disegno (es. "230A79F10").
26. **description_en**: Descrizione inglese (es. "Finish machined Impeller").
27. **description_it**: Descrizione italiana (es. "Girante lavorata").
28. **revision**: Revisione corrente (es. "02").

=== TUTTI I DIAMETRI (catch-all) ===
29. **all_diameters**: Lista di TUTTI i diametri Φ visibili nel disegno.
    Restituisci come stringa separata da virgola (es. "Φ246, Φ233, Φ192, Φ170, Φ135, Φ118, Φ99").

REGOLE:
- Restituisci SOLO un oggetto JSON valido, senza testo aggiuntivo.
- Per i valori numerici, restituisci solo il numero (senza unità di misura).
- Se un dato non è visibile o non sei sicuro, metti null.
- Per il peso, il valore PRIMA del ± è quello che interessa (es. 86±15% → 86).
- I diametri sono preceduti dal simbolo Φ.
- Le viste (sezione/frontale) possono essere a destra o sinistra nel disegno.
- Leggi TUTTO il disegno incluse note laterali, in basso, e nel cartiglio.
"""


# ============================================================
# REGEX FALLBACK (cerca nel testo OCR)
# ============================================================

def _extract_from_ocr_text(ocr_text: str) -> dict:
    """
    Estrazione rapida da testo OCR tramite regex.
    Fallback se Vision AI non è disponibile.
    """
    data = {}
    text = ocr_text or ""

    # Peso finito: "Finished weight calculated : 86±15% kg"
    # Varianti: "Peso finito calcolato", "Finished weight", diverse spaziature
    weight_patterns = [
        r'(?:finished\s+weight\s*(?:calculated)?|peso\s+finito\s*(?:calcolato)?)\s*[:=]?\s*(\d+[.,]?\d*)\s*(?:[±+-]\s*\d+%?)?\s*kg',
        r'(?:raw\s+weight|peso\s+grezzo|peso\s+(?:di\s+)?fusione)\s*[:=]?\s*(\d+[.,]?\d*)\s*(?:[±+-]\s*\d+%?)?\s*kg',
    ]
    for i, pattern in enumerate(weight_patterns):
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            val = float(m.group(1).replace(",", "."))
            if i == 0:
                data["finished_weight_kg"] = val
            else:
                data["raw_weight_kg"] = val

    # Numero pale: "N.3 blades" o "N.3 pale" o "3 blades"
    blade_m = re.search(r'(?:N\.?\s*)?(\d+)\s*(?:blades?|pale|vanes?)', text, re.IGNORECASE)
    if blade_m:
        data["num_blades"] = int(blade_m.group(1))

    # Foro albero: "25 H9" o "Φ25 H7"
    bore_m = re.search(r'[Φφ]?\s*(\d+(?:[.,]\d+)?)\s*H\d+', text)
    if bore_m:
        data["shaft_bore_mm"] = float(bore_m.group(1).replace(",", "."))

    # Equilibratura: "ISO 1940-1 grade 2.5" o "grado 2.5"
    bal_m = re.search(r'(?:grade|grado)\s*(\d+[.,]?\d*)', text, re.IGNORECASE)
    if bal_m:
        data["balancing_grade"] = f"G{bal_m.group(1)}"

    # Diametri (Φ seguito da numero) — prendi il più grande come D2
    diameters = re.findall(r'[Φφ]\s*(\d+(?:[.,]\d*)?)', text)
    if diameters:
        diam_values = [float(d.replace(",", ".")) for d in diameters]
        data["d2_mm"] = max(diam_values)

    # Modello pompa: pattern come "100AP63", "250AP50", "300BG45"
    pump_m = re.search(r'\b(\d{2,3}\s*[A-Z]{2}\s*\d{2,3})\b', text)
    if pump_m:
        data["pump_model"] = pump_m.group(1).replace(" ", "")

    # Numero disegno: pattern come "230A79F10"
    dwg_m = re.search(r'\b(\d{3}A\d{2,3}[A-Z]\d{1,3})\b', text)
    if dwg_m:
        data["drawing_number"] = dwg_m.group(1)

    # Spessore disco equilibratura: "17.8 ±0.4 at Φ650" o "(17.8±0.4 a Φ650)"
    balance_m = re.search(
        r'(\d+[.,]?\d*)\s*[±+-]\s*\d+[.,]?\d*\s*(?:at|a|@)\s*[Φφ]\s*(\d+)',
        text, re.IGNORECASE
    )
    if balance_m:
        data["disc_thickness_at_balance_mm"] = float(balance_m.group(1).replace(",", "."))
        data["balance_ref_diameter_mm"] = float(balance_m.group(2))

    return data


# ============================================================
# ESTRATTORE PRINCIPALE (registrato nel registry)
# ============================================================

@register_extractor("impeller")
def extract_impeller(image_path: str, ocr_text: str = "") -> dict:
    """
    Estrae dati specifici di una girante dal disegno tecnico.
    
    Strategia:
        1. Vision AI (GPT-4o) sull'immagine completa con prompt mirato
        2. Regex fallback sul testo OCR per integrare dati mancanti
        3. Merge dei risultati (Vision AI ha priorità)
    """
    result = {}

    # --- STEP 1: Vision AI (prioritaria) ---
    logger.info(f"Estrazione impeller con Vision AI da {image_path}")
    vision_response = _call_vision_ai(image_path, IMPELLER_VISION_PROMPT)
    
    if vision_response:
        vision_data = _parse_json_response(vision_response)
        if vision_data:
            # Filtra valori null e converti tipi
            for key, value in vision_data.items():
                if value is not None and value != "null" and value != "":
                    # Converti stringhe numeriche in numeri
                    if key.endswith(("_kg", "_mm")) and isinstance(value, str):
                        try:
                            value = float(value.replace(",", "."))
                        except ValueError:
                            continue
                    if key == "num_blades" and isinstance(value, str):
                        try:
                            value = int(value)
                        except ValueError:
                            continue
                    result[key] = value
            logger.info(f"Vision AI: estratti {len(result)} campi")

    # --- STEP 2: Regex fallback (integra dati mancanti) ---
    if ocr_text:
        regex_data = _extract_from_ocr_text(ocr_text)
        for key, value in regex_data.items():
            if key not in result:  # Non sovrascrivere Vision AI
                result[key] = value
                logger.info(f"Regex fallback: aggiunto {key}={value}")

    # --- STEP 3: Validazione ---
    # D2 deve essere ragionevole per una girante (50-1500 mm)
    if "d2_mm" in result:
        d2 = result["d2_mm"]
        if not (50 <= d2 <= 1500):
            logger.warning(f"D2={d2}mm fuori range ragionevole, rimosso")
            del result["d2_mm"]

    # Peso deve essere ragionevole (0.5-5000 kg)
    for wk in ("finished_weight_kg", "raw_weight_kg"):
        if wk in result:
            w = result[wk]
            if not (0.5 <= w <= 5000):
                logger.warning(f"{wk}={w}kg fuori range ragionevole, rimosso")
                del result[wk]

    # Numero pale: 1-20
    if "num_blades" in result:
        nb = result["num_blades"]
        if not (1 <= nb <= 20):
            logger.warning(f"num_blades={nb} fuori range, rimosso")
            del result["num_blades"]

    # --- STEP 4: Calcolo Nq dalla curva aziendale + validazione ---
    _validate_nq_curve(result)

    return result


def _validate_nq_curve(result: dict):
    """
    Calcola Nq dalla curva aziendale usando D2 e b2 estratti.
    Confronta dati reali vs calcolati e aggiunge flag OK/KO.
    
    Campi aggiunti:
        - b2_d2_ratio: rapporto b2/D2 reale
        - nq_calculated: Nq stimato dalla curva (reverse lookup da b2/D2)
        - b2_from_nq_mm: b2 che la curva darebbe con l'Nq calcolato (verifica)
        - data_validation: "OK" o "KO"
        - data_validation_notes: dettagli confronto
    """
    d2 = result.get("d2_mm")
    b2 = result.get("b2_mm")
    
    if not d2 or not b2 or d2 <= 0 or b2 <= 0:
        return
    
    try:
        from weight_engine.nq_curve import NQ_B2D2_CURVE, get_b2_d2_ratio, calc_b2
    except ImportError:
        logger.warning("Modulo nq_curve non disponibile per validazione")
        return
    
    # Calcola rapporto reale
    ratio_real = b2 / d2
    result["b2_d2_ratio"] = round(ratio_real, 4)
    
    # Reverse lookup: dato b2/D2, trova Nq interpolando la curva
    nq_calc = None
    for i in range(len(NQ_B2D2_CURVE) - 1):
        nq_lo, r_lo = NQ_B2D2_CURVE[i]
        nq_hi, r_hi = NQ_B2D2_CURVE[i + 1]
        if r_lo <= ratio_real <= r_hi:
            if r_hi != r_lo:
                t = (ratio_real - r_lo) / (r_hi - r_lo)
                nq_calc = nq_lo + t * (nq_hi - nq_lo)
            break
    
    # Se fuori range curva
    if nq_calc is None:
        if ratio_real <= NQ_B2D2_CURVE[0][1]:
            nq_calc = NQ_B2D2_CURVE[0][0]
        elif ratio_real >= NQ_B2D2_CURVE[-1][1]:
            nq_calc = NQ_B2D2_CURVE[-1][0]
    
    if nq_calc is None:
        return
    
    result["nq_calculated"] = round(nq_calc, 1)
    
    # Verifica: con Nq calcolato, quale b2 otterremmo?
    b2_from_curve = calc_b2(nq_calc, d2)
    result["b2_from_nq_mm"] = round(b2_from_curve, 1)
    
    # Calcola errore
    delta_b2 = abs(b2 - b2_from_curve)
    delta_pct = (delta_b2 / b2 * 100) if b2 > 0 else 999
    
    # Validazione: OK se errore < 15%, KO altrimenti
    notes = []
    validation_ok = True
    
    # Check b2 coerenza
    if delta_pct > 15:
        validation_ok = False
        notes.append(f"b2 reale={b2:.1f}mm vs calcolato={b2_from_curve:.1f}mm (Δ={delta_pct:.1f}%)")
    else:
        notes.append(f"b2 OK: reale={b2:.1f}mm ≈ calcolato={b2_from_curve:.1f}mm (Δ={delta_pct:.1f}%)")
    
    # Check D2 vs other diameters (sanity)
    if d2 < b2:
        validation_ok = False
        notes.append(f"ANOMALIA: D2={d2}mm < b2={b2}mm")
    
    # Check rapporto b2/D2 nel range ragionevole (0.03 - 0.50)
    if not (0.03 <= ratio_real <= 0.50):
        validation_ok = False
        notes.append(f"b2/D2={ratio_real:.4f} fuori range (0.03-0.50)")
    
    # Check peso vs D2 (sanity: peso dovrebbe crescere con D2)
    weight = result.get("finished_weight_kg")
    if weight and d2:
        # Peso atteso approssimativo: ~0.001 * D2^2.5 per acciaio
        weight_expected_min = 0.0003 * d2 ** 2.3
        weight_expected_max = 0.005 * d2 ** 2.5
        if weight < weight_expected_min or weight > weight_expected_max:
            notes.append(f"Peso={weight}kg vs range atteso={weight_expected_min:.0f}-{weight_expected_max:.0f}kg (verifica)")
    
    result["data_validation"] = "OK" if validation_ok else "KO"
    result["data_validation_notes"] = " | ".join(notes)
    result["nq_info"] = f"Nq≈{nq_calc:.0f} (da b2/D2={ratio_real:.4f}, curva aziendale)"
    
    logger.info(f"Validazione Nq: {result['data_validation']} — {result['data_validation_notes']}")


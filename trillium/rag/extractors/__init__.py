"""
Trillium V2 — Component-Specific Extractors
============================================
Modulo per l'estrazione mirata di dati tecnici da disegni per tipo di componente.
Ogni file contiene un estrattore specifico (impeller.py, casing.py, shaft.py, ...)
che usa Vision AI (GPT-4o) per trovare e estrarre i parametri chiave.

Architettura:
    1. Il disegno viene classificato (dal tipo documento o dal nome file)
    2. L'estrattore specifico viene richiamato con un prompt mirato
    3. I dati estratti vengono salvati nei metadati Qdrant

Utilizzo:
    from rag.extractors import extract_component_data
    data = extract_component_data(image_path, ocr_text, component_type="impeller")
"""

import os
import io
import re
import json
import base64
import logging
from typing import Optional
from PIL import Image

logger = logging.getLogger(__name__)

# Registry degli estrattori per tipo componente
_EXTRACTORS = {}


def register_extractor(component_type: str):
    """Decoratore per registrare un estrattore per tipo componente."""
    def decorator(func):
        _EXTRACTORS[component_type.lower()] = func
        return func
    return decorator


def get_available_extractors() -> list[str]:
    """Restituisce la lista dei tipi componente con estrattore registrato."""
    return list(_EXTRACTORS.keys())


def extract_component_data(
    image_path: str,
    ocr_text: str = "",
    component_type: str = "",
    source_filename: str = "",
) -> dict:
    """
    Estrae dati specifici per tipo componente dal disegno.
    
    1. Se component_type è specificato, usa l'estrattore corrispondente
    2. Altrimenti, tenta di classificare il disegno dal testo OCR e dal nome file
    3. Esegue l'estrazione mirata con Vision AI + regex fallback
    
    Returns:
        dict con i dati estratti (es. finished_weight_kg, d2_mm, num_blades, ...)
        Include sempre la chiave "component_type" con il tipo identificato.
    """
    # Auto-detect component type se non specificato
    if not component_type:
        component_type = _detect_component_type(ocr_text, source_filename)

    if not component_type:
        logger.info(f"Tipo componente non identificato per {source_filename}")
        return {}

    component_type = component_type.lower()

    # Cerca estrattore registrato
    extractor_func = _EXTRACTORS.get(component_type)
    if not extractor_func:
        logger.info(f"Nessun estrattore registrato per tipo '{component_type}'")
        return {"component_type": component_type}

    try:
        result = extractor_func(image_path, ocr_text)
        result["component_type"] = component_type
        logger.info(f"Estratti {len(result)} campi per {component_type} da {source_filename}")
        return result
    except Exception as e:
        logger.error(f"Errore estrazione {component_type} da {source_filename}: {e}")
        return {"component_type": component_type}


def _detect_component_type(ocr_text: str, filename: str) -> str:
    """
    Rileva automaticamente il tipo di componente dal testo OCR e dal nome file.

    Usa un sistema a PUNTEGGI: ogni keyword ha un peso. Il tipo con
    il punteggio più alto vince. Questo risolve le collisioni tra
    keyword (es. un disegno casing che cita "raw casting" nei riferimenti).

    Le keyword sono scelte per essere specifiche del CARTIGLIO / DESCRIZIONE,
    NON del testo generico sparso nel disegno.
    """
    text_lower = (ocr_text or "").lower()
    name_lower = (filename or "").lower()
    combined = text_lower + " " + name_lower

    # Dizionario: tipo → lista di (keyword, peso)
    # Peso alto (10-15) = frase dal cartiglio/descrizione, molto specifica
    # Peso medio (3-5)  = keyword tecnica specifica del componente
    # Peso basso (1-2)  = keyword generica che può apparire in altri contesti
    scoring = {
        "hydraulic_layout": [
            ("hydraulic layout", 15),
            ("tracciato idraulico", 15),
            ("tracciato idraulic", 12),
            ("external profile", 5),
            ("internal profile", 5),
            ("profilo esterno", 5),
            ("profilo interno", 5),
        ],
        "template": [
            ("impeller template", 15),
            ("seste di controllo", 15),
            ("template girante", 15),
            ("sesta ingresso", 10),
            ("sesta uscita", 10),
            ("sesta angolo", 10),
            ("inlet template", 10),
            ("outlet template", 10),
            ("discharge angle template", 10),
        ],
        "pattern": [
            ("raw casting impeller", 15),
            ("raw casting casing", 15),
            ("girante grezza", 15),
            ("corpo grezzo", 15),
            ("grezzo lavorato", 12),
            ("note per il modellista", 12),
            ("notes for patternmaker", 12),
            ("pattern and foundry", 12),
            ("note per il modellista e la fonderia", 12),
            ("iso 8062", 8),
            ("angoli di sformo", 8),
            ("draft angle", 5),
            ("sovrametallo", 8),
            ("machining allowance", 5),
            ("raw casting weight", 10),
            ("peso getto grezzo", 10),
        ],
        "impeller": [
            # NB: "finished weight calculated" è presente in TUTTI i
            # componenti, non solo giranti — peso basso!
            ("finished weight calculated", 1),
            ("peso finito calcolato", 1),
            ("dynamic balancing", 12),
            ("equilibratura dinamica", 12),
            ("balancing grade", 10),
            ("grado di equilibratura", 10),
            ("balancing thickness", 10),
            ("spessore equilibratura", 10),
            ("impeller assy", 10),
            ("girante lavorata", 10),
            ("girante finita", 10),
            ("impeller", 2),
            ("girante", 2),
        ],
        "wear_ring": [
            ("cover wear ring", 15),
            ("casing wear ring", 15),
            ("impeller wear ring", 15),
            ("anello usura coperchio", 15),
            ("anello usura corpo", 15),
            ("anello usura girante", 15),
            ("wear ring", 10),
            ("anello usura", 10),
            ("anello di usura", 10),
            ("hard-faced surface", 8),
            ("hard faced", 5),
            # Varianti OCR comuni (errori di riconoscimento)
            ("weer ring", 12),
            ("wearring", 10),
            ("usura coperchio", 12),
            ("usura corpo", 12),
            ("usura girante", 12),
        ],
        "casing": [
            ("volute casing", 15),
            ("finish machined volute", 15),
            ("corpo pompa lavorato", 15),
            ("corpo pompa", 10),
            ("casing assy", 10),
            ("part identification code", 8),
            ("codice identificativo", 8),
            ("spot-faces", 5),
            ("spot faces", 5),
            ("flange face finish", 5),
        ],
        "fastener": [
            ("impeller nut", 15),
            ("dado bloccaggio girante", 15),
            ("dado blocca girante", 15),
            ("lock nut", 10),
            ("dado bloccaggio", 10),
            ("cap screw", 10),
            ("foundation bolt", 10),
            ("bullone fondazione", 10),
            ("prigioniero", 8),
            ("stud bolt", 8),
            ("ghiera", 5),
            # Varianti OCR comuni
            ("mpeller nut", 12),
            ("dado blocaggio", 12),
            ("dado blocca", 10),
        ],
        "shaft": [
            ("pump shaft", 15),
            ("albero pompa", 15),
            ("shaft assy", 10),
            ("albero lavorato", 10),
            ("keyway", 5),
            ("linguetta", 3),
            ("bearing journal", 5),
        ],
        "cover": [
            ("suction cover", 15),
            ("discharge cover", 15),
            ("coperchio aspirazione", 15),
            ("coperchio mandata", 15),
            ("back plate", 10),
            ("piastra posteriore", 10),
        ],
        "bearing_housing": [
            ("bearing housing", 15),
            ("supporto cuscinetti", 15),
            ("bearing bracket", 10),
            ("staffa cuscinetti", 10),
        ],
    }

    # Calcola punteggi
    scores = {}
    for comp_type, keywords in scoring.items():
        score = 0
        for kw, weight in keywords:
            if kw in combined:
                score += weight
        if score > 0:
            scores[comp_type] = score

    # Il tipo con il punteggio più alto vince
    if scores:
        best = max(scores, key=scores.get)
        return best

    return ""



def _image_to_base64(image_path: str, max_side: int = 2048) -> tuple[str, str]:
    """
    Converte un'immagine in base64 per Vision AI.
    Ridimensiona se troppo grande. Supporta TIF.
    """
    img = Image.open(image_path)
    
    # Per TIF multi-frame, prendi il primo frame
    if hasattr(img, 'n_frames') and img.n_frames > 1:
        img.seek(0)
    
    # Converti in RGB se necessario
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    
    # Ridimensiona se troppo grande
    w, h = img.size
    if max(w, h) > max_side:
        ratio = max_side / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
    
    buf = io.BytesIO()
    img.save(buf, format="PNG", quality=90)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return b64, "image/png"


def _call_vision_ai(image_path: str, prompt: str) -> str:
    """
    Chiama GPT-4o Vision con un prompt specifico sull'immagine.
    Restituisce la risposta grezza come stringa.
    """
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from config import OPENAI_API_KEY
    
    if not OPENAI_API_KEY:
        logger.warning("OpenAI API key non configurata per estrazione componente")
        return ""
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        b64, mime = _image_to_base64(image_path)
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
                ]
            }],
            temperature=0.1,
            max_tokens=2000,
        )
        return (response.choices[0].message.content or "").strip()
    except Exception as e:
        logger.error(f"Errore Vision AI: {e}")
        return ""


def _parse_json_response(response: str) -> dict:
    """Parsa risposta JSON da Vision AI, gestendo markdown code blocks."""
    if not response:
        return {}
    
    # Rimuovi eventuale markdown ```json ... ```
    text = response.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Rimuovi prima e ultima riga (```json e ```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Prova a trovare un blocco JSON nella risposta
        import re
        match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        logger.warning(f"Impossibile parsare risposta JSON: {text[:200]}")
        return {}


# Import degli estrattori specifici (auto-registrazione via decoratore)
from rag.extractors import impeller  # noqa: F401, E402
from rag.extractors import wear_ring  # noqa: F401, E402
from rag.extractors import fastener  # noqa: F401, E402
from rag.extractors import template  # noqa: F401, E402
from rag.extractors import casing  # noqa: F401, E402
from rag.extractors import hydraulic_layout  # noqa: F401, E402
from rag.extractors import pattern  # noqa: F401, E402

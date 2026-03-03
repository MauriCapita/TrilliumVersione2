"""
Trillium V2 — AI Parts List Extractor
Usa GPT-4o per estrarre una Parts List (BOM) strutturata dal testo
dei disegni tecnici indicizzati. Molto più potente dell'estrazione regex.
"""

import json
import logging
import os
import sys
import time

logger = logging.getLogger(__name__)

# Aggiungi il percorso padre per import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# PROMPT TEMPLATE
# ============================================================

_BOM_EXTRACTION_PROMPT = """You are an expert technical data extractor for centrifugal pump components.
Analyze the following text extracted from a technical document (drawing, parts list, datasheet, or specification).

Extract a STRUCTURED PARTS LIST (Bill of Materials) with the following fields for EACH component found:

For each component provide:
- "item": item number (from the document, or "N/A")
- "part_number": part number or drawing number
- "description": component name/description
- "material": material specification (e.g. A216-WCB, A351-CF8M, AISI 4140)
- "weight_kg": weight in kg (convert from lbs if needed: 1 lb = 0.4536 kg)
- "weight_type": one of: "net", "gross", "premachined", "finished", "shipping", "unknown"
- "quantity": number of pieces
- "notes": any additional notes

Also extract DOCUMENT-LEVEL information:
- "pump_family": pump family if mentioned (OH1, OH2, BB1, BB5, VS1, VS4, etc.)
- "pump_model": pump model or size
- "document_type": one of: "parts_list", "general_arrangement", "cross_section", "datasheet", "specification", "calculation", "procedure", "standard", "other"
- "flange_rating": flange rating if mentioned (150, 300, 600, etc.)
- "design_pressure_bar": design pressure in bar
- "design_temperature_c": design temperature in °C
- "total_weight_kg": total assembly weight if available
- "standards_cited": list of standards referenced (e.g. ["API 610", "ASME B16.5"])
- "project_number": project or order number if visible

Return ONLY valid JSON with this structure:
{
  "components": [ ... ],
  "pump_family": "...",
  "pump_model": "...",
  "document_type": "...",
  "flange_rating": null,
  "design_pressure_bar": null,
  "design_temperature_c": null,
  "total_weight_kg": null,
  "standards_cited": [],
  "project_number": null,
  "extraction_confidence": 0.0-1.0
}

If no components are found, return an empty "components" array.
Be extremely thorough. Extract EVERY component mentioned with a weight or material.

TEXT TO ANALYZE:
---
{text}
---
"""


# ============================================================
# FUNZIONE PRINCIPALE: ESTRAZIONE AI
# ============================================================

def extract_parts_list_ai(text: str, source: str = "", max_text_chars: int = 12000) -> dict:
    """
    Usa GPT-4o per estrarre una Parts List strutturata dal testo di un documento.

    Args:
        text: Testo completo del documento
        source: Percorso sorgente del file (per logging)
        max_text_chars: Limite caratteri testo inviato al LLM

    Returns:
        Dict con "components" (lista BOM) e metadati documento
    """
    if not text or len(text.strip()) < 50:
        return _empty_result(source)

    # Tronca testo se troppo lungo
    analysis_text = text[:max_text_chars]
    if len(text) > max_text_chars:
        # Aggiungi anche la fine del documento (spesso contiene pesi totali)
        tail = text[-2000:]
        analysis_text += f"\n\n[... testo troncato ...]\n\n{tail}"

    prompt = _BOM_EXTRACTION_PROMPT.format(text=analysis_text)

    try:
        from config import PROVIDER, OPENAI_API_KEY, OPENROUTER_API_KEY

        if PROVIDER == "openai" and OPENAI_API_KEY:
            result = _call_openai(prompt)
        elif OPENROUTER_API_KEY:
            result = _call_openrouter(prompt)
        elif OPENAI_API_KEY:
            result = _call_openai(prompt)
        else:
            logger.warning("Nessun provider LLM configurato per AI extraction")
            return _empty_result(source)

        if result:
            result["source"] = source
            result["filename"] = os.path.basename(source) if source else ""

            # Post-processing: normalizza pesi
            for comp in result.get("components", []):
                _normalize_weight(comp)

            # Calcola score qualità
            result["quality_score"] = _compute_quality_score(result)

            logger.info(
                f"AI extraction: {os.path.basename(source)} → "
                f"{len(result.get('components', []))} componenti, "
                f"confidence={result.get('extraction_confidence', 0):.2f}"
            )
            return result

    except Exception as e:
        logger.warning(f"Errore AI extraction per {source}: {e}")

    return _empty_result(source)


# ============================================================
# LLM PROVIDERS
# ============================================================

def _call_openai(prompt: str, max_retries: int = 3) -> dict:
    """Chiama OpenAI GPT-4o per estrazione BOM."""
    from openai import OpenAI
    from config import OPENAI_API_KEY

    client = OpenAI(api_key=OPENAI_API_KEY)

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a technical document analyzer for pump engineering. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
            text = response.choices[0].message.content.strip()
            return _parse_json_safe(text)

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate_limit" in error_msg.lower():
                wait = min(2 ** attempt, 30)
                time.sleep(wait)
                continue
            raise

    return None


def _call_openrouter(prompt: str, max_retries: int = 3) -> dict:
    """Chiama OpenRouter (Claude/GPT-4o) per estrazione BOM."""
    from openai import OpenAI
    from config import OPENROUTER_API_KEY

    client = OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1"
    )

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="anthropic/claude-3.5-sonnet",
                messages=[
                    {"role": "system", "content": "You are a technical document analyzer for pump engineering. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=4000,
            )
            text = response.choices[0].message.content.strip()
            return _parse_json_safe(text)

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate_limit" in error_msg.lower():
                wait = min(2 ** attempt, 30)
                time.sleep(wait)
                continue
            raise

    return None


# ============================================================
# UTILITIES
# ============================================================

def _parse_json_safe(text: str) -> dict:
    """Estrae JSON da risposta LLM (gestisce markdown fences, etc.)."""
    # Rimuovi markdown fences
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Rimuovi prima e ultima riga (fences)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Prova a trovare il JSON nel testo
        import re
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return None


def _normalize_weight(comp: dict):
    """Normalizza il campo peso: gestisce stringhe, unità, conversioni."""
    weight = comp.get("weight_kg")
    if weight is None:
        return

    if isinstance(weight, str):
        weight = weight.replace(",", ".").strip()
        try:
            weight = float(weight)
        except (ValueError, TypeError):
            comp["weight_kg"] = None
            return

    if isinstance(weight, (int, float)):
        comp["weight_kg"] = round(float(weight), 2)
    else:
        comp["weight_kg"] = None


def _compute_quality_score(result: dict) -> float:
    """Calcola un punteggio di qualità 0.0-1.0 per l'estrazione."""
    score = 0.0
    components = result.get("components", [])

    if not components:
        return 0.1  # Solo metadati, nessun componente

    # Punti per numero componenti
    n = len(components)
    score += min(n / 10, 0.3)  # Max 0.3 per 10+ componenti

    # Punti per componenti con peso
    with_weight = sum(1 for c in components if c.get("weight_kg"))
    if n > 0:
        score += (with_weight / n) * 0.25  # Max 0.25

    # Punti per componenti con materiale
    with_material = sum(1 for c in components if c.get("material") and c["material"] != "N/A")
    if n > 0:
        score += (with_material / n) * 0.15  # Max 0.15

    # Punti per metadati documento
    if result.get("pump_family"):
        score += 0.1
    if result.get("document_type") and result["document_type"] != "other":
        score += 0.1
    if result.get("total_weight_kg"):
        score += 0.1

    return min(score, 1.0)


def _empty_result(source: str = "") -> dict:
    """Ritorna un risultato vuoto."""
    return {
        "components": [],
        "pump_family": None,
        "pump_model": None,
        "document_type": "other",
        "flange_rating": None,
        "design_pressure_bar": None,
        "design_temperature_c": None,
        "total_weight_kg": None,
        "standards_cited": [],
        "project_number": None,
        "extraction_confidence": 0.0,
        "quality_score": 0.0,
        "source": source,
        "filename": os.path.basename(source) if source else "",
    }

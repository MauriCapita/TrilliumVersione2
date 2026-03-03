"""
Trillium V2 — AI Reference Pump Matcher
Usa il sistema RAG per trovare la pompa di riferimento più simile
ai parametri di input e estrarre dati tecnici dai documenti.
"""

import os
import sys
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Aggiungi il percorso padre per import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def find_reference_pump(
    params: dict,
    top_k: int = 10,
    use_ai_extraction: bool = True,
) -> Optional[dict]:
    """
    Cerca la pompa di riferimento più simile usando il RAG e il pump database.

    Flusso:
    1. Costruisce una query semantica dai parametri input
    2. Cerca nei documenti indicizzati via Qdrant
    3. Usa il LLM per analizzare i documenti e estrarre dati tecnici
    4. Fallback: usa il pump database locale

    Args:
        params: Parametri della pompa target
        top_k: Numero documenti da recuperare
        use_ai_extraction: Se True, usa LLM per estrarre dati strutturati

    Returns:
        dict con dati della pompa di riferimento, o None
    """
    docs = []
    try:
        from rag.query import retrieve_relevant_docs, generate_answer
        from config import PROVIDER

        # 1. Costruisci query semantica
        query = _build_search_query(params)
        logger.info(f"Query ricerca pompa riferimento: {query}")

        # 2. Recupera documenti rilevanti
        try:
            docs = retrieve_relevant_docs(query)
            if docs:
                logger.info(f"Trovati {len(docs)} documenti rilevanti")
        except Exception as e:
            logger.error(f"Errore nel recupero documenti: {e}")

    except ImportError as e:
        logger.warning(f"Impossibile importare moduli RAG: {e}")

    # 3. Usa AI per estrarre dati strutturati (solo se ci sono docs)
    if docs and use_ai_extraction:
        try:
            ref_data = _extract_reference_data_ai(docs, params)
            if ref_data:
                return ref_data
        except Exception as e:
            logger.warning(f"Estrazione AI fallita: {e}, uso fallback manuale")

    # 4. Fallback: estrazione basica (pump database + docs se disponibili)
    return _extract_reference_data_basic(docs or [], params)


def _build_search_query(params: dict) -> str:
    """Costruisce una query semantica ottimizzata per trovare pompe simili."""
    parts = []

    family = params.get("pump_family", "")
    if family:
        parts.append(f"pompa {family}")
        # Aggiungi tipo esteso
        type_map = {
            "OH": "overhung centrifugal pump",
            "BB": "between bearings multistage pump",
            "VS": "vertical suspended pump",
        }
        for prefix, desc in type_map.items():
            if family.startswith(prefix):
                parts.append(desc)
                break

    nq = params.get("nq")
    if nq:
        parts.append(f"specific speed Nq {nq}")
        parts.append(f"velocità specifica Nq={nq}")

    material = params.get("material", "")
    if material:
        parts.append(f"materiale {material}")

    pressure = params.get("pressure")
    if pressure:
        parts.append(f"pressione {pressure} bar design pressure")

    temperature = params.get("temperature")
    if temperature:
        parts.append(f"temperatura {temperature}°C")

    # Aggiungi keywords per weight estimation
    parts.append("weight peso componenti parts list disegno drawing")

    return " ".join(parts)


def _extract_reference_data_ai(docs: list, params: dict) -> Optional[dict]:
    """
    Usa il LLM per analizzare i documenti e estrarre dati strutturati
    sulla pompa di riferimento.
    """
    try:
        from rag.query import generate_answer
        from config import PROVIDER
    except ImportError:
        return None

    # Costruisci il contesto dai documenti
    context_parts = []
    sources = []
    for i, doc in enumerate(docs[:5]):  # Max 5 documenti per non eccedere token
        text = doc.get("text", doc.get("content", ""))
        source = doc.get("source", doc.get("metadata", {}).get("source", f"doc-{i}"))
        if text:
            context_parts.append(f"[DOC-{i+1}] Fonte: {source}\n{text[:3000]}")
            sources.append(source)

    context = "\n\n".join(context_parts)

    # Prompt per estrazione dati strutturati
    family = params.get("pump_family", "")
    nq = params.get("nq", "")

    extraction_prompt = f"""Analizza i documenti seguenti e cerca di identificare una pompa di riferimento 
simile a quella che stiamo progettando (famiglia {family}, Nq≈{nq}).

Estrai i seguenti dati dalla pompa di riferimento più adatta:
1. Nome/codice del disegno o documento da cui proviene il dato
2. Famiglia pompa (es. OH2, BB5, VS6)
3. Velocità specifica Nq (se disponibile)
4. Diametro girante (mm) se disponibile
5. Materiale principale usato
6. Spessore parete (mm) se disponibile
7. Per ogni componente trovato, il peso (kg) se indicato

IMPORTANTE: Rispondi SOLO con un JSON valido nel seguente formato, senza testo aggiuntivo:
{{
    "source": "nome del documento/disegno sorgente",
    "pump_family": "XX",
    "nq": 0,
    "impeller_diameter": 0,
    "material": "nome materiale",
    "wall_thickness": 0,
    "components": {{
        "Casing": {{"weight_kg": 0, "material": ""}},
        "Impeller": {{"weight_kg": 0, "material": ""}}
    }},
    "confidence_note": "nota sulla affidabilità dei dati estratti"
}}

Se non riesci a estrarre dati sufficienti, rispondi con: {{"source": "none", "error": "motivo"}}

DOCUMENTI:
{context}"""

    try:
        # Usa generate_answer del modulo RAG
        answer = generate_answer(
            query=extraction_prompt,
            context="",
            provider=PROVIDER,
        )

        if not answer:
            return None

        # Prova a parsare il JSON dalla risposta
        ref_data = _parse_json_from_response(answer)
        if ref_data and ref_data.get("source") != "none":
            logger.info(f"Pompa riferimento trovata via AI: {ref_data.get('source')}")
            return ref_data

    except Exception as e:
        logger.warning(f"Errore nell'estrazione AI: {e}")

    return None


def _parse_json_from_response(response: str) -> Optional[dict]:
    """Estrae e parsa JSON da una risposta LLM."""
    # Prova prima il parsing diretto
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Cerca JSON in blocchi di codice
    import re
    json_patterns = [
        r'```json\s*\n(.*?)\n```',
        r'```\s*\n(.*?)\n```',
        r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',
    ]

    for pattern in json_patterns:
        matches = re.findall(pattern, response, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

    return None


def _extract_reference_data_basic(docs: list, params: dict) -> Optional[dict]:
    """
    Fallback: estrazione basica dai metadata dei documenti.
    Integra anche dati dal pump database locale.
    """

    # Prendi il documento più rilevante (se disponibile)
    best_doc = docs[0] if docs else {}
    source = best_doc.get("source", best_doc.get("metadata", {}).get("source", "database locale"))

    # Cerca componenti con peso nel pump database per la famiglia selezionata
    components = {}
    try:
        from weight_engine.pump_database import get_pumps_by_family
        family = params.get("pump_family", "")
        if family:
            family_pumps = get_pumps_by_family(family)
            for p in family_pumps:
                comp_type = p.get("component_type", "unknown")
                weight = p.get("weight_kg")
                if weight and weight > 0:
                    # Se abbiamo già questo componente, tieni il più pesante (o aggiungi suffisso)
                    key = comp_type
                    if key in components:
                        # Tieni il peso migliore (finished > raw > generic)
                        existing_type = components[key].get("weight_type", "generic")
                        new_type = p.get("weight_type", "generic")
                        priority = {"finished": 0, "premachined": 1, "raw": 2, "generic": 3}
                        if priority.get(new_type, 99) < priority.get(existing_type, 99):
                            components[key] = {
                                "weight_kg": weight,
                                "weight_type": new_type,
                                "material": p.get("material_primary", ""),
                                "source": p.get("filename", ""),
                            }
                    else:
                        components[key] = {
                            "weight_kg": weight,
                            "weight_type": p.get("weight_type", "generic"),
                            "material": p.get("material_primary", ""),
                            "source": p.get("filename", ""),
                        }
    except Exception as e:
        logger.warning(f"Errore lettura pump database per riferimento: {e}")

    has_components = any(c.get("weight_kg", 0) > 0 for c in components.values())

    return {
        "source": source if has_components else "none",
        "pump_family": params.get("pump_family", ""),
        "nq": params.get("nq", 0),
        "material": "Carbon Steel",
        "wall_thickness": params.get("wall_thickness", 0),
        "components": components,
        "confidence_note": f"Dati estratti dal database locale ({len(components)} componenti)."
                          if has_components else
                          "Dati estratti da metadata base, senza analisi AI. "
                          "I pesi dei componenti di riferimento non sono disponibili.",
    }


# ============================================================
# ANALISI COMPATIBILITÀ POMPA
# ============================================================

def score_reference_compatibility(ref_data: dict, target_params: dict) -> float:
    """
    Calcola un punteggio di compatibilità (0-100) tra pompa di riferimento e target.

    Fattori considerati:
    - Stessa famiglia pompa
    - Vicinanza Nq
    - Stesso tipo di materiale
    - Numero componenti con pesi disponibili
    """
    score = 0
    max_score = 100

    # Famiglia pompa (30 punti)
    ref_family = ref_data.get("pump_family", "")
    target_family = target_params.get("pump_family", "")
    if ref_family and target_family:
        if ref_family.upper() == target_family.upper():
            score += 30
        elif ref_family[:2] == target_family[:2]:  # Stesso tipo (OH, BB, VS)
            score += 15

    # Nq (25 punti)
    ref_nq = ref_data.get("nq", 0)
    target_nq = target_params.get("nq", 0)
    if ref_nq > 0 and target_nq > 0:
        ratio = min(ref_nq, target_nq) / max(ref_nq, target_nq)
        score += int(25 * ratio)

    # Materiale (20 punti)
    ref_mat = ref_data.get("material", "")
    target_mat = target_params.get("material", "")
    if ref_mat and target_mat:
        if ref_mat.lower() == target_mat.lower():
            score += 20
        else:
            # Stessa classe di materiale
            from .materials import get_density
            rho_ref = get_density(ref_mat)
            rho_target = get_density(target_mat)
            if rho_ref and rho_target:
                density_ratio = min(rho_ref, rho_target) / max(rho_ref, rho_target)
                if density_ratio > 0.9:
                    score += 10

    # Componenti disponibili (25 punti)
    components = ref_data.get("components", {})
    n_components = len([c for c in components.values()
                        if isinstance(c, dict) and c.get("weight_kg", 0) > 0])
    score += min(25, n_components * 5)  # Max 25 punti per 5+ componenti con peso

    return min(score, max_score)

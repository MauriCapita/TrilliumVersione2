"""
Trillium RAG - Relevance Feedback Loop
Usa i dati di feedback (👍/👎) per aggiustare i pesi di ricerca futuri.
Documenti spesso citati in risposte positive → score boost.
Documenti citati in risposte negative → score penalty.
"""

import os
import json
import re
from typing import Dict


_FEEDBACK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "feedback_data.json")
_BOOST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "relevance_boosts.json")


def _load_feedback() -> list:
    """Carica i dati di feedback."""
    try:
        if os.path.exists(_FEEDBACK_FILE):
            with open(_FEEDBACK_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _load_boosts() -> dict:
    """Carica i boost di rilevanza."""
    try:
        if os.path.exists(_BOOST_FILE):
            with open(_BOOST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_boosts(boosts: dict):
    """Salva i boost di rilevanza."""
    try:
        with open(_BOOST_FILE, "w", encoding="utf-8") as f:
            json.dump(boosts, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def compute_boosts() -> dict:
    """
    Analizza tutti i feedback e calcola boost/penalty per ogni sorgente.
    Chiamare periodicamente o dopo ogni feedback.
    
    Returns:
        Dict {source_path: boost_score} dove:
        - boost_score > 0 = documento affidabile
        - boost_score < 0 = documento problematico
    """
    feedback = _load_feedback()
    if not feedback:
        return {}

    source_scores = {}  # {source: {"positive": N, "negative": N}}

    for entry in feedback:
        rating = entry.get("rating", "")
        answer = entry.get("answer", "")
        
        # Estrai riferimenti a documenti dalla risposta
        sources = set()
        # Pattern: [SOP-518], [Mod.497], nomi file
        for match in re.finditer(r"\[([^\]]+)\]", answer):
            sources.add(match.group(1))
        
        for source in sources:
            if source not in source_scores:
                source_scores[source] = {"positive": 0, "negative": 0}
            if rating == "positive":
                source_scores[source]["positive"] += 1
            elif rating == "negative":
                source_scores[source]["negative"] += 1

    # Calcola boost normalizzato
    boosts = {}
    for source, counts in source_scores.items():
        total = counts["positive"] + counts["negative"]
        if total >= 2:  # Minimo 2 valutazioni per essere significativo
            # Score: -1.0 (tutto negativo) a +1.0 (tutto positivo)
            score = (counts["positive"] - counts["negative"]) / total
            boosts[source] = round(score, 3)

    _save_boosts(boosts)
    return boosts


def apply_relevance_boosts(docs: list, boost_weight: float = 0.15) -> list:
    """
    Applica i boost di rilevanza ai documenti recuperati.
    Documenti con feedback positivo salgono, negativi scendono.
    
    Args:
        docs: Lista documenti
        boost_weight: Quanto influisce il feedback (0.0-1.0)
    
    Returns:
        Lista documenti riordinati
    """
    boosts = _load_boosts()
    if not boosts or not docs:
        return docs

    scored = []
    n = len(docs)
    for i, doc in enumerate(docs):
        source = doc.get("source", "")
        # Score base: posizione inversa (normalizzata 0-1)
        base_score = 1.0 - (i / n) if n > 1 else 1.0
        
        # Cerca boost per questa sorgente
        doc_boost = 0.0
        source_lower = source.lower()
        for key, boost_val in boosts.items():
            if key.lower() in source_lower or source_lower in key.lower():
                doc_boost = boost_val
                break
            # Match parziale: SOP-518 in percorso
            if re.search(re.escape(key), source, re.IGNORECASE):
                doc_boost = boost_val
                break

        # Score finale
        final_score = base_score + (doc_boost * boost_weight)
        scored.append((final_score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in scored]

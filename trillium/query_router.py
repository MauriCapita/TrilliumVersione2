"""
Trillium RAG - Query Router
Instrada automaticamente domande diverse verso strategie di ricerca ottimali.
- Formule/numeri → keyword matching pesante (BM25)
- Concetti/spiegazioni → semantica pura
- SOP/Mod specifico → filtra direttamente per documento
- Confronti → decomposizione automatica
"""

import re


# Patterns per classificazione query
_FORMULA_PATTERNS = [
    r"formula", r"calcol[oia]", r"equazion[ei]", r"valore numerico",
    r"\d+[\.,]\d+", r"[=<>≤≥±]", r"coefficiente", r"parametro",
]
_SPECIFIC_DOC_PATTERNS = [
    r"SOP[-_\s]?(\d{3,4})", r"Mod\.?\s?(\d{3,4})",
    r"paragrafo", r"sezione\s+\d", r"capitolo\s+\d",
    r"§\s*\d",
]
_COMPARISON_PATTERNS = [
    r"differenz[ae]", r"confronta", r"vs\.?", r"rispetto a",
    r"meglio", r"peggio", r"vantaggi", r"svantaggi",
]
_CONCEPTUAL_PATTERNS = [
    r"cos[aì]è", r"cosa\s+significa", r"spieg[ami]", r"come\s+funziona",
    r"perché", r"qual[ei]\s+(è|sono)", r"descrivi",
]


def classify_query(query: str) -> dict:
    """
    Classifica il tipo di query e restituisce la strategia ottimale.
    
    Returns:
        dict con:
        - type: "formula", "specific_doc", "comparison", "conceptual", "general"
        - bm25_weight: peso BM25 da usare nella ricerca ibrida (0.0-1.0)
        - doc_filter: eventuale filtro documento specifico
        - should_decompose: se decomporre la query
        - hyde_enabled: se usare HyDE
    """
    q = query.lower()
    result = {
        "type": "general",
        "bm25_weight": 0.3,    # Default bilanciato
        "doc_filter": None,
        "should_decompose": False,
        "hyde_enabled": True,
    }

    # 1. Domanda su formula/calcolo → keyword pesante
    formula_score = sum(1 for p in _FORMULA_PATTERNS if re.search(p, q, re.IGNORECASE))
    if formula_score >= 2:
        result["type"] = "formula"
        result["bm25_weight"] = 0.6  # Keyword matching forte
        result["hyde_enabled"] = False  # HyDE meno utile per formule esatte
        return result

    # 2. Documento specifico → filtro diretto
    sop_match = re.search(r"SOP[-_\s]?(\d{3,4})", query, re.IGNORECASE)
    mod_match = re.search(r"Mod\.?\s?(\d{3,4})", query, re.IGNORECASE)
    if sop_match or mod_match:
        specific_score = sum(1 for p in _SPECIFIC_DOC_PATTERNS if re.search(p, q, re.IGNORECASE))
        if specific_score >= 2:
            result["type"] = "specific_doc"
            result["bm25_weight"] = 0.5  # Mix keyword + semantica
            if sop_match:
                sop_num = int(sop_match.group(1))
                result["doc_filter"] = {"sop_min": sop_num, "sop_max": sop_num}
            return result

    # 3. Confronto → decomposizione
    comparison_score = sum(1 for p in _COMPARISON_PATTERNS if re.search(p, q, re.IGNORECASE))
    if comparison_score >= 1:
        result["type"] = "comparison"
        result["should_decompose"] = True
        result["bm25_weight"] = 0.3
        return result

    # 4. Concettuale → semantica pura + HyDE
    conceptual_score = sum(1 for p in _CONCEPTUAL_PATTERNS if re.search(p, q, re.IGNORECASE))
    if conceptual_score >= 1:
        result["type"] = "conceptual"
        result["bm25_weight"] = 0.1  # Quasi solo semantica
        result["hyde_enabled"] = True  # HyDE molto utile per concetti
        return result

    return result


def get_routing_description(route: dict) -> str:
    """Descrizione human-readable della strategia scelta."""
    descriptions = {
        "formula": "Ricerca formula/calcolo → keyword matching prioritario",
        "specific_doc": "Documento specifico → filtro diretto + mix keyword/semantica",
        "comparison": "Confronto → decomposizione in sotto-query",
        "conceptual": "Domanda concettuale → ricerca semantica + HyDE",
        "general": "Domanda generica → strategia bilanciata",
    }
    return descriptions.get(route["type"], "Strategia standard")

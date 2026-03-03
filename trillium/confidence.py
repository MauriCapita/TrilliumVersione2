"""
Trillium RAG - Confidence Score
Calcola un punteggio di confidenza basato sulla similarità dei documenti recuperati.
"""


def calculate_confidence(docs: list, query: str) -> dict:
    """
    Calcola un confidence score (0-100) basato su:
    - Numero di documenti trovati
    - Presenza di SOP/Mod nel risultato
    - Lunghezza del testo recuperato
    
    Returns:
        {"score": int 0-100, "level": "alta"|"media"|"bassa", "message": str}
    """
    if not docs:
        return {
            "score": 0,
            "level": "bassa",
            "message": "Nessun documento trovato per questa domanda.",
        }

    score = 0

    # 1. Numero documenti (max 30 punti)
    n_docs = len(docs)
    if n_docs >= 5:
        score += 30
    elif n_docs >= 3:
        score += 20
    elif n_docs >= 1:
        score += 10

    # 2. Documenti con testo sostanziale (max 30 punti)
    substantial = sum(1 for d in docs if len(d.get("text", "")) > 200)
    if substantial >= 4:
        score += 30
    elif substantial >= 2:
        score += 20
    elif substantial >= 1:
        score += 10

    # 3. Presenza di SOP o Mod nei documenti (max 20 punti)
    import re
    has_sop = any(re.search(r"SOP[-\s]?\d{3,4}", d.get("source", "") + d.get("text", "")[:500], re.IGNORECASE) for d in docs)
    has_mod = any(re.search(r"Mod\.?\s?\d{3,4}", d.get("source", "") + d.get("text", "")[:500], re.IGNORECASE) for d in docs)
    if has_sop:
        score += 10
    if has_mod:
        score += 10

    # 4. Rilevanza testuale — query keywords nel testo (max 20 punti)
    query_words = set(w.lower() for w in re.findall(r"\w{3,}", query) if len(w) >= 3)
    if query_words:
        total_matches = 0
        for d in docs[:5]:  # Solo primi 5 per velocità
            text_lower = d.get("text", "")[:1000].lower()
            matches = sum(1 for w in query_words if w in text_lower)
            total_matches += matches
        
        match_ratio = total_matches / (len(query_words) * min(len(docs), 5))
        if match_ratio > 0.5:
            score += 20
        elif match_ratio > 0.2:
            score += 10
        elif match_ratio > 0:
            score += 5

    # Classifica
    score = min(100, max(0, score))
    if score >= 70:
        level = "alta"
        message = "I documenti recuperati coprono bene questa domanda."
    elif score >= 40:
        level = "media"
        message = "Copertura parziale. Alcuni aspetti potrebbero non essere documentati."
    else:
        level = "bassa"
        message = "Pochi documenti rilevanti trovati. La risposta potrebbe essere incompleta."

    return {"score": score, "level": level, "message": message}

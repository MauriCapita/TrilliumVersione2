"""
Trillium RAG - HyDE (Hypothetical Document Embedding)
Genera una risposta ipotetica alla domanda, poi usa il suo embedding
per cercare documenti simili. Migliora il retrieval del 20-30%.
"""

from config import OPENAI_API_KEY


def generate_hypothetical_document(query: str) -> str:
    """
    Genera un documento ipotetico che risponderebbe alla query.
    L'embedding di questo documento viene usato per il retrieval
    (più simile ai documenti reali rispetto all'embedding della query).
    
    Returns:
        Testo del documento ipotetico, o la query originale se fallisce.
    """
    if not OPENAI_API_KEY:
        return query

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"""Sei un ingegnere esperto di pompe centrifughe.
Scrivi un breve paragrafo tecnico (100-150 parole) che potrebbe trovarsi
in un documento SOP o Mod di Trillium e che risponderebbe a questa domanda:

"{query}"

Includi terminologia tecnica, numeri di riferimento SOP/Mod plausibili,
e formule se rilevanti. Scrivi in italiano tecnico."""
            }],
            temperature=0.7,  # Un po' di creatività per diversificazione
            max_tokens=250,
        )

        hypothetical = response.choices[0].message.content.strip()
        if hypothetical and len(hypothetical) > 30:
            return hypothetical
        return query

    except Exception:
        return query


def hyde_search(query: str, retrieve_func, n_results: int = 8) -> list:
    """
    Esegue HyDE: genera documento ipotetico, poi cerca documenti simili.
    Combina risultati di ricerca con query originale + documento ipotetico.
    
    Args:
        query: Domanda originale
        retrieve_func: Funzione di retrieval (retrieve_vector_docs)
        n_results: Numero risultati desiderati
    
    Returns:
        Lista documenti ordinati per rilevanza
    """
    # Retrieval con query originale
    original_docs = retrieve_func(query)
    
    # Genera documento ipotetico
    hyp_doc = generate_hypothetical_document(query)
    
    if hyp_doc == query:
        # HyDE non disponibile, usa solo risultati originali
        return original_docs

    # Retrieval con documento ipotetico
    hyde_docs = retrieve_func(hyp_doc)
    
    # Merge: prima i documenti originali, poi quelli HyDE non duplicati
    seen_ids = {d.get("id", "") for d in original_docs}
    merged = list(original_docs)
    
    for doc in hyde_docs:
        doc_id = doc.get("id", "")
        if doc_id and doc_id not in seen_ids:
            doc["_hyde"] = True  # Marca come trovato via HyDE
            merged.append(doc)
            seen_ids.add(doc_id)

    return merged[:n_results * 2]  # Restituisci un po' di più per il re-ranking

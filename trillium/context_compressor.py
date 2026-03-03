"""
Trillium RAG - Context Compressor
Comprime i documenti recuperati rimuovendo parti irrilevanti prima di inviarli all'LLM.
Riduce token → risposta più veloce e focalizzata.
"""

import re
from config import OPENAI_API_KEY


def compress_context(query: str, docs: list, max_chars_per_doc: int = 2000) -> list:
    """
    Comprime i documenti mantenendo solo le parti rilevanti alla query.
    
    Strategia:
    1. Divide ogni documento in paragrafi
    2. Scorerrà ogni paragrafo per rilevanza
    3. Tieni solo i paragrafi più rilevanti fino al limite di caratteri
    
    Args:
        query: La domanda dell'utente
        docs: Lista documenti (con "text" e "source")
        max_chars_per_doc: Massimo caratteri per documento dopo compressione
    
    Returns:
        Lista documenti compressi
    """
    if not docs:
        return docs

    query_terms = set(re.findall(r"\w{3,}", query.lower()))
    compressed = []

    for doc in docs:
        text = doc.get("text", "")
        
        # Se il testo è già corto, tienilo com'è
        if len(text) <= max_chars_per_doc:
            compressed.append(doc)
            continue

        # Dividi in paragrafi/sezioni
        paragraphs = re.split(r"\n\s*\n|\n(?=[A-Z0-9])", text)
        if not paragraphs:
            compressed.append(doc)
            continue

        # Calcola score di rilevanza per ogni paragrafo
        scored_paragraphs = []
        for p in paragraphs:
            p = p.strip()
            if len(p) < 20:
                continue
            p_words = set(re.findall(r"\w{3,}", p.lower()))
            overlap = len(query_terms & p_words)
            # Bonus per numeri SOP/Mod, formule, tabelle
            bonus = 0
            if re.search(r"SOP[-_\s]?\d{3,4}", p, re.IGNORECASE):
                bonus += 2
            if re.search(r"Mod\.?\s?\d{3,4}", p, re.IGNORECASE):
                bonus += 2
            if re.search(r"[=<>≤≥±]", p):
                bonus += 1  # Formule
            if re.search(r"\d+[\.,]\d+", p):
                bonus += 1  # Valori numerici
            scored_paragraphs.append((overlap + bonus, p))

        # Ordina per rilevanza e prendi i migliori
        scored_paragraphs.sort(key=lambda x: x[0], reverse=True)
        
        kept = []
        total_chars = 0
        for score, p in scored_paragraphs:
            if total_chars + len(p) > max_chars_per_doc:
                break
            kept.append(p)
            total_chars += len(p)

        # Se non ha trovato nulla di rilevante, prendi l'inizio
        if not kept:
            kept = [text[:max_chars_per_doc]]

        compressed_doc = dict(doc)
        compressed_doc["text"] = "\n\n".join(kept)
        compressed_doc["_compressed"] = True
        compressed.append(compressed_doc)

    return compressed


def compress_context_llm(query: str, docs: list) -> list:
    """
    Compressione avanzata con LLM: estrae solo le parti rilevanti alla query.
    Più costoso ma più preciso della compressione rule-based.
    Usare solo se necessario (molti documenti lunghi).
    """
    if not OPENAI_API_KEY or not docs:
        return compress_context(query, docs)
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        compressed = []
        for doc in docs:
            text = doc.get("text", "")
            if len(text) < 500:
                compressed.append(doc)
                continue
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": f"""Estrai SOLO le parti del testo seguente che sono rilevanti per questa domanda.
Mantieni formule, numeri, nomi di documenti (SOP, Mod) e riferimenti tecnici.
NON aggiungere commenti, restituisci solo il testo estratto.

DOMANDA: {query}

TESTO:
{text[:3000]}"""
                }],
                temperature=0,
                max_tokens=1000,
            )
            
            extracted = response.choices[0].message.content.strip()
            compressed_doc = dict(doc)
            compressed_doc["text"] = extracted
            compressed_doc["_compressed"] = True
            compressed.append(compressed_doc)
        
        return compressed
    except Exception:
        return compress_context(query, docs)

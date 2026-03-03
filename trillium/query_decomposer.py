"""
Trillium RAG - Query Decomposer
Per domande complesse multi-parte, le spezza in sotto-query,
recupera documenti per ciascuna, poi li unsce senza duplicati.
"""

import re
from config import OPENAI_API_KEY


def should_decompose(query: str) -> bool:
    """
    Determina se una query è abbastanza complessa da richiedere decomposizione.
    """
    indicators = [
        # Confronti
        r"\bdifferenz[ae]\b", r"\bconfrontare?\b", r"\bvs\.?\b", r"\brispetto\b",
        r"\bcompared?\b", r"\bdifference\b",
        # Multi-parte
        r"\be\s+(anche|inoltre|in più)\b", r"\binoltre\b",
        # Liste
        r"\btutt[ie]\b.*\b(SOP|Mod)\b", r"\bquali\b.*\b(SOP|Mod)\b",
        # Cause/effetto
        r"\bperché\b.*\be\b.*\bcome\b",
    ]
    q = query.lower()
    matches = sum(1 for p in indicators if re.search(p, q))
    
    # Decomposizione se: query lunga + keyword match, o SOP/Mod multipli
    sop_count = len(re.findall(r"SOP[-_\s]?\d{3,4}", query, re.IGNORECASE))
    mod_count = len(re.findall(r"Mod\.?\s?\d{3,4}", query, re.IGNORECASE))
    
    return matches >= 1 or (sop_count + mod_count) >= 2 or len(query.split()) > 25


def decompose_query(query: str) -> list:
    """
    Decompone una query complessa in sotto-query più semplici.
    
    Returns:
        Lista di sotto-query (1-3 query). Se non serve decomposizione, [query originale].
    """
    if not should_decompose(query):
        return [query]

    if not OPENAI_API_KEY:
        return [query]  # Fallback: non decomporre

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"""Sei un esperto di documentazione tecnica su pompe centrifughe.
La seguente domanda è complessa. Scomponila in 2-3 sotto-domande più semplici e specifiche
che insieme coprano l'intera domanda originale.

DOMANDA: {query}

Rispondi con una sotto-domanda per riga, senza numerazione o prefissi.
Non aggiungere spiegazioni."""
            }],
            temperature=0,
            max_tokens=200,
        )

        text = response.choices[0].message.content.strip()
        sub_queries = [line.strip() for line in text.split("\n") if line.strip() and len(line.strip()) > 10][ :3]
        
        if sub_queries:
            return sub_queries
        return [query]

    except Exception:
        return [query]


def merge_docs(all_docs_lists: list) -> list:
    """
    Unisce documenti da più sotto-query senza duplicati.
    Mantiene l'ordine di rilevanza.
    """
    merged = []
    seen_ids = set()
    
    for docs in all_docs_lists:
        for doc in docs:
            doc_id = doc.get("id", "")
            if doc_id and doc_id not in seen_ids:
                merged.append(doc)
                seen_ids.add(doc_id)
            elif not doc_id:
                # Deduplicazione basata su source + primi 100 chars
                key = f"{doc.get('source', '')}_{doc.get('text', '')[:100]}"
                if key not in seen_ids:
                    merged.append(doc)
                    seen_ids.add(key)

    return merged

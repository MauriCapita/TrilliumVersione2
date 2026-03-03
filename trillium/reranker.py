"""
Trillium RAG - Re-Ranking
Ri-ordina i documenti recuperati dal retrieval usando un cross-encoder LLM leggero.
Migliora significativamente la precisione delle risposte.
"""

from config import OPENAI_API_KEY
from rich import print


def rerank_documents(query: str, docs: list, top_n: int = None) -> list:
    """
    Ri-ordina i documenti per rilevanza usando GPT-4o-mini come cross-encoder.
    
    Args:
        query: Domanda dell'utente
        docs: Lista di documenti recuperati (con "text" e "source")
        top_n: Numero documenti da restituire (None = tutti, riordinati)
    
    Returns:
        Lista documenti riordinati per rilevanza
    """
    if not docs or len(docs) <= 1:
        return docs

    if not OPENAI_API_KEY:
        print("[yellow]Re-ranking non disponibile (nessuna chiave OpenAI)[/yellow]")
        return docs

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        # Prepara i documenti per il re-ranking (max 15 per costo/velocità)
        candidates = docs[:15]
        doc_summaries = []
        for i, d in enumerate(candidates):
            text = d.get("text", "")[:300]
            source = d.get("source", "sconosciuto")
            doc_summaries.append(f"[{i}] Source: {source}\nText: {text}")

        prompt = f"""Sei un esperto di documentazione tecnica su pompe centrifughe.
Data questa domanda e la lista di documenti, ordina i documenti dal PIÙ rilevante al MENO rilevante.

DOMANDA: {query}

DOCUMENTI:
{chr(10).join(doc_summaries)}

Rispondi SOLO con gli indici ordinati per rilevanza, separati da virgola.
Esempio: 3,0,2,1,4
Non aggiungere spiegazioni."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=100,
        )

        ranking_text = response.choices[0].message.content.strip()

        # Parse gli indici
        import re
        indices = [int(x.strip()) for x in re.findall(r"\d+", ranking_text)]
        
        # Riordina
        reranked = []
        seen = set()
        for idx in indices:
            if 0 <= idx < len(candidates) and idx not in seen:
                reranked.append(candidates[idx])
                seen.add(idx)
        
        # Aggiungi documenti non menzionati
        for i, d in enumerate(candidates):
            if i not in seen:
                reranked.append(d)

        # Aggiungi documenti oltre il limite iniziale
        if len(docs) > 15:
            reranked.extend(docs[15:])

        if top_n:
            reranked = reranked[:top_n]

        print(f"[dim]  Re-ranking completato: {len(reranked)} documenti[/dim]")
        return reranked

    except Exception as e:
        print(f"[yellow]Re-ranking fallito: {e}[/yellow]")
        return docs

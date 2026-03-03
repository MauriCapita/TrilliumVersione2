"""
Trillium RAG - Query Rewriter
Riscrive la query dell'utente in linguaggio naturale per migliorare il retrieval.
Usa un LLM leggero per espandere sinonimi, termini tecnici e tradurre IT↔EN.
"""

from config import OPENAI_API_KEY, PROVIDER
from rich import print


def rewrite_query(original_query: str) -> str:
    """
    Riscrive la query dell'utente per migliorare il retrieval vettoriale.
    Restituisce la query riscritta (o l'originale se fallisce).
    
    Strategia:
    - Espande sinonimi tecnici (IT + EN)
    - Aggiunge termini correlati (SOP, Mod, normative)
    - Mantiene breve per non diluire il segnale semantico
    """
    if not OPENAI_API_KEY:
        return original_query

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        response = client.chat.completions.create(
            model="gpt-4o-mini",  # modello veloce ed economico
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Sei un assistente che riscrive query di ricerca per un sistema RAG di documentazione "
                        "tecnica su pompe centrifughe (SOP, moduli Excel, normative API/ASME). "
                        "Il tuo compito:\n"
                        "1. Espandi la query con sinonimi tecnici in italiano E inglese.\n"
                        "2. Aggiungi termini correlati (numeri SOP/Mod se noti, normative).\n"
                        "3. Mantieni la query BREVE (max 50 parole).\n"
                        "4. Restituisci SOLO la query riscritta, nient'altro.\n"
                        "5. NON aggiungere spiegazioni o commenti."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Riscrivi questa query per ricerca semantica:\n{original_query}",
                },
            ],
            temperature=0.3,
            max_tokens=150,
        )

        rewritten = response.choices[0].message.content.strip()

        # Sanity check: se la risposta è vuota o troppo lunga, usa l'originale
        if not rewritten or len(rewritten) > 500:
            return original_query

        print(f"[dim]  Query riscritta: {rewritten[:80]}...[/dim]")
        return rewritten

    except Exception as e:
        print(f"[yellow]Query rewriting non disponibile: {e}[/yellow]")
        return original_query

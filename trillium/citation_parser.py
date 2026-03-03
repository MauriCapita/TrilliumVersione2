"""
Trillium RAG - Citation Parser
Analizza la risposta LLM per estrarre citazioni inline e costruire
la lista strutturata per il pannello bibliografia.
"""

import re
from typing import List, Dict


def parse_citations(answer_text: str) -> List[Dict]:
    """
    Estrae citazioni inline dalla risposta dell'LLM.
    
    Formati riconosciuti:
    - [SOP-518], [SOP-518 § 5.2.3], [SOP-518 § 5.2.3 Long Seals]
    - [Mod.497], [Mod.497 - Bolts]
    - [API 610], [ASME B73.1], [ISO 13709]
    - Percorsi file tra parentesi o dopo "Percorso:"
    
    Returns:
        Lista di dict: {"id": "SOP-518", "section": "§ 5.2.3", "full": "[SOP-518 § 5.2.3]"}
    """
    citations = []
    seen = set()

    # Pattern 1: [SOP-xxx ...] o [SOP xxx ...]
    for match in re.finditer(r"\[(SOP[-\s]?\d{3,4})([^\]]*)\]", answer_text, re.IGNORECASE):
        doc_id = match.group(1).replace(" ", "-").upper()
        section = match.group(2).strip()
        full = match.group(0)
        key = f"{doc_id}|{section}"
        if key not in seen:
            seen.add(key)
            citations.append({"id": doc_id, "section": section, "full": full, "type": "sop"})

    # Pattern 2: [Mod.xxx ...] o [Mod xxx ...]
    for match in re.finditer(r"\[(Mod\.?\s?\d{3,4})([^\]]*)\]", answer_text, re.IGNORECASE):
        doc_id = match.group(1).replace(" ", "")
        section = match.group(2).strip()
        full = match.group(0)
        key = f"{doc_id}|{section}"
        if key not in seen:
            seen.add(key)
            citations.append({"id": doc_id, "section": section, "full": full, "type": "mod"})

    # Pattern 3: [API xxx], [ASME xxx], [ISO xxx]
    for match in re.finditer(r"\[((?:API|ASME|ISO)\s*[^\]]+)\]", answer_text, re.IGNORECASE):
        doc_id = match.group(1).strip()
        full = match.group(0)
        key = doc_id
        if key not in seen:
            seen.add(key)
            citations.append({"id": doc_id, "section": "", "full": full, "type": "standard"})

    return citations


def match_citations_to_sources(citations: List[Dict], docs: list) -> List[Dict]:
    """
    Collega le citazioni estratte ai documenti recuperati dal database.
    
    Args:
        citations: Lista di citazioni da parse_citations()
        docs: Lista documenti dal retrieval (con "source" e "text")
    
    Returns:
        Lista arricchita: ogni citazione ha un campo "matched_source" se trovata
    """
    for citation in citations:
        cit_id = citation["id"].lower().replace("-", "").replace(".", "").replace(" ", "")
        
        for doc in docs:
            source = doc.get("source", "").lower()
            source_normalized = source.replace("-", "").replace(".", "").replace(" ", "")
            
            if cit_id in source_normalized:
                citation["matched_source"] = doc.get("source", "")
                # Estrai snippet rilevante (prime 200 chars del testo)
                text = doc.get("text", "")
                citation["snippet"] = text[:200].strip() + "..." if len(text) > 200 else text.strip()
                break

    return citations


def get_cited_source_paths(citations: List[Dict]) -> List[str]:
    """
    Restituisce i percorsi dei documenti citati (per evidenziare nel pannello fonti).
    """
    paths = []
    for c in citations:
        if "matched_source" in c and c["matched_source"] not in paths:
            paths.append(c["matched_source"])
    return paths

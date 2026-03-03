"""
Trillium RAG - Filtri di Ricerca
Fornisce filtri per tipo documento, range SOP, estensioni file,
e ricerca ibrida (BM25 keyword matching + semantica).
"""

import re
from typing import List, Dict, Optional


# ============================================================
# FILTRI METADATA PER TIPO DOCUMENTO
# ============================================================

def classify_document(source: str) -> str:
    """
    Classifica un documento in base al nome/percorso.
    Returns: "sop", "mod", "standard", "image", "other"
    """
    s = source.lower()
    basename = s.split("/")[-1].split("\\")[-1]

    if re.search(r"sop[-_\s]?\d{3,4}", basename):
        return "sop"
    if re.search(r"mod\.?\s?\d{3,4}", basename):
        return "mod"
    if any(k in basename for k in ("api ", "api-", "asme", "iso ")):
        return "standard"
    
    ext = basename.rsplit(".", 1)[-1] if "." in basename else ""
    if ext in ("png", "jpg", "jpeg", "tif", "tiff", "bmp", "heic"):
        return "image"
    
    return "other"


def filter_docs_by_type(docs: list, doc_types: List[str]) -> list:
    """
    Filtra documenti per tipo (sop, mod, standard, other).
    Se doc_types è vuoto, restituisce tutti.
    """
    if not doc_types:
        return docs
    return [d for d in docs if classify_document(d.get("source", "")) in doc_types]


def filter_docs_by_sop_range(docs: list, sop_min: int, sop_max: int) -> list:
    """
    Filtra documenti SOP per range numerico (es. 500-530).
    """
    filtered = []
    for d in docs:
        source = d.get("source", "")
        match = re.search(r"SOP[-_\s]?(\d{3,4})", source, re.IGNORECASE)
        if match:
            num = int(match.group(1))
            if sop_min <= num <= sop_max:
                filtered.append(d)
        else:
            # Non è una SOP, includila comunque
            filtered.append(d)
    return filtered


# ============================================================
# FILTRI ESTENSIONI FILE PER INDICIZZAZIONE
# ============================================================

DEFAULT_EXTENSIONS = {
    "pdf", "docx", "doc", "xlsx", "xls", "pptx", "ppt",
    "txt", "md", "csv", "rtf",
    "png", "jpg", "jpeg", "tif", "tiff", "bmp", "heic",
}

def filter_files_by_extension(file_paths: list, include_ext: set = None, exclude_ext: set = None) -> list:
    """
    Filtra percorsi file per estensione.
    include_ext: set di estensioni da includere (es. {"pdf", "docx"})
    exclude_ext: set di estensioni da escludere
    """
    result = []
    for path in file_paths:
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        if include_ext and ext not in include_ext:
            continue
        if exclude_ext and ext in exclude_ext:
            continue
        result.append(path)
    return result


# ============================================================
# RICERCA IBRIDA: BM25 (KEYWORD) + SEMANTICA
# ============================================================

def bm25_score(query: str, text: str) -> float:
    """
    Calcola un score BM25 semplificato per keyword matching.
    """
    query_terms = set(re.findall(r"\w{3,}", query.lower()))
    text_lower = text.lower()
    text_words = re.findall(r"\w{3,}", text_lower)
    
    if not query_terms or not text_words:
        return 0.0

    # Term frequency normalizzata
    doc_len = len(text_words)
    avg_len = 500  # stima
    k1 = 1.2
    b = 0.75
    
    score = 0.0
    word_counts = {}
    for w in text_words:
        word_counts[w] = word_counts.get(w, 0) + 1

    for term in query_terms:
        tf = word_counts.get(term, 0)
        if tf > 0:
            # BM25 formula semplificata
            tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_len / avg_len))
            score += tf_norm

    return score


def hybrid_rerank(query: str, docs: list, bm25_weight: float = 0.3) -> list:
    """
    Combina il ranking semantico (posizione nel risultato) con BM25 keyword score.
    bm25_weight: peso relativo del BM25 (0.0 = solo semantico, 1.0 = solo keyword).
    """
    if not docs:
        return docs

    scored = []
    n = len(docs)
    for i, d in enumerate(docs):
        # Score semantico: inverso della posizione (normalizzato 0-1)
        semantic_score = 1.0 - (i / n) if n > 1 else 1.0
        # Score BM25
        keyword_score = bm25_score(query, d.get("text", ""))
        # Normalizza BM25 (approssimativo)
        max_possible = len(set(re.findall(r"\w{3,}", query.lower()))) * 2
        keyword_norm = min(1.0, keyword_score / max_possible) if max_possible > 0 else 0.0
        # Score combinato
        combined = (1 - bm25_weight) * semantic_score + bm25_weight * keyword_norm
        scored.append((combined, d))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in scored]

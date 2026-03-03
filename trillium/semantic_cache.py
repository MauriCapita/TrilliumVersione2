"""
Trillium RAG - Semantic Cache
Cache intelligente per risposte RAG. Se una domanda simile è già stata fatta,
restituisce la risposta dalla cache senza rifare embedding + LLM call.
Usa hash della query normalizzata + match fuzzy per similarità.
"""

import os
import json
import hashlib
import time
import re
from typing import Optional, Tuple


_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "semantic_cache.json")
_MAX_CACHE_SIZE = 200  # Massimo numero di entry
_CACHE_TTL = 86400 * 7  # 7 giorni


def _normalize_query(query: str) -> str:
    """Normalizza la query per matching."""
    q = query.lower().strip()
    q = re.sub(r"\s+", " ", q)
    q = re.sub(r"[?!.,;:]+$", "", q)
    return q


def _query_hash(query: str) -> str:
    """Hash della query normalizzata."""
    return hashlib.sha256(_normalize_query(query).encode()).hexdigest()[:16]


def _similarity_score(q1: str, q2: str) -> float:
    """Score di similarità semplificato basato su parole condivise."""
    words1 = set(re.findall(r"\w{3,}", _normalize_query(q1)))
    words2 = set(re.findall(r"\w{3,}", _normalize_query(q2)))
    if not words1 or not words2:
        return 0.0
    intersection = words1 & words2
    union = words1 | words2
    return len(intersection) / len(union)  # Jaccard similarity


def _load_cache() -> dict:
    """Carica la cache da disco."""
    try:
        if os.path.exists(_CACHE_FILE):
            with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"entries": {}}


def _save_cache(cache: dict):
    """Salva la cache su disco."""
    try:
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def cache_get(query: str, filters: dict = None, threshold: float = 0.85) -> Optional[Tuple[str, list]]:
    """
    Cerca nella cache una risposta per la query data.
    
    Returns:
        Tuple (answer, docs) se trovata, None altrimenti
    """
    cache = _load_cache()
    now = time.time()
    qhash = _query_hash(query)
    
    # Match esatto per hash
    if qhash in cache["entries"]:
        entry = cache["entries"][qhash]
        if now - entry.get("timestamp", 0) < _CACHE_TTL:
            return entry["answer"], entry.get("docs", [])

    # Match fuzzy per similarità
    best_score = 0.0
    best_entry = None
    for key, entry in cache["entries"].items():
        if now - entry.get("timestamp", 0) >= _CACHE_TTL:
            continue
        score = _similarity_score(query, entry.get("query", ""))
        if score > best_score and score >= threshold:
            best_score = score
            best_entry = entry

    if best_entry:
        return best_entry["answer"], best_entry.get("docs", [])

    return None


def cache_set(query: str, answer: str, docs: list = None):
    """Salva una risposta nella cache."""
    cache = _load_cache()
    qhash = _query_hash(query)
    
    cache["entries"][qhash] = {
        "query": query,
        "answer": answer,
        "docs": [{"source": d.get("source", ""), "text": d.get("text", "")[:200]} for d in (docs or [])],
        "timestamp": time.time(),
    }

    # Pulizia: rimuovi entry scadute e limita dimensione
    now = time.time()
    valid = {k: v for k, v in cache["entries"].items()
             if now - v.get("timestamp", 0) < _CACHE_TTL}
    
    if len(valid) > _MAX_CACHE_SIZE:
        # Rimuovi le più vecchie
        sorted_entries = sorted(valid.items(), key=lambda x: x[1].get("timestamp", 0))
        valid = dict(sorted_entries[-_MAX_CACHE_SIZE:])
    
    cache["entries"] = valid
    _save_cache(cache)


def cache_clear():
    """Svuota la cache."""
    _save_cache({"entries": {}})


def cache_stats() -> dict:
    """Statistiche della cache."""
    cache = _load_cache()
    now = time.time()
    entries = cache.get("entries", {})
    valid = [e for e in entries.values() if now - e.get("timestamp", 0) < _CACHE_TTL]
    return {
        "total_entries": len(entries),
        "valid_entries": len(valid),
        "expired_entries": len(entries) - len(valid),
    }

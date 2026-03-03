"""
Trillium V2 — Context Loader
Carica il file domain_context.md e lo rende disponibile come:
1. Pre-prompt per il LLM (contesto di dominio aggiuntivo)
2. Keywords per augmentation della query di ricerca su Qdrant
"""

import os
import re
import logging

logger = logging.getLogger(__name__)

# Percorso del file di contesto
_CONTEXT_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "domain_context.md"
)

# Cache in memoria (caricato una sola volta)
_domain_context_cache: str | None = None
_keywords_cache: list[str] | None = None


# ============================================================
# 1. PRE-PROMPT: contesto di dominio per il LLM
# ============================================================

def get_domain_context() -> str:
    """
    Restituisce il contenuto di domain_context.md come testo da iniettare
    nel prompt del LLM. Se il file non esiste o è vuoto, restituisce "".
    """
    global _domain_context_cache

    if _domain_context_cache is not None:
        return _domain_context_cache

    if not os.path.exists(_CONTEXT_FILE):
        _domain_context_cache = ""
        return ""

    try:
        with open(_CONTEXT_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
        _domain_context_cache = content
        if content:
            logger.info(f"Domain context caricato: {len(content)} caratteri")
        return content
    except Exception as e:
        logger.warning(f"Errore lettura domain_context.md: {e}")
        _domain_context_cache = ""
        return ""


def get_domain_prompt_section() -> str:
    """
    Restituisce il contesto di dominio formattato come sezione del prompt.
    Pronto per essere iniettato nel system message o nel prompt utente.
    """
    context = get_domain_context()
    if not context:
        return ""

    return f"""
CONTESTO DI DOMINIO (conoscenza di base del sistema):
{context}

Usa queste informazioni come conoscenza di base per interpretare le domande
e i documenti recuperati. Le regole e le formule qui indicate hanno priorità
sulle interpretazioni generiche.
"""


# ============================================================
# 2. QUERY AUGMENTATION: keywords per arricchire la ricerca
# ============================================================

def get_search_keywords() -> list[str]:
    """
    Estrae keywords dal domain_context.md per l'augmentation delle query.
    Restituisce una lista di termini chiave (sinonimi, nomi documenti, termini tecnici).
    """
    global _keywords_cache

    if _keywords_cache is not None:
        return _keywords_cache

    context = get_domain_context()
    if not context:
        _keywords_cache = []
        return []

    keywords = set()

    # Estrai termini dalle tabelle del glossario (formato: | termine | termine | ... |)
    table_rows = re.findall(r'\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|', context)
    for row in table_rows:
        for cell in row:
            cell = cell.strip()
            # Salta header e separatori
            if cell.startswith("-") or cell.startswith("=") or not cell:
                continue
            if "Termine" in cell or "Sinonimi" in cell or "Materiale" in cell:
                continue
            if "Argomento" in cell or "Documenti" in cell or "Densità" in cell:
                continue
            if "Uso tipico" in cell:
                continue
            # Aggiungi termini significativi
            for term in re.split(r'[,/]', cell):
                term = term.strip()
                if len(term) >= 3 and not term.startswith("#"):
                    keywords.add(term)

    # Estrai codici documento (SOP-xxx, Mod.xxx, API xxx)
    doc_codes = re.findall(r'(SOP-\d+|Mod[\. ]\d+|API \d+|ASME [A-Z0-9.]+)', context)
    keywords.update(doc_codes)

    # Estrai codici famiglia pompa
    families = re.findall(r'\b(OH[1-5]|BB[1-5]|VS[1-7])\b', context)
    keywords.update(families)

    _keywords_cache = sorted(keywords)
    logger.info(f"Keywords di dominio estratte: {len(_keywords_cache)}")
    return _keywords_cache


def augment_query(query: str, max_extra_terms: int = 10) -> str:
    """
    Arricchisce la query con termini rilevanti dal contesto di dominio.
    Aggiunge SOLO sinonimi/termini pertinenti alla query originale, non tutto.

    Args:
        query: Query originale dell'utente
        max_extra_terms: Numero massimo di termini extra da aggiungere

    Returns:
        Query arricchita
    """
    keywords = get_search_keywords()
    if not keywords:
        return query

    query_lower = query.lower()
    extra_terms = []

    # Mappa sinonimi dal glossario
    synonym_map = _get_synonym_map()

    for term in synonym_map:
        if term.lower() in query_lower:
            # Trovato un termine nella query → aggiungi i suoi sinonimi
            for synonym in synonym_map[term]:
                if synonym.lower() not in query_lower:
                    extra_terms.append(synonym)

    # Aggiungi codici documento rilevanti
    doc_map = _get_document_map()
    for topic_keyword, docs in doc_map.items():
        if topic_keyword.lower() in query_lower:
            extra_terms.extend(docs)

    # Limita il numero di termini extra
    extra_terms = extra_terms[:max_extra_terms]

    if extra_terms:
        augmented = query + " " + " ".join(extra_terms)
        logger.info(f"Query augmented: +{len(extra_terms)} termini → {augmented[:100]}...")
        return augmented

    return query


# ============================================================
# HELPER: mappe strutturate dal contesto
# ============================================================

def _get_synonym_map() -> dict[str, list[str]]:
    """Mappa termine → lista sinonimi dal glossario."""
    context = get_domain_context()
    if not context:
        return {}

    synonyms = {}

    # Parse tabella glossario
    # Formato: | Termine IT | Termine EN | Sinonimi |
    glossary_section = re.search(
        r'## Glossario e Sinonimi.*?\n(.*?)(?=\n---|\n## |\Z)',
        context, re.DOTALL
    )
    if not glossary_section:
        return {}

    rows = re.findall(
        r'\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|',
        glossary_section.group(1)
    )
    for it_term, en_term, extra in rows:
        it_term = it_term.strip()
        en_term = en_term.strip()
        extra = extra.strip()

        if it_term.startswith("-") or "Termine" in it_term:
            continue

        all_terms = [it_term, en_term]
        if extra:
            all_terms.extend([t.strip() for t in re.split(r'[,/]', extra) if t.strip()])

        # Ogni termine mappa a tutti gli altri
        for t in all_terms:
            if len(t) >= 2:
                synonyms[t] = [other for other in all_terms if other != t and len(other) >= 2]

    return synonyms


def _get_document_map() -> dict[str, list[str]]:
    """Mappa keyword argomento → codici documento dal mapping."""
    context = get_domain_context()
    if not context:
        return {}

    doc_map = {}

    # Parse tabella mapping documenti
    mapping_section = re.search(
        r'## Mapping Documenti Chiave.*?\n(.*?)(?=\n---|\n## |\Z)',
        context, re.DOTALL
    )
    if not mapping_section:
        return {}

    rows = re.findall(
        r'\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|',
        mapping_section.group(1)
    )
    for topic, docs in rows:
        topic = topic.strip().lower()
        docs = docs.strip()

        if topic.startswith("-") or "argomento" in topic:
            continue

        # Estrai parole chiave dal topic
        topic_words = [w for w in re.split(r'[\s/]+', topic) if len(w) >= 3]
        # Estrai codici documento
        doc_codes = re.findall(r'(SOP-\d+|Mod[\. ]\d+|API \d+|ASME [A-Z0-9.]+)', docs)

        for word in topic_words:
            doc_map[word] = doc_codes

    return doc_map


def reload_context():
    """Forza il ricaricamento del file di contesto (utile dopo modifiche)."""
    global _domain_context_cache, _keywords_cache
    _domain_context_cache = None
    _keywords_cache = None
    logger.info("Domain context cache invalidata, sarà ricaricato alla prossima richiesta")

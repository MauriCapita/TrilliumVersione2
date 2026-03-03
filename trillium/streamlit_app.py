"""
Trillium RAG System - Interfaccia Streamlit
Entry point principale: configurazione pagina, sidebar, routing.
"""

import os
import sys
import streamlit as st

# Aggiungi il percorso del progetto al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup pagina e stili (DEVE essere la prima chiamata Streamlit)
from modules.styles import setup_page
setup_page()

# Import moduli pagina
from modules import dashboard, indexing, chat, compare, settings
from modules import doc_graph, analytics, weight_estimation, drawing_analysis
from modules import pump_dashboard, manual, trend_analysis
from modules.onboarding import is_onboarding_done, render_onboarding
from modules.helpers import get_db_stats
from config import PROVIDER, VECTOR_DB, PARALLEL_WORKERS
from auth import check_auth, get_allowed_pages, show_user_info_sidebar

# ============================================================
# AUTENTICAZIONE
# ============================================================

check_auth()

# ============================================================
# INIZIALIZZAZIONE SESSION STATE
# ============================================================

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'selected_provider' not in st.session_state:
    st.session_state.selected_provider = PROVIDER

if 'use_web_search' not in st.session_state:
    st.session_state.use_web_search = False
if 'use_depth_reasoning' not in st.session_state:
    st.session_state.use_depth_reasoning = False

if 'indexing_in_progress' not in st.session_state:
    st.session_state.indexing_in_progress = False

if 'indexing_results' not in st.session_state:
    st.session_state.indexing_results = None

if 'last_retrieved_docs' not in st.session_state:
    st.session_state.last_retrieved_docs = []

if 'last_citations' not in st.session_state:
    st.session_state.last_citations = []

if 'last_confidence' not in st.session_state:
    st.session_state.last_confidence = None

if 'suggested_questions' not in st.session_state:
    st.session_state.suggested_questions = []

# ============================================================
# SIDEBAR - NAVIGAZIONE
# ============================================================

# Pagine consentite per il ruolo corrente
allowed_pages = get_allowed_pages()

# Mappa nomi pagina → label
PAGE_LABELS = {
    "Dashboard": "Dashboard",
    "Stima Pesi": "Stima Pesi",
    "Database Pompe": "Database Pompe",
    "Indicizza": "Indicizza Documenti",
    "Chat RAG": "Chat RAG",
    "Confronta Modelli": "Confronta Modelli",
    "Grafo Documenti": "Grafo Documenti",
    "Analytics": "Analytics",
    "Configurazione": "Configurazione",
    "Trend Analysis": "Trend Analysis",
    "Manuale": "Manuale",
}

with st.sidebar:
    st.markdown("## Trillium V2")
    st.markdown("---")

    # Info utente e logout
    show_user_info_sidebar()
    st.markdown("---")

    # Navigazione filtrata per ruolo
    nav_labels = [PAGE_LABELS.get(p, p) for p in allowed_pages]
    page = st.radio(
        "Navigazione",
        nav_labels,
        label_visibility="collapsed",
    )

    # Help contestuale: descrizione della pagina selezionata
    PAGE_HELP = {
        "Dashboard": "Panoramica sistema: statistiche documenti, stato database e configurazione.",
        "Stima Pesi": "Calcola il peso stimato dei componenti di una pompa centrifuga "
                      "a partire da parametri di progetto (famiglia, Nq, pressione, materiale).",
        "Database Pompe": "Consulta i componenti estratti automaticamente dai disegni tecnici "
                         "indicizzati. Cerca per pompa, tipo componente o materiale.",
        "Analisi Disegni": "Inventario della conoscenza: per ogni documento vedi quali dati "
                          "tecnici sono stati estratti e cosa manca (pesi, materiali, dimensioni).",
        "Indicizza Documenti": "Carica e indicizza nuovi documenti tecnici (PDF, Excel, Word, immagini) "
                              "nel database vettoriale per renderli disponibili al sistema.",
        "Chat RAG": "Fai domande in linguaggio naturale sui documenti indicizzati. "
                    "Il sistema cerca nei documenti e genera risposte con fonti citate.",
        "Confronta Modelli": "Confronta le risposte di diversi modelli AI sullo stesso quesito. "
                            "Utile per validare l'accuratezza delle informazioni estratte.",
        "Grafo Documenti": "Visualizza le relazioni tra documenti, componenti e concetti "
                          "come un grafo interattivo navigabile.",
        "Analytics": "Analisi avanzate sull'uso del sistema, query più frequenti e "
                    "copertura documentale.",
        "Configurazione": "Impostazioni del sistema: provider LLM, database, parametri "
                         "di indicizzazione e contesto di dominio.",
        "Trend Analysis": "Analisi storico stime: pattern per famiglia e materiale, "
                         "predizione costi materia prima, confronto con la media, export CSV.",
        "Manuale": "Guida completa del sistema con esempi pratici, workflow tipici, "
                  "FAQ e spiegazione di ogni funzionalità. Un manuale sempre aggiornato.",
    }
    help_text = PAGE_HELP.get(page, "")
    if help_text:
        st.caption(help_text)

    st.markdown("---")

    # Statistiche rapide
    stats = get_db_stats()
    st.markdown("**Statistiche**")
    st.metric("Documenti", stats["total_documents"])
    st.metric("Chunk", stats["total_chunks"])
    st.metric("File Letti", stats.get("files_read", 0))
    if stats.get("files_failed", 0) > 0:
        st.metric("File Non Letti", stats.get("files_failed", 0))
    st.caption(f"DB: {stats['db_size']}")
    st.caption(f"Status: {stats['status']}")

    st.markdown("---")
    st.caption(f"Provider: {PROVIDER}")
    st.caption(f"Database: {VECTOR_DB.upper()}")

    # Help: Contesto di Dominio
    st.markdown("---")
    with st.expander("Contesto di Dominio", expanded=False):
        # Stato attuale
        try:
            from context_loader import get_domain_context, get_search_keywords
            ctx = get_domain_context()
            kw = get_search_keywords()
            if ctx:
                st.success(f"Attivo — {len(ctx)} caratteri, {len(kw)} keywords")
            else:
                st.info("Vuoto — il sistema funziona normalmente")
        except Exception:
            st.info("Non configurato")

        st.markdown("""
**Cos'è?**
Il file `domain_context.md` contiene la "conoscenza di base" del sistema.
Viene usato in due modi:

1. **Pre-prompt**: il contenuto viene passato all'AI prima di ogni risposta,
   così "conosce" già le regole di calcolo, i materiali e le famiglie pompe.

2. **Arricchimento ricerca**: aggiunge sinonimi e codici documento alla ricerca
   per trovare più risultati pertinenti.

**Esempio pratico:**

Senza contesto:
> Cerchi: *"peso casing OH2"*
> → Qdrant cerca solo: `peso casing OH2`

Con contesto:
> Cerchi: *"peso casing OH2"*
> → Qdrant cerca: `peso casing OH2 Corpo pompa corpo housing barrel`
> → Trova anche documenti che usano "corpo pompa" o "housing"!

**Come modificarlo:**
Modifica il file `domain_context.md` nella cartella `trillium/`.
Se lo lasci vuoto, tutto funziona come prima.
        """)

        # Tasto per ricaricare dopo modifiche
        if st.button("Ricarica contesto", key="reload_ctx", use_container_width=True):
            try:
                from context_loader import reload_context
                reload_context()
                st.success("Contesto ricaricato!")
                st.rerun()
            except Exception as e:
                st.error(f"Errore: {e}")

# ============================================================
# ONBOARDING (prima volta)
# ============================================================

if not is_onboarding_done():
    render_onboarding()
    st.stop()

# ============================================================
# ROUTING PAGINE
# ============================================================

if page == "Dashboard":
    dashboard.render()
elif page == "Stima Pesi":
    weight_estimation.render()
elif page == "Database Pompe":
    pump_dashboard.render()
elif page == "Indicizza Documenti":
    indexing.render()
elif page == "Chat RAG":
    chat.render()
elif page == "Confronta Modelli":
    compare.render()
elif page == "Grafo Documenti":
    doc_graph.render()
elif page == "Analytics":
    analytics.render()
elif page == "Analisi Disegni":
    drawing_analysis.render()
elif page == "Configurazione":
    settings.render()
elif page == "Trend Analysis":
    trend_analysis.render()
elif page == "Manuale":
    manual.render()

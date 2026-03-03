"""
Trillium RAG - Pagina Configurazione
"""

import streamlit as st

from config import (
    PROVIDER, VECTOR_DB, CHROMA_DB_PATH,
    OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY,
    QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION_NAME,
    PARALLEL_WORKERS, CHUNK_BATCH_SIZE,
    TOP_K, CHUNK_SIZE, CHUNK_OVERLAP, USE_RERANKING, USE_HYBRID_SEARCH,
    USE_TILE_OCR, TILE_OVERLAP_PCT, TITLE_BLOCK_ZOOM, TILE_VISION_PROVIDER,
)
from modules.helpers import get_db_stats, get_available_providers


def render():
    """Renderizza la pagina Configurazione."""
    st.markdown("# Configurazione Sistema")
    
    # Informazioni database
    st.markdown("## Database Vettoriale")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"**Tipo:** {VECTOR_DB.upper()}")
        if VECTOR_DB == "chromadb":
            st.info(f"**Path:** {CHROMA_DB_PATH}")
        else:
            st.info(f"**Host:** {QDRANT_HOST}:{QDRANT_PORT}")
            st.info(f"**Collection:** {QDRANT_COLLECTION_NAME}")
    
    with col2:
        stats = get_db_stats()
        st.metric("Documenti", stats["total_documents"])
        st.metric("Chunk", stats["total_chunks"])
        st.metric("Dimensione", stats["db_size"])
    
    # Provider LLM
    st.markdown("## Provider LLM")
    
    providers = get_available_providers()
    
    if providers:
        for name, model, code in providers:
            st.success(f"**{name}** ({model})")
    else:
        st.warning("Nessun provider LLM configurato")
    
    # Chiavi API
    st.markdown("## Chiavi API")
    
    api_keys = {
        "OpenAI": OPENAI_API_KEY,
        "Anthropic": ANTHROPIC_API_KEY,
        "Gemini": GEMINI_API_KEY,
        "OpenRouter": OPENROUTER_API_KEY
    }
    
    for name, key in api_keys.items():
        if key:
            masked_key = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "***"
            st.success(f"**{name}:** {masked_key}")
        else:
            st.error(f"**{name}:** Non configurata")
    
    # OCR Disegni Tecnici
    st.markdown("---")
    st.markdown("## OCR Disegni Tecnici")
    st.caption("Configurazione del sistema di lettura a zone (Tile OCR) per disegni tecnici.")

    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Tile OCR", "ON" if USE_TILE_OCR else "OFF")
        st.caption("Divide il disegno in zone per leggere meglio il testo piccolo")
        st.metric("Overlap", f"{int(TILE_OVERLAP_PCT * 100)}%")
        st.caption("Sovrapposizione tra zone adiacenti")
    
    with col2:
        st.metric("Zoom Cartiglio", f"{TITLE_BLOCK_ZOOM}x")
        st.caption("Zoom extra sulla zona cartiglio (title block)")
        
        # Tile Vision Provider con indicatore stato
        provider_labels = {
            "none": "Solo Tesseract (locale)",
            "openai": "Tesseract + GPT-4o Vision",
            "openrouter": "Tesseract + Claude/Gemini",
        }
        provider_label = provider_labels.get(TILE_VISION_PROVIDER, TILE_VISION_PROVIDER)
        if TILE_VISION_PROVIDER == "none":
            st.info(f"**Vision Provider:** {provider_label}")
        else:
            st.success(f"**Vision Provider:** {provider_label}")
    
    with st.expander("Cosa significa Vision Provider per tile OCR?", expanded=False):
        st.markdown("""
**Il sistema divide ogni disegno in zone (tile) e le legge separatamente.**
Puoi scegliere come leggere ogni zona:

| Valore | Cosa fa | Qualita testo | Costo |
|--------|---------|---------------|-------|
| **`none`** | Solo Tesseract (OCR locale) | ~50% del testo | Gratis |
| **`openai`** | Tesseract + GPT-4o Vision su ogni zona | ~90% del testo | Usa API OpenAI |
| **`openrouter`** | Tesseract + Claude/Gemini su ogni zona | ~90% del testo | Usa API OpenRouter |

**Come funziona con `openai` o `openrouter`:**
1. Prima Tesseract legge ogni zona (gratis, veloce)
2. Poi GPT-4o/Claude "guarda" ogni zona e legge tutto il testo visibile
3. I risultati vengono combinati per massima copertura
4. Il cartiglio (basso-destra) viene zoomato 2x per leggere peso, materiale, part number

**Consiglio:** Con abbonamento ChatGPT Enterprise, usa **`openai`** per la massima qualita.

**Per cambiare:** Modifica `TILE_VISION_PROVIDER` nel file `.env`.
        """)
    
    # Performance
    st.markdown("---")
    st.markdown("## Performance")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Parallel Workers", PARALLEL_WORKERS)
        st.caption("Numero di file processati in parallelo")
    
    with col2:
        st.metric("Batch Size", CHUNK_BATCH_SIZE)
        st.caption("Chunk processati insieme per batch")
    
    # Parametri RAG Engine
    st.markdown("---")
    st.markdown("## Motore RAG")

    r1, r2, r3, r4 = st.columns(4)
    with r1:
        st.metric("TOP_K", TOP_K)
        st.caption("Documenti recuperati")
    with r2:
        st.metric("Chunk Size", f"{CHUNK_SIZE}")
        st.caption("Caratteri per chunk")
    with r3:
        st.metric("Overlap", f"{CHUNK_OVERLAP}")
        st.caption("Sovrapposizione chunk")
    with r4:
        st.metric("Re-ranking", "ON" if USE_RERANKING else "OFF")
        st.metric("Hybrid Search", "ON" if USE_HYBRID_SEARCH else "OFF")
    st.caption("Questi parametri influenzano come vengono cercati e scelti i documenti per rispondere alle domande. I valori mostrati sono quelli attualmente in uso (solo lettura).")
    
    r1, r2 = st.columns(2)
    
    with r1:
        with st.container():
            st.markdown("#### 📌 Termini aggiuntivi di ricerca")
            st.caption("Sinonimi o parole correlate che il sistema può includere nella ricerca per allargare i risultati (es. *long seal*, *bushing* per domande sulla boccola).")
            st.markdown("**Valore attuale:** *Non impostato — usa regole interne*")
        
        st.markdown("")
        
        with st.container():
            st.markdown("#### 📄 Documento / paragrafo preferito")
            st.caption("SOP o Mod da privilegiare per certi tipi di domanda, con eventuale paragrafo (es. *SOP-518 § 5.2.3 Long Seals*).")
            st.markdown("**Valore attuale:** *Non impostato — usa regole interne*")
    
    with r2:
        with st.container():
            st.markdown("#### 🔢 Documenti massimi da considerare")
            st.caption("Quanti documenti (chunk) recuperare dalla ricerca vettoriale per costruire il contesto della risposta. Più documenti = più contesto, ma risposta più lenta.")
            st.markdown(f"**Valore attuale:** `{TOP_K}`")
        
        st.markdown("")
        
        with st.container():
            st.markdown("#### 🌐 Espansione ricerca")
            st.caption("Se attiva, per alcune domande (es. analisi laterale + boccola) il sistema lancia anche una ricerca aggiuntiva mirata per includere documenti rilevanti (es. SOP-518 Long Seals).")
            st.markdown("**Valore attuale:** *Attiva — regole interne*")
    
    with st.expander("📋 Dettaglio regole interne (cosa fa il sistema oggi)"):
        st.markdown("""
**📌 Termini aggiuntivi di ricerca**  
- Non ci sono termini aggiuntivi impostabili dall'utente.  
- Il sistema, per **espansione ricerca** (vedi sotto), usa in automatico una query aggiuntiva con termini fissi quando riconosce certi tipi di domanda.

**📄 Documento / paragrafo preferito**  
- Per domande su **analisi laterale** e **posizionamento stazioni** in presenza di **boccola, bushing, long seal, wear ring**, il prompt istruisce il modello a:  
  - cercare nel contesto **SOP-518** e la sezione **§ 5.2.3 Long Seals**;  
  - basare la risposta su quella sezione e citarla in «Riferimenti documenti da scaricare»;  
  - se SOP-518 non è nei documenti recuperati, indicare comunque all'utente di consultare **SOP-518 § 5.2.3 Long Seals** per le regole sulle stazioni.

**🔢 Documenti massimi da considerare**  
- Valore letto da configurazione: **TOP_K** (es. 8).  
- È il numero massimo di chunk recuperati dalla ricerca vettoriale per costruire il contesto di ogni risposta.

**🌐 Espansione ricerca**  
- **Condizione:** la domanda contiene *analisi laterale* (o *lateral analysis*) **e** almeno uno tra: *boccola*, *stazioni*, *bending*, *long seal*, *wear ring*, *bushing*, *posizione*.  
- **Azione:** oltre alla ricerca normale, il sistema esegue una **seconda ricerca vettoriale** con la query:  
  *«SOP-518 Long Seals 5.2.3 stazioni posizionamento analisi laterale damped natural frequency boccola bushing»*.  
- I documenti trovati con questa seconda ricerca vengono aggiunti in cima alla lista (senza duplicati), così il modello vede prima il contesto su Long Seals / SOP-518.
        """)
    
    st.markdown("---")
    st.info("💡 Per modificare la configurazione, edita il file `.env` nella root del progetto e riavvia l'applicazione.")

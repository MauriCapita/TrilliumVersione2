"""
Trillium RAG - Pagina Confronto Modelli
"""

import streamlit as st
import pandas as pd

from rag.query import retrieve_relevant_docs, build_context
from config import (
    OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY,
)


def render():
    """Renderizza la pagina Confronto Modelli."""
    st.markdown("# ⚖️ Confronto Modelli LLM")
    
    # Mostra risultati precedenti se esistono
    if 'compare_results' in st.session_state and st.session_state.compare_results:
        st.markdown("### 📊 Risultati Confronto Precedente")
        st.info(f"**Domanda:** {st.session_state.compare_question}")
        st.markdown("---")
    
    question = st.text_input(
        "Domanda da confrontare",
        placeholder="Inserisci una domanda per confrontare le risposte di diversi modelli...",
        help="Tutti i modelli configurati risponderanno a questa domanda usando lo stesso contesto RAG",
        value=st.session_state.get('compare_question', '')
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        compare_button = st.button("▶️ Confronta Modelli", type="primary", use_container_width=True)
    
    if compare_button:
        if question:
            st.session_state.compare_question = question
            
            progress_container = st.container()
            results_container = st.container()
            
            with progress_container:
                st.markdown("### 🔄 Confronto in corso...")
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    status_text.info("📄 Recupero documenti rilevanti...")
                    progress_bar.progress(0.1)
                    
                    docs = retrieve_relevant_docs(question)
                    if not docs:
                        st.warning("⚠️ Nessun documento trovato per questa domanda.")
                        st.stop()
                    
                    prompt = build_context(question, docs)
                    
                    status_text.info(f"Contesto preparato con {len(docs)} documenti. Interrogo i modelli...")
                    progress_bar.progress(0.3)
                    
                    from rag.model_compare import MODEL_LIST, run_model
                    available_models = {}
                    
                    for model_name, cfg in MODEL_LIST.items():
                        provider = cfg["provider"]
                        if (provider == "openai" and OPENAI_API_KEY) or \
                           (provider == "anthropic" and ANTHROPIC_API_KEY) or \
                           (provider == "gemini" and GEMINI_API_KEY) or \
                           (provider == "openrouter" and OPENROUTER_API_KEY):
                            available_models[model_name] = cfg
                    
                    if not available_models:
                        st.error("❌ Nessun modello configurato. Configura almeno una chiave API nel file .env")
                        st.stop()
                    
                    results = {}
                    total_models = len(available_models)
                    
                    for idx, (model_name, cfg) in enumerate(available_models.items()):
                        status_text.info(f"Interrogo {model_name}... ({idx + 1}/{total_models})")
                        progress = 0.3 + (idx + 1) / total_models * 0.7
                        progress_bar.progress(progress)
                        
                        answer = run_model(cfg["provider"], cfg["model"], prompt)
                        if not answer or answer.strip() == "":
                            answer = f"⚠️ Errore: Risposta vuota da {model_name}"
                        results[model_name] = answer
                    
                    st.session_state.compare_results = results
                    
                    progress_bar.progress(1.0)
                    status_text.success("✅ Confronto completato!")
                    
                    st.session_state.compare_results = results
                    st.session_state.just_generated = True
                    
                    progress_bar.empty()
                    status_text.empty()
                    
                except Exception as e:
                    progress_bar.progress(0)
                    status_text.error(f"❌ Errore durante il confronto")
                    st.error(f"❌ Errore: {str(e)}")
                    import traceback
                    with st.expander("🔍 Dettagli Errore"):
                        st.code(traceback.format_exc())
            
            # Mostra risultati (fuori dal container progress)
            if st.session_state.get('compare_results'):
                _show_compare_results(question, st.session_state.compare_results)
        else:
            st.warning("⚠️ Inserisci una domanda per confrontare i modelli")
    
    # Mostra risultati salvati se esistono e non c'è una nuova ricerca in corso
    if 'compare_results' in st.session_state and st.session_state.compare_results and not compare_button:
        if not st.session_state.get('just_generated', False):
            st.markdown("---")
            st.markdown("### 📊 Risultati Confronto Precedente")
            st.markdown(f"**💬 Domanda:** {st.session_state.compare_question}")
            st.markdown("---")
            
            results = st.session_state.compare_results
            
            if len(results) <= 2:
                cols = st.columns(len(results))
                for idx, (model_name, answer) in enumerate(results.items()):
                    with cols[idx]:
                        st.markdown(f"#### {model_name}")
                        st.markdown("---")
                        if answer:
                            st.write(answer)
                        else:
                            st.warning("⚠️ Risposta vuota")
            else:
                tabs = st.tabs(list(results.keys()))
                for idx, (model_name, answer) in enumerate(results.items()):
                    with tabs[idx]:
                        st.markdown(f"**Risposta di {model_name}:**")
                        st.markdown("---")
                        if answer:
                            st.write(answer)
                        else:
                            st.warning("⚠️ Risposta vuota")
            
            if st.button("🗑️ Pulisci Risultati"):
                st.session_state.compare_results = None
                st.session_state.compare_question = None
                st.session_state.just_generated = False
                st.rerun()
        else:
            st.session_state.just_generated = False


def _show_compare_results(question, results):
    """Mostra i risultati del confronto modelli."""
    st.markdown("---")
    st.markdown("### 📊 Risultati Confronto")
    st.markdown(f"**💬 Domanda:** {question}")
    st.markdown("---")
    
    # Mostra risposte in tabs o side-by-side
    if len(results) <= 2:
        cols = st.columns(len(results))
        for idx, (model_name, answer) in enumerate(results.items()):
            with cols[idx]:
                st.markdown(f"#### {model_name}")
                st.markdown("---")
                if answer:
                    st.write(answer)
                else:
                    st.warning("⚠️ Risposta vuota o errore")
    else:
        tabs = st.tabs(list(results.keys()))
        for idx, (model_name, answer) in enumerate(results.items()):
            with tabs[idx]:
                st.markdown(f"**Risposta di {model_name}:**")
                st.markdown("---")
                if answer and answer.strip():
                    with st.container():
                        st.write(answer)
                    with st.expander("🔍 Info Debug"):
                        st.code(f"Lunghezza: {len(answer)} caratteri\nParole: {len(answer.split())}\nPrimi 100 caratteri: {answer[:100]}")
                else:
                    st.error(f"⚠️ Risposta vuota o errore per {model_name}")
                    st.code(f"Risposta ricevuta: {repr(answer)}")
    
    # Tabella comparativa compatta
    st.markdown("---")
    st.markdown("### 📋 Tabella Comparativa")
    
    comparison_data = {
        "Modello": list(results.keys()),
        "Anteprima Risposta": [answer[:200] + "..." if len(answer) > 200 else answer for answer in results.values()],
        "Lunghezza (caratteri)": [len(answer) if answer else 0 for answer in results.values()],
        "Parole": [len(answer.split()) if answer else 0 for answer in results.values()]
    }
    df = pd.DataFrame(comparison_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Metriche
    st.markdown("---")
    st.markdown("### 📈 Metriche")
    metric_cols = st.columns(len(results))
    for idx, (model_name, answer) in enumerate(results.items()):
        with metric_cols[idx]:
            if answer:
                st.metric(
                    model_name.split()[0],
                    f"{len(answer)} caratteri",
                    f"{len(answer.split())} parole"
                )
            else:
                st.metric(model_name.split()[0], "0 caratteri", "Errore")

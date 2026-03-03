"""
Trillium RAG - Pagina Dashboard
"""

import streamlit as st

# Import plotly con fallback
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

from config import (
    PROVIDER, VECTOR_DB, CHROMA_DB_PATH,
    QDRANT_HOST, QDRANT_PORT,
    PARALLEL_WORKERS, CHUNK_BATCH_SIZE,
)
from modules.helpers import get_db_stats, get_document_distribution


def render():
    """Renderizza la pagina Dashboard."""
    st.markdown('<div class="main-header">Trillium RAG System</div>', unsafe_allow_html=True)
    st.caption("ℹ️ Panoramica dello stato del sistema. "
               "**Documenti** = file indicizzati nel DB. **Chunk** = frammenti di testo (ogni documento viene spezzato per la ricerca). "
               "**Tasso Successo** = % file letti correttamente. "
               "Se vedi file 'Non Letti', vai su Indicizza Documenti per verificare i formati.")

    # Statistiche principali
    stats = get_db_stats()

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Documenti", stats["total_documents"])
    with col2:
        st.metric("Chunk", stats["total_chunks"])
    with col3:
        st.metric("File Letti", stats.get("files_read", 0))
    with col4:
        files_failed = stats.get("files_failed", 0)
        if files_failed > 0:
            st.metric("File Non Letti", files_failed, delta=f"-{files_failed}", delta_color="inverse")
        else:
            st.metric("File Non Letti", files_failed)
    with col5:
        st.metric("Status", stats["status"])

    # Seconda riga
    col6, col7 = st.columns(2)
    with col6:
        st.metric("Database", stats["db_size"])
    with col7:
        total_files = stats.get("files_read", 0) + stats.get("files_failed", 0)
        if total_files > 0:
            success_rate = (stats.get("files_read", 0) / total_files) * 100
            st.metric("Tasso Successo", f"{success_rate:.1f}%")
        else:
            st.metric("Tasso Successo", "N/A")

    st.markdown("---")

    # Grafici
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Distribuzione Documenti")
        file_distribution = get_document_distribution()
        total_files = sum(file_distribution.values())

        if total_files > 0:
            if PLOTLY_AVAILABLE:
                labels = list(file_distribution.keys())
                values = list(file_distribution.values())
                filtered_data = [(l, v) for l, v in zip(labels, values) if v > 0]
                if filtered_data:
                    labels_f, values_f = zip(*filtered_data)
                    fig_pie = go.Figure(data=[go.Pie(
                        labels=labels_f, values=values_f, hole=0.4,
                        marker=dict(colors=["#344054", "#667085", "#98a2b3", "#d0d5dd", "#e4e7ec"])
                    )])
                    fig_pie.update_layout(height=300, showlegend=True, margin=dict(l=0, r=0, t=0, b=0))
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("Nessun documento nel database.")
            else:
                st.dataframe({
                    "Tipo": list(file_distribution.keys()),
                    "Quantità": list(file_distribution.values()),
                }, use_container_width=True)
        else:
            st.info("Nessun documento indicizzato. Indicizza alcuni documenti per vedere la distribuzione.")

    with col2:
        st.markdown("### Statistiche Database")
        if PLOTLY_AVAILABLE and total_files > 0:
            labels = list(file_distribution.keys())
            values = list(file_distribution.values())
            filtered_data = [(l, v) for l, v in zip(labels, values) if v > 0]
            if filtered_data:
                labels_f, values_f = zip(*filtered_data)
                fig_bar = px.bar(
                    x=labels_f, y=values_f,
                    labels={"x": "Tipo Documento", "y": "Quantità"},
                    title="Documenti per Tipo",
                    color_discrete_sequence=["#344054"],
                )
                fig_bar.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0))
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.metric("Documenti totali", stats["total_documents"])
        else:
            st.metric("Documenti totali", stats["total_documents"])
            st.metric("Chunk totali", stats["total_chunks"])
            if total_files == 0:
                st.info("Indicizza documenti per vedere statistiche dettagliate.")

    # Configurazione sistema
    st.markdown("---")
    st.markdown("### Configurazione Sistema")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"**Provider LLM:** {PROVIDER.upper()}")
        st.info(f"**Database:** {VECTOR_DB.upper()}")
    with col2:
        if VECTOR_DB == "chromadb":
            st.info(f"**Path DB:** {CHROMA_DB_PATH}")
        else:
            st.info(f"**Qdrant:** {QDRANT_HOST}:{QDRANT_PORT}")
    with col3:
        st.info(f"**Parallel Workers:** {PARALLEL_WORKERS}")
        st.info(f"**Batch Size:** {CHUNK_BATCH_SIZE}")

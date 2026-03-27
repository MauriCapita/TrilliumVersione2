"""
Trillium RAG - Pagina Dashboard (Premium Restyling)
"""

import streamlit as st

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


# Icone per i provider
PROVIDER_ICONS = {
    "openai": "🟢",
    "anthropic": "🟣",
    "gemini": "🔵",
    "openrouter": "🟠",
}

# Colori palette
COLORS = ["#16A34A", "#3B82F6", "#F59E0B", "#EF4444", "#8B5CF6"]


def render():
    """Renderizza la pagina Dashboard con design premium."""

    # ============================================================
    # HERO HEADER
    # ============================================================
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 60%, #bbf7d0 100%);
        border: 1px solid #86efac;
        border-radius: 16px;
        padding: 2rem 2.5rem;
        margin-bottom: 2rem;
        display: flex;
        align-items: center;
        gap: 1.5rem;
        box-shadow: 0 4px 24px -4px rgba(22, 163, 74, 0.12);
    ">
        <div style="font-size: 3.5rem; line-height: 1;">⚙️</div>
        <div>
            <h1 style="
                margin: 0;
                font-size: 2rem;
                font-weight: 800;
                color: #14532d;
                letter-spacing: -0.03em;
            ">Trillium V2</h1>
            <p style="
                margin: 0.3rem 0 0;
                font-size: 1rem;
                color: #166534;
                font-weight: 400;
            ">AI Weight Estimation System · Pompe Centrifughe API 610</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ============================================================
    # STATISTICHE
    # ============================================================
    stats = get_db_stats()
    file_distribution = get_document_distribution()
    total_files = sum(file_distribution.values())

    # Riga metriche con icone
    st.markdown("### 📊 Stato del Sistema")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("📄 Documenti", f"{stats['total_documents']:,}")
    with col2:
        st.metric("🧩 Chunk", f"{stats['total_chunks']:,}")
    with col3:
        st.metric("✅ File Letti", stats.get("files_read", 0))
    with col4:
        files_failed = stats.get("files_failed", 0)
        if files_failed > 0:
            st.metric("❌ Non Letti", files_failed,
                      delta=f"-{files_failed}", delta_color="inverse")
        else:
            st.metric("❌ Non Letti", 0)
    with col5:
        total_f = stats.get("files_read", 0) + stats.get("files_failed", 0)
        if total_f > 0:
            pct = round((stats.get("files_read", 0) / total_f) * 100, 1)
            st.metric("🎯 Successo", f"{pct}%")
        else:
            st.metric("🎯 Successo", "—")

    # Seconda riga
    col6, col7 = st.columns(2)
    with col6:
        status_icon = "🟢" if "Connesso" in stats["status"] or "Attivo" in stats["status"] else "🔴"
        st.metric(f"{status_icon} Database", stats["db_size"])
    with col7:
        st.metric("🗄️ Status", stats["status"])

    st.markdown("---")

    # ============================================================
    # GRAFICI — 2 COLONNE
    # ============================================================
    col_charts_left, col_charts_right = st.columns(2)

    with col_charts_left:
        st.markdown("#### Distribuzione Documenti")

        if total_files > 0 and PLOTLY_AVAILABLE:
            labels = list(file_distribution.keys())
            values = list(file_distribution.values())
            filtered = [(l, v) for l, v in zip(labels, values) if v > 0]
            if filtered:
                lf, vf = zip(*filtered)
                fig_pie = go.Figure(data=[go.Pie(
                    labels=lf,
                    values=vf,
                    hole=0.45,
                    marker=dict(
                        colors=COLORS[:len(lf)],
                        line=dict(color="#ffffff", width=2)
                    ),
                    textinfo="label+percent",
                    textfont=dict(size=12, family="Inter"),
                )])
                fig_pie.update_layout(
                    height=300,
                    showlegend=False,
                    margin=dict(l=10, r=10, t=10, b=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig_pie, use_container_width=True)
        elif total_files == 0:
            st.info("Nessun documento indicizzato ancora.")

    with col_charts_right:
        st.markdown("#### File per Tipo")

        if total_files > 0 and PLOTLY_AVAILABLE:
            filtered = [(l, v) for l, v in zip(
                file_distribution.keys(), file_distribution.values()) if v > 0]
            if filtered:
                lf, vf = zip(*filtered)
                fig_bar = go.Figure(data=[go.Bar(
                    x=list(lf),
                    y=list(vf),
                    marker=dict(
                        color=COLORS[:len(lf)],
                        line=dict(color="rgba(0,0,0,0)"),
                    ),
                    text=list(vf),
                    textposition="outside",
                    textfont=dict(size=12),
                )])
                fig_bar.update_layout(
                    height=300,
                    margin=dict(l=10, r=10, t=10, b=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    showlegend=False,
                    yaxis=dict(showgrid=True, gridcolor="#f0f0f0",
                               zeroline=False, showticklabels=False),
                    xaxis=dict(showgrid=False),
                )
                st.plotly_chart(fig_bar, use_container_width=True)
        elif total_files == 0:
            st.info("Nessun dato da mostrare.")

    st.markdown("---")

    # ============================================================
    # CONFIGURAZIONE SISTEMA — Card stilizzate
    # ============================================================
    st.markdown("### ⚙️ Configurazione Sistema")

    provider_icon = PROVIDER_ICONS.get(PROVIDER.lower(), "⚡")
    db_icon = "🔷" if VECTOR_DB == "qdrant" else "🟡"

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div style="background:#fff;border:1px solid #e4e7ec;border-radius:12px;
                    padding:1rem 1.2rem;box-shadow:0 2px 8px rgba(0,0,0,0.05);">
            <div style="font-size:0.7rem;color:#6b7280;text-transform:uppercase;
                        letter-spacing:0.8px;font-weight:600;margin-bottom:0.4rem;">
                Provider LLM
            </div>
            <div style="font-size:1.1rem;font-weight:700;color:#111827;">
                {provider_icon} {PROVIDER.upper()}
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        db_host = f"{QDRANT_HOST}:{QDRANT_PORT}" if VECTOR_DB == "qdrant" else CHROMA_DB_PATH
        st.markdown(f"""
        <div style="background:#fff;border:1px solid #e4e7ec;border-radius:12px;
                    padding:1rem 1.2rem;box-shadow:0 2px 8px rgba(0,0,0,0.05);">
            <div style="font-size:0.7rem;color:#6b7280;text-transform:uppercase;
                        letter-spacing:0.8px;font-weight:600;margin-bottom:0.4rem;">
                Database
            </div>
            <div style="font-size:1.1rem;font-weight:700;color:#111827;">
                {db_icon} {VECTOR_DB.upper()}
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div style="background:#fff;border:1px solid #e4e7ec;border-radius:12px;
                    padding:1rem 1.2rem;box-shadow:0 2px 8px rgba(0,0,0,0.05);">
            <div style="font-size:0.7rem;color:#6b7280;text-transform:uppercase;
                        letter-spacing:0.8px;font-weight:600;margin-bottom:0.4rem;">
                Parallel Workers
            </div>
            <div style="font-size:1.1rem;font-weight:700;color:#111827;">
                🚀 {PARALLEL_WORKERS}
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div style="background:#fff;border:1px solid #e4e7ec;border-radius:12px;
                    padding:1rem 1.2rem;box-shadow:0 2px 8px rgba(0,0,0,0.05);">
            <div style="font-size:0.7rem;color:#6b7280;text-transform:uppercase;
                        letter-spacing:0.8px;font-weight:600;margin-bottom:0.4rem;">
                Chunk Batch
            </div>
            <div style="font-size:1.1rem;font-weight:700;color:#111827;">
                📦 {CHUNK_BATCH_SIZE}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Endpoint Qdrant opzionale
    if VECTOR_DB == "qdrant":
        st.caption(f"🔗 Qdrant endpoint: `{QDRANT_HOST}:{QDRANT_PORT}`")
    else:
        st.caption(f"🗂️ ChromaDB path: `{CHROMA_DB_PATH}`")

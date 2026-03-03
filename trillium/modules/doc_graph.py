"""
Trillium RAG - Pagina Grafo Documenti
Visualizzazione interattiva dei collegamenti SOP ↔ Mod.
"""

import streamlit as st

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

from sop_mod_mapping import SOP_TO_MOD


def render():
    """Renderizza il grafo interattivo dei collegamenti SOP ↔ Mod."""
    st.markdown("## Grafo Documenti")
    st.caption("Visualizzazione dei collegamenti tra procedure (SOP) e moduli di calcolo (Mod)")

    if not PLOTLY_AVAILABLE:
        st.error("Installa plotly per la visualizzazione: pip install plotly")
        return

    # Costruisci nodi e archi
    nodes = set()
    edges = []
    for sop, mods in SOP_TO_MOD.items():
        nodes.add(sop)
        for mod in mods:
            nodes.add(mod)
            edges.append((sop, mod))

    nodes = sorted(nodes)
    node_idx = {n: i for i, n in enumerate(nodes)}

    # Layout circolare
    import math
    n = len(nodes)
    x_pos = [math.cos(2 * math.pi * i / n) for i in range(n)]
    y_pos = [math.sin(2 * math.pi * i / n) for i in range(n)]

    # Colori: SOP = blu scuro, Mod = grigio
    node_colors = ["#1a2332" if n.startswith("SOP") else "#667085" for n in nodes]
    node_sizes = [18 if n.startswith("SOP") else 14 for n in nodes]

    # Archi
    edge_x, edge_y = [], []
    for sop, mod in edges:
        i, j = node_idx[sop], node_idx[mod]
        edge_x += [x_pos[i], x_pos[j], None]
        edge_y += [y_pos[i], y_pos[j], None]

    # Crea figure
    fig = go.Figure()

    # Archi
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y,
        mode="lines",
        line=dict(width=0.8, color="#d0d5dd"),
        hoverinfo="none",
    ))

    # Nodi
    fig.add_trace(go.Scatter(
        x=x_pos, y=y_pos,
        mode="markers+text",
        marker=dict(size=node_sizes, color=node_colors, line=dict(width=1, color="#e4e7ec")),
        text=nodes,
        textposition="top center",
        textfont=dict(size=8),
        hoverinfo="text",
        hovertext=[
            f"{n} → {', '.join(SOP_TO_MOD.get(n, []))}" if n.startswith("SOP")
            else f"{n} ← usato da ..." for n in nodes
        ],
    ))

    fig.update_layout(
        showlegend=False,
        height=700,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor="#ffffff",
    )

    st.plotly_chart(fig, use_container_width=True)

    # Tabella riepilogativa
    st.markdown("---")
    st.markdown("### Dettaglio Collegamenti")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Totale SOP", len(SOP_TO_MOD))
    with col2:
        all_mods = set()
        for mods in SOP_TO_MOD.values():
            all_mods.update(mods)
        st.metric("Totale Mod", len(all_mods))

    # Ricerca
    search = st.text_input("Cerca SOP o Mod", placeholder="es. SOP-521 o Mod.497")
    
    data_rows = []
    for sop, mods in sorted(SOP_TO_MOD.items()):
        row = {"SOP": sop, "Moduli Collegati": ", ".join(mods)}
        if search:
            s = search.upper().replace(" ", "")
            if s in sop.replace("-", "") or any(s in m.replace(".", "") for m in mods):
                data_rows.append(row)
        else:
            data_rows.append(row)

    if data_rows:
        st.dataframe(data_rows, use_container_width=True, hide_index=True)
    elif search:
        st.info(f"Nessun risultato per '{search}'.")

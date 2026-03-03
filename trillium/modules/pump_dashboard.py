"""
Trillium V2 — Dashboard Pompe
Panoramica visiva di tutte le pompe estratte dai disegni indicizzati:
tabella interattiva, grafici distribuzione, filtri, dettaglio.
"""

import streamlit as st
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


def render():
    """Renderizza la Dashboard Pompe."""

    # Header
    st.markdown("""
    <div style="background: linear-gradient(135deg, hsl(142, 50%, 95%) 0%, hsl(142, 60%, 88%) 100%);
                color: hsl(215, 25%, 15%); padding: 1.5rem 2rem; border-radius: 12px; margin-bottom: 1.5rem;
                border: 1px solid hsl(142, 40%, 82%);
                box-shadow: 0 4px 6px -1px hsla(142, 76%, 36%, 0.08);">
        <h2 style="color: hsl(142, 76%, 30%); margin: 0;">⚙️ Database Pompe</h2>
        <p style="color: hsl(215, 16%, 47%); margin: 0.5rem 0 0;">
            Componenti estratti automaticamente dai disegni tecnici indicizzati
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.caption("ℹ️ Questa pagina mostra i componenti estratti automaticamente dai disegni indicizzati. "
               "Per ogni componente puoi vedere: tipo (Cover, Casing, Impeller...), peso, materiale, part number, rating. "
               "Usa i filtri per cercare per famiglia o tipo. "
               "Esempio: filtra per 'Impeller' per vedere tutte le giranti trovate nei disegni, con peso e materiale.")

    from weight_engine.pump_database import (
        get_all_pumps, get_pump_stats, rebuild_from_qdrant, clear_database
    )

    # Azioni
    col_action1, col_action2 = st.columns([3, 1])

    with col_action1:
        if st.button("Ricostruisci Database dai Documenti Indicizzati",
                      use_container_width=True, type="primary"):
            with st.spinner("Analisi documenti in corso..."):
                count = rebuild_from_qdrant()
            st.success(f"Database ricostruito: {count} componenti estratti")
            st.rerun()

    with col_action2:
        if st.button("Svuota Database", use_container_width=True):
            deleted = clear_database()
            st.warning(f"{deleted} entry eliminate")
            st.rerun()

    # Carica dati
    pumps = get_all_pumps()

    if not pumps:
        st.info("Il database pompe e' vuoto. "
                "Clicca su **Ricostruisci Database** per analizzare "
                "i documenti indicizzati ed estrarre automaticamente i dati.")
        return

    stats = get_pump_stats()

    # ============================================================
    # METRICHE TOP-LEVEL
    # ============================================================

    st.markdown("### Panoramica")
    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Componenti Totali", stats["total"])
    col2.metric("Con Peso", stats["with_weight"])
    col3.metric("Peso Medio", f"{stats['avg_weight']:.0f} kg" if stats["avg_weight"] else "N/D")
    col4.metric("Range Pesi", stats.get("weight_range", "N/D"))
    col5.metric("Famiglie", len(stats.get("families", {})))

    # ============================================================
    # FILTRI
    # ============================================================

    st.markdown("### Filtri")
    fcol1, fcol2, fcol3, fcol4 = st.columns(4)

    all_families = sorted(stats.get("families", {}).keys())
    all_components = sorted(stats.get("components", {}).keys())
    all_materials = sorted(stats.get("materials", {}).keys())

    with fcol1:
        filter_family = st.selectbox(
            "Famiglia Pompa", ["Tutte"] + all_families, key="pd_fam"
        )
    with fcol2:
        filter_component = st.selectbox(
            "Tipo Componente", ["Tutti"] + all_components, key="pd_comp"
        )
    with fcol3:
        filter_material = st.selectbox(
            "Materiale", ["Tutti"] + all_materials, key="pd_mat"
        )
    with fcol4:
        filter_weight = st.selectbox(
            "Peso", ["Tutti", "Con peso", "Senza peso"], key="pd_weight"
        )

    # Applica filtri
    filtered = pumps
    if filter_family != "Tutte":
        filtered = [p for p in filtered
                    if (p.get("pump_family") or "N/D") == filter_family]
    if filter_component != "Tutti":
        filtered = [p for p in filtered
                    if p.get("component_type", "unknown") == filter_component]
    if filter_material != "Tutti":
        filtered = [p for p in filtered
                    if filter_material in (p.get("materials") or [])]
    if filter_weight == "Con peso":
        filtered = [p for p in filtered
                    if p.get("weight_kg") and p["weight_kg"] > 0]
    elif filter_weight == "Senza peso":
        filtered = [p for p in filtered
                    if not p.get("weight_kg")]

    st.caption(f"Mostrando {len(filtered)}/{len(pumps)} componenti")

    # ============================================================
    # TABELLA INTERATTIVA
    # ============================================================

    st.markdown("### Tabella Componenti")

    if HAS_PANDAS and filtered:
        rows = []
        for p in filtered:
            rows.append({
                "Componente": p.get("component_type", "?").replace("_", " ").title(),
                "Famiglia": p.get("pump_family") or "—",
                "Part Number": p.get("part_number") or "—",
                "Rev.": p.get("revision") or "—",
                "Peso (kg)": p.get("weight_kg") or None,
                "Tipo Peso": (p.get("weight_type") or "—").title(),
                "Materiali": ", ".join(p.get("materials") or ["—"]),
                "Flange": p.get("flange_rating") or "—",
                "Formato": p.get("drawing_format") or "—",
                "Confidenza": f"{p.get('confidence', 0):.0%}",
                "File": os.path.basename(p.get("source", "")),
            })

        df = pd.DataFrame(rows)

        # Ordinamento per peso decrescente
        df_sorted = df.sort_values("Peso (kg)", ascending=False, na_position="last")

        st.dataframe(
            df_sorted,
            use_container_width=True,
            hide_index=True,
            height=min(400, len(df_sorted) * 35 + 40),
            column_config={
                "Peso (kg)": st.column_config.NumberColumn(format="%.1f"),
                "Confidenza": st.column_config.TextColumn(width="small"),
                "Rev.": st.column_config.TextColumn(width="small"),
                "Formato": st.column_config.TextColumn(width="small"),
            },
        )
    elif filtered:
        for p in filtered[:20]:
            w = p.get("weight_kg")
            w_str = f"{w:.1f} kg" if w else "—"
            comp = p.get("component_type", "?").replace("_", " ").title()
            st.text(f"{comp} | {p.get('part_number','—')} | {w_str}")
    else:
        st.info("Nessun componente corrisponde ai filtri selezionati.")

    # ============================================================
    # GRAFICI
    # ============================================================

    if HAS_PLOTLY and filtered:
        st.markdown("---")
        st.markdown("### Analisi Visiva")

        # Solo componenti con peso per i grafici
        with_weight = [p for p in filtered if p.get("weight_kg") and p["weight_kg"] > 0]

        if with_weight:
            col_chart1, col_chart2 = st.columns(2)

            # 1. Scatter: peso per componente, colorato per famiglia
            with col_chart1:
                scatter_data = []
                for p in with_weight:
                    scatter_data.append({
                        "Componente": p.get("component_type", "?").replace("_", " ").title(),
                        "Peso (kg)": p["weight_kg"],
                        "Famiglia": p.get("pump_family") or "N/D",
                        "Part Number": p.get("part_number") or "N/D",
                    })

                if HAS_PANDAS:
                    df_scatter = pd.DataFrame(scatter_data)
                    fig_scatter = px.strip(
                        df_scatter, x="Componente", y="Peso (kg)",
                        color="Famiglia",
                        hover_data=["Part Number"],
                        title="Pesi per Tipo Componente",
                    )
                    fig_scatter.update_layout(
                        height=400,
                        font=dict(family="Inter, sans-serif", size=11),
                        margin=dict(t=40, b=40, l=20, r=20),
                    )
                    st.plotly_chart(fig_scatter, use_container_width=True)

            # 2. Bar: distribuzione peso medio per famiglia
            with col_chart2:
                family_weights = {}
                for p in with_weight:
                    fam = p.get("pump_family") or "N/D"
                    if fam not in family_weights:
                        family_weights[fam] = []
                    family_weights[fam].append(p["weight_kg"])

                if family_weights:
                    bar_data = {
                        "Famiglia": [],
                        "Peso Medio (kg)": [],
                        "N Componenti": [],
                    }
                    for fam, ws in sorted(family_weights.items()):
                        bar_data["Famiglia"].append(fam)
                        bar_data["Peso Medio (kg)"].append(round(sum(ws) / len(ws), 1))
                        bar_data["N Componenti"].append(len(ws))

                    fig_bar = px.bar(
                        bar_data, x="Famiglia", y="Peso Medio (kg)",
                        text="N Componenti",
                        title="Peso Medio per Famiglia",
                        color_discrete_sequence=["#3B82F6"],
                    )
                    fig_bar.update_traces(texttemplate="%{text} comp.", textposition="auto")
                    fig_bar.update_layout(
                        height=400,
                        font=dict(family="Inter, sans-serif", size=11),
                        margin=dict(t=40, b=40, l=20, r=20),
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)

            # 3. Pie: materiali piu usati
            col_pie1, col_pie2 = st.columns(2)

            with col_pie1:
                mat_count = {}
                for p in filtered:
                    for mat in (p.get("materials") or []):
                        mat_count[mat] = mat_count.get(mat, 0) + 1

                if mat_count:
                    # Top 10 materiali
                    top_mats = sorted(mat_count.items(), key=lambda x: x[1], reverse=True)[:10]
                    fig_pie = px.pie(
                        names=[m[0] for m in top_mats],
                        values=[m[1] for m in top_mats],
                        title="Materiali piu Usati",
                        hole=0.4,
                    )
                    fig_pie.update_layout(
                        height=380,
                        font=dict(family="Inter, sans-serif", size=11),
                        margin=dict(t=40, b=20, l=20, r=20),
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)

            # 4. Pie: distribuzione componenti
            with col_pie2:
                comp_count = {}
                for p in filtered:
                    comp = p.get("component_type", "unknown").replace("_", " ").title()
                    comp_count[comp] = comp_count.get(comp, 0) + 1

                if comp_count:
                    top_comps = sorted(comp_count.items(), key=lambda x: x[1], reverse=True)[:10]
                    fig_comp = px.pie(
                        names=[c[0] for c in top_comps],
                        values=[c[1] for c in top_comps],
                        title="Distribuzione Componenti",
                        hole=0.4,
                    )
                    fig_comp.update_layout(
                        height=380,
                        font=dict(family="Inter, sans-serif", size=11),
                        margin=dict(t=40, b=20, l=20, r=20),
                    )
                    st.plotly_chart(fig_comp, use_container_width=True)

    st.markdown("---")
    st.markdown("### Dettaglio Componente Selezionato")

    if filtered:
        # Costruisci lista leggibile
        comp_labels = []
        for i, p in enumerate(filtered):
            comp = p.get("component_type", "?").replace("_", " ").title()
            w = p.get("weight_kg")
            w_str = f"{w:.1f} kg" if w else "—"
            filename = os.path.basename(p.get("source", ""))
            label = f"{comp} — {w_str} — {filename}"
            comp_labels.append(label)

        selected_idx = st.selectbox(
            "Seleziona componente",
            range(len(comp_labels)),
            format_func=lambda i: comp_labels[i],
            index=0,
        )

        p = filtered[selected_idx]

        comp = p.get("component_type", "?").replace("_", " ").title()
        w = p.get("weight_kg")
        conf = p.get("confidence", 0)
        conf_pct = int(conf * 100)

        # Confidenza
        if conf >= 0.7:
            conf_icon = "🟢"
        elif conf >= 0.4:
            conf_icon = "🟡"
        else:
            conf_icon = "🔴"

        st.markdown(f"**{conf_icon} {comp}**")
        st.progress(conf, text=f"Confidenza: {conf_pct}%")

        # Griglia dettagli
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Peso", f"{w:.1f} kg" if w else "—")
            st.caption(f"Tipo: {(p.get('weight_type') or '—').title()}")
        with c2:
            st.metric("Materiali", ", ".join(p.get("materials") or ["—"]))
        with c3:
            st.metric("Part Number", p.get("part_number") or "—")

        c4, c5, c6 = st.columns(3)
        with c4:
            st.metric("Famiglia", p.get("pump_family") or "—")
        with c5:
            flange = f"{p['flange_rating']}#" if p.get("flange_rating") else "—"
            st.metric("Rating Flange", flange)
        with c6:
            st.metric("Revisione", f"{p.get('revision', '—')} / {p.get('drawing_format', '—')}")

        # Dimensioni
        if p.get("dimensions"):
            dims_str = ", ".join(f"{k}: {v}" for k, v in p["dimensions"].items())
            st.caption(f"📐 Dimensioni: {dims_str}")

        st.caption(f"📄 File: {os.path.basename(p.get('source', ''))}")
    else:
        st.info("Nessun componente corrisponde ai filtri selezionati.")


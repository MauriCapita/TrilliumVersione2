"""
Trillium V2 — Trend Analysis & Predizione Costi
Dashboard analytics sullo storico delle stime pesi:
KPI, distribuzione per famiglia/materiale, costo stimato materia prima,
confronto con la media, export CSV.
"""

import streamlit as st
import sys
import os
import io
import csv
from datetime import datetime

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

from weight_engine.estimation_history import get_history, get_stats
from weight_engine.materials import get_cost_per_kg, get_density


# ============================================================
# STILI CSS SPECIFICI
# ============================================================

def _inject_styles():
    st.markdown("""
    <style>
    /* KPI Cards */
    .trend-kpi-card {
        background: linear-gradient(135deg, #ffffff 0%, #f0fdf4 100%);
        border: 1px solid #bbf7d0;
        border-radius: 12px;
        padding: 20px 16px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        transition: transform 0.2s ease;
    }
    .trend-kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
    }
    .trend-kpi-value {
        font-size: 28px;
        font-weight: 700;
        color: #1B9C4F;
        margin: 4px 0;
    }
    .trend-kpi-label {
        font-size: 13px;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .trend-kpi-sub {
        font-size: 11px;
        color: #94A3B8;
        margin-top: 4px;
    }

    /* Badge sopra/sotto media */
    .badge-above {
        display: inline-block;
        background: #FEF3C7;
        color: #92400E;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-below {
        display: inline-block;
        background: #DCFCE7;
        color: #166534;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-average {
        display: inline-block;
        background: #E0F2FE;
        color: #075985;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 12px;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)


# ============================================================
# CALCOLO COSTO STIMATO
# ============================================================

def _calc_estimated_cost(entry: dict) -> float | None:
    """Calcola il costo stimato materia prima (€) = peso × costo/kg."""
    material = entry.get("material", "")
    weight = entry.get("total_weight_kg", 0)
    if not material or not weight:
        return None
    cost_kg = get_cost_per_kg(material)
    if cost_kg is None:
        return None
    return round(weight * cost_kg, 0)


def _get_family_averages(history: list) -> dict:
    """Calcola la media peso per famiglia pompa."""
    fam_data = {}
    for entry in history:
        fam = entry.get("pump_family", "")
        w = entry.get("total_weight_kg", 0)
        if fam and w > 0:
            fam_data.setdefault(fam, []).append(w)
    return {f: sum(ws) / len(ws) for f, ws in fam_data.items()}


def _deviation_badge(weight: float, avg: float) -> str:
    """Restituisce HTML badge con deviazione % dalla media."""
    if avg == 0:
        return ""
    pct = ((weight - avg) / avg) * 100
    if abs(pct) < 5:
        return f'<span class="badge-average">≈ media ({pct:+.0f}%)</span>'
    elif pct > 0:
        return f'<span class="badge-above">↑ {pct:+.0f}% sopra media</span>'
    else:
        return f'<span class="badge-below">↓ {pct:+.0f}% sotto media</span>'


# ============================================================
# EXPORT CSV
# ============================================================

def _export_csv(history: list) -> bytes:
    """Genera CSV con tutti i dati storico + costo stimato."""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    # Header
    writer.writerow([
        "Job ID", "Data", "Progetto", "Rev.",
        "Famiglia", "Nq", "F. Scala", "Stadi",
        "Pressione (bar)", "Temperatura (°C)", "Materiale",
        "Rating", "Peso Totale (kg)", "Costo Stimato (€)",
        "Comp. Stimati", "Comp. Totali", "Alta Confidenza", "Warning"
    ])
    for e in history:
        cost = _calc_estimated_cost(e)
        params = e.get("params", {})
        writer.writerow([
            e.get("job_id", ""),
            e.get("timestamp", "")[:19],
            e.get("project_name", ""),
            e.get("revision", ""),
            e.get("pump_family", ""),
            params.get("nq", e.get("nq", "")),
            params.get("scale_factor", e.get("scale_factor", "")),
            params.get("num_stages", 1),
            params.get("pressure", e.get("pressure", "")),
            params.get("temperature", e.get("temperature", "")),
            e.get("material", ""),
            e.get("flange_rating", ""),
            e.get("total_weight_kg", ""),
            f"{cost:.0f}" if cost else "N/D",
            e.get("components_estimated", ""),
            e.get("components_total", ""),
            e.get("high_confidence", ""),
            e.get("warnings", 0),
        ])
    return output.getvalue().encode("utf-8-sig")


# ============================================================
# PAGINA PRINCIPALE
# ============================================================

def render():
    _inject_styles()

    st.markdown("""
    <div style="text-align: center; padding: 20px 0 10px;">
        <h1 style="color: #1B9C4F; margin-bottom: 5px;">📈 Trend Analysis</h1>
        <p style="color: #64748B; font-size: 15px;">
            Analisi storico stime, pattern per famiglia/materiale e predizione costi materia prima
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.caption("ℹ️ Questa pagina analizza tutte le stime salvate. Più stime effettui, "
               "più i dati diventano significativi. I costi sono indicativi (€/kg da letteratura industriale).")

    # Carica dati
    history = get_history()

    if not history:
        st.info("📭 **Nessuna stima nello storico.** Vai su **Stima Pesi**, esegui un calcolo e "
                "salvalo per vedere i dati di trend qui.")
        st.markdown("""
        **Come iniziare:**
        1. Vai su **⚖️ Stima Pesi**
        2. Compila i parametri e clicca **Calcola Stima**
        3. In fondo alla pagina clicca **💾 Salva Progetto**
        4. Torna qui per vedere il trend
        """)
        return

    # ============================================================
    # KPI CARDS
    # ============================================================

    stats = get_stats()
    total_stime = stats.get("total", 0)
    avg_weight = stats.get("avg_weight", 0)
    max_weight = stats.get("max_weight", 0)
    min_weight = stats.get("min_weight", 0)
    avg_conf = stats.get("avg_confidence_pct", 0)

    # Calcolo costo medio
    costs = [c for c in (_calc_estimated_cost(e) for e in history) if c is not None]
    avg_cost = sum(costs) / len(costs) if costs else 0
    total_cost = sum(costs) if costs else 0

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="trend-kpi-card">
            <div class="trend-kpi-label">Stime Totali</div>
            <div class="trend-kpi-value">{total_stime}</div>
            <div class="trend-kpi-sub">{len(stats.get('families', {}))} famiglie diverse</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="trend-kpi-card">
            <div class="trend-kpi-label">Peso Medio</div>
            <div class="trend-kpi-value">{avg_weight:,.0f} kg</div>
            <div class="trend-kpi-sub">Min {min_weight:,.0f} — Max {max_weight:,.0f} kg</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="trend-kpi-card">
            <div class="trend-kpi-label">Costo Medio MP</div>
            <div class="trend-kpi-value">€ {avg_cost:,.0f}</div>
            <div class="trend-kpi-sub">Totale cumulato: € {total_cost:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="trend-kpi-card">
            <div class="trend-kpi-label">Confidenza Media</div>
            <div class="trend-kpi-value">{avg_conf:.0f}%</div>
            <div class="trend-kpi-sub">% componenti alta confidenza</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")

    # ============================================================
    # GRAFICI DISTRIBUZIONE
    # ============================================================

    if HAS_PLOTLY:
        st.markdown("### 📊 Distribuzione Stime")

        col_g1, col_g2 = st.columns(2)

        # --- Grafico per famiglia ---
        families = stats.get("families", {})
        if families:
            with col_g1:
                fig_fam = go.Figure(data=[
                    go.Bar(
                        x=list(families.keys()),
                        y=list(families.values()),
                        marker_color=["#1B9C4F", "#16A085", "#2ECC71", "#27AE60",
                                       "#3498DB", "#2980B9", "#9B59B6", "#8E44AD"][:len(families)],
                        text=list(families.values()),
                        textposition="auto",
                    )
                ])
                fig_fam.update_layout(
                    title="Stime per Famiglia Pompa",
                    xaxis_title="Famiglia",
                    yaxis_title="Numero Stime",
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    height=350,
                    margin=dict(l=40, r=20, t=50, b=40),
                )
                st.plotly_chart(fig_fam, use_container_width=True)

        # --- Grafico per materiale ---
        materials = stats.get("materials", {})
        if materials:
            with col_g2:
                fig_mat = go.Figure(data=[
                    go.Pie(
                        labels=list(materials.keys()),
                        values=list(materials.values()),
                        hole=0.4,
                        textinfo="label+percent",
                        marker=dict(colors=px.colors.qualitative.Set3[:len(materials)]),
                    )
                ])
                fig_mat.update_layout(
                    title="Distribuzione per Materiale",
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    height=350,
                    margin=dict(l=20, r=20, t=50, b=20),
                    showlegend=True,
                    legend=dict(font=dict(size=11)),
                )
                st.plotly_chart(fig_mat, use_container_width=True)

        # --- Grafico peso nel tempo ---
        if len(history) >= 2:
            st.markdown("### 📉 Andamento Pesi nel Tempo")
            dates = []
            weights = []
            labels = []
            for e in history:
                ts = e.get("timestamp", "")
                try:
                    dt = datetime.fromisoformat(ts)
                    dates.append(dt)
                    weights.append(e.get("total_weight_kg", 0))
                    labels.append(f"{e.get('pump_family', '?')} — {e.get('material', '?')}")
                except (ValueError, TypeError):
                    pass

            if dates:
                fig_time = go.Figure()
                fig_time.add_trace(go.Scatter(
                    x=dates, y=weights,
                    mode="lines+markers+text",
                    text=labels,
                    textposition="top center",
                    textfont=dict(size=10),
                    marker=dict(size=10, color="#1B9C4F"),
                    line=dict(color="#1B9C4F", width=2),
                    name="Peso Totale",
                ))
                # Linea media
                avg_w = sum(weights) / len(weights)
                fig_time.add_hline(y=avg_w, line_dash="dash", line_color="#94A3B8",
                                   annotation_text=f"Media: {avg_w:,.0f} kg",
                                   annotation_position="top left")
                fig_time.update_layout(
                    xaxis_title="Data",
                    yaxis_title="Peso Totale (kg)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    height=350,
                    margin=dict(l=40, r=20, t=30, b=40),
                )
                st.plotly_chart(fig_time, use_container_width=True)
    else:
        st.warning("Plotly non disponibile. Installa con: `pip install plotly`")

    # ============================================================
    # TABELLA STORICO CON COSTI E CONFRONTO MEDIA
    # ============================================================

    st.markdown("### 📋 Storico Stime Completo")

    family_avgs = _get_family_averages(history)

    # Filtri
    col_f1, col_f2 = st.columns(2)
    all_families = sorted(set(e.get("pump_family", "") for e in history if e.get("pump_family")))
    all_materials = sorted(set(e.get("material", "") for e in history if e.get("material")))

    with col_f1:
        filter_fam = st.multiselect("Filtra per famiglia", all_families, default=[],
                                     key="trend_filter_fam")
    with col_f2:
        filter_mat = st.multiselect("Filtra per materiale", all_materials, default=[],
                                     key="trend_filter_mat")

    filtered = history
    if filter_fam:
        filtered = [e for e in filtered if e.get("pump_family") in filter_fam]
    if filter_mat:
        filtered = [e for e in filtered if e.get("material") in filter_mat]

    if HAS_PANDAS and filtered:
        rows = []
        for e in filtered:
            cost = _calc_estimated_cost(e)
            fam = e.get("pump_family", "")
            w = e.get("total_weight_kg", 0)
            avg = family_avgs.get(fam, 0)

            # Delta vs media
            if avg > 0 and w > 0:
                delta_pct = ((w - avg) / avg) * 100
                if abs(delta_pct) < 5:
                    vs_media = f"≈ media ({delta_pct:+.0f}%)"
                elif delta_pct > 0:
                    vs_media = f"↑ +{delta_pct:.0f}%"
                else:
                    vs_media = f"↓ {delta_pct:.0f}%"
            else:
                vs_media = "—"

            params = e.get("params", {})
            rows.append({
                "ID": e.get("job_id", "")[:8],
                "Data": e.get("timestamp", "")[:10],
                "Progetto": e.get("project_name", "") or "—",
                "Famiglia": fam,
                "Nq": params.get("nq", e.get("nq", "")),
                "f": params.get("scale_factor", e.get("scale_factor", "")),
                "Materiale": e.get("material", ""),
                "Rating": e.get("flange_rating", ""),
                "Peso (kg)": f"{w:,.0f}",
                "Costo (€)": f"{cost:,.0f}" if cost else "N/D",
                "vs Media": vs_media,
                "Conf.": f"{e.get('high_confidence', 0)}/{e.get('components_total', 0)}",
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, height=400)

        # Riepilogo sotto tabella
        st.markdown(f"""
        **Riepilogo filtro:** {len(filtered)} stime
        {"— Peso medio: **" + f"{sum(e.get('total_weight_kg', 0) for e in filtered) / len(filtered):,.0f}" + " kg**" if filtered else ""}
        """)

    elif not HAS_PANDAS:
        st.warning("Pandas non disponibile. Installa con: `pip install pandas`")
        # Fallback: lista semplice
        for e in filtered:
            cost = _calc_estimated_cost(e)
            st.markdown(f"- **{e.get('job_id', '')[:8]}** — "
                        f"{e.get('pump_family', '')} {e.get('material', '')} — "
                        f"{e.get('total_weight_kg', 0):,.0f} kg — "
                        f"€ {cost:,.0f}" if cost else "N/D")
    else:
        st.info("Nessuna stima corrisponde ai filtri selezionati.")

    # ============================================================
    # CONFRONTO FAMIGLIE
    # ============================================================

    if len(family_avgs) >= 2 and HAS_PLOTLY:
        st.markdown("### 🏭 Confronto Peso Medio per Famiglia")

        fam_names = list(family_avgs.keys())
        fam_avgs_vals = [family_avgs[f] for f in fam_names]
        fam_counts = [len([e for e in history if e.get("pump_family") == f]) for f in fam_names]

        fig_comp = go.Figure()
        fig_comp.add_trace(go.Bar(
            x=fam_names,
            y=fam_avgs_vals,
            text=[f"{v:,.0f} kg<br>({c} stime)" for v, c in zip(fam_avgs_vals, fam_counts)],
            textposition="auto",
            marker_color=["#1B9C4F", "#16A085", "#3498DB", "#2980B9",
                           "#9B59B6", "#E67E22", "#E74C3C", "#1ABC9C"][:len(fam_names)],
        ))
        fig_comp.update_layout(
            xaxis_title="Famiglia Pompa",
            yaxis_title="Peso Medio (kg)",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            height=350,
            margin=dict(l=40, r=20, t=30, b=40),
        )
        st.plotly_chart(fig_comp, use_container_width=True)

    # ============================================================
    # COSTO PER MATERIALE
    # ============================================================

    if len(all_materials) >= 2 and HAS_PLOTLY:
        st.markdown("### 💰 Costo Medio Materia Prima per Materiale")

        mat_costs = {}
        for e in history:
            mat = e.get("material", "")
            cost = _calc_estimated_cost(e)
            if mat and cost:
                mat_costs.setdefault(mat, []).append(cost)

        if mat_costs:
            mat_names = list(mat_costs.keys())
            mat_avg_costs = [sum(v) / len(v) for v in mat_costs.values()]
            mat_labels = [f"€ {c:,.0f}" for c in mat_avg_costs]

            fig_cost = go.Figure(data=[
                go.Bar(
                    x=mat_names,
                    y=mat_avg_costs,
                    text=mat_labels,
                    textposition="auto",
                    marker_color=["#F59E0B", "#EAB308", "#F97316", "#FB923C",
                                   "#FBBF24", "#FCD34D", "#D97706", "#B45309"][:len(mat_names)],
                )
            ])
            fig_cost.update_layout(
                xaxis_title="Materiale",
                yaxis_title="Costo Medio (€)",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                height=350,
                margin=dict(l=40, r=20, t=30, b=40),
            )
            st.plotly_chart(fig_cost, use_container_width=True)

    # ============================================================
    # EXPORT
    # ============================================================

    st.markdown("---")
    st.markdown("### 📥 Esporta Dati")

    col_exp1, col_exp2 = st.columns([1, 3])
    with col_exp1:
        csv_data = _export_csv(history)
        st.download_button(
            "⬇️ Scarica CSV",
            data=csv_data,
            file_name=f"trillium_trend_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
            key="download_trend_csv",
        )
    with col_exp2:
        st.caption(f"Esporta tutte le {len(history)} stime in formato CSV (separatore ;) "
                   "compatibile con Excel. Include: parametri, peso, costo stimato, confidenza.")

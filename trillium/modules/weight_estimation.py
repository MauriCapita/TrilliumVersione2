"""
Trillium V2 — Pagina Stima Pesi Componenti Pompe
Form input parametri pompa, validazione real-time, esecuzione stima,
grafici interattivi, confronto configurazioni, download Excel.
"""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@st.dialog("Anteprima Documento", width="large")
def _show_fullscreen_preview_we():
    """Mostra l'anteprima del documento a schermo intero."""
    img_path = st.session_state.get("_preview_img_path")
    img_name = st.session_state.get("_preview_img_name", "Documento")
    pdf_bytes = st.session_state.get("_preview_pdf_bytes")
    st.markdown(f"**{img_name}**")
    if img_path and os.path.isfile(img_path):
        from PIL import Image as PILImage
        img = PILImage.open(img_path)
        if img.mode not in ("RGB", "L", "RGBA"):
            img = img.convert("RGB")
        st.image(img, use_container_width=True)
    elif pdf_bytes:
        st.image(pdf_bytes, use_container_width=True)
    else:
        st.warning("Anteprima non disponibile.")

from weight_engine.materials import (
    list_materials, list_material_categories, get_density, get_properties,
    density_ratio,
)
from weight_engine.parts_list import (
    list_pump_families, get_family_names, get_family_info,
)
from weight_engine.estimator import WeightEstimator, run_estimation
from weight_engine.excel_generator import generate_excel, get_filename

# Per i grafici
try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


# ============================================================
# STILI CSS SPECIFICI
# ============================================================

def _inject_styles():
    st.markdown("""
    <style>
    .estimation-header {
        background: linear-gradient(135deg, hsl(142, 50%, 95%) 0%, hsl(142, 60%, 88%) 100%);
        color: hsl(215, 25%, 15%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        border: 1px solid hsl(142, 40%, 82%);
        box-shadow: 0 4px 6px -1px hsla(142, 76%, 36%, 0.08);
    }
    .estimation-header h2 { color: hsl(142, 76%, 30%); margin: 0; }
    .estimation-header p { color: hsl(215, 16%, 47%); margin: 0.5rem 0 0; }

    .param-section {
        background: hsl(210, 40%, 96%);
        padding: 1rem 1.5rem;
        border-radius: 12px;
        border-left: 4px solid hsl(142, 76%, 36%);
        margin-bottom: 1rem;
    }
    .param-section h4 { color: hsl(142, 76%, 30%); margin: 0 0 0.5rem; }

    .confidence-alta { color: #2E7D32; font-weight: bold; }
    .confidence-media { color: #F57F17; font-weight: bold; }
    .confidence-bassa { color: #C62828; font-weight: bold; }

    .total-weight {
        background: linear-gradient(135deg, hsl(142, 50%, 95%) 0%, hsl(142, 60%, 88%) 100%);
        color: hsl(142, 76%, 28%);
        padding: 1rem 1.5rem;
        border-radius: 12px;
        text-align: center;
        font-size: 1.5rem;
        font-weight: bold;
        border: 1px solid hsl(142, 40%, 82%);
    }

    .validation-ok {
        color: #2E7D32;
        padding: 0.3rem 0;
        font-size: 0.9rem;
    }
    .validation-warn {
        color: #E65100;
        padding: 0.3rem 0;
        font-size: 0.9rem;
        font-weight: bold;
    }
    .validation-error {
        color: #C62828;
        padding: 0.3rem 0;
        font-size: 0.9rem;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)


# ============================================================
# VALIDAZIONE IN TEMPO REALE
# ============================================================

# Tabella max pressione per rating (bar) — da ASME B16.5 a ~38°C
RATING_MAX_PRESSURE = {
    150: 19.6,
    300: 51.1,
    600: 102.1,
    900: 153.2,
    1500: 255.3,
    2500: 425.5,
}


def _validate_params(material, temperature, pressure, flange_rating, scale_factor):
    """Validazione in tempo reale dei parametri. Restituisce lista di (livello, messaggio)."""
    warnings = []

    # 1. Temperatura vs limite materiale
    props = get_properties(material)
    if props:
        t_limit = props.get("temperature_limit", 9999)
        if temperature > t_limit:
            warnings.append(("error", f"⛔ {material}: temperatura max = {t_limit}°C, hai impostato {temperature}°C"))
        elif temperature > t_limit * 0.85:
            warnings.append(("warn", f"⚠ {material}: prossimo al limite termico ({temperature}°C / {t_limit}°C max)"))
        else:
            warnings.append(("ok", f"✓ {material}: temperatura OK ({temperature}°C / {t_limit}°C max)"))

    # 2. Pressione vs flange rating
    max_p = RATING_MAX_PRESSURE.get(flange_rating, 0)
    if max_p > 0:
        if pressure > max_p:
            warnings.append(("error", f"⛔ Rating {flange_rating}# insufficiente per {pressure} bar (max {max_p:.1f} bar)"))
        elif pressure > max_p * 0.85:
            warnings.append(("warn", f"⚠ Rating {flange_rating}# vicino al limite ({pressure}/{max_p:.1f} bar)"))
        else:
            warnings.append(("ok", f"✓ Rating {flange_rating}#: pressione OK ({pressure}/{max_p:.1f} bar)"))

    # 3. Castabilità
    if props:
        castability = props.get("castability", "")
        if "difficile" in castability.lower():
            warnings.append(("warn", f"⚠ {material}: castabilità '{castability}' — verificare fattibilità fusioni"))

    # 4. Scale factor
    if scale_factor > 2.0:
        warnings.append(("warn", f"⚠ Scale factor {scale_factor} molto alto — accuratezza ridotta"))
    elif scale_factor < 0.5:
        warnings.append(("warn", f"⚠ Scale factor {scale_factor} molto basso — verificare geometria"))

    # 5. Temperatura sotto zero
    if temperature < -29:
        warnings.append(("warn", f"⚠ Temperatura {temperature}°C: verificare requisiti MDMT e Charpy"))

    return warnings


# ============================================================
# GRAFICI INTERATTIVI
# ============================================================

def _render_charts(result):
    """Render pie chart pesi, bar chart confidenza, e breakdown."""
    if not HAS_PLOTLY:
        st.info("Installa plotly per i grafici: `pip install plotly`")
        return

    # Dati per i grafici
    estimated = [c for c in result.components if c.is_estimated and c.estimated_weight_kg]

    if not estimated:
        return

    st.markdown("### Analisi Grafica")
    st.caption("Distribuzione pesi per gruppo, livello di confidenza e top 10 componenti più pesanti.")

    col_pie, col_bar = st.columns(2)

    # 1. Pie chart: peso per gruppo
    with col_pie:
        groups = {}
        for c in estimated:
            g = c.group
            groups[g] = groups.get(g, 0) + (c.estimated_weight_kg or 0)

        fig_pie = px.pie(
            names=list(groups.keys()),
            values=list(groups.values()),
            title="Distribuzione Pesi per Gruppo",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig_pie.update_layout(
            font=dict(family="Calibri", size=12),
            margin=dict(t=40, b=20, l=20, r=20),
            height=350,
            legend=dict(orientation="h", yanchor="bottom", y=-0.3),
        )
        fig_pie.update_traces(
            textposition="inside",
            textinfo="label+percent",
            textfont_size=10,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # 2. Bar chart: confidenza per componente
    with col_bar:
        conf_counts = {"alta": 0, "media": 0, "bassa": 0}
        for c in result.components:
            if c.confidence in conf_counts:
                conf_counts[c.confidence] += 1

        colors = {"alta": "#2E7D32", "media": "#F57F17", "bassa": "#C62828"}
        fig_bar = go.Figure(data=[
            go.Bar(
                x=list(conf_counts.keys()),
                y=list(conf_counts.values()),
                marker_color=[colors[k] for k in conf_counts.keys()],
                text=list(conf_counts.values()),
                textposition="auto",
            )
        ])
        fig_bar.update_layout(
            title="Livello di Confidenza",
            font=dict(family="Calibri", size=12),
            margin=dict(t=40, b=20, l=20, r=20),
            height=350,
            xaxis_title="Confidenza",
            yaxis_title="N° Componenti",
            showlegend=False,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # 3. Bar chart orizzontale: top 10 componenti più pesanti
    top_components = sorted(estimated, key=lambda c: c.estimated_weight_kg or 0, reverse=True)[:10]
    if top_components:
        names = [c.component_name for c in top_components]
        weights = [c.estimated_weight_kg for c in top_components]
        conf_colors = [colors.get(c.confidence, "#999") for c in top_components]

        fig_top = go.Figure(data=[
            go.Bar(
                y=names[::-1],
                x=weights[::-1],
                orientation="h",
                marker_color=conf_colors[::-1],
                text=[f"{w:.1f} kg" for w in weights[::-1]],
                textposition="auto",
            )
        ])
        fig_top.update_layout(
            title="Top 10 Componenti più Pesanti",
            font=dict(family="Calibri", size=12),
            margin=dict(t=40, b=20, l=40, r=20),
            height=400,
            xaxis_title="Peso (kg)",
            showlegend=False,
        )
        st.plotly_chart(fig_top, use_container_width=True)


# ============================================================
# CONFRONTO CONFIGURAZIONI
# ============================================================

def _render_comparison(base_params, base_result):
    """Render confronto side-by-side con materiale alternativo."""
    st.markdown("### Confronto Configurazioni")
    st.caption("Confronta il peso totale con un materiale alternativo per valutare opzioni progettuali.")

    all_materials = list_materials()
    current_mat = base_params.get("material", "Carbon Steel")

    # Suggerisci materiali alternativi comuni
    suggested = ["Carbon Steel", "SS 316", "Duplex 2205", "Super Duplex 2507",
                  "13Cr-4Ni", "Inconel 625", "Titanium Gr.2", "Bronze"]
    suggested = [m for m in suggested if m in all_materials and m != current_mat]

    alt_material = st.selectbox(
        "Materiale alternativo per confronto",
        suggested + [m for m in all_materials if m not in suggested and m != current_mat],
        key="comparison_material",
    )

    if st.button("Confronta", key="compare_btn", use_container_width=True):
        alt_params = dict(base_params)
        alt_params["material"] = alt_material

        with st.spinner(f"Calcolo con {alt_material}..."):
            alt_result = run_estimation(alt_params)

        # Tabella confronto
        delta_kg = alt_result.total_weight_kg - base_result.total_weight_kg
        delta_pct = (delta_kg / base_result.total_weight_kg * 100) if base_result.total_weight_kg > 0 else 0

        rho_base = get_density(current_mat) or 7850
        rho_alt = get_density(alt_material) or 7850

        col1, col2, col3 = st.columns(3)
        col1.metric(f"{current_mat}", f"{base_result.total_weight_kg:,.1f} kg",
                     help=f"ρ = {rho_base} kg/m³")
        col2.metric(f"{alt_material}", f"{alt_result.total_weight_kg:,.1f} kg",
                     delta=f"{delta_kg:+,.1f} kg ({delta_pct:+.1f}%)",
                     delta_color="inverse",
                     help=f"ρ = {rho_alt} kg/m³")
        col3.metric("Rapporto Densità", f"{rho_alt/rho_base:.4f}")

        # Tabella dettaglio per componente
        with st.expander("Dettaglio per componente", expanded=True):
            rows = []
            for c_base, c_alt in zip(base_result.components, alt_result.components):
                w_base = c_base.estimated_weight_kg or 0
                w_alt = c_alt.estimated_weight_kg or 0
                delta = w_alt - w_base
                rows.append({
                    "Componente": c_base.component_name,
                    f"{current_mat} (kg)": round(w_base, 1) if w_base else "—",
                    f"{alt_material} (kg)": round(w_alt, 1) if w_alt else "—",
                    "Δ (kg)": f"{delta:+.1f}" if w_base and w_alt else "—",
                })

            import pandas as pd
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

        # Grafico confronto
        if HAS_PLOTLY:
            base_groups = {}
            alt_groups = {}
            for c in base_result.components:
                if c.is_estimated:
                    base_groups[c.group] = base_groups.get(c.group, 0) + (c.estimated_weight_kg or 0)
            for c in alt_result.components:
                if c.is_estimated:
                    alt_groups[c.group] = alt_groups.get(c.group, 0) + (c.estimated_weight_kg or 0)

            all_groups = sorted(set(list(base_groups.keys()) + list(alt_groups.keys())))
            fig = go.Figure(data=[
                go.Bar(name=current_mat, x=all_groups,
                       y=[base_groups.get(g, 0) for g in all_groups],
                       marker_color="#2F5496"),
                go.Bar(name=alt_material, x=all_groups,
                       y=[alt_groups.get(g, 0) for g in all_groups],
                       marker_color="#E67E22"),
            ])
            fig.update_layout(
                title="Confronto Pesi per Gruppo",
                barmode="group",
                font=dict(family="Calibri", size=12),
                height=350,
                xaxis_title="Gruppo", yaxis_title="Peso (kg)",
                legend=dict(orientation="h", yanchor="bottom", y=-0.4),
            )
            st.plotly_chart(fig, use_container_width=True)


# ============================================================
# AUTO-SUGGEST POMPA RIFERIMENTO
# ============================================================

def _render_auto_suggest(pump_family, nq):
    """Mostra pompe di riferimento simili dal database RAG."""
    if not pump_family:
        return

    with st.expander("Pompe di Riferimento Simili (dal database)", expanded=False):
        try:
            from weight_engine.ai_matcher import find_reference_pump, score_reference_compatibility
            params = {"pump_family": pump_family, "nq": nq, "material": "Carbon Steel"}

            with st.spinner("Ricerca nel database..."):
                ref = find_reference_pump(params, use_ai_extraction=False)

            if ref and ref.get("source") != "none":
                score = score_reference_compatibility(ref, params)
                st.markdown(f"**Pompa trovata:** {ref.get('source', 'N/D')}")
                st.progress(int(score), text=f"Compatibilità: {score:.0f}%")

                if ref.get("components"):
                    st.caption("Componenti con pesi disponibili:")
                    for comp_name, comp_data in ref["components"].items():
                        w = comp_data.get("weight_kg", 0)
                        if w > 0:
                            st.caption(f"  • {comp_name}: {w} kg")
            else:
                st.info("Nessuna pompa di riferimento trovata nel database. "
                        "Il sistema userà stime parametriche.")
                st.caption("Suggerimento: indicizza i disegni con la parts list per migliorare i risultati.")
        except Exception as e:
            st.info(f"Ricerca riferimento non disponibile: database non connesso o non configurato")


# ============================================================
# CERCA NEI DOCUMENTI (RAG Search)
# ============================================================

def _build_rag_query_from_params(params: dict) -> str:
    """Costruisce una query RAG ottimizzata dai parametri del form."""
    parts = []

    family = params.get("pump_family", "")
    if family:
        parts.append(f"pompa {family}")
        # Nomi estesi
        type_map = {
            "OH": "overhung end suction centrifugal pump",
            "BB": "between bearings multistage barrel pump",
            "VS": "vertical suspended pump",
        }
        for prefix, desc in type_map.items():
            if family.startswith(prefix):
                parts.append(desc)
                break

    nq = params.get("nq")
    if nq:
        parts.append(f"velocità specifica Nq {nq}")

    material = params.get("material", "")
    if material:
        parts.append(f"materiale {material}")

    pressure = params.get("pressure")
    if pressure:
        parts.append(f"pressione {pressure} bar")

    temperature = params.get("temperature")
    if temperature and temperature != 20:
        parts.append(f"temperatura {temperature}°C")

    parts.append("peso componenti parts list weight disegno tecnico drawing")
    parts.append("casing impeller shaft bearing seal flange")

    return " ".join(parts)


def _render_rag_search(params: dict):
    """Cerca nei documenti indicizzati informazioni rilevanti per i parametri correnti."""
    query = _build_rag_query_from_params(params)

    with st.status("Ricerca nei documenti indicizzati...", expanded=True) as status:
        st.write(f"Query: *{query[:100]}...*")

        try:
            from rag.query import retrieve_relevant_docs, generate_answer, build_context
            from config import PROVIDER

            # 1. Recupera documenti
            st.write("Ricerca documenti rilevanti...")
            docs = retrieve_relevant_docs(query)

            if not docs:
                status.update(label="Nessun documento trovato", state="error")
                st.warning("Nessun documento rilevante trovato nel database. "
                           "Prova a indicizzare più documenti.")
                return

            st.write(f"Trovati {len(docs)} documenti")

            # 2. Mostra documenti trovati
            status.update(label=f"{len(docs)} documenti trovati", state="complete")

        except Exception as e:
            status.update(label="Errore nella ricerca", state="error")
            st.error(f"Impossibile cercare: {e}")
            return

    # Mostra risultati
    st.markdown("#### Documenti Trovati")

    for i, doc in enumerate(docs[:8], 1):
        source = doc.get("source", "N/D")
        text = doc.get("text", "")[:400]
        score = doc.get("score", None)

        basename = os.path.basename(source) if source != "N/D" else "N/D"
        score_str = f" — Rilevanza: {score:.0%}" if score else ""

        with st.expander(f"[{i}] {basename}{score_str}", expanded=(i <= 2)):
            st.caption(f"Percorso: {source}")
            st.text(text + ("..." if len(doc.get("text", "")) > 400 else ""))

    # 3. Genera risposta AI
    st.markdown("#### Analisi AI")
    try:
        prompt = build_context(
            query=f"Cerca informazioni su pesi, dimensioni e materiali per una pompa "
                  f"{params.get('pump_family','')} con Nq={params.get('nq','')}, "
                  f"materiale {params.get('material','')}, pressione {params.get('pressure','')} bar. "
                  f"Elenca tutti i pesi di componenti che trovi nei documenti.",
            docs=docs,
        )

        with st.spinner("L'AI sta analizzando i documenti..."):
            answer = generate_answer(prompt)

        if answer and not answer.startswith("❌"):
            st.markdown(answer)
        else:
            st.warning("Impossibile generare l'analisi AI.")

    except Exception as e:
        st.info(f"Analisi AI non disponibile: {e}")
        st.caption("I documenti sopra sono comunque consultabili manualmente.")

# ============================================================
# ALERT INTELLIGENTI (Copertura Documentale)
# ============================================================

def _render_smart_alerts(result, params):
    """Mostra alert intelligenti sulla qualità della stima."""
    st.markdown("### Alert Intelligenti")
    st.caption("Il sistema verifica la copertura documentale: quanti documenti di riferimento "
               "supportano la tua configurazione. Più alta la copertura, più affidabile la stima.")

    family = params.get("pump_family", "")
    material = params.get("material", "")
    flange_rating = params.get("flange_rating", 150)

    alerts = []
    doc_count = 0
    family_docs = 0
    material_docs = 0

    # Query Qdrant per copertura
    try:
        from config import VECTOR_DB
        if VECTOR_DB == "qdrant":
            from rag.qdrant_db import get_client
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            client = get_client()
            collections = client.get_collections().collections
            col_name = collections[0].name if collections else None

            if col_name:
                # Documenti totali
                col_info = client.get_collection(col_name)
                doc_count = col_info.points_count or 0

                # Documenti con questa famiglia
                try:
                    family_results = client.scroll(
                        collection_name=col_name,
                        scroll_filter=Filter(must=[
                            FieldCondition(key="pump_family", match=MatchValue(value=family))
                        ]),
                        limit=100,
                    )
                    family_docs = len(family_results[0]) if family_results[0] else 0
                except Exception:
                    pass

                # Documenti con questo materiale
                try:
                    mat_results = client.scroll(
                        collection_name=col_name,
                        scroll_filter=Filter(must=[
                            FieldCondition(key="material", match=MatchValue(value=material))
                        ]),
                        limit=100,
                    )
                    material_docs = len(mat_results[0]) if mat_results[0] else 0
                except Exception:
                    pass
        else:
            # ChromaDB fallback
            from modules.helpers import get_db_stats
            stats = get_db_stats()
            doc_count = stats.get("total_documents", 0)
    except Exception:
        pass

    # Calcola copertura (0-100%)
    if doc_count > 0:
        # Score basato su family docs (peso 60%) + material docs (peso 20%) + totale (peso 20%)
        family_score = min(family_docs / 5, 1.0) * 60  # 5+ doc = pieno
        material_score = min(material_docs / 3, 1.0) * 20  # 3+ doc = pieno
        total_score = min(doc_count / 50, 1.0) * 20  # 50+ doc = pieno
        coverage = int(family_score + material_score + total_score)
    else:
        coverage = 0

    # Mostra barra copertura
    if coverage >= 70:
        st.progress(coverage / 100, text=f"Copertura documentale: {coverage}% — Buona")
    elif coverage >= 40:
        st.progress(coverage / 100, text=f"Copertura documentale: {coverage}% — Parziale")
    else:
        st.progress(max(coverage, 1) / 100, text=f"Copertura documentale: {coverage}% — Insufficiente")

    # Metriche
    c1, c2, c3 = st.columns(3)
    c1.metric("Documenti Totali", doc_count)
    c2.metric(f"Doc. famiglia {family}", family_docs)
    c3.metric(f"Doc. materiale", material_docs)

    # Alert specifici
    if doc_count == 0:
        st.error("**Nessun documento indicizzato.** La stima è basata solo su formule "
                 "generiche. Indicizza almeno 50 disegni tecnici per migliorare l'accuratezza.")

    if doc_count > 0 and family_docs == 0:
        st.warning(f"**Nessun documento trovato per la famiglia {family}.** "
                   f"La stima usa solo parametri generici. "
                   f"Consiglio: indicizza disegni di pompe {family} per dati più specifici.")
    elif family_docs > 0 and family_docs < 3:
        st.warning(f"Solo **{family_docs} documenti** trovati per {family}. "
                   f"Accuratezza potrebbe essere limitata. "
                   f"Consiglio: indicizza altri disegni {family} per raggiungere almeno 5 documenti.")
    elif family_docs >= 5:
        st.success(f"**{family_docs} documenti** trovati per {family}. "
                   f"Base dati solida per una stima affidabile.")

    if material_docs == 0 and doc_count > 0:
        st.info(f"Nessun documento specifico per **{material}**. "
                f"I pesi sono calcolati con le formule di densità standard. "
                f"Per dati più precisi, indicizza disegni con componenti in {material}.")

    # Warnings dalla stima
    if result.warnings:
        for w in result.warnings:
            st.warning(w)


# ============================================================
# CONFRONTO STIMA vs REALE (Game-Changer)
# ============================================================

def _render_validation(result, params):
    """Confronto automatico tra stima e dati reali nel database."""
    st.markdown("### Confronto Stima vs Reale")
    st.caption("Il sistema cerca pompe simili con peso reale noto e confronta la tua stima. "
               "Più dati di riferimento hai, più affidabile sarà la validazione.")

    total_estimated = result.total_weight_kg
    family = params.get("pump_family", "")
    similar_refs = []

    # 1. Cerca nei pesi di riferimento
    try:
        from weight_engine.reference_weights import find_similar
        similar_refs = find_similar(params, top_k=5)
    except Exception:
        pass

    # 2. Cerca nei componenti estratti dal database pompe
    db_refs = []
    try:
        from weight_engine.pump_database import get_pumps_by_family
        db_pumps = get_pumps_by_family(family)
        for pump in db_pumps[:5]:
            if pump.get("weight_kg") and pump["weight_kg"] > 0:
                db_refs.append({
                    "pump_name": os.path.basename(pump.get("source", "DB")),
                    "total_weight_kg": pump["weight_kg"],
                    "family": family,
                })
    except Exception:
        pass

    all_refs = similar_refs + db_refs

    if not all_refs:
        st.info(f"Nessuna pompa di riferimento trovata per **{family}**. "
                f"Aggiungi pesi reali nella sezione 'Inserisci Peso Reale' per attivare il confronto.")
        return

    # Calcola accuratezza
    ref_weights = [r["total_weight_kg"] for r in all_refs if r.get("total_weight_kg")]
    if not ref_weights:
        return

    avg_ref = sum(ref_weights) / len(ref_weights)
    deviation = abs(total_estimated - avg_ref) / avg_ref * 100 if avg_ref > 0 else 100
    accuracy = max(0, 100 - deviation)

    # Badge
    if accuracy >= 90:
        badge = "●"
        badge_text = "Eccellente"
    elif accuracy >= 70:
        badge = "●"
        badge_text = "Buona"
    else:
        badge = "●"
        badge_text = "Da verificare"

    # Mostra risultati
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("La tua stima", f"{total_estimated:,.1f} kg")
    c2.metric("Media riferimenti", f"{avg_ref:,.1f} kg")
    c3.metric("Accuratezza", f"{accuracy:.1f}%")
    c4.metric("Giudizio", f"{badge} {badge_text}")

    # Dettaglio pompe simili
    st.markdown("**Pompe di riferimento trovate:**")
    for ref in all_refs:
        ref_w = ref.get("total_weight_kg", 0)
        delta = total_estimated - ref_w
        delta_pct = (delta / ref_w * 100) if ref_w > 0 else 0
        delta_str = f"+{delta:.1f}" if delta >= 0 else f"{delta:.1f}"
        st.caption(f"▸ **{ref['pump_name']}** — {ref_w:,.1f} kg — "
                   f"Δ {delta_str} kg ({delta_pct:+.1f}%)")


# ============================================================
# INSERISCI PESO REALE (Reference Weights)
# ============================================================

def _render_reference_weights_form(family: str):
    """Form per inserire pesi reali di pompe costruite."""
    st.markdown("### Inserisci Peso Reale")
    st.caption("Aggiungi il peso misurato di una pompa costruita. "
               "Questi dati vengono usati per validare le stime future e migliorare l'accuratezza. "
               "Più dati reali inserisci, più il sistema diventa preciso.")

    try:
        from weight_engine.reference_weights import add_reference, get_references

        with st.expander("+ Aggiungi nuovo peso reale", expanded=False):
            ref_name = st.text_input("Nome pompa", placeholder="es. BB1-8x6-13-Progetto-XY",
                                     key="ref_name")
            ref_family = st.text_input("Famiglia", value=family, key="ref_family")
            ref_weight = st.number_input("Peso totale misurato (kg)",
                                         min_value=0.0, max_value=100000.0,
                                         value=0.0, step=10.0, key="ref_weight")
            ref_notes = st.text_area("Note", placeholder="es. Peso da bolla di carico, con basamento",
                                     key="ref_notes")

            if st.button("Salva Riferimento", key="save_ref"):
                if ref_name.strip() and ref_weight > 0:
                    if add_reference(ref_name.strip(), ref_family, ref_weight,
                                     notes=ref_notes):
                        st.success(f"Peso reale **{ref_name.strip()}** ({ref_weight:.1f} kg) salvato.")
                    else:
                        st.error("Errore nel salvataggio.")
                else:
                    st.warning("Inserisci nome e peso > 0.")

        # Mostra riferimenti esistenti per questa famiglia
        refs = get_references(family)
        if refs:
            st.caption(f"**{len(refs)} riferimenti** per famiglia {family}:")
            for ref in refs[:10]:
                st.caption(f"▸ {ref['pump_name']} — {ref['total_weight_kg']:,.1f} kg "
                           f"({ref.get('notes', '')[:50]})")

    except ImportError:
        st.info("Modulo reference_weights non disponibile.")




def _render_ref_vs_estimate(result, ref_pump):
    """Mostra confronto visivo tra dati pompa di riferimento e stima calcolata."""
    if not ref_pump or ref_pump.get("source") == "none":
        return

    ref_components = ref_pump.get("components", {})
    if not ref_components:
        return

    st.markdown("### Confronto: Riferimento vs Stima")
    st.caption("Confronto visivo tra i dati della pompa di riferimento nel database e la stima calcolata con i parametri attuali.")
    st.caption(f"Pompa di riferimento: {ref_pump.get('source', 'N/D')}")

    if not HAS_PLOTLY:
        pass  # Si procede comunque con la tabella

    import pandas as pd

    rows = []
    for comp in result.components:
        if not comp.is_estimated or not comp.estimated_weight_kg:
            continue

        # Cerca componente corrispondente nel riferimento
        ref_data = ref_components.get(comp.component_name, {})
        ref_weight = ref_data.get("weight_kg", 0)

        est_weight = comp.estimated_weight_kg

        if ref_weight and ref_weight > 0:
            delta_pct = ((est_weight - ref_weight) / ref_weight) * 100

            # Indicatore incertezza
            abs_delta = abs(delta_pct)
            if abs_delta <= 10:
                indicator = "●"
                uncertainty = "Bassa"
            elif abs_delta <= 20:
                indicator = "◐"
                uncertainty = "Media"
            else:
                indicator = "○"
                uncertainty = "Alta"

            rows.append({
                "": indicator,
                "Componente": comp.component_name,
                "Rif. (kg)": round(ref_weight, 1),
                "Stima (kg)": round(est_weight, 1),
                "Delta": f"{delta_pct:+.1f}%",
                "Incertezza": uncertainty,
                "Scaling": comp.calculation_details.get("formula", "") if comp.calculation_details else "",
            })
        else:
            rows.append({
                "": "—",
                "Componente": comp.component_name,
                "Rif. (kg)": "—",
                "Stima (kg)": round(est_weight, 1),
                "Delta": "N/D",
                "Incertezza": "No rif.",
                "Scaling": "",
            })

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Legenda
        st.caption("● Delta <10% | ◐ Delta 10-20% | ○ Delta >20% | — Nessun riferimento")

        # Metriche riepilogo confronto
        with_ref = [r for r in rows if r["Delta"] != "N/D"]
        if with_ref:
            low = sum(1 for r in with_ref if r["Incertezza"] == "Bassa")
            med = sum(1 for r in with_ref if r["Incertezza"] == "Media")
            high = sum(1 for r in with_ref if r["Incertezza"] == "Alta")

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Componenti Confrontati", len(with_ref))
            col2.metric("Bassa Incertezza", low)
            col3.metric("Media Incertezza", med)
            col4.metric("Alta Incertezza", high)

        # Grafico radar (se Plotly disponibile e ci sono dati)
        if HAS_PLOTLY and len(with_ref) >= 3:
            ref_values = []
            est_values = []
            labels = []
            for r in with_ref[:8]:
                if isinstance(r["Rif. (kg)"], (int, float)):
                    labels.append(r["Componente"][:20])
                    ref_values.append(r["Rif. (kg)"])
                    est_values.append(r["Stima (kg)"])

            if len(labels) >= 3:
                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(
                    r=ref_values + [ref_values[0]],
                    theta=labels + [labels[0]],
                    fill='toself', name='Riferimento',
                    line_color='#2F5496', opacity=0.6,
                ))
                fig.add_trace(go.Scatterpolar(
                    r=est_values + [est_values[0]],
                    theta=labels + [labels[0]],
                    fill='toself', name='Stima',
                    line_color='#E67E22', opacity=0.6,
                ))
                fig.update_layout(
                    title="Confronto Visivo Pesi (Radar)",
                    polar=dict(radialaxis=dict(visible=True)),
                    showlegend=True,
                    height=400,
                    font=dict(family="Inter, sans-serif", size=11),
                )
                st.plotly_chart(fig, use_container_width=True)


# ============================================================
# CERCA POMPE SIMILI NEL DATABASE
# ============================================================

_COMPONENT_TYPE_IT = {
    "impeller": "Girante",
    "casing": "Corpo",
    "shaft": "Albero",
    "cover": "Coperchio",
    "bearing_housing": "Supporto",
    "wear_ring": "Anello Usura",
    "fastener": "Viteria",
    "template": "Sesta Controllo",
    "casing": "Corpo Pompa",
    "hydraulic_layout": "Tracciato Idraulico",
    "pattern": "Modello Fusione",
}


def _component_type_label(doc: dict) -> str:
    """Restituisce etichetta tipo componente in italiano, con fallback a doc_type."""
    ct = doc.get("component_type", "")
    if ct and ct in _COMPONENT_TYPE_IT:
        return _COMPONENT_TYPE_IT[ct]
    dt = doc.get("doc_type", "")
    return (dt or "").replace("_", " ").title() if dt else "—"


def _render_pump_search_results(params: dict):
    """Cerca pompe simili nel database indicizzato usando i parametri del form."""
    import pandas as pd

    family = params.get("pump_family", "")
    nq = params.get("nq", 0)
    d2_mm = params.get("d2_mm", 0)
    scale_factor = params.get("scale_factor", 1.0)
    num_stages = params.get("num_stages", 1)

    # Costruisci query semantica (solo famiglia, Nq, D2 — no scale/stadi)
    query_parts = []
    if family:
        query_parts.append(f"pompa centrifuga {family}")
    if nq:
        query_parts.append(f"velocità specifica Nq {nq}")
    if d2_mm > 0:
        query_parts.append(f"diametro girante D2 {d2_mm} mm")
    query_parts.append("peso weight parts list componenti disegno tecnico datasheet")

    search_query = " ".join(query_parts)

    # Filtri Qdrant per metadata
    qdrant_filters = {}
    if family:
        qdrant_filters["pump_family"] = family

    with st.status("🔍 Ricerca pompe simili nel database...", expanded=True) as status:
        st.write(f"**Famiglia:** {family or 'Tutte'}")
        st.write(f"**Parametri:** Nq={nq}, D2={d2_mm}mm")

        try:
            from rag.qdrant_db import qdrant_query
            # Prima ricerca: con filtro famiglia (max 15 risultati)
            docs = qdrant_query(search_query, n_results=15, filters=qdrant_filters if qdrant_filters else None)

            # Se pochi risultati con filtro, prova senza filtro famiglia
            if len(docs) < 5 and family:
                st.write("Pochi risultati con filtro famiglia, amplio la ricerca...")
                docs_extra = qdrant_query(search_query, n_results=10, filters=None)
                # Merge senza duplicati
                seen_ids = {d["id"] for d in docs}
                for d in docs_extra:
                    if d["id"] not in seen_ids:
                        docs.append(d)
                        seen_ids.add(d["id"])

            if not docs:
                status.update(label="Nessuna pompa trovata", state="error")
                st.warning("Nessun documento trovato nel database. "
                           "Prova a indicizzare più documenti tecnici (disegni, parts list, datasheet).")
                return

            status.update(label=f"✅ Ricerca completata", state="complete")

        except Exception as e:
            status.update(label="Errore nella ricerca", state="error")
            st.error(f"Errore connessione database: {e}")
            return

    # --- Deduplicazione: un solo record per file (miglior score + merge metadati) ---
    seen_files = {}      # basename -> best doc
    file_metadata = {}   # basename -> merged metadata da tutti i chunk
    for doc in docs:
        source = doc.get("source", "")
        basename = os.path.basename(source) if source else "N/D"
        score = doc.get("score", 0)
        # Accumula metadati da tutti i chunk dello stesso file
        if basename not in file_metadata:
            file_metadata[basename] = {}
        for k, v in doc.items():
            if v is not None and v != "" and v != "—" and k not in ("text", "id", "score"):
                file_metadata[basename][k] = v
        # Tieni il chunk con score migliore
        if basename not in seen_files or score > seen_files[basename].get("score", 0):
            seen_files[basename] = doc

    # Merge metadati nel doc migliore di ogni file
    for basename, doc in seen_files.items():
        meta = file_metadata.get(basename, {})
        for k, v in meta.items():
            if k not in doc or doc[k] is None or doc[k] == "" or doc[k] == "—":
                doc[k] = v

    # Filtra: se si cerca con D2, mostra solo documenti con dati reali
    if d2_mm > 0:
        filtered = {k: v for k, v in seen_files.items()
                    if v.get("d2_mm") or v.get("finished_weight_kg") or v.get("has_weight")}
        if filtered:
            seen_files = filtered

    # --- Tabella risultati ---
    n_unique = len(seen_files)
    st.markdown(f"#### 📋 Pompe e Documenti Trovati ({n_unique})")
    st.caption(f"Risultati per: **{family}** | Nq={nq} | D2={d2_mm}mm")

    rows = []
    for i, (basename, doc) in enumerate(seen_files.items(), 1):
        text = doc.get("text", "")
        score = doc.get("score", 0)
        doc_family = doc.get("pump_family", "—")
        doc_type = doc.get("doc_type", "—")
        materials = doc.get("materials", [])
        has_weight = doc.get("has_weight", False)

        # Score in percentuale
        score_pct = round(score * 100, 1) if score <= 1.0 else round(score, 1)

        # Usa metadati estratti dal componente (priorità) o regex fallback
        import re
        # Pesi: prima da metadati, poi regex
        weight_val = doc.get("finished_weight_kg")
        if weight_val:
            weights_str = f"{weight_val} kg"
        else:
            weight_mentions = re.findall(r'(\d+[.,]?\d*)\s*(?:kg|Kg|KG)', text)
            weights_str = ", ".join(weight_mentions[:5]) + " kg" if weight_mentions else "—"

        # D2: prima da metadati, poi regex
        d2_val = doc.get("d2_mm")
        if d2_val:
            d2_str = f"{d2_val} mm"
        else:
            d2_mentions = re.findall(r'[Dd]2\s*[=:]\s*(\d+)', text)
            d2_str = ", ".join(d2_mentions[:3]) + " mm" if d2_mentions else "—"

        # Nq: prima da metadati, poi regex
        nq_val = doc.get("nq_calculated") or doc.get("nq")
        if nq_val:
            nq_str = str(nq_val)
        else:
            nq_mentions = re.findall(r'[Nn][Qq]\s*[=:]\s*(\d+[.,]?\d*)', text)
            nq_str = ", ".join(nq_mentions[:3]) if nq_mentions else "—"

        # Validazione
        validation = doc.get("data_validation", "")

        rows.append({
            "#": i,
            "Documento": basename[:40],
            "Rilevanza": f"{score_pct}%",
            "Famiglia": doc_family if doc_family != "—" else "",
            "Tipo": _component_type_label(doc),
            "Pesi": weights_str,
            "D2": d2_str,
            "Nq": nq_str,
            "Materiali": ", ".join(materials[:3]) if materials else "—",
            "Ha Pesi": "✅" if has_weight or weight_val else "",
            "Valid.": validation,
        })

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True,
                     column_config={
                         "#": st.column_config.NumberColumn(width="small"),
                         "Rilevanza": st.column_config.TextColumn(
                             width="small",
                             help="Similarity Coseno: misura quanto il testo del documento "
                                  "è simile alla tua ricerca. Non è un voto di accuratezza! "
                                  "Funziona così: il sistema converte sia la tua ricerca che il documento "
                                  "in vettori numerici, poi misura l'angolo tra di essi. "
                                  "Più sono 'allineati', più il punteggio è alto. "
                                  "Un 50-60% è già un buon match per testi tecnici OCR. "
                                  "Per confermare la corrispondenza, guarda i dati estratti (D2, Nq, Peso) "
                                  "e la colonna Valid. (OK/KO)."
                         ),
                         "Ha Pesi": st.column_config.TextColumn(width="small"),
                     })

        # Metriche riepilogative
        n_with_weight = sum(1 for r in rows if r["Ha Pesi"] == "✅")
        n_with_d2 = sum(1 for r in rows if r["D2"] != "—")
        n_with_nq = sum(1 for r in rows if r["Nq"] != "—")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Documenti Trovati", len(rows))
        c2.metric("Con Dati Peso", n_with_weight)
        c3.metric("Con D2", n_with_d2)
        c4.metric("Con Nq", n_with_nq)

        # Dettaglio espandibile per ogni documento con dati componente
        st.markdown("---")
        st.markdown("#### 📄 Dettaglio Documenti")
        for i, (basename, doc) in enumerate(seen_files.items(), 1):
            source = doc.get("source", "N/D")
            text = doc.get("text", "")
            score = doc.get("score", 0)
            score_pct = round(score * 100, 1) if score <= 1.0 else round(score, 1)
            comp_type = _component_type_label(doc)

            with st.expander(f"[{i}] {basename} — {comp_type} — {score_pct}%", expanded=(i <= 1)):
                st.caption(f"📁 `{source}`")

                # --- Scheda dati componente (se disponibili) ---
                has_comp_data = doc.get("d2_mm") or doc.get("finished_weight_kg")
                if has_comp_data:
                    # Validazione
                    val = doc.get("data_validation", "")
                    val_icon = "✅" if val == "OK" else ("❌" if val == "KO" else "")
                    nq_info = doc.get("nq_info", "")
                    if val or nq_info:
                        st.info(f"{val_icon} **Validazione: {val}** — {nq_info}")

                    # --- Riga 1: Peso + Diametri ---
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown("**⚖️ Peso**")
                        fw = doc.get("finished_weight_kg")
                        rw = doc.get("raw_weight_kg")
                        if fw: st.write(f"Peso finito: **{fw} kg**")
                        if rw: st.write(f"Peso grezzo: {rw} kg")
                    with col2:
                        st.markdown("**📐 Diametri**")
                        for k, label in [("d2_mm","D2"), ("suction_diameter_mm","Aspirazione"),
                                         ("hub_diameter_mm","Mozzo"), ("shaft_bore_mm","Foro albero"),
                                         ("wear_ring_diameter_mm","Anello usura"), ("eye_diameter_mm","Occhio")]:
                            v = doc.get(k)
                            if v: st.write(f"{label}: **{v}** mm")
                    with col3:
                        st.markdown("**📏 Geometria Sezione**")
                        for k, label in [("overall_width_mm","Larghezza totale"), ("b2_mm","b2 (uscita)"),
                                         ("shroud_thickness_mm","Spessore shroud"), ("key_radii","Raggi")]:
                            v = doc.get(k)
                            if v: st.write(f"{label}: **{v}**{' mm' if isinstance(v,(int,float)) else ''}")

                    # --- Riga 2: Pale + Equilibratura + Tolleranze ---
                    col4, col5, col6 = st.columns(3)
                    with col4:
                        st.markdown("**🔄 Pale**")
                        nb = doc.get("num_blades")
                        if nb: st.write(f"N. pale: **{nb}**")
                        bh = doc.get("blade_holes_diameter_mm")
                        if bh: st.write(f"Fori pale: Φ{bh} mm")
                        bc = doc.get("blade_holes_count")
                        if bc: st.write(f"N. fori: {bc}")
                    with col5:
                        st.markdown("**⚖️ Equilibratura**")
                        for k, label in [("disc_thickness_at_balance_mm","Spessore disco"),
                                         ("balance_ref_diameter_mm","Diametro rif."),
                                         ("min_disc_thickness_mm","Spessore min."),
                                         ("balancing_grade","Grado")]:
                            v = doc.get(k)
                            if v: st.write(f"{label}: **{v}**{' mm' if 'mm' in k else ''}")
                    with col6:
                        st.markdown("**📋 Cartiglio**")
                        for k, label in [("pump_model","Modello"), ("drawing_number","N. disegno"),
                                         ("revision","Revisione"), ("description_it","Descrizione")]:
                            v = doc.get(k)
                            if v: st.write(f"{label}: **{v}**")
                        sf = doc.get("surface_finishes")
                        if sf: st.write(f"Finiture: {sf}")
                        kt = doc.get("key_tolerances")
                        if kt: st.write(f"Tolleranze: {kt}")

                    # Tutti i diametri
                    ad = doc.get("all_diameters")
                    if ad:
                        st.caption(f"🔵 Tutti i diametri: {ad}")

                else:
                    # Nessun dato componente — mostra info base
                    if doc.get("pump_family"):
                        st.caption(f"🏷️ Famiglia: **{doc['pump_family']}** | "
                                  f"Tipo: {doc.get('doc_type', '—')}")
                    snippet = text[:400].strip()
                    if len(text) > 400:
                        snippet += "..."
                    st.text(snippet)

                # Download
                if source and not source.startswith(("http://", "https://")):
                    from modules.helpers import get_file_for_download
                    file_info = get_file_for_download(source)
                    if file_info:
                        file_data, name, mime = file_info
                        st.download_button(
                            f"📥 Scarica {name[:30]}",
                            data=file_data, file_name=name, mime=mime,
                            key=f"dl_pump_search_{i}",
                        )


# ============================================================
# PAGINA PRINCIPALE
# ============================================================

def render():
    _inject_styles()

    # Header
    st.markdown("""
    <div class="estimation-header">
        <h2>Stima Pesi Componenti Pompe</h2>
        <p>Inserisci i parametri di progetto per ottenere la stima dei pesi dei componenti principali</p>
    </div>
    """, unsafe_allow_html=True)

    # ============================================
    # GESTIONE MULTI-PROGETTO
    # ============================================
    try:
        from weight_engine.project_manager import list_projects, load_project, save_project, delete_project
        projects = list_projects()

        if projects:
            st.markdown("### Progetti Salvati")
            st.caption("Seleziona un progetto per caricare i parametri nel form, oppure creane uno nuovo. "
                       "Ogni progetto salva famiglia, Nq, pressione, materiale e tutti gli altri parametri.")

            proj_names = ["— Nuovo Progetto —"] + [
                f"{p['name']}  (Rev.{p['revision']} | {p['family']} | {p['material']})"
                for p in projects
            ]
            selected_proj = st.selectbox("Carica Progetto", proj_names, index=0,
                                         key="project_select")

            if selected_proj != "— Nuovo Progetto —":
                proj_name = selected_proj.split("  (Rev.")[0]
                loaded = load_project(proj_name)
                if loaded:
                    st.session_state["loaded_project"] = loaded
                    st.session_state["loaded_project_name"] = proj_name
                    st.success(f"Progetto **{proj_name}** caricato — parametri applicati al form.")

                    col_del, _ = st.columns([1, 3])
                    with col_del:
                        if st.button("Elimina questo progetto", key="del_proj"):
                            delete_project(proj_name)
                            st.session_state.pop("loaded_project", None)
                            st.session_state.pop("loaded_project_name", None)
                            st.rerun()
            else:
                st.session_state.pop("loaded_project", None)
                st.session_state.pop("loaded_project_name", None)

            st.markdown("---")
    except ImportError:
        pass

    # Layout: Form (sinistra) + Info (destra)
    col_form, col_info = st.columns([2, 1])

    with col_form:
        # Helper per caricare default da progetto salvato
        _lp = st.session_state.get("loaded_project", {})

        st.markdown("### Parametri di Progetto")
        st.caption("Compilando questi parametri il sistema calcola il peso di ogni componente della pompa. "
                   "Ogni campo modifica il risultato: più dati inserisci, più la stima sarà accurata. "
                   "I campi con * sono obbligatori, gli altri hanno un default ragionevole.")

        with st.expander("Esempio: come compilare il form", expanded=False):
            st.markdown("""
**Esempio: Pompa BB1 — 8×6×13 — alta pressione — acciaio inox**

| Campo | Valore da inserire | Perché |
|-------|--------------------|--------|
| **Famiglia Pompa** * | `BB1 — BB1 - Axially Split Single Stage` | È una pompa a cassa bipartita monostadio |
| **Nq** * | `45` | Velocità specifica dal datasheet (girante mista) |
| **Scale Factor** | `1.15` | Girante 15% più grande del riferimento |
| **Numero Stadi** | `1` | Monostadio (BB1) |
| **Pressione** | `35` bar | Dal datasheet: pressione di progetto |
| **Temperatura** | `180` °C | Dal datasheet: fluido caldo |
| **Materiale** * | `SS 316` | Richiesto per resistenza alla corrosione |
| **Spessore Parete** | `0` (auto) | Non disponibile → calcolo automatico |
| **Flange Rating** | `300` | 300# perché pressione 35 bar (150# non basta) |
| **Aspirazione** | `8"` | Dal datasheet della pompa |
| **Mandata** | `6"` | Dal datasheet della pompa |

**Risultato atteso:** Il sistema calcolerà ~22 componenti (corpo, coperchi, girante, albero, cuscinetti, 
tenute, flange, bulloneria, basamento...) con peso totale stimato e confidenza per ogni voce.

**Se non hai tutti i dati**, lascia i default — il sistema funziona comunque, ma la stima sarà meno precisa.
            """)

        # --- Sezione 1: Pompa ---
        st.markdown('<div class="param-section"><h4>Pompa</h4></div>',
                    unsafe_allow_html=True)
        st.caption("Questi campi determinano QUALI componenti vengono calcolati e la loro DIMENSIONE. "
                   "Famiglia = lista componenti (OH2 ha 24 componenti dalla Standard Part List, BB ~22, VS ~18). "
                   "Nq + D2 = geometria girante e corpo. Scale Factor = rapporto D2 nuova/riferimento. "
                   "Se inserisci D2, il sistema cerca automaticamente disegni simili nel database e usa il loro peso come riferimento.")

        family_names = get_family_names()
        family_options = [f"{k} — {v}" for k, v in sorted(family_names.items())]
        # Calcola index famiglia da progetto caricato
        _lp_family = _lp.get("pump_family", "")
        _family_idx = 0
        if _lp_family:
            for i, opt in enumerate(family_options):
                if opt.startswith(_lp_family):
                    _family_idx = i
                    break

        selected_family = st.selectbox(
            "Famiglia Pompa *",
            family_options,
            index=_family_idx,
            help="OBBLIGATORIO. Determina il template dei componenti e le formule di scaling. "
                 "OH2 = pompe overhung a sbalzo con supporti (24 componenti dalla Standard Part List: "
                 "Corpo 102, Coperchio 161, Girante 230, Albero 210, Supporto 330, ecc.). "
                 "BB = between bearings (cassa bipartita, ~22 componenti). "
                 "VS = verticali (colonna + coppa, ~18 componenti). "
                 "Sotto la selezione vengono mostrati i modelli TPI e Legacy corrispondenti.",
        )
        pump_family = selected_family.split(" — ")[0] if selected_family else ""

        # Mostra modelli TPI e Legacy
        try:
            from weight_engine.parts_list import get_pump_models
            _models = get_pump_models(pump_family)
            if _models:
                _tpi_str = ", ".join(_models.get("tpi", [])) or "—"
                _leg_str = ", ".join(_models.get("legacy", [])) or "—"
                _notes = _models.get("notes", "")
                st.caption(f"**Modelli TPI:** {_tpi_str}  |  **Legacy:** {_leg_str}  |  _{_notes}_")
        except Exception:
            pass

        col_nq, col_d2 = st.columns(2)
        with col_nq:
            nq = st.number_input(
                "Nq (velocità specifica) *",
                min_value=0.0, max_value=500.0, value=float(_lp.get("nq", 30.0)), step=1.0,
                help="OBBLIGATORIO. Nq = n·√Q / H^(3/4). "
                     "Determina il rapporto b2/D2 dalla curva empirica (Standard aziendali). "
                     "Nq basso (<25): girante radiale, b2/D2≈0.07. "
                     "Nq medio (25-80): b2/D2≈0.09-0.18. "
                     "Nq alto (>80): girante assiale, b2/D2≈0.19+.",
            )
        with col_d2:
            d2_mm = st.number_input(
                "D2 — Diametro girante (mm)",
                min_value=0.0, max_value=2000.0,
                value=float(_lp.get("d2_mm", 0.0)), step=10.0,
                help="Diametro esterno girante in mm. Dato fondamentale per la stima. "
                     "EFFETTI quando inserisci D2: "
                     "1) Calcola automaticamente b2 (larghezza uscita) dalla curva Nq aziendale. "
                     "2) Cerca nel database disegni con D2 simile (±30%) per ogni componente (girante, corpo, coperchio). "
                     "3) Usa il peso del disegno più simile come base per lo scaling. "
                     "4) Calcola scale factor = D2_new / D2_riferimento. "
                     "Esempio: D2=350mm, Nq=30 → b2=31.9mm, trova girante 230A70P20 (D2=327mm, 103kg, 61% match). "
                     "Se non hai D2, lascia 0: il sistema usa solo stime parametriche.",
            )

        # Auto-calcolo b2 dalla curva Nq + D2
        try:
            from weight_engine.nq_curve import get_b2_d2_ratio, calc_b2
            _b2d2 = get_b2_d2_ratio(nq)
            if d2_mm > 0:
                _b2 = calc_b2(nq, d2_mm)
                st.markdown(
                    f"""<div style="
                        background: linear-gradient(135deg, #e8f5e9, #f1f8e9);
                        border-left: 4px solid #2e7d32;
                        border-radius: 6px;
                        padding: 10px 14px;
                        margin: 6px 0 10px 0;
                        font-size: 0.92em;
                    ">
                        <span title="Il rapporto b2/D2 è ricavato dalla curva aziendale Nq (Standard interni TPI).
b2 = larghezza uscita girante, calcolata come b2/D2 × D2.
Nq basso (&lt;25) → girante stretta (b2/D2≈0.07).
Nq medio (25-80) → b2/D2 tra 0.09 e 0.18.
Nq alto (&gt;80) → girante larga (b2/D2≈0.19+).
Questo valore viene usato per cercare giranti simili nel database."
                        style="cursor: help; text-decoration: underline dotted #888;">
                            ℹ️ <strong>Curva Nq</strong>
                        </span>
                        &nbsp;→&nbsp; b2/D2 = <span style="color:#1b5e20; font-weight:600;">{_b2d2:.3f}</span>
                        &nbsp;→&nbsp; b2 = <span style="color:#1b5e20; font-weight:700; font-size:1.05em;">{_b2:.1f} mm</span>
                        <span style="color:#555;"> (con D2 = {d2_mm:.0f} mm)</span>
                    </div>""",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""<div style="
                        background: #f5f5f5;
                        border-left: 4px solid #bdbdbd;
                        border-radius: 6px;
                        padding: 10px 14px;
                        margin: 6px 0 10px 0;
                        font-size: 0.92em;
                        color: #777;
                    ">
                        <span title="Inserisci il diametro girante D2 per calcolare automaticamente b2."
                        style="cursor: help; text-decoration: underline dotted #aaa;">
                            ℹ️ <strong>Curva Nq</strong>
                        </span>
                        &nbsp;→&nbsp; b2/D2 = <span style="font-weight:600;">{_b2d2:.3f}</span>
                        &nbsp;|&nbsp; <em>Inserisci D2 per calcolare b2</em>
                    </div>""",
                    unsafe_allow_html=True,
                )
        except Exception:
            pass

        # Scale Factor e Numero Stadi — nascosti (valori di default)
        scale_factor = float(_lp.get("scale_factor", 1.0))
        num_stages = int(_lp.get("num_stages", 1))

        # --- Bottone CERCA POMPE SIMILI ---
        _search_params = {
            "pump_family": pump_family,
            "nq": nq,
            "d2_mm": d2_mm,
            "scale_factor": scale_factor,
            "num_stages": num_stages,
        }
        search_pump_clicked = st.button(
            "🔍 Cerca Pompe Simili nel Database",
            use_container_width=True,
            help="Cerca nel database indicizzato tutte le pompe che corrispondono "
                 "ai parametri inseriti (famiglia, Nq, D2, scale factor). "
                 "Mostra pesi, materiali e documenti di riferimento trovati.",
            key="search_similar_pumps",
        )

        if search_pump_clicked:
            _render_pump_search_results(_search_params)


        st.markdown('<div class="param-section"><h4>Condizioni di Progetto</h4></div>',
                    unsafe_allow_html=True)
        st.caption("Pressione e temperatura influenzano lo SPESSORE delle pareti — peso corpo e coperchi. "
                   "Se li lasci al default (10 bar, 20°C) la stima sarà per condizioni standard. "
                   "Inserendo i valori reali il sistema verifica anche la compatibilità materiale/rating.")

        col_p, col_t = st.columns(2)
        with col_p:
            pressure = st.number_input(
                "MAWP — Pressione di Progetto (bar)",
                min_value=0.0, max_value=1000.0, value=float(_lp.get("pressure", 10.0)), step=0.5,
                help="MAWP = Maximum Allowable Working Pressure. Pressione max ammissibile di esercizio. "
                     "Default 10 bar. Effetti della pressione sulla stima: "
                     "1) Aumenta lo spessore pareti del corpo (SOP-569) → peso corpo e coperchi maggiore. "
                     "2) Il sistema verifica compatibilità con il rating flange scelto "
                     "(es. 150# max ~20 bar a temperatura ambiente per acciaio al carbonio). "
                     "3) Se superi il rating, appare un avviso rosso. "
                     "Inserisci la MAWP reale dal datasheet per una stima accurata.",
            )
        with col_t:
            temperature = st.number_input(
                "Temperatura di Progetto (°C)",
                min_value=-200.0, max_value=1000.0, value=float(_lp.get("temperature", 20.0)), step=5.0,
                help="Default 20°C (ambiente). Modificando la temperatura: "
                     "1) Il sistema verifica che il materiale scelto sia compatibile (ogni materiale ha un T_max). "
                     "2) Sotto -29°C: avviso Charpy (servono prove d'urto sul materiale). "
                     "3) Sopra 400°C: avviso creep (deformazione a caldo). "
                     "Lascia 20°C solo per applicazioni a temperatura ambiente.",
            )

        # --- Sezione 3: Materiale ---
        st.markdown('<div class="param-section"><h4>Materiale</h4></div>',
                    unsafe_allow_html=True)
        st.caption("Il materiale cambia il peso di TUTTI i componenti in proporzione alla densità. "
                   "Default: Carbon Steel (7850 kg/m³). Acciaio inox → +2%, Titanio → -43%! "
                   "Lo spessore parete (0=auto) aggiunge precisione se conosci il valore dal datasheet.")

        categories = list_material_categories()
        all_materials = []
        for cat, mats in categories.items():
            for mat in mats:
                all_materials.append(mat)

        material = st.selectbox(
            "Materiale Principale *",
            all_materials,
            index=all_materials.index("Carbon Steel") if "Carbon Steel" in all_materials else 0,
            help="OBBLIGATORIO. Default: Carbon Steel (ρ=7850 kg/m³). "
                 "Cambiando materiale cambia il peso di TUTTI i componenti in proporzione alla densità: "
                 "es. SS 316 (ρ=7990) → +2% peso, Duplex 2205 (ρ=7800) → -1%, "
                 "Titanium Gr.2 (ρ=4510) → -43% peso! "
                 "Usa il Confronto Configurazioni più sotto per comparare due materiali.",
        )

        # Info materiale
        if material:
            rho = get_density(material)
            props = get_properties(material)
            info_parts = [f"ρ = {rho} kg/m³" if rho else ""]
            if props:
                info_parts.append(f"Yield = {props.get('yield_strength','N/D')} MPa")
                info_parts.append(f"UTS = {props.get('tensile_strength','N/D')} MPa")
                info_parts.append(f"T_max = {props.get('temperature_limit','N/D')}°C")
                info_parts.append(f"Fornitura: {props.get('supply','N/D')}")
            st.caption(" | ".join([p for p in info_parts if p]))

        wall_thickness = st.number_input(
            "Spessore Parete (mm)",
            min_value=0.0, max_value=200.0, value=float(_lp.get("wall_thickness", 0.0)), step=0.5,
            help="Default 0 = calcolo AUTOMATICO secondo SOP-569 (pressione interna + limiti fondibilità). "
                 "Se conosci lo spessore dal datasheet, inseriscilo per una stima più precisa. "
                 "Valori tipici: 8-15mm per pompe standard, 20-40mm per alta pressione. "
                 "Lascia 0 se non hai il dato: il sistema calcola con SOP-569.",
        )

        # Mostra spessore calcolato SOP-569 / SOP-546
        if wall_thickness == 0 and pressure > 0 and material:
            try:
                from weight_engine.nq_curve import calc_casing_thickness, calc_impeller_disc_thickness
                _props = get_properties(material)
                if _props and _props.get('yield_strength', 0) > 0:
                    _ys = _props['yield_strength']
                    # Stima D_interno ≈ D2 della girante (appross. per Nq)
                    _d_est = 200 + nq * 3  # approssimazione empirica
                    th = calc_casing_thickness(pressure, _d_est, _ys)
                    th_imp = calc_impeller_disc_thickness(pressure, _d_est, _ys)
                    with st.expander("Spessori calcolati (SOP-569/546)", expanded=False):
                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown(f"**Corpo pompa (SOP-569)**")
                            st.caption(f"t calcolato = {th['t_calc_mm']} mm")
                            st.caption(f"+ sovrametallo = {th['t_with_corrosion_mm']} mm")
                            st.caption(f"Min fondibile = {th['t_min_castable_mm']} mm")
                            st.metric("Spessore finale", f"{th['t_final_mm']} mm")
                            st.caption(f"Controllato da: **{th['controlling']}**")
                        with c2:
                            st.markdown(f"**Disco girante (SOP-546)**")
                            st.caption(f"t posteriore = {th_imp['t_rear_mm']} mm")
                            st.caption(f"t anteriore = {th_imp['t_front_mm']} mm")
                            st.caption(f"Min spessore = {th_imp['t_min_mm']} mm")
            except Exception:
                pass

        # --- Sezione 4: Flangiatura ---
        st.markdown('<div class="param-section"><h4>Flangiatura</h4></div>',
                    unsafe_allow_html=True)
        st.caption("Rating e dimensioni flange determinano il peso degli attacchi (2 flange da 50-300 kg ciascuna). "
                   "Default: 150# / 8\" asp. / 6\" mand. Se hai i dati reali, inseriscili: "
                   "rating più alto = flange più pesanti, diametri più grandi = peso maggiore.")

        rating_options = [150, 300, 600, 900, 1500, 2500]
        flange_rating = st.selectbox(
            "Flange Rating",
            rating_options,
            index=0,
            help="Default 150# (bassa pressione, fino a ~20 bar). "
                 "Aumentando il rating: flange più spesse e pesanti. "
                 "150#: ~20 bar | 300#: ~51 bar | 600#: ~102 bar | "
                 "900#: ~153 bar | 1500#: ~255 bar | 2500#: ~425 bar. "
                 "Il sistema avvisa se la pressione di progetto supera il rating scelto. "
                 "Seleziona il rating corretto per il tuo impianto.",
        )

        col_suc, col_dis = st.columns(2)
        with col_suc:
            suction_size = st.number_input(
                "Aspirazione (pollici)",
                min_value=1.0, max_value=48.0, value=float(_lp.get("suction_size", 8.0)), step=1.0,
                help="Default 8\". Diametro attacco aspirazione. "
                     "Flange più grandi = peso flange maggiore. "
                     "Tipico: 3\" per pompe piccole, 8-12\" per medie, 16-24\" per grandi. "
                     "Modifica in base al tuo datasheet per calcolo flange accurato.",
            )
        with col_dis:
            discharge_size = st.number_input(
                "Mandata (pollici)",
                min_value=1.0, max_value=48.0, value=float(_lp.get("discharge_size", 6.0)), step=1.0,
                help="Default 6\". Generalmente 1-2 misure più piccolo dell'aspirazione "
                     "(es. asp. 8\" → mandata 6\"). "
                     "Influenza il peso della flangia di mandata e del diffusore. "
                     "Modifica in base al datasheet della pompa.",
            )

        # --- Sezione 4b: Calcolo Nozzle automatico (Mod.463) ---
        st.caption("Se conosci la portata (m³/h), il sistema suggerisce il DN ottimale per aspirazione e mandata "
                   "basandosi sui limiti di velocità API 610 (Mod.463). Esempio: Q=500 m³/h → 8\" asp. / 6\" mand.")
        with st.expander("Suggerimento DN Nozzle (Mod.463)", expanded=False):
            _q_flow = st.number_input(
                "Portata (m³/h)",
                min_value=0.0, max_value=50000.0, value=0.0, step=10.0,
                help="Inserisci la portata volumetrica per calcolare automaticamente il DN ottimale. "
                     "Esempio: Q=500 m³/h → aspirazione DN200 (8\"), mandata DN150 (6\"). "
                     "Limiti velocità API 610: aspirazione ≤4.6 m/s, mandata ≤7.6 m/s.",
            )
            if _q_flow > 0:
                try:
                    from weight_engine.nq_curve import select_nozzle_size
                    _noz = select_nozzle_size(_q_flow)
                    c1, c2 = st.columns(2)
                    with c1:
                        st.metric("Aspirazione suggerita",
                                  f"DN{_noz['suction_mm']} ({_noz['suction_inch']}\")")
                        st.caption(f"V = {_noz['suction_velocity']} m/s (limite: 4.6 m/s)")
                    with c2:
                        st.metric("Mandata suggerita",
                                  f"DN{_noz['discharge_mm']} ({_noz['discharge_inch']}\")")
                        st.caption(f"V = {_noz['discharge_velocity']} m/s (limite: 7.6 m/s)")
                    st.caption("Fonte: Mod.463 Rev.0 — Flange Nozzle Selection")
                except Exception:
                    pass

        # --- Sezione 4c: Dimensionamento Albero (Mod.496) ---
        with st.expander("Dimensionamento Albero (Mod.496 / API 610)", expanded=False):
            st.caption("Se conosci portata, prevalenza e velocità rotazione, il sistema calcola il diametro minimo "
                       "dell'albero secondo API 610 (Mod.496). Esempio: Q=500 m³/h, H=80m, n=1450 rpm → d=35mm")
            _c1, _c2, _c3 = st.columns(3)
            with _c1:
                _shaft_q = st.number_input("Q portata (m³/h)", min_value=0.0, value=0.0, step=10.0,
                                           key="shaft_q", help="Portata volumetrica per calcolo potenza assorbita")
            with _c2:
                _shaft_h = st.number_input("H prevalenza (m)", min_value=0.0, value=0.0, step=1.0,
                                           key="shaft_h", help="Prevalenza per calcolo potenza assorbita")
            with _c3:
                _shaft_n = st.number_input("n velocità (rpm)", min_value=100.0, value=3000.0, step=50.0,
                                           key="shaft_n", help="Velocità rotazione albero")

            if _shaft_q > 0 and _shaft_h > 0 and _shaft_n > 0:
                try:
                    from weight_engine.nq_curve import calc_shaft_diameter
                    _shaft = calc_shaft_diameter(
                        speed_rpm=_shaft_n, pump_family=pump_family,
                        q_m3h=_shaft_q, head_m=_shaft_h,
                    )
                    if _shaft["d_standard_mm"] > 0:
                        _sc1, _sc2, _sc3, _sc4 = st.columns(4)
                        with _sc1:
                            st.metric("Potenza", f"{_shaft['power_kw']} kW")
                        with _sc2:
                            st.metric("Coppia", f"{_shaft['torque_nm']} Nm")
                        with _sc3:
                            st.metric("d min", f"{_shaft['d_min_mm']} mm")
                        with _sc4:
                            st.metric("d standard", f"{_shaft['d_standard_mm']} mm")
                        st.caption(f"k = {_shaft['k_factor']} ({_shaft['family']}) — "
                                   f"Fonte: Mod.496 Rev.0 / API 610")
                except Exception:
                    pass

        # ============================================
        # VALIDAZIONE IN TEMPO REALE (Feature 2)
        # ============================================
        validation_results = _validate_params(
            material, temperature, pressure, flange_rating, scale_factor
        )

        if validation_results:
            st.markdown("---")
            for level, msg in validation_results:
                css_class = f"validation-{level}"
                st.markdown(f'<div class="{css_class}">{msg}</div>', unsafe_allow_html=True)

        # --- Sezione 5: Opzioni Avanzate ---
        with st.expander("Opzioni Avanzate"):
            use_ai_matching = st.checkbox(
                "Usa AI per trovare pompa di riferimento (RAG)",
                value=True,
                help="Cerca nei documenti indicizzati una pompa storica simile",
            )
            use_parametric_fallback = st.checkbox(
                "Abilita stime parametriche di fallback",
                value=True,
                help="Se non trova riferimento, usa correlazioni empiriche approssimate",
            )

        # --- Bottone Stima ---
        st.markdown("---")

        # Blocca se ci sono errori critici
        has_errors = any(level == "error" for level, _ in validation_results)
        if has_errors:
            st.error("Correggi gli errori di validazione prima di procedere")

        estimate_clicked = st.button(
            "Calcola Stima Pesi",
            type="primary",
            use_container_width=True,
            disabled=has_errors,
        )

        # --- Bottone Cerca nei Documenti (RAG) ---
        rag_search_clicked = st.button(
            "Cerca nei Documenti",
            use_container_width=True,
            help="Cerca automaticamente nei documenti indicizzati informazioni su pesi e disegni per questa configurazione",
        )

    # --- Info Panel (colonna destra) ---
    with col_info:
        if pump_family:
            family_info = get_family_info(pump_family)
            if family_info:
                st.markdown("### Info Famiglia")
                st.caption("Caratteristiche della famiglia di pompa selezionata secondo la classificazione API 610.")
                st.info(f"**{family_info['name']}**\n\n{family_info['description']}")

                template = family_info["template"]
                groups = {}
                for comp in template:
                    g = comp["group"]
                    if g not in groups:
                        groups[g] = 0
                    groups[g] += 1

                st.markdown("**Componenti per gruppo:**")
                for g, count in groups.items():
                    st.caption(f"• {g}: {count}")
                st.caption(f"**Totale: {len(template)} componenti**")

        # Auto-suggest pompa riferimento (Feature 4)
        _render_auto_suggest(pump_family, nq)

        # --- Auto-Popola da Database Pompe ---
        st.markdown("### Dati dal Database")
        st.caption("Componenti estratti automaticamente dai documenti indicizzati che corrispondono alla configurazione selezionata.")
        st.caption("Cerca componenti simili estratti dai disegni")
        if st.button("Auto-Popola da Disegni", use_container_width=True,
                     help="Cerca nel database pompe componenti simili e mostra i dati estratti"):
            try:
                from weight_engine.pump_database import search_pumps, get_all_pumps
                db_pumps = get_all_pumps()
                if not db_pumps:
                    st.info("Database pompe vuoto. Vai a 'Database Pompe' e clicca 'Ricostruisci'.")
                else:
                    # Cerca per famiglia
                    query = {}
                    if pump_family:
                        query["pump_family"] = pump_family.split(".")[0][:3]  # OH2 da OH2.xxx
                    results = search_pumps(query) if query else db_pumps
                    results_with_weight = [r for r in results if r.get("weight_kg")]

                    if results_with_weight:
                        st.success(f"Trovati {len(results_with_weight)} componenti con peso")
                        import pandas as pd
                        rows = []
                        # Salva i source paths per la preview
                        st.session_state["_db_component_sources"] = []
                        for p in results_with_weight[:30]:
                            rows.append({
                                "Componente": p.get("component_type", "?").replace("_", " ").title(),
                                "Peso (kg)": p.get("weight_kg"),
                                "Tipo": (p.get("weight_type") or "").title(),
                                "Materiali": ", ".join(p.get("materials") or []),
                                "Part Number": p.get("part_number") or "",
                                "File": os.path.basename(p.get("source", "")),
                            })
                            st.session_state["_db_component_sources"].append(p.get("source", ""))
                        df = pd.DataFrame(rows)
                        st.session_state["_db_component_df"] = df

            except Exception as e:
                st.warning(f"Ricerca non disponibile: {e}")

        # Mostra tabella interattiva (persistente dopo il click)
        if "_db_component_df" in st.session_state:
            df = st.session_state["_db_component_df"]
            event = st.dataframe(
                df, use_container_width=True, hide_index=True,
                column_config={"Peso (kg)": st.column_config.NumberColumn(format="%.1f")},
                on_select="rerun",
                selection_mode="single-row",
                key="db_component_table",
            )

            # Preview documento selezionato
            if event and event.selection and event.selection.rows:
                sel_idx = event.selection.rows[0]
                sources = st.session_state.get("_db_component_sources", [])
                if sel_idx < len(sources):
                    doc_path = sources[sel_idx]
                    if doc_path and os.path.isfile(doc_path):
                        ext = os.path.splitext(doc_path)[1].lower()
                        st.caption(f"Anteprima: `{os.path.basename(doc_path)}`")

                        if ext in (".tif", ".tiff", ".png", ".jpg", ".jpeg", ".bmp"):
                            try:
                                from PIL import Image as PILImage
                                img = PILImage.open(doc_path)
                                if img.mode not in ("RGB", "L", "RGBA"):
                                    img = img.convert("RGB")
                                st.image(img, caption=os.path.basename(doc_path), use_container_width=True)
                                st.session_state["_preview_img_path"] = doc_path
                                st.session_state["_preview_img_name"] = os.path.basename(doc_path)
                                if st.button("Schermo intero", key="fs_we_img", use_container_width=True):
                                    _show_fullscreen_preview_we()
                            except Exception as e:
                                st.caption(f"Anteprima non disponibile: {e}")
                        elif ext == ".pdf":
                            try:
                                import fitz
                                pdf_doc = fitz.open(doc_path)
                                if pdf_doc.page_count > 0:
                                    page = pdf_doc[0]
                                    mat = fitz.Matrix(150 / 72, 150 / 72)
                                    pix = page.get_pixmap(matrix=mat)
                                    img_bytes = pix.tobytes("png")
                                    st.image(img_bytes, caption=f"{os.path.basename(doc_path)} (pag. 1/{pdf_doc.page_count})", use_container_width=True)
                                    mat_hd = fitz.Matrix(300 / 72, 300 / 72)
                                    pix_hd = page.get_pixmap(matrix=mat_hd)
                                    st.session_state["_preview_pdf_bytes"] = pix_hd.tobytes("png")
                                    st.session_state["_preview_img_name"] = f"{os.path.basename(doc_path)} (pag. 1/{pdf_doc.page_count})"
                                    st.session_state["_preview_img_path"] = None
                                    if st.button("Schermo intero", key="fs_we_pdf", use_container_width=True):
                                        _show_fullscreen_preview_we()
                                pdf_doc.close()
                            except Exception as e:
                                st.caption(f"Anteprima PDF non disponibile: {e}")
                    elif doc_path:
                        st.caption(f"File non trovato: {doc_path}")

        st.markdown("### Formule di Scaling")
        st.caption("Mostra le formule utilizzate per calcolare il peso di ogni componente. "
                   "Il peso scala con f² o f^2.35 a seconda del tipo (casting vs pressurizzato).")
        st.markdown("""
        **Componenti casting:**
        ```
        pnew = pref × f^2.35 × ρnew/ρref
        ```

        **Componenti pressurizzati:**
        ```
        pnew = pref × f² × ρnew/ρref × Snew/Sref
        ```

        **Flange:**
        Tabella ASME B16.5
        """)

    # ============================================================
    # CERCA NEI DOCUMENTI (RAG)
    # ============================================================

    if rag_search_clicked:
        rag_params = {
            "pump_family": pump_family,
            "nq": nq,
            "material": material,
            "pressure": pressure,
            "temperature": temperature,
        }
        st.markdown("---")
        st.markdown("## Risultati Ricerca Documenti")
        _render_rag_search(rag_params)

    # ============================================================
    # ESECUZIONE STIMA
    # ============================================================

    if estimate_clicked:
        params = {
            "pump_family": pump_family,
            "nq": nq,
            "d2_mm": d2_mm,
            "scale_factor": scale_factor,
            "pressure": pressure,
            "temperature": temperature,
            "material": material,
            "flange_rating": flange_rating,
            "wall_thickness": wall_thickness,
            "num_stages": num_stages,
            "suction_size_inch": suction_size,
            "discharge_size_inch": discharge_size,
        }

        # Progress animation (Feature 9)
        with st.status("Stima in corso...", expanded=True) as status:
            import time as _time

            # Step 1: Validazione
            st.write("Validazione parametri...")
            _time.sleep(0.3)

            # Step 2: Ricerca pompa riferimento
            ref_pump = None
            if use_ai_matching:
                st.write("Ricerca pompa di riferimento via AI...")
                try:
                    from weight_engine.ai_matcher import find_reference_pump
                    ref_pump = find_reference_pump(params)
                    if ref_pump:
                        st.write(f"✓ Pompa trovata: {ref_pump.get('source', 'N/D')}")
                    else:
                        st.write("⚠ Nessuna pompa trovata, uso stime parametriche")
                except Exception as e:
                    st.write(f"⚠ Ricerca AI non disponibile: {e}")
            else:
                st.write("— Ricerca AI disabilitata")

            # Step 3: Calcolo componenti
            st.write("Calcolo pesi componenti...")
            result = run_estimation(params, reference_pump=ref_pump)

            # Step 4: Risultati
            estimated = len([c for c in result.components if c.is_estimated])
            st.write(f"✓ {estimated}/{len(result.components)} componenti stimati")
            st.write(f"✓ Peso totale: {result.total_weight_kg:,.1f} kg")

            status.update(label=f"Stima completata — {result.total_weight_kg:,.1f} kg", state="complete")

        # Salva nello storico
        try:
            from weight_engine.estimation_history import save_estimation
            save_estimation(result)
        except Exception:
            pass

        # Salva risultato in session state
        st.session_state["last_estimation"] = result
        st.session_state["last_estimation_params"] = params
        st.session_state["last_ref_pump"] = ref_pump

        # ============================================================
        # VISUALIZZAZIONE RISULTATI
        # ============================================================

        st.markdown("---")
        st.markdown("## Risultati Stima")

        # Peso totale
        st.markdown(
            f'<div class="total-weight">'
            f'Peso Totale Stimato: {result.total_weight_kg:,.1f} kg'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Metriche riepilogo
        col1, col2, col3, col4 = st.columns(4)
        estimated = len([c for c in result.components if c.is_estimated])
        total = len(result.components)
        high_conf = len([c for c in result.components if c.confidence == "alta"])
        warnings_count = len(result.warnings)

        col1.metric("Job ID", result.job_id)
        col2.metric("Componenti Stimati", f"{estimated}/{total}")
        col3.metric("Confidenza Alta", high_conf)
        col4.metric("Warning", warnings_count)

        # Warning
        if result.warnings:
            with st.expander(f"⚠ Warning ({len(result.warnings)})", expanded=True):
                for w in result.warnings:
                    st.warning(w)

        # ============================================
        # GRAFICI INTERATTIVI (Feature 1)
        # ============================================
        _render_charts(result)

        # ============================================
        # ALERT INTELLIGENTI (Copertura Documentale)
        # ============================================
        _render_smart_alerts(result, params)

        # ============================================
        # CONFRONTO STIMA vs REALE (Game-Changer)
        # ============================================
        _render_validation(result, params)

        # ============================================
        # INSERISCI PESO REALE (Reference Weights)
        # ============================================
        _render_reference_weights_form(pump_family)

        # Tabella risultati con dettaglio calcolo espandibile (Feature 7)
        st.markdown("### Parts List Dettagliata")
        st.caption("Lista completa di tutti i componenti stimati con peso, gruppo, metodo di calcolo e livello di confidenza.")
        st.caption("Clicca su un componente per vedere il dettaglio del calcolo")

        # Organizza per gruppo
        groups = {}
        for comp in result.components:
            g = comp.group
            if g not in groups:
                groups[g] = []
            groups[g].append(comp)

        for group_name, comps in groups.items():
            with st.expander(f"**{group_name}** ({len(comps)} componenti)", expanded=True):
                for comp in comps:
                    col_name, col_weight, col_conf = st.columns([3, 1, 1])

                    with col_name:
                        st.markdown(f"**{comp.component_name}**")
                        if comp.notes:
                            st.caption(comp.notes)

                    with col_weight:
                        if comp.estimated_weight_kg is not None:
                            st.metric("kg", f"{comp.estimated_weight_kg:,.1f}")
                        else:
                            st.caption("N/D")

                    with col_conf:
                        conf_class = f"confidence-{comp.confidence}"
                        st.markdown(
                            f'<span class="{conf_class}">{comp.confidence.upper()}</span>',
                            unsafe_allow_html=True,
                        )

                    # Feature 7: Dettaglio calcolo espandibile
                    if comp.calculation_details:
                        details = comp.calculation_details
                        with st.expander(f"Dettaglio calcolo — {comp.component_name}", expanded=False):
                            st.markdown(f"**Formula:** `{details.get('formula', 'N/D')}`")

                            if details.get("inputs"):
                                st.markdown("**Input:**")
                                for k, v in details["inputs"].items():
                                    st.caption(f"  • {k} = {v}")

                            if details.get("steps"):
                                st.markdown("**Passaggi:**")
                                for i, step in enumerate(details["steps"], 1):
                                    st.code(f"  {i}. {step}", language=None)

                    if comp.warnings:
                        for w in comp.warnings:
                            st.caption(f"⚠ {w}")

        # Log
        with st.expander("Log Elaborazione"):
            for entry in result.log_entries:
                if "WARNING" in entry or "ERRORE" in entry:
                    st.warning(entry)
                elif "✓" in entry:
                    st.success(entry)
                else:
                    st.text(entry)

        # ============================================
        # CONFRONTO RIFERIMENTO vs STIMA (Feature nuovo)
        # ============================================
        _render_ref_vs_estimate(result, ref_pump)

        # ============================================
        # CONFRONTO CONFIGURAZIONI (Feature 3)
        # ============================================
        _render_comparison(params, result)

        # ============================================
        # DOWNLOAD EXCEL
        # ============================================
        st.markdown("### Download")
        st.caption("Scarica i risultati completi della stima in formato Excel per uso esterno o archiviazione.")
        try:
            excel_buf = generate_excel(result)
            excel_bytes = excel_buf.getvalue() if hasattr(excel_buf, 'getvalue') else excel_buf
            filename = get_filename(result)

            st.download_button(
                label=f"📥 Scarica Excel ({filename})",
                data=excel_bytes,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True,
                key="download_parts_list_excel",
            )
        except ImportError as e:
            st.error(f"Impossibile generare Excel: {e}")
        except Exception as e:
            st.error(f"Errore generazione Excel: {e}")

        # ============================================
        # SALVA PROGETTO
        # ============================================
        st.markdown("### Salva Progetto")
        st.caption("Salva questa configurazione come progetto per richiamarla in futuro. "
                   "Se il nome esiste già, il progetto verrà aggiornato (nuova revisione).")
        try:
            from weight_engine.project_manager import save_project

            default_name = st.session_state.get("loaded_project_name", "")
            proj_name = st.text_input("Nome Progetto", value=default_name,
                                      placeholder="es. BB1-8x6-SS316-Rev.A",
                                      key="save_proj_name")
            if st.button("Salva Progetto", use_container_width=True, key="save_proj_btn"):
                if proj_name.strip():
                    if save_project(proj_name.strip(), params):
                        st.success(f"Progetto **{proj_name.strip()}** salvato.")
                    else:
                        st.error("Errore nel salvataggio del progetto.")
                else:
                    st.warning("Inserisci un nome per il progetto.")
        except ImportError:
            pass

    # ============================================================
    # DASHBOARD ANALYTICS (Feature 8)
    # ============================================================

    st.markdown("---")
    _render_analytics()


def _render_analytics():
    """Dashboard analytics sullo storico stime."""
    try:
        from weight_engine.estimation_history import get_stats, get_history
        stats = get_stats()
    except Exception:
        return

    if stats.get("total", 0) == 0:
        st.caption("Esegui la prima stima per attivare le analytics.")
        return

    st.markdown("### Dashboard Analytics")
    st.caption("Storico delle stime effettuate: trend temporale, distribuzione per famiglia e materiale, ultime stime salvate.")

    # Metriche principali
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Stime Totali", stats["total"])
    col2.metric("Peso Medio", f"{stats['avg_weight']:,.0f} kg")
    col3.metric("Peso Max", f"{stats['max_weight']:,.0f} kg")
    col4.metric("Confidenza Media", f"{stats['avg_confidence_pct']:.0f}%")

    if HAS_PLOTLY:
        col_fam, col_mat = st.columns(2)

        # Distribuzione famiglie
        with col_fam:
            fam_data = stats.get("families", {})
            if fam_data:
                fig = px.pie(
                    names=list(fam_data.keys()),
                    values=list(fam_data.values()),
                    title="Famiglie Pompe Stimate",
                    hole=0.45,
                    color_discrete_sequence=px.colors.qualitative.Set2,
                )
                fig.update_layout(height=300, margin=dict(t=40, b=20, l=20, r=20))
                st.plotly_chart(fig, use_container_width=True)

        # Distribuzione materiali
        with col_mat:
            mat_data = stats.get("materials", {})
            if mat_data:
                sorted_mats = sorted(mat_data.items(), key=lambda x: x[1], reverse=True)[:8]
                fig = go.Figure(data=[go.Bar(
                    x=[m[0] for m in sorted_mats],
                    y=[m[1] for m in sorted_mats],
                    marker_color="#3B82F6",
                )])
                fig.update_layout(
                    title="Materiali più Utilizzati",
                    height=300, margin=dict(t=40, b=20, l=20, r=20),
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)

    # Ultime stime
    recent = stats.get("recent", [])
    if recent:
        with st.expander(f"Ultime {len(recent)} stime", expanded=False):
            import pandas as pd
            df = pd.DataFrame(recent)
            display_cols = ["job_id", "timestamp", "pump_family", "material",
                           "total_weight_kg", "components_estimated"]
            df_display = df[[c for c in display_cols if c in df.columns]]
            df_display.columns = ["Job ID", "Data", "Famiglia", "Materiale",
                                  "Peso (kg)", "Componenti"][:len(df_display.columns)]
            st.dataframe(df_display, use_container_width=True, hide_index=True)


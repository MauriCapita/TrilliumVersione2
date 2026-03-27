"""
Trillium V2 — Document Analytics & Data Quality
Dashboard per metadati estratti, export Excel, validazione incrociata,
albero documenti, confronto revisioni, deduplicazione.
"""

import streamlit as st
import os
import re
import json
from typing import Optional

try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    from rag.qdrant_db import get_qdrant_client, COLLECTION_NAME
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False


# ============================================================
# HELPER: LEGGI TUTTI I DOCUMENTI DA QDRANT
# ============================================================

def _get_all_documents(limit: int = 5000) -> list:
    """Recupera tutti i documenti con metadati da Qdrant."""
    if not QDRANT_AVAILABLE:
        return []
    try:
        client = get_qdrant_client()
        result = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        docs = []
        for point in result[0]:
            payload = point.payload or {}
            payload["_id"] = str(point.id)
            docs.append(payload)
        return docs
    except Exception as e:
        st.error(f"Errore lettura Qdrant: {e}")
        return []


# ============================================================
# TAB 1: DASHBOARD METADATI
# ============================================================

def _render_metadata_dashboard(docs: list):
    """Dashboard statistiche metadati."""
    st.markdown("### 📊 Statistiche Metadati")

    if not docs:
        st.info("Nessun documento indicizzato.")
        return

    # Filtra solo documenti unici (no chunk duplicati)
    unique_docs = {}
    for d in docs:
        src = d.get("source", "")
        if src and src not in unique_docs:
            unique_docs[src] = d
    docs_list = list(unique_docs.values())

    # Metriche principali
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📄 Documenti Totali", len(docs_list))
    with col2:
        images = sum(1 for d in docs_list if d.get("is_image"))
        st.metric("🖼 Disegni Tecnici", images)
    with col3:
        with_weight = sum(1 for d in docs_list if d.get("has_weight"))
        st.metric("⚖️ Con Peso", with_weight)
    with col4:
        avg_quality = sum(d.get("ocr_quality_score", 0) for d in docs_list) / max(len(docs_list), 1)
        st.metric("🎯 Qualità OCR Media", f"{avg_quality:.0f}%")

    st.markdown("---")

    if not PLOTLY_AVAILABLE:
        st.warning("Installa plotly per i grafici: `pip install plotly`")
        return

    # Grafici
    col_a, col_b = st.columns(2)

    # Distribuzione tipo componente
    with col_a:
        st.markdown("#### Tipo Componente")
        comp_types = {}
        for d in docs_list:
            ct = d.get("component_type", "non classificato")
            comp_types[ct] = comp_types.get(ct, 0) + 1
        if comp_types:
            fig = px.pie(values=list(comp_types.values()),
                        names=list(comp_types.keys()),
                        hole=0.4,
                        color_discrete_sequence=px.colors.qualitative.Set3)
            fig.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig, use_container_width=True)

    # Distribuzione materiali
    with col_b:
        st.markdown("#### Materiali Più Usati")
        all_mats = {}
        for d in docs_list:
            for mat in d.get("materials", []):
                if isinstance(mat, str):
                    all_mats[mat] = all_mats.get(mat, 0) + 1
        if all_mats:
            top_mats = sorted(all_mats.items(), key=lambda x: x[1], reverse=True)[:10]
            fig = px.bar(x=[m[0] for m in top_mats],
                        y=[m[1] for m in top_mats],
                        labels={"x": "Materiale", "y": "Documenti"},
                        color_discrete_sequence=["#344054"])
            fig.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig, use_container_width=True)

    # Distribuzione pesi
    col_c, col_d = st.columns(2)
    with col_c:
        st.markdown("#### Distribuzione Pesi (kg)")
        weights = [d.get("max_weight_kg", 0) for d in docs_list if d.get("max_weight_kg")]
        if weights:
            fig = px.histogram(x=weights, nbins=20,
                             labels={"x": "Peso (kg)", "y": "Documenti"},
                             color_discrete_sequence=["#667085"])
            fig.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig, use_container_width=True)

    with col_d:
        st.markdown("#### Flange Rating")
        ratings = {}
        for d in docs_list:
            r = d.get("flange_rating")
            if r:
                r_str = str(r)
                ratings[r_str] = ratings.get(r_str, 0) + 1
        if ratings:
            fig = px.pie(values=list(ratings.values()),
                        names=[f"{r} LB" for r in ratings.keys()],
                        hole=0.4)
            fig.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig, use_container_width=True)

    # OCR Quality distribution
    st.markdown("#### 🎯 Distribuzione Qualità OCR")
    quality_scores = [d.get("ocr_quality_score", 0) for d in docs_list if d.get("is_image")]
    if quality_scores:
        fig = px.histogram(x=quality_scores, nbins=10,
                         labels={"x": "OCR Quality Score (%)", "y": "Documenti"},
                         color_discrete_sequence=["#10803e"])
        fig.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)

        # Documenti con bassa qualità
        low_quality = [(d.get("source", ""), d.get("ocr_quality_score", 0))
                       for d in docs_list if d.get("ocr_quality_score", 0) < 30 and d.get("is_image")]
        if low_quality:
            with st.expander(f"⚠️ {len(low_quality)} documenti con bassa qualità OCR (<30%)"):
                for src, score in sorted(low_quality, key=lambda x: x[1]):
                    st.text(f"  {score}% — {os.path.basename(src)}")


# ============================================================
# TAB 2: EXPORT EXCEL
# ============================================================

def _render_export_excel(docs: list):
    """Export metadati in Excel."""
    st.markdown("### 📥 Export Metadati Excel")

    if not docs:
        st.info("Nessun documento da esportare.")
        return

    # Filtra documenti unici
    unique_docs = {}
    for d in docs:
        src = d.get("source", "")
        if src and src not in unique_docs:
            unique_docs[src] = d
    docs_list = list(unique_docs.values())

    # Costruisci DataFrame
    try:
        import pandas as pd
    except ImportError:
        st.error("Installa pandas: `pip install pandas`")
        return

    rows = []
    for d in docs_list:
        row = {
            "File": os.path.basename(d.get("source", "")),
            "Tipo Doc": d.get("doc_type", ""),
            "Tipo Componente": d.get("component_type", ""),
            "Pompa": d.get("pump_size", ""),
            "DN Mandata": d.get("pump_size_dn", ""),
            "Part Number": d.get("part_number", ""),
            "Revisione": d.get("revision", ""),
            "Peso Finito (kg)": d.get("finish_weight_kg", ""),
            "Peso Max (kg)": d.get("max_weight_kg", ""),
            "Rating Flangia": d.get("flange_rating", ""),
            "Materiali": ", ".join(d.get("materials", [])) if isinstance(d.get("materials"), list) else "",
            "Standards": ", ".join(d.get("standards", [])) if isinstance(d.get("standards"), list) else "",
            "Bolt Patterns": ", ".join(d.get("bolt_patterns", [])) if isinstance(d.get("bolt_patterns"), list) else "",
            "Connessioni Aux": ", ".join(d.get("aux_connections", [])) if isinstance(d.get("aux_connections"), list) else "",
            "Rugosità Ra": ", ".join(d.get("surface_roughness", [])) if isinstance(d.get("surface_roughness"), list) else "",
            "Cuscinetti": ", ".join(d.get("bearing_classes", [])) if isinstance(d.get("bearing_classes"), list) else "",
            "Tipo Tenuta": d.get("seal_type", ""),
            "Scala": d.get("drawing_scale", ""),
            "Doc Collegati": ", ".join(d.get("referenced_docs", [])) if isinstance(d.get("referenced_docs"), list) else "",
            "Sezioni": d.get("section_labels", ""),
            "AI Description": d.get("ai_drawing_description", "")[:200] if d.get("ai_drawing_description") else "",
            "OCR Quality": d.get("ocr_quality_score", 0),
            "BOM Items": d.get("bom_count", 0),
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    # Mostra anteprima
    st.dataframe(df, use_container_width=True, height=400)

    # Download button
    try:
        from io import BytesIO
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Metadati")
        output.seek(0)
        st.download_button(
            label="📥 Scarica Excel",
            data=output.getvalue(),
            file_name="trillium_metadati_export.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except ImportError:
        st.warning("Installa openpyxl per export Excel: `pip install openpyxl`")
        # CSV fallback
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Scarica CSV",
            data=csv,
            file_name="trillium_metadati_export.csv",
            mime="text/csv",
        )


# ============================================================
# TAB 3: VALIDAZIONE INCROCIATA
# ============================================================

_PUMP_WEIGHT_RANGES = {
    # pump_size_dn → (min_weight_kg, max_weight_kg) ragionevoli per volute casing
    50: (5, 100),
    80: (10, 200),
    100: (15, 400),
    150: (30, 800),
    200: (50, 1500),
    250: (100, 3000),
    300: (150, 5000),
    350: (200, 8000),
    400: (300, 12000),
    500: (500, 20000),
}


def _render_validation(docs: list):
    """Validazione incrociata coerenza metadati."""
    st.markdown("### 🔧 Validazione Incrociata")

    if not docs:
        st.info("Nessun documento da validare.")
        return

    unique_docs = {}
    for d in docs:
        src = d.get("source", "")
        if src and src not in unique_docs:
            unique_docs[src] = d
    docs_list = list(unique_docs.values())

    warnings = []
    errors = []

    for d in docs_list:
        fname = os.path.basename(d.get("source", ""))
        dn = d.get("pump_size_dn")
        weight = d.get("max_weight_kg")

        # Check 1: Peso vs DN pompa
        if dn and weight and dn in _PUMP_WEIGHT_RANGES:
            min_w, max_w = _PUMP_WEIGHT_RANGES[dn]
            if weight < min_w * 0.5:
                errors.append(f"❌ **{fname}**: peso {weight} kg troppo basso per DN{dn} (atteso >{min_w} kg)")
            elif weight > max_w * 1.5:
                errors.append(f"❌ **{fname}**: peso {weight} kg troppo alto per DN{dn} (atteso <{max_w} kg)")

        # Check 2: Componente senza peso (disegno)
        if d.get("is_image") and d.get("component_type") and not d.get("has_weight"):
            warnings.append(f"⚠️ **{fname}**: disegno {d.get('component_type')} senza peso")

        # Check 3: Part number mancante su disegni
        if d.get("is_image") and not d.get("part_number"):
            warnings.append(f"⚠️ **{fname}**: disegno senza part number")

        # Check 4: OCR quality molto bassa
        quality = d.get("ocr_quality_score", 0)
        if d.get("is_image") and quality < 15:
            errors.append(f"❌ **{fname}**: qualità OCR {quality}% — potrebbe necessitare re-scan")

        # Check 5: Pump size nel filename ma non estratto
        if d.get("is_image") and not d.get("pump_size") and d.get("component_type"):
            warnings.append(f"⚠️ **{fname}**: tipo componente trovato ma pump_size mancante")

    # Mostra risultati
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Documenti Analizzati", len(docs_list))
    with col2:
        st.metric("⚠️ Warning", len(warnings))
    with col3:
        st.metric("❌ Errori", len(errors))

    if errors:
        with st.expander(f"❌ {len(errors)} Errori di Coerenza", expanded=True):
            for e in errors:
                st.markdown(e)

    if warnings:
        with st.expander(f"⚠️ {len(warnings)} Warning"):
            for w in warnings:
                st.markdown(w)

    if not errors and not warnings:
        st.success("✅ Tutti i documenti superano la validazione!")


# ============================================================
# TAB 4: ALBERO DOCUMENTI
# ============================================================

def _render_document_tree(docs: list):
    """Albero relazioni tra documenti basato su referenced_docs."""
    st.markdown("### 🌳 Albero Documenti")

    if not docs:
        st.info("Nessun documento indicizzato.")
        return

    # Costruisci mappa: part_number → documento
    unique_docs = {}
    for d in docs:
        src = d.get("source", "")
        if src and src not in unique_docs:
            unique_docs[src] = d

    # Costruisci grafo
    pn_to_file = {}
    file_to_refs = {}
    for src, d in unique_docs.items():
        pn = d.get("part_number", "")
        if pn:
            pn_to_file[pn] = os.path.basename(src)
        refs = d.get("referenced_docs", [])
        if refs and isinstance(refs, list):
            file_to_refs[os.path.basename(src)] = refs

    if not file_to_refs:
        st.info("Nessun collegamento trovato tra documenti. I documenti referenziati verranno rilevati dopo la re-indicizzazione.")
        return

    # Visualizza albero
    st.markdown(f"**{len(file_to_refs)} documenti** con riferimenti a **{sum(len(v) for v in file_to_refs.values())} documenti collegati**")

    for fname, refs in sorted(file_to_refs.items()):
        with st.expander(f"📂 {fname}"):
            for ref in refs:
                # Cerca se il riferimento è un part number di un altro file
                matched = pn_to_file.get(ref, "")
                if matched:
                    st.markdown(f"  → **{ref}** — `{matched}`")
                else:
                    st.markdown(f"  → **{ref}** — _(non indicizzato)_")


# ============================================================
# TAB 5: CONFRONTO REVISIONI
# ============================================================

def _render_revision_compare(docs: list):
    """Confronta diverse revisioni dello stesso disegno."""
    st.markdown("### 🔄 Confronto Revisioni")

    unique_docs = {}
    for d in docs:
        src = d.get("source", "")
        if src and src not in unique_docs:
            unique_docs[src] = d

    # Raggruppa per part_number
    by_pn = {}
    for src, d in unique_docs.items():
        pn = d.get("part_number", "")
        if pn:
            rev = d.get("revision", "??")
            if pn not in by_pn:
                by_pn[pn] = []
            by_pn[pn].append((rev, os.path.basename(src), d))

    # Filtra solo quelli con più revisioni
    multi_rev = {pn: revs for pn, revs in by_pn.items() if len(revs) > 1}

    if not multi_rev:
        st.info("Nessun documento con revisioni multiple trovato.")
        return

    st.markdown(f"**{len(multi_rev)} documenti** con revisioni multiple:")

    for pn, revs in sorted(multi_rev.items()):
        revs_sorted = sorted(revs, key=lambda x: x[0])
        with st.expander(f"📋 {pn} — {len(revs)} revisioni"):
            # Tabella comparativa
            compare_fields = ["pump_size", "finish_weight_kg", "max_weight_kg",
                            "flange_rating", "component_type", "materials",
                            "bolt_patterns", "aux_connections", "n_sections"]
            for i in range(len(revs_sorted) - 1):
                rev_a, fname_a, data_a = revs_sorted[i]
                rev_b, fname_b, data_b = revs_sorted[i + 1]
                st.markdown(f"**REV {rev_a}** → **REV {rev_b}**")

                changes = []
                for field in compare_fields:
                    val_a = data_a.get(field)
                    val_b = data_b.get(field)
                    if val_a != val_b and (val_a or val_b):
                        changes.append(f"  - `{field}`: {val_a} → **{val_b}**")

                if changes:
                    for c in changes:
                        st.markdown(c)
                else:
                    st.markdown("  _Nessuna differenza nei metadati estratti_")


# ============================================================
# TAB 6: DEDUPLICAZIONE
# ============================================================

def _render_deduplication(docs: list):
    """Trova documenti potenzialmente duplicati."""
    st.markdown("### 🔍 Deduplicazione")

    unique_docs = {}
    for d in docs:
        src = d.get("source", "")
        if src and src not in unique_docs:
            unique_docs[src] = d

    # Criterio 1: stesso part_number
    by_pn = {}
    for src, d in unique_docs.items():
        pn = d.get("part_number", "")
        rev = d.get("revision", "")
        if pn:
            key = f"{pn}-REV{rev}"
            if key not in by_pn:
                by_pn[key] = []
            by_pn[key].append(os.path.basename(src))

    duplicates = {k: v for k, v in by_pn.items() if len(v) > 1}

    # Criterio 2: filename molto simili
    from difflib import SequenceMatcher
    fnames = list(unique_docs.keys())
    similar_pairs = []
    for i in range(len(fnames)):
        for j in range(i + 1, min(i + 20, len(fnames))):  # Limita confronti
            bn_i = os.path.basename(fnames[i])
            bn_j = os.path.basename(fnames[j])
            if SequenceMatcher(None, bn_i, bn_j).ratio() > 0.85:
                similar_pairs.append((bn_i, bn_j))

    # Risultati
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Duplicati Part Number", len(duplicates))
    with col2:
        st.metric("File Simili", len(similar_pairs))

    if duplicates:
        with st.expander(f"🔄 {len(duplicates)} gruppi con stesso Part Number"):
            for key, files in sorted(duplicates.items()):
                st.markdown(f"**{key}**: {', '.join(files)}")

    if similar_pairs:
        with st.expander(f"📄 {len(similar_pairs)} coppie di file simili"):
            for f1, f2 in similar_pairs[:20]:
                st.markdown(f"- `{f1}` ↔ `{f2}`")


# ============================================================
# RENDER PRINCIPALE
# ============================================================

def render():
    """Renderizza la pagina Document Analytics."""
    st.markdown("## 📊 Document Analytics & Data Quality")
    st.caption("Dashboard metadati, export, validazione e relazioni tra documenti")

    # Carica documenti (una volta, cache in session)
    if "doc_analytics_data" not in st.session_state:
        with st.spinner("Caricamento documenti da Qdrant..."):
            st.session_state["doc_analytics_data"] = _get_all_documents()

    docs = st.session_state["doc_analytics_data"]

    if st.button("🔄 Aggiorna Dati"):
        with st.spinner("Ricaricamento..."):
            st.session_state["doc_analytics_data"] = _get_all_documents()
            docs = st.session_state["doc_analytics_data"]

    if not docs:
        st.warning("Nessun documento trovato in Qdrant. Indicizza prima dei documenti.")
        return

    st.info(f"📚 **{len(docs)} record** caricati da Qdrant")

    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Dashboard", "📥 Export Excel", "🔧 Validazione",
        "🌳 Albero Documenti", "🔄 Revisioni", "🔍 Duplicati"
    ])

    with tab1:
        _render_metadata_dashboard(docs)
    with tab2:
        _render_export_excel(docs)
    with tab3:
        _render_validation(docs)
    with tab4:
        _render_document_tree(docs)
    with tab5:
        _render_revision_compare(docs)
    with tab6:
        _render_deduplication(docs)

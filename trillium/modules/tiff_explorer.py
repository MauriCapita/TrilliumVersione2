"""
Trillium V2 — TIFF Explorer
Per ogni file TIFF indicizzato mostra tutti i metadati estratti,
evidenziando cosa è stato recuperato e cosa manca.
Filtri avanzati per ricerca mirata.
"""

import streamlit as st
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    from rag.qdrant_db import get_qdrant_client
    from config import QDRANT_COLLECTION_NAME
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False


# ============================================================
# COSTANTI — Campi metadati organizzati per sezione
# ============================================================

FIELD_SECTIONS = {
    "🆔 Identificazione": [
        ("part_number", "Part Number"),
        ("revision", "Revisione"),
        ("drawing_description", "Descrizione (EN)"),
        ("drawing_description_it", "Descrizione (IT)"),
        ("pump_size", "Designazione Pompa"),
        ("pump_family", "Famiglia Pompa"),
        ("pump_size_dn", "DN Mandata (mm)"),
        ("pump_size_impeller", "Impeller (pollici)"),
    ],
    "⚙️ Componente": [
        ("component_type", "Tipo Componente"),
        ("doc_type", "Tipo Documento"),
        ("manufacturer", "Fabbricante"),
        ("drawing_scale", "Scala Disegno"),
        ("drawing_format", "Formato Foglio"),
        ("drawing_date", "Data Disegno"),
        ("general_tolerances", "Tolleranze Generali"),
    ],
    "⚖️ Pesi": [
        ("has_weight", "Ha Peso"),
        ("max_weight_kg", "Peso Max (kg)"),
        ("finish_weight_kg", "Peso Finito (kg)"),
        ("raw_weight_kg", "Peso Grezzo (kg)"),
        ("weight_count", "N° Pesi Trovati"),
    ],
    "🔩 Materiali & Dimensioni": [
        ("materials", "Materiali"),
        ("material_description", "Descrizione Materiale"),
        ("d2_mm", "D2 Girante (mm)"),
        ("nq", "Nq Velocità Specifica"),
        ("flange_rating", "Rating Flangia"),
        ("flange_dn", "DN Flangia"),
        ("flange_face_type", "Tipo Faccia Flangia"),
        ("nozzle_suction_inch", "Bocchello Aspirazione (in)"),
        ("nozzle_discharge_inch", "Bocchello Mandata (in)"),
        ("dimensions", "Dimensioni"),
    ],
    "🔧 Dettagli Tecnici": [
        ("standards", "Normative"),
        ("bolt_patterns", "Bolt Patterns"),
        ("surface_roughness", "Rugosità Ra"),
        ("bearing_classes", "Classi Cuscinetti"),
        ("seal_type", "Tipo Tenuta"),
        ("aux_connections", "Connessioni Ausiliarie"),
        ("alt_solution", "Alt. Sol."),
        ("ffft", "F.F.F.T."),
        ("has_bom", "Ha BOM"),
        ("bom_count", "N° Voci BOM"),
    ],
    "🤖 Qualità & AI": [
        ("ocr_quality_score", "OCR Quality Score"),
        ("ai_enriched", "Arricchito AI"),
        ("ai_components_count", "N° Componenti AI"),
        ("ai_quality_score", "AI Quality Score"),
    ],
    "🔗 Riferimenti": [
        ("referenced_docs", "Documenti Collegati"),
        ("pre_machined_pn", "PN Pre-lavorato"),
        ("raw_casting_pn", "PN Grezzo/Fusione"),
        ("project_number", "N° Progetto"),
    ],
}


# ============================================================
# HELPER: CARICA TIFF DA QDRANT
# ============================================================

def _get_tiff_documents(limit: int = 5000) -> list:
    """Recupera tutti i documenti TIFF da Qdrant, raggruppati per source."""
    if not QDRANT_AVAILABLE:
        return []
    try:
        client = get_qdrant_client()
        result = client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        # Raggruppa chunk per sorgente, tieni solo TIFF
        sources = {}
        for point in result[0]:
            payload = point.payload or {}
            source = payload.get("source", "")
            ext = os.path.splitext(source)[1].lower()
            if ext not in (".tif", ".tiff"):
                continue
            if source not in sources:
                sources[source] = {
                    "source": source,
                    "basename": os.path.basename(source),
                    "chunk_count": 0,
                    "meta": {},
                    "texts": [],
                }
            sources[source]["chunk_count"] += 1
            # Raccogli testo OCR di ogni chunk
            text = payload.get("text", "")
            if text and text.strip():
                chunk_num = payload.get("chunk", 0)
                sources[source]["texts"].append((chunk_num, text.strip()))
            # Merge metadati (il primo chunk che ha un campo vince)
            for k, v in payload.items():
                if k not in ("text",) and k not in sources[source]["meta"]:
                    sources[source]["meta"][k] = v
                elif k not in ("text", "source") and v and not sources[source]["meta"].get(k):
                    sources[source]["meta"][k] = v
        return list(sources.values())
    except Exception as e:
        st.error(f"Errore lettura Qdrant: {e}")
        return []


def _format_value(val):
    """Formatta un valore per la visualizzazione."""
    if val is None:
        return None
    if isinstance(val, bool):
        return "Sì" if val else "No"
    if isinstance(val, list):
        if not val:
            return None
        return ", ".join(str(v) for v in val[:10])
    if isinstance(val, dict):
        if not val:
            return None
        return ", ".join(f"{k}: {v}" for k, v in val.items())
    if isinstance(val, float):
        return f"{val:.1f}"
    return str(val)


def _get_unique_values(docs: list, field: str) -> list:
    """Ottiene i valori unici di un campo dai documenti."""
    values = set()
    for d in docs:
        v = d["meta"].get(field)
        if v and not isinstance(v, (list, dict, bool)):
            values.add(str(v))
    return sorted(values)


# ============================================================
# DIALOG FULLSCREEN PREVIEW
# ============================================================

@st.dialog("Anteprima Disegno", width="large")
def _show_fullscreen_preview():
    """Mostra il TIFF a schermo intero con controlli di rotazione."""
    img_path = st.session_state.get("_tiff_preview_path")
    img_name = st.session_state.get("_tiff_preview_name", "Documento")

    st.markdown(f"**{img_name}**")

    if img_path and os.path.isfile(img_path):
        try:
            from PIL import Image as PILImage

            # Stato rotazione nel session_state
            if "_tiff_rotation" not in st.session_state:
                st.session_state["_tiff_rotation"] = 0

            # Bottoni rotazione
            rc1, rc2, rc3, rc4 = st.columns(4)
            with rc1:
                if st.button("↕️ 0°", use_container_width=True, key="rot_0"):
                    st.session_state["_tiff_rotation"] = 0
                    st.rerun()
            with rc2:
                if st.button("↪️ 90°", use_container_width=True, key="rot_90"):
                    st.session_state["_tiff_rotation"] = 90
                    st.rerun()
            with rc3:
                if st.button("🔄 180°", use_container_width=True, key="rot_180"):
                    st.session_state["_tiff_rotation"] = 180
                    st.rerun()
            with rc4:
                if st.button("↩️ 270°", use_container_width=True, key="rot_270"):
                    st.session_state["_tiff_rotation"] = 270
                    st.rerun()

            rotation = st.session_state.get("_tiff_rotation", 0)

            img = PILImage.open(img_path)
            if img.mode not in ("RGB", "L", "RGBA"):
                img = img.convert("RGB")

            # Applica rotazione
            if rotation != 0:
                img = img.rotate(-rotation, expand=True)
                st.caption(f"Rotazione: {rotation}°")

            st.image(img, use_container_width=True)

            # Download
            with open(img_path, "rb") as f:
                file_bytes = f.read()
            st.download_button(
                label=f"📥 Scarica: {img_name}",
                data=file_bytes,
                file_name=img_name,
                use_container_width=True,
                key="dl_fullscreen",
            )
        except Exception as e:
            st.error(f"Impossibile aprire l'immagine: {e}")
    else:
        st.warning("File non trovato su disco.")


# ============================================================
# RENDER
# ============================================================

def render():
    """Renderizza la pagina TIFF Explorer."""

    # Header
    st.markdown("""
    <div style="background: linear-gradient(135deg, hsl(213, 50%, 95%) 0%, hsl(213, 60%, 88%) 100%);
                color: hsl(215, 25%, 15%); padding: 1.5rem 2rem; border-radius: 12px; margin-bottom: 1.5rem;
                border: 1px solid hsl(213, 40%, 82%);
                box-shadow: 0 4px 6px -1px hsla(213, 76%, 36%, 0.08);">
        <h2 style="color: hsl(213, 76%, 40%); margin: 0;">🖼 TIFF Explorer</h2>
        <p style="color: hsl(215, 16%, 47%); margin: 0.5rem 0 0;">
            Per ogni disegno TIFF indicizzato: tutti i dati estratti, cosa è stato recuperato e cosa manca
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Carica dati
    cache_key = "tiff_explorer_data"
    if cache_key not in st.session_state:
        with st.spinner("Caricamento TIFF dal database..."):
            st.session_state[cache_key] = _get_tiff_documents()

    docs = st.session_state[cache_key]

    # Bottone refresh
    if st.button("🔄 Aggiorna Dati", key="tiff_refresh"):
        with st.spinner("Ricaricamento..."):
            st.session_state[cache_key] = _get_tiff_documents()
            docs = st.session_state[cache_key]

    if not docs:
        st.warning("Nessun file TIFF trovato nel database Qdrant. "
                    "Indicizza prima dei disegni tecnici.")
        return

    # ============================================================
    # METRICHE TOP
    # ============================================================

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("🖼 TIFF Totali", len(docs))
    with col2:
        with_weight = sum(1 for d in docs if d["meta"].get("has_weight"))
        st.metric("⚖️ Con Peso", with_weight)
    with col3:
        without_weight = len(docs) - with_weight
        st.metric("❌ Senza Peso", without_weight)
    with col4:
        scores = [d["meta"].get("ocr_quality_score", 0) for d in docs]
        avg_ocr = sum(scores) / max(len(scores), 1)
        st.metric("🎯 OCR Quality Media", f"{avg_ocr:.0f}%")
    with col5:
        ai_enriched = sum(1 for d in docs if d["meta"].get("ai_enriched"))
        st.metric("🤖 Arricchiti AI", ai_enriched)

    st.markdown("---")

    # ============================================================
    # FILTRI
    # ============================================================

    st.markdown("### 🔍 Filtri")

    # Riga 1: testo + famiglia + tipo componente
    fc1, fc2, fc3 = st.columns([3, 2, 2])
    with fc1:
        search_text = st.text_input(
            "Cerca nel nome file",
            "",
            placeholder="es. 230A70, impeller, casing...",
            key="tiff_search",
        )
    with fc2:
        families = ["Tutti"] + _get_unique_values(docs, "pump_family")
        sel_family = st.selectbox("Famiglia Pompa", families, key="tiff_family")
    with fc3:
        comp_types = ["Tutti"] + _get_unique_values(docs, "component_type")
        sel_comp = st.selectbox("Tipo Componente", comp_types, key="tiff_comp")

    # Riga 2: doc_type + peso + OCR quality
    fc4, fc5, fc6 = st.columns([2, 2, 3])
    with fc4:
        doc_types = ["Tutti"] + _get_unique_values(docs, "doc_type")
        sel_doctype = st.selectbox("Tipo Documento", doc_types, key="tiff_doctype")
    with fc5:
        peso_filter = st.selectbox(
            "Filtro Peso",
            ["Tutti", "Solo con peso", "Solo senza peso"],
            key="tiff_peso",
        )
    with fc6:
        ocr_range = st.slider(
            "OCR Quality Score",
            0, 100, (0, 100),
            key="tiff_ocr_range",
        )

    # Applica filtri
    filtered = docs

    if search_text.strip():
        q = search_text.strip().lower()
        filtered = [d for d in filtered if q in d["basename"].lower()]

    if sel_family != "Tutti":
        filtered = [d for d in filtered if str(d["meta"].get("pump_family", "")) == sel_family]

    if sel_comp != "Tutti":
        filtered = [d for d in filtered if str(d["meta"].get("component_type", "")) == sel_comp]

    if sel_doctype != "Tutti":
        filtered = [d for d in filtered if str(d["meta"].get("doc_type", "")) == sel_doctype]

    if peso_filter == "Solo con peso":
        filtered = [d for d in filtered if d["meta"].get("has_weight")]
    elif peso_filter == "Solo senza peso":
        filtered = [d for d in filtered if not d["meta"].get("has_weight")]

    filtered = [d for d in filtered
                if ocr_range[0] <= d["meta"].get("ocr_quality_score", 0) <= ocr_range[1]]

    st.caption(f"Mostrando **{len(filtered)}** / {len(docs)} file TIFF")

    # ============================================================
    # TABELLA RIEPILOGATIVA
    # ============================================================

    st.markdown("### 📋 Riepilogo TIFF Indicizzati")

    if not PANDAS_AVAILABLE:
        st.error("pandas non disponibile")
        return

    table_data = []
    for d in filtered:
        m = d["meta"]
        table_data.append({
            "File": d["basename"],
            "Famiglia": m.get("pump_family", "—"),
            "Componente": m.get("component_type", "—"),
            "Tipo Doc": m.get("doc_type", "—"),
            "Peso (kg)": f"{m['max_weight_kg']:.0f}" if m.get("max_weight_kg") else "—",
            "Materiali": ", ".join(m.get("materials", [])[:3]) if isinstance(m.get("materials"), list) and m.get("materials") else "—",
            "D2": f"{m['d2_mm']}" if m.get("d2_mm") else "—",
            "Nq": f"{m['nq']}" if m.get("nq") else "—",
            "Rating": str(m.get("flange_rating", "—")) if m.get("flange_rating") else "—",
            "OCR %": f"{m.get('ocr_quality_score', 0):.0f}",
            "Chunks": d["chunk_count"],
            "AI": "✅" if m.get("ai_enriched") else "—",
        })

    df = pd.DataFrame(table_data)

    # Tabella interattiva
    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        height=min(500, 38 * len(df) + 40),
        on_select="rerun",
        selection_mode="single-row",
        key="tiff_table",
    )

    # ============================================================
    # DETTAGLIO DOCUMENTO SELEZIONATO
    # ============================================================

    st.markdown("---")
    st.markdown("### 📄 Dettaglio Documento")

    selected_doc = None
    if event and event.selection and event.selection.rows:
        row_idx = event.selection.rows[0]
        if row_idx < len(filtered):
            selected_doc = filtered[row_idx]

    if not selected_doc:
        st.info("👆 Seleziona un TIFF dalla tabella per vederne il dettaglio completo.")
        return

    m = selected_doc["meta"]

    # Header documento
    st.markdown(f"""
    <div style="background: hsl(0, 0%, 100%); padding: 1.2rem 1.5rem; border-radius: 12px;
                border: 1px solid hsl(220, 13%, 91%);
                box-shadow: 0 4px 6px -1px hsla(215, 25%, 15%, 0.06); margin-bottom: 1rem;">
        <h3 style="margin: 0; color: hsl(215, 25%, 15%);">📄 {selected_doc['basename']}</h3>
        <p style="margin: 0.3rem 0 0; color: hsl(215, 16%, 47%); font-size: 0.85rem;">
            {selected_doc['chunk_count']} chunk • OCR Quality: {m.get('ocr_quality_score', 0):.0f}%
            • {'✅ Arricchito AI' if m.get('ai_enriched') else '— Non arricchito AI'}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ============================================================
    # AI DESCRIPTION (subito visibile, prima di tutto)
    # ============================================================

    ai_desc = m.get("ai_drawing_description", "")
    if ai_desc:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, hsl(250, 60%, 97%), hsl(210, 60%, 97%));
                    padding: 1rem 1.2rem; border-radius: 10px;
                    border-left: 4px solid hsl(250, 60%, 55%); margin-bottom: 1rem;">
            <p style="margin: 0 0 0.3rem; font-weight: 600; color: hsl(250, 50%, 40%); font-size: 0.85rem;">
                🤖 AI Description ({len(ai_desc)} chars)</p>
            <p style="margin: 0; color: hsl(215, 25%, 25%); font-size: 0.9rem; line-height: 1.5;">
                {ai_desc}</p>
        </div>
        """, unsafe_allow_html=True)

    # ============================================================
    # COMPLETEZZA METADATI (subito visibile)
    # ============================================================

    # Conteggio campi presenti/mancanti
    total_fields = 0
    present_fields = 0
    for section_name, fields in FIELD_SECTIONS.items():
        for field_key, field_label in fields:
            total_fields += 1
            val = m.get(field_key)
            if val is not None and val != "" and val != [] and val != {}:
                if isinstance(val, bool) and not val and field_key != "has_weight":
                    continue
                present_fields += 1

    completeness = present_fields / max(total_fields, 1)
    st.progress(completeness, text=f"Completezza metadati: {present_fields}/{total_fields} campi ({completeness:.0%})")

    # Sezioni metadati (subito visibili, PRIMA dell'immagine)
    for section_name, fields in FIELD_SECTIONS.items():
        with st.expander(section_name, expanded=True):
            for field_key, field_label in fields:
                val = m.get(field_key)
                formatted = _format_value(val)

                if formatted is not None and formatted != "":
                    st.markdown(f"✅ **{field_label}**: {formatted}")
                else:
                    st.markdown(f"❌ **{field_label}**: _non estratto_")

    # ============================================================
    # TESTO OCR ESTRATTO
    # ============================================================

    with st.expander("📝 Testo OCR Estratto", expanded=False):
        # AI Drawing Description
        ai_desc = m.get("ai_drawing_description", "")
        if ai_desc:
            st.markdown("#### 🤖 Descrizione AI")
            st.markdown(ai_desc)
            st.markdown("---")

        # Testo OCR grezzo da tutti i chunk
        texts = selected_doc.get("texts", [])
        if texts:
            # Ordina per numero chunk
            texts_sorted = sorted(texts, key=lambda x: x[0])
            st.markdown(f"#### 📄 Testo OCR ({len(texts_sorted)} chunk)")
            full_text = "\n\n".join(t[1] for t in texts_sorted)
            st.text_area(
                "Testo completo",
                value=full_text,
                height=400,
                disabled=True,
                key="ocr_text_area",
                label_visibility="collapsed",
            )
        else:
            st.caption("Nessun testo OCR disponibile per questo documento.")

    # ============================================================
    # ANTEPRIMA IMMAGINE (in expander, DOPO i metadati)
    # ============================================================

    doc_path = selected_doc["source"]
    if doc_path and os.path.isfile(doc_path):
        with st.expander("🖼 Anteprima Disegno", expanded=False):
            try:
                from PIL import Image as PILImage
                img = PILImage.open(doc_path)
                if img.mode not in ("RGB", "L", "RGBA"):
                    img = img.convert("RGB")
                st.image(img, caption=selected_doc["basename"], use_container_width=True)
            except Exception as e:
                st.caption(f"Anteprima non disponibile: {e}")

        # Salva path per il dialog fullscreen
        st.session_state["_tiff_preview_path"] = doc_path
        st.session_state["_tiff_preview_name"] = selected_doc["basename"]

        # Bottoni: Schermo intero + Download
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button("🔍 Schermo Intero", key="fs_tiff", use_container_width=True):
                _show_fullscreen_preview()
        with btn_col2:
            try:
                with open(doc_path, "rb") as f:
                    file_bytes = f.read()
                st.download_button(
                    label=f"📥 Scarica: {selected_doc['basename']}",
                    data=file_bytes,
                    file_name=selected_doc["basename"],
                    use_container_width=True,
                )
            except Exception as e:
                st.caption(f"Impossibile leggere il file: {e}")
    elif doc_path:
        st.caption(f"⚠️ File non trovato su disco: `{doc_path}`")



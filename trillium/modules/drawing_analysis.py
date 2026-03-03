"""
Trillium V2 — Analisi Disegni e Documenti Indicizzati
Inventario strutturato della conoscenza: per ogni documento analizza
cosa contiene (pesi, materiali, dimensioni) e cosa manca.
"""

import streamlit as st
import sys
import os
import re
import json
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)


@st.dialog("Anteprima Documento", width="large")
def _show_fullscreen_preview():
    """Mostra l'anteprima del documento a schermo intero in un dialog."""
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

# Campi che cerchiamo in ogni documento
FIELDS_OF_INTEREST = {
    "weights": {
        "label": "Pesi Componenti",
        "icon": "⚖",
        "patterns": [
            r"\b\d+[\.,]?\d*\s*kg\b",
            r"[Ww]eight\s*[=:]\s*\d+[\.,]?\d*",
            r"[Pp]eso\s*[=:]\s*\d+[\.,]?\d*",
            r"[Mm]ass[ae]?\s*[=:]\s*\d+[\.,]?\d*",
        ],
    },
    "materials": {
        "label": "Materiali",
        "icon": "🔩",
        "patterns": [
            r"(?:A216|A351|A182|SS\s*\d{3}|Carbon Steel|Duplex|Inconel|Monel|Hastelloy|Bronze|Titanium|Cast Iron|Ductile Iron)",
            r"(?:WCB|CF8M|CF8|CF3M|CA6NM|CA15|CN-7M)",
            r"\b(?:ASTM|ASME)\s+[A-Z]\d+",
        ],
    },
    "dimensions": {
        "label": "Dimensioni",
        "icon": "📐",
        "patterns": [
            r"(?:diameter|diametro|Ø|DN)\s*[=:]*\s*(\d+[\.,]?\d*)\s*(?:mm|in|\")",
            r"(?:thickness|spessore)\s*[=:]*\s*(\d+[\.,]?\d*)\s*(?:mm)",
            r"(\d+)\s*[\"x×]\s*(\d+)",
        ],
    },
    "pump_family": {
        "label": "Famiglia Pompa",
        "icon": "🏭",
        "patterns": [
            r"\b(OH[1-6]|BB[1-5]|VS[1-7])\b",
            r"(?:overhung|between bearing|vertical|barrel|multistage)",
        ],
    },
    "flange_rating": {
        "label": "Rating Flange",
        "icon": "🔧",
        "patterns": [
            r"(?:class|rating|#)\s*(\d{3,4})",
            r"(\d{3,4})\s*(?:#|class|lb)",
            r"\bASME\s+B16\.5\b",
        ],
    },
    "components": {
        "label": "Componenti Identificati",
        "icon": "⚙",
        "patterns": [
            r"\b(?:casing|impeller|shaft|bearing|seal|flange|wear ring|diffuser|bowl|column|baseplate)\b",
            r"\b(?:corpo|girante|albero|cuscinetto|tenuta|flangia|anello usura|piastra base)\b",
        ],
    },
    "nq_speed": {
        "label": "Velocità/Nq",
        "icon": "🔄",
        "patterns": [
            r"[Nn][qsS]\s*[=:]\s*(\d+[\.,]?\d*)",
            r"(\d+)\s*(?:rpm|giri|rev)",
            r"specific\s+speed\s*[=:]\s*(\d+[\.,]?\d*)",
        ],
    },
    "pressure_temp": {
        "label": "Pressione/Temperatura",
        "icon": "🌡",
        "patterns": [
            r"(\d+[\.,]?\d*)\s*(?:bar|barg|psi|MPa|atm)",
            r"(\d+[\.,]?\d*)\s*°?[CF]",
            r"(?:pressure|pressione)\s*[=:]\s*(\d+[\.,]?\d*)",
            r"(?:temperature|temperatura)\s*[=:]\s*(\d+[\.,]?\d*)",
        ],
    },
}

TOTAL_FIELDS = len(FIELDS_OF_INTEREST)


# ============================================================
# ANALISI DOCUMENTO
# ============================================================

def analyze_document(text: str, source: str = "") -> dict:
    """Analizza un documento e restituisce i campi trovati/mancanti."""
    result = {
        "source": source,
        "basename": os.path.basename(source) if source else "N/D",
        "text_length": len(text),
        "fields_found": {},
        "fields_missing": [],
        "completeness": 0.0,
        "matches": {},
    }

    found_count = 0
    text_lower = text.lower()

    for field_id, field_info in FIELDS_OF_INTEREST.items():
        matches = []
        for pattern in field_info["patterns"]:
            try:
                found = re.findall(pattern, text, re.IGNORECASE)
                if found:
                    # Normalizza: se è un gruppo, prendi il primo elemento
                    for m in found:
                        if isinstance(m, tuple):
                            matches.append(m[0])
                        else:
                            matches.append(str(m))
            except re.error:
                pass

        if matches:
            unique_matches = list(set(matches))[:10]
            result["fields_found"][field_id] = {
                "label": field_info["label"],
                "icon": field_info["icon"],
                "count": len(matches),
                "examples": unique_matches[:5],
            }
            result["matches"][field_id] = unique_matches
            found_count += 1
        else:
            result["fields_missing"].append({
                "id": field_id,
                "label": field_info["label"],
                "icon": field_info["icon"],
            })

    result["completeness"] = found_count / TOTAL_FIELDS if TOTAL_FIELDS > 0 else 0

    return result


def get_all_documents_from_qdrant() -> list[dict]:
    """Recupera tutti i documenti da Qdrant raggruppati per source."""
    try:
        from rag.qdrant_db import qdrant_get_all
        data = qdrant_get_all()
    except Exception as e:
        logger.warning(f"Errore connessione Qdrant: {e}")
        return []

    # Raggruppa chunks per sorgente
    sources = {}
    for doc_id, text, meta in zip(data["ids"], data["documents"], data["metadatas"]):
        source = meta.get("source", "unknown")
        if source not in sources:
            sources[source] = {
                "source": source,
                "chunks": [],
                "total_text": "",
                "chunk_count": 0,
                "metadata": meta,
            }
        sources[source]["chunks"].append(text)
        sources[source]["total_text"] += " " + text
        sources[source]["chunk_count"] += 1

    return list(sources.values())


# ============================================================
# CACHE ANALISI
# ============================================================

_CACHE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    ".drawing_analysis_cache.json"
)


def _load_cache() -> dict:
    if os.path.exists(_CACHE_FILE):
        try:
            with open(_CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_cache(cache: dict):
    try:
        with open(_CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


# ============================================================
# PAGINA STREAMLIT
# ============================================================

def render():
    # Header
    st.markdown("""
    <div style="background: linear-gradient(135deg, hsl(142, 50%, 95%) 0%, hsl(142, 60%, 88%) 100%);
                color: hsl(215, 25%, 15%); padding: 1.5rem 2rem; border-radius: 12px; margin-bottom: 1.5rem;
                border: 1px solid hsl(142, 40%, 82%);
                box-shadow: 0 4px 6px -1px hsla(142, 76%, 36%, 0.08);">
        <h2 style="color: hsl(142, 76%, 30%); margin: 0;">Analisi Disegni & Documenti</h2>
        <p style="color: hsl(215, 16%, 47%); margin: 0.5rem 0 0;">
            Inventario della conoscenza: per ogni documento vedi cosa contiene e cosa manca
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.caption("Questa pagina analizza la completezza dei dati per ogni documento indicizzato. "
               "Per ciascuno vedrai se contiene pesi, materiali, dimensioni, famiglia pompa. "
               "Usa i filtri combinati (AND/OR) per trovare documenti specifici. "
               "Esempio: seleziona 'Pesi' + 'Materiali' in AND per trovare solo i disegni con ENTRAMBI i dati.")

    # Carica documenti
    with st.spinner("Caricamento documenti dal database..."):
        documents = get_all_documents_from_qdrant()

    if not documents:
        st.warning("Nessun documento trovato nel database Qdrant. "
                    "Vai alla pagina Indicizzazione per aggiungere documenti.")
        st.info("Suggerimento: indicizza i disegni tecnici, le parts list e i datasheet "
                "per popolare questa analisi.")
        return

    # Analizza ogni documento
    cache = _load_cache()
    analyses = []

    progress = st.progress(0, text="Analisi documenti...")
    for i, doc in enumerate(documents):
        source = doc["source"]
        # Usa cache se presente
        if source in cache:
            analyses.append(cache[source])
        else:
            analysis = analyze_document(doc["total_text"], source)
            analysis["chunk_count"] = doc["chunk_count"]
            analyses.append(analysis)
            cache[source] = analysis

        progress.progress((i + 1) / len(documents),
                         text=f"Analisi: {i+1}/{len(documents)}")

    progress.empty()
    _save_cache(cache)

    # ============================================================
    # METRICHE GENERALI
    # ============================================================

    st.markdown("### Panoramica")
    col1, col2, col3, col4 = st.columns(4)

    avg_completeness = sum(a["completeness"] for a in analyses) / len(analyses) * 100
    with_weights = sum(1 for a in analyses if "weights" in a["fields_found"])
    with_materials = sum(1 for a in analyses if "materials" in a["fields_found"])
    with_components = sum(1 for a in analyses if "components" in a["fields_found"])

    col1.metric("Documenti Totali", len(analyses))
    col2.metric("Completezza Media", f"{avg_completeness:.0f}%")
    col3.metric("Con Pesi", f"{with_weights}/{len(analyses)}")
    col4.metric("Con Materiali", f"{with_materials}/{len(analyses)}")

    # ============================================================
    # FILTRI
    # ============================================================

    st.markdown("### Filtri Combinati")

    all_field_labels = [f["label"] for f in FIELDS_OF_INTEREST.values()]

    # Riga 1: Ricerca testo + Completezza + Logica
    fc1, fc2, fc3 = st.columns([3, 2, 1])
    with fc1:
        search_text = st.text_input("Cerca nel nome documento", "", placeholder="es. SOP, KARASSIK, casing...")
    with fc2:
        completeness_filter = st.selectbox(
            "Completezza",
            ["Tutti", "Alta (>75%)", "Media (25-75%)", "Bassa (<25%)"],
            index=0,
        )
    with fc3:
        filter_logic = st.radio("Logica campi", ["AND", "OR"], index=0, horizontal=True)

    # Riga 2: Multi-select dati presenti + dati mancanti
    fc4, fc5 = st.columns(2)
    with fc4:
        present_fields = st.multiselect(
            "Dati che DEVONO essere presenti",
            all_field_labels,
            default=[],
        )
    with fc5:
        missing_fields = st.multiselect(
            "Dati che DEVONO mancare",
            all_field_labels,
            default=[],
        )

    # Applica filtri
    filtered = analyses

    # Filtro testo
    if search_text.strip():
        q = search_text.strip().lower()
        filtered = [a for a in filtered if q in a["basename"].lower()]

    # Filtro completezza
    if completeness_filter == "Alta (>75%)":
        filtered = [a for a in filtered if a["completeness"] > 0.75]
    elif completeness_filter == "Media (25-75%)":
        filtered = [a for a in filtered if 0.25 <= a["completeness"] <= 0.75]
    elif completeness_filter == "Bassa (<25%)":
        filtered = [a for a in filtered if a["completeness"] < 0.25]

    # Filtro campi presenti (AND/OR)
    if present_fields:
        present_ids = [k for k, v in FIELDS_OF_INTEREST.items() if v["label"] in present_fields]
        if filter_logic == "AND":
            filtered = [a for a in filtered if all(fid in a["fields_found"] for fid in present_ids)]
        else:
            filtered = [a for a in filtered if any(fid in a["fields_found"] for fid in present_ids)]

    # Filtro campi mancanti (AND/OR)
    if missing_fields:
        missing_ids = [k for k, v in FIELDS_OF_INTEREST.items() if v["label"] in missing_fields]
        missing_in_doc = lambda a: [m["id"] for m in a["fields_missing"]]
        if filter_logic == "AND":
            filtered = [a for a in filtered if all(mid in missing_in_doc(a) for mid in missing_ids)]
        else:
            filtered = [a for a in filtered if any(mid in missing_in_doc(a) for mid in missing_ids)]

    st.caption(f"Mostrando **{len(filtered)}** / {len(analyses)} documenti")

    # ============================================================
    # HEATMAP COMPLETEZZA (se plotly disponibile)
    # ============================================================

    try:
        import plotly.graph_objects as go

        # Matrice completezza
        field_ids = list(FIELDS_OF_INTEREST.keys())
        field_labels = [FIELDS_OF_INTEREST[f]["icon"] + " " + FIELDS_OF_INTEREST[f]["label"]
                        for f in field_ids]
        heatmap_docs = filtered[:20]
        doc_labels = [a["basename"][:30] for a in heatmap_docs]

        z_data = []
        for a in heatmap_docs:
            row = []
            for fid in field_ids:
                if fid in a["fields_found"]:
                    row.append(a["fields_found"][fid]["count"])
                else:
                    row.append(0)
            z_data.append(row)

        if z_data:
            fig = go.Figure(data=[go.Heatmap(
                z=z_data,
                x=field_labels,
                y=doc_labels,
                colorscale=[
                    [0.0, "hsl(210, 40%, 96%)"],
                    [0.01, "hsl(142, 50%, 90%)"],
                    [0.3, "hsl(142, 60%, 70%)"],
                    [0.6, "hsl(142, 76%, 45%)"],
                    [1.0, "hsl(142, 76%, 36%)"],
                ],
                hoverongaps=False,
                text=[[str(v) if v > 0 else "—" for v in row] for row in z_data],
                texttemplate="%{text}",
                textfont={"size": 10},
            )])
            fig.update_layout(
                title="Mappa Completezza (primi 20 documenti) — clicca per selezionare",
                height=max(300, len(doc_labels) * 28 + 100),
                margin=dict(t=40, b=20, l=200, r=20),
                xaxis=dict(side="top"),
                font=dict(family="Inter, sans-serif", size=11),
            )

            # Heatmap interattiva: cattura click per selezionare documento
            heatmap_event = st.plotly_chart(
                fig, use_container_width=True,
                on_select="rerun",
                key="heatmap_chart",
            )

            # Se l'utente clicca su una cella, seleziona il documento
            if heatmap_event and heatmap_event.selection and heatmap_event.selection.points:
                point = heatmap_event.selection.points[0]
                y_idx = point.get("point_index", [None, None])
                if isinstance(y_idx, (list, tuple)) and len(y_idx) >= 1:
                    row_idx = y_idx[0]
                elif isinstance(y_idx, int):
                    row_idx = y_idx
                else:
                    row_idx = point.get("y", None)
                    # Cerca l'indice dal label
                    if isinstance(row_idx, str):
                        try:
                            row_idx = doc_labels.index(row_idx)
                        except ValueError:
                            row_idx = None

                if row_idx is not None and 0 <= row_idx < len(heatmap_docs):
                    st.session_state["_heatmap_selected_doc"] = heatmap_docs[row_idx]["basename"]
    except ImportError:
        pass

    # ============================================================
    # LISTA DOCUMENTI DETTAGLIATA
    # ============================================================

    st.markdown("### Dettaglio per Documento")
    st.caption("Clicca su una riga per selezionare il documento e vederne il dettaglio.")

    # Costruisci tabella riepilogo con Pandas
    import pandas as pd

    table_data = []
    for a in filtered:
        comp = a["completeness"]
        if comp >= 0.75:
            stato = "Alta"
        elif comp >= 0.4:
            stato = "Media"
        else:
            stato = "Bassa"

        found_labels = ", ".join(fd["label"] for fd in a["fields_found"].values())
        missing_labels = ", ".join(m["label"] for m in a["fields_missing"])

        table_data.append({
            "Documento": a["basename"],
            "Completezza": f"{int(comp * 100)}%",
            "Campi": f"{len(a['fields_found'])}/{TOTAL_FIELDS}",
            "Stato": stato,
            "Trovati": found_labels or "—",
            "Mancanti": missing_labels or "—",
        })

    df = pd.DataFrame(table_data)

    # Aggiungi colonna numerica per ordinamento e ordina per completezza decrescente
    df["_comp_num"] = [a["completeness"] for a in filtered]
    df = df.sort_values("_comp_num", ascending=False).reset_index(drop=True)

    # Riordina anche la lista filtered per mantenere corrispondenza riga-documento
    sorted_indices = df.index.tolist()
    # Ricostruisci l'ordine basato sul sort
    comp_values = [(i, a["completeness"]) for i, a in enumerate(filtered)]
    comp_values.sort(key=lambda x: x[1], reverse=True)
    filtered_sorted = [filtered[i] for i, _ in comp_values]

    df = df.drop(columns=["_comp_num"])

    # Tabella interattiva: cliccando una riga si seleziona il documento
    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        height=min(400, 38 * len(df) + 40),
        on_select="rerun",
        selection_mode="single-row",
        key="doc_table",
    )

    # Determina quale documento è selezionato (dalla tabella o dall'heatmap)
    selected = None
    if event and event.selection and event.selection.rows:
        selected_row_idx = event.selection.rows[0]
        if selected_row_idx < len(filtered_sorted):
            selected = filtered_sorted[selected_row_idx]["basename"]

    # Fallback: se nessuna riga selezionata nella tabella, usa selezione dall'heatmap
    if not selected and "_heatmap_selected_doc" in st.session_state:
        selected = st.session_state["_heatmap_selected_doc"]

    # --- Dettaglio documento selezionato ---
    st.markdown("---")
    st.markdown("### Dettaglio Documento Selezionato")

    if not selected:
        st.info("Seleziona un documento dalla tabella o dalla mappa completezza per vederne il dettaglio.")

    if selected:
        sel_analysis = next((a for a in filtered if a["basename"] == selected), None)
        if sel_analysis:
            comp = sel_analysis["completeness"]
            st.progress(comp, text=f"Completezza: {int(comp * 100)}%")

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Dati Trovati:**")
                if sel_analysis["fields_found"]:
                    for fid, fd in sel_analysis["fields_found"].items():
                        examples_str = ", ".join(str(e) for e in fd["examples"][:3])
                        st.write(f"{fd['icon']} {fd['label']} ({fd['count']}) — {examples_str}")
                else:
                    st.write("Nessun dato trovato")
            with c2:
                st.markdown("**Dati Mancanti:**")
                if sel_analysis["fields_missing"]:
                    for m in sel_analysis["fields_missing"]:
                        st.write(f"{m['icon']} {m['label']}")
                else:
                    st.write("Nessun dato mancante")

            st.caption(f"Percorso: `{sel_analysis.get('source', selected)}`")

            # Preview del documento
            doc_path = sel_analysis.get("source", "")
            if doc_path and os.path.isfile(doc_path):
                ext = os.path.splitext(doc_path)[1].lower()

                # Preview per immagini (TIF, PNG, JPG, BMP)
                if ext in (".tif", ".tiff", ".png", ".jpg", ".jpeg", ".bmp"):
                    try:
                        from PIL import Image as PILImage
                        img = PILImage.open(doc_path)
                        # Converti se necessario (TIFF può avere mode I;16)
                        if img.mode not in ("RGB", "L", "RGBA"):
                            img = img.convert("RGB")
                        st.image(img, caption=sel_analysis["basename"], use_container_width=True)
                        # Salva per fullscreen
                        st.session_state["_preview_img_path"] = doc_path
                        st.session_state["_preview_img_name"] = sel_analysis["basename"]
                        if st.button("Schermo intero", key="fs_img", use_container_width=True):
                            _show_fullscreen_preview()
                    except Exception as e:
                        st.caption(f"Anteprima non disponibile: {e}")

                # Preview per PDF (prima pagina)
                elif ext == ".pdf":
                    try:
                        import fitz  # PyMuPDF
                        pdf_doc = fitz.open(doc_path)
                        if pdf_doc.page_count > 0:
                            page = pdf_doc[0]
                            # Render a 150 DPI per anteprima
                            mat = fitz.Matrix(150 / 72, 150 / 72)
                            pix = page.get_pixmap(matrix=mat)
                            img_bytes = pix.tobytes("png")
                            st.image(img_bytes, caption=f"{sel_analysis['basename']} (pag. 1/{pdf_doc.page_count})", use_container_width=True)
                            # Salva per fullscreen (render ad alta risoluzione)
                            mat_hd = fitz.Matrix(300 / 72, 300 / 72)
                            pix_hd = page.get_pixmap(matrix=mat_hd)
                            st.session_state["_preview_pdf_bytes"] = pix_hd.tobytes("png")
                            st.session_state["_preview_img_name"] = f"{sel_analysis['basename']} (pag. 1/{pdf_doc.page_count})"
                            st.session_state["_preview_img_path"] = None  # usa pdf_bytes
                            if st.button("Schermo intero", key="fs_pdf", use_container_width=True):
                                _show_fullscreen_preview()
                        pdf_doc.close()
                    except Exception as e:
                        st.caption(f"Anteprima PDF non disponibile: {e}")

                # Bottone per scaricare il documento originale
                try:
                    with open(doc_path, "rb") as f:
                        file_bytes = f.read()
                    st.download_button(
                        label=f"Scarica: {sel_analysis['basename']}",
                        data=file_bytes,
                        file_name=sel_analysis["basename"],
                        use_container_width=True,
                    )
                except Exception as e:
                    st.caption(f"Impossibile leggere il file: {e}")
            elif doc_path:
                st.caption(f"File non trovato su disco: {doc_path}")

    # ============================================================
    # RIEPILOGO COSA MANCA GLOBALMENTE
    # ============================================================

    st.markdown("---")
    st.markdown("### Riepilogo Globale — Cosa Manca")

    missing_global = {}
    for a in analyses:
        for m in a["fields_missing"]:
            fid = m["id"]
            if fid not in missing_global:
                missing_global[fid] = {"label": m["label"], "icon": m["icon"], "count": 0, "docs": []}
            missing_global[fid]["count"] += 1
            missing_global[fid]["docs"].append(a["basename"])

    # Ordina per più mancante
    sorted_missing = sorted(missing_global.items(), key=lambda x: x[1]["count"], reverse=True)

    for fid, info in sorted_missing:
        pct = info["count"] / len(analyses) * 100
        st.markdown(f"{info['icon']} **{info['label']}** — mancante in **{info['count']}** "
                     f"documenti ({pct:.0f}%)")
        if info["count"] <= 5:
            st.caption(f"  Documenti: {', '.join(info['docs'][:5])}")

    # Bottone per rinfrescare cache
    st.markdown("---")
    if st.button("Rianalizza Tutti i Documenti", use_container_width=True):
        if os.path.exists(_CACHE_FILE):
            os.remove(_CACHE_FILE)
        st.rerun()

"""
Trillium RAG - Pagina Indicizzazione
"""

import os
import time
import streamlit as st

from rag.indexer import index_folder, index_folder_streaming, reset_database
from config import VECTOR_DB
from modules.helpers import get_db_stats


def render():
    """Renderizza la pagina Indicizzazione."""
    st.markdown("## Indicizzazione Documenti")
    st.caption("ℹ️ Carica nuovi documenti tecnici nel database vettoriale. "
               "I formati supportati sono: PDF, Excel, Word, TIF, immagini. "
               "Ogni file viene letto, spezzato in chunk, e salvato con un embedding vettoriale per la ricerca semantica. "
               "Esempio: indicizza la cartella 'Weight Estimation Project-2' con i disegni tecnici delle pompe.")

    # Tabs per metodi di indicizzazione
    tab1, tab2 = st.tabs(["Cartella Locale", "SharePoint / OneDrive"])

    with tab1:
        st.markdown("### Indicizza da Cartella Locale")

        # Percorso precompilato alla cartella documenti del progetto
        default_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "Technical Documentation Project"
        )
        if not os.path.isdir(default_path):
            default_path = ""

        # Folder picker nativo macOS
        import subprocess

        col_browse, col_path = st.columns([1, 5])
        with col_browse:
            if st.button("Sfoglia...", key="browse_folder", use_container_width=True):
                try:
                    result = subprocess.run(
                        ["osascript", "-e",
                         'tell application "Finder" to activate\n'
                         'return POSIX path of (choose folder with prompt "Seleziona cartella documenti")'],
                        capture_output=True, text=True, timeout=120,
                    )
                    chosen = result.stdout.strip().rstrip("/")
                    if chosen and os.path.isdir(chosen):
                        st.session_state.browse_path = chosen
                        st.rerun()
                except Exception:
                    pass

        with col_path:
            folder_path = st.text_input(
                "Percorso cartella",
                value=st.session_state.get("browse_path", default_path),
                placeholder="/path/to/documents",
                help="Clicca 'Sfoglia...' per selezionare oppure digita il percorso",
                key="folder_path_input",
            )
            if folder_path:
                st.session_state.browse_path = folder_path




        # Anteprima contenuto cartella
        display_path = st.session_state.get("browse_path", folder_path or "")
        if display_path and os.path.isdir(display_path):
            try:
                all_files = [f for f in os.listdir(display_path)
                             if os.path.isfile(os.path.join(display_path, f)) and not f.startswith(".")]
                subdirs = [d for d in os.listdir(display_path)
                           if os.path.isdir(os.path.join(display_path, d)) and not d.startswith(".")]
                if all_files or subdirs:
                    exts = {}
                    for f in all_files:
                        ext = os.path.splitext(f)[1].lower() or "(altro)"
                        exts[ext] = exts.get(ext, 0) + 1
                    summary = ", ".join(f"{count} {ext}" for ext, count in sorted(exts.items(), key=lambda x: -x[1]))
                    parts = []
                    if all_files:
                        parts.append(f"**{len(all_files)} file** ({summary})")
                    if subdirs:
                        parts.append(f"**{len(subdirs)} sottocartelle**")
                    st.info(" · ".join(parts))
            except PermissionError:
                st.warning("Permesso negato per questa cartella.")

        # Filtri estensioni
        with st.expander("Filtri e Parametri Indicizzazione"):
            st.markdown("**Estensioni da includere:**")
            ext_options = ["pdf", "docx", "doc", "xlsx", "xls", "pptx", "txt", "md", "csv",
                          "png", "jpg", "jpeg", "tif", "tiff"]
            selected_exts = st.multiselect(
                "Estensioni",
                ext_options,
                default=ext_options,
                key="idx_extensions",
                help="Seleziona i tipi di file da indicizzare",
                label_visibility="collapsed",
            )
            st.session_state.idx_selected_extensions = set(selected_exts)

            st.markdown("---")
            st.markdown("**Parametri Chunking:**")
            from config import CHUNK_SIZE, CHUNK_OVERLAP
            col_cs, col_co = st.columns(2)
            with col_cs:
                st.metric("Chunk Size", f"{CHUNK_SIZE} chars")
            with col_co:
                st.metric("Overlap", f"{CHUNK_OVERLAP} chars")
            st.caption("Modifica in .env: CHUNK_SIZE e CHUNK_OVERLAP")

            # Anteprima chunking
            if display_path and os.path.isdir(display_path):
                st.markdown("---")
                st.markdown("**Anteprima Chunking:**")
                try:
                    # Conta file e stima chunk
                    total_files = 0
                    total_size = 0
                    for root, dirs, files in os.walk(display_path):
                        dirs[:] = [d for d in dirs if not d.startswith(".")]
                        for f in files:
                            if f.startswith("."):
                                continue
                            ext = f.rsplit(".", 1)[-1].lower() if "." in f else ""
                            if selected_exts and ext not in selected_exts:
                                continue
                            fp = os.path.join(root, f)
                            total_files += 1
                            total_size += os.path.getsize(fp)

                    est_chunks = max(1, int(total_size / max(1, CHUNK_SIZE - CHUNK_OVERLAP)))
                    size_mb = total_size / (1024 * 1024)

                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric("File da indicizzare", total_files)
                    with c2:
                        st.metric("Dimensione totale", f"{size_mb:.1f} MB")
                    with c3:
                        st.metric("Chunk stimati", f"~{est_chunks}")
                except Exception:
                    pass

        col1, col2 = st.columns([1, 4])
        with col1:
            index_button = st.button("Avvia Indicizzazione", type="primary", use_container_width=True)

        if index_button and folder_path:
            if os.path.exists(folder_path):
                st.session_state.indexing_in_progress = True

                with st.container():
                    st.markdown("### Indicizzazione in corso")

                    # Contatore documenti
                    counter_placeholder = st.empty()
                    progress_bar = st.progress(0)

                    # Log in contenitore scrollabile a altezza fissa
                    st.markdown(
                        "<style>.log-container{max-height:300px;overflow-y:auto;background:#1a1a2e;"
                        "border:1px solid #333;border-radius:6px;padding:12px;font-family:monospace;"
                        "font-size:12px;color:#ccc;white-space:pre-wrap;}</style>",
                        unsafe_allow_html=True,
                    )
                    log_placeholder = st.empty()

                    try:
                        # Conta file totali per il contatore
                        total_files = 0
                        sel_ext = st.session_state.get("idx_selected_extensions")
                        for root, dirs, files in os.walk(folder_path):
                            dirs[:] = [d for d in dirs if not d.startswith(".")]
                            for f in files:
                                if f.startswith("."):
                                    continue
                                ext = f.rsplit(".", 1)[-1].lower() if "." in f else ""
                                if sel_ext and ext not in sel_ext:
                                    continue
                                total_files += 1

                        counter_placeholder.info(f"**0 / {total_files}** documenti indicizzati (0%)")

                        all_log_lines = []
                        processed = 0
                        stats_before = get_db_stats()

                        for progress, new_lines in index_folder_streaming(folder_path):
                            all_log_lines.extend(new_lines)
                            processed = int(progress * total_files) if total_files > 0 else 0
                            pct = int(progress * 100)

                            # Aggiorna contatore
                            counter_placeholder.info(
                                f"**{processed} / {total_files}** documenti indicizzati ({pct}%)"
                            )
                            progress_bar.progress(min(1.0, progress))

                            # Log scrollabile: mostra solo le ultime 200 righe
                            visible_lines = all_log_lines[-200:]
                            log_html = "<br>".join(
                                line.replace("<", "&lt;").replace(">", "&gt;")
                                for line in visible_lines
                            )
                            log_placeholder.markdown(
                                f"<div class='log-container'>{log_html}</div>",
                                unsafe_allow_html=True,
                            )

                        stats_after = get_db_stats()
                        new_docs = stats_after["total_documents"] - stats_before["total_documents"]

                        progress_bar.progress(1.0)
                        counter_placeholder.success(
                            f"**Completato!** {total_files} file processati — "
                            f"{new_docs} nuovi documenti aggiunti"
                        )

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Documenti prima", stats_before["total_documents"])
                        with col2:
                            st.metric("Nuovi documenti", new_docs, delta=new_docs)
                        with col3:
                            st.metric("Documenti totali", stats_after["total_documents"])

                        st.session_state.indexing_in_progress = False

                    except Exception as e:
                        progress_bar.progress(0)
                        counter_placeholder.error(f"Errore: {str(e)}")
                        st.session_state.indexing_in_progress = False
            else:
                st.error("Percorso non valido. Verifica che la cartella esista.")

    with tab2:
        st.markdown("### Indicizza da SharePoint / OneDrive")

        sharepoint_url = st.text_input(
            "URL SharePoint/OneDrive",
            placeholder="https://tenant-my.sharepoint.com/...",
            help="Incolla l'URL completo della cartella SharePoint/OneDrive",
        )

        col1, col2 = st.columns([1, 4])
        with col1:
            index_sp_button = st.button("Avvia", type="primary", use_container_width=True, key="sp_btn")

        if index_sp_button and sharepoint_url:
            if sharepoint_url.startswith(("http://", "https://")):
                st.session_state.indexing_in_progress = True

                info_box = st.info("Autenticazione in corso...")
                progress_bar = st.progress(0)
                status_text = st.empty()

                log_expander_sp = st.expander("Log Indicizzazione", expanded=True)
                log_placeholder_sp = log_expander_sp.empty()
                with st.spinner("Autenticazione e indicizzazione in corso..."):
                    try:
                        status_text.text("Autenticazione con Microsoft...")
                        progress_bar.progress(0.1)
                        stats_before = get_db_stats()
                        all_log_lines = []
                        for progress, new_lines in index_folder_streaming(sharepoint_url):
                            all_log_lines.extend(new_lines)
                            progress_bar.progress(min(1.0, progress))
                            if all_log_lines:
                                log_placeholder_sp.code("\n".join(all_log_lines), language=None)
                        progress_bar.progress(1.0)
                        status_text.success("Indicizzazione completata.")
                        stats_after = get_db_stats()
                        new_docs = stats_after["total_documents"] - stats_before["total_documents"]
                        if all_log_lines:
                            log_placeholder_sp.code("\n".join(all_log_lines), language=None)
                        info_box.success(f"Indicizzazione da SharePoint completata. Aggiunti {new_docs} nuovi documenti.")

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Documenti prima", stats_before["total_documents"])
                        with col2:
                            st.metric("Nuovi documenti", new_docs, delta=new_docs)
                        with col3:
                            st.metric("Documenti totali", stats_after["total_documents"])

                        st.session_state.indexing_in_progress = False
                    except Exception as e:
                        progress_bar.progress(0)
                        status_text.error("Errore durante l'indicizzazione.")
                        info_box.error(f"Errore: {str(e)}")
                        st.session_state.indexing_in_progress = False
            else:
                st.error("URL non valido. Deve iniziare con http:// o https://")

    # Reset database
    st.markdown("---")
    st.markdown("### Reset Database")

    current_stats = get_db_stats()

    col1, col2 = st.columns([3, 1])
    with col1:
        st.warning(f"""
        **ATTENZIONE: Reset Completo del Database**

        Questa azione cancellerà permanentemente:
        - **{current_stats['total_documents']} documenti** indicizzati
        - **{current_stats['total_chunks']} chunk** di testo
        - Tutti i dati nel database vettoriale ({VECTOR_DB.upper()})

        **Questa azione è irreversibile.** Dovrai re-indicizzare tutti i documenti.
        """)
    with col2:
        if st.button("Reset Database", type="secondary", use_container_width=True):
            st.session_state.reset_confirm = True

    if st.session_state.get("reset_confirm", False):
        st.error("**Ultima conferma richiesta**")
        confirm_text = st.text_input(
            "Digita 'CONFERMO' per procedere con la cancellazione:",
            placeholder="CONFERMO",
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Conferma Reset", type="primary"):
                if confirm_text == "CONFERMO":
                    try:
                        with st.spinner("Cancellazione database in corso..."):
                            reset_database()
                        st.success("Database resettato con successo.")
                        st.info("Tutti i documenti sono stati cancellati. Puoi ora indicizzare nuovi documenti.")
                        st.session_state.reset_confirm = False
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore durante il reset: {str(e)}")
                        st.session_state.reset_confirm = False
                else:
                    st.warning("Devi digitare esattamente 'CONFERMO' per procedere.")
        with col2:
            if st.button("Annulla", type="secondary"):
                st.session_state.reset_confirm = False
                st.rerun()

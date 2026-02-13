"""
Trillium RAG System - Interfaccia Streamlit
Interfaccia grafica elegante per il sistema RAG
"""

import streamlit as st
import os
import sys
import time
from pathlib import Path
from datetime import datetime
import threading
import queue
import pandas as pd

# Import plotly con fallback
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    # Non possiamo usare st.warning qui perché streamlit non è ancora inizializzato
    # Mostreremo il messaggio quando necessario

# Aggiungi il percorso del progetto al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importa moduli del progetto
from rag.indexer import index_folder, index_folder_streaming, reset_database, get_chroma, get_vector_db, index_api_data
from rag.query import rag_query, retrieve_relevant_docs, build_context, build_context
from rag.model_compare import compare_models
from rag.api_integration import index_all_orders, index_prestashop_orders, index_shippypro_orders
from config import (
    PROVIDER, VECTOR_DB, CHROMA_DB_PATH, 
    OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY,
    QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION_NAME,
    PARALLEL_WORKERS, CHUNK_BATCH_SIZE,
    TOP_K,
)

# Base path consentiti per il download (progetto Trillium e parent)
_TRILLIUM_ROOT = os.path.abspath(os.path.dirname(__file__))
_ALLOWED_DOWNLOAD_ROOTS = (_TRILLIUM_ROOT, os.path.abspath(os.path.join(_TRILLIUM_ROOT, os.pardir)))

def _short_path_for_display(file_path: str, max_segments: int = 4) -> str:
    """Restituisce solo le ultime max_segments parti del percorso (es. ultime 3 cartelle + file)."""
    parts = Path(file_path).parts
    if len(parts) <= max_segments:
        return file_path.replace("\\", "/")
    return "…/" + "/".join(parts[-max_segments:])


def _get_file_for_download(file_path: str):
    """
    Se il percorso è un file locale esistente e sotto una cartella consentita,
    restituisce (bytes, nome_file, mime) per st.download_button; altrimenti None.
    """
    if not file_path or file_path.strip().lower().startswith(("http://", "https://")):
        return None
    path = Path(file_path).resolve()
    try:
        if not path.is_file():
            return None
        abs_path = str(path)
        try:
            if not any(os.path.commonpath([abs_path, str(Path(r).resolve())]) == str(Path(r).resolve()) for r in _ALLOWED_DOWNLOAD_ROOTS):
                return None
        except ValueError:
            return None
        data = path.read_bytes()
        name = path.name
        suffix = path.suffix.lower()
        mime_map = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xlsm": "application/vnd.ms-excel.sheet.macroEnabled.12",
            ".xls": "application/vnd.ms-excel",
            ".txt": "text/plain",
        }
        mime = mime_map.get(suffix, "application/octet-stream")
        return (data, name, mime)
    except Exception:
        return None

# ============================================================
# CONFIGURAZIONE PAGINA
# ============================================================

st.set_page_config(
    page_title="Trillium RAG System",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS PERSONALIZZATO
# ============================================================

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
    }
    .metric-label {
        font-size: 1rem;
        opacity: 0.9;
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .user-message {
        background-color: #e3f2fd;
        margin-left: 20%;
    }
    .assistant-message {
        background-color: #f5f5f5;
        margin-right: 20%;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# INIZIALIZZAZIONE SESSION STATE
# ============================================================

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'selected_provider' not in st.session_state:
    st.session_state.selected_provider = PROVIDER

if 'use_web_search' not in st.session_state:
    st.session_state.use_web_search = False
if 'use_depth_reasoning' not in st.session_state:
    st.session_state.use_depth_reasoning = False

if 'indexing_in_progress' not in st.session_state:
    st.session_state.indexing_in_progress = False

if 'indexing_results' not in st.session_state:
    st.session_state.indexing_results = None

# ============================================================
# FUNZIONI HELPER
# ============================================================

def get_db_stats():
    """Ottiene statistiche del database"""
    try:
        if VECTOR_DB == "qdrant":
            from qdrant_client import QdrantClient
            client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
            collection_info = client.get_collection(QDRANT_COLLECTION_NAME)
            points_count = collection_info.points_count
            
            # Conta file unici (letti con successo)
            points, _ = client.scroll(
                collection_name=QDRANT_COLLECTION_NAME,
                limit=100000
            )
            unique_files = set()
            for point in points:
                payload = point.payload if point.payload else {}
                source = payload.get("source", "")
                if source:
                    # Usa solo il nome file base per evitare duplicati
                    file_key = source.split("/")[-1] if "/" in source else source
                    unique_files.add(file_key)
            
            return {
                "total_documents": points_count,
                "total_chunks": points_count,
                "files_read": len(unique_files),
                "files_failed": 0,  # Non tracciato attualmente
                "db_size": "N/A (Qdrant)",
                "status": "✓ Connesso"
            }
        else:
            # ChromaDB
            collection = get_chroma()
            count = collection.count()
            db_path = Path(CHROMA_DB_PATH)
            db_size = sum(f.stat().st_size for f in db_path.rglob('*') if f.is_file()) / (1024**3)  # GB
            
            # Conta file unici (letti con successo)
            all_data = collection.get()
            unique_files = set()
            if all_data and "metadatas" in all_data:
                for metadata in all_data["metadatas"]:
                    if metadata and "source" in metadata:
                        source = metadata["source"]
                        # Usa solo il nome file base per evitare duplicati
                        file_key = source.split("/")[-1] if "/" in source else source
                        unique_files.add(file_key)
            
            return {
                "total_documents": count,
                "total_chunks": count,
                "files_read": len(unique_files),
                "files_failed": 0,  # Non tracciato attualmente
                "db_size": f"{db_size:.2f} GB",
                "status": "✓ Attivo"
            }
    except Exception as e:
        return {
            "total_documents": 0,
            "total_chunks": 0,
            "files_read": 0,
            "files_failed": 0,
            "db_size": "N/A",
            "status": f"✗ Errore: {str(e)[:50]}"
        }

def get_available_providers():
    """Ottiene lista provider LLM disponibili"""
    providers = []
    if OPENAI_API_KEY:
        providers.append(("OpenAI", "GPT-5.1", "openai"))
    if ANTHROPIC_API_KEY:
        providers.append(("Anthropic", "Claude 3.5 Sonnet", "anthropic"))
    if GEMINI_API_KEY:
        providers.append(("Google", "Gemini 2.5 Flash", "gemini"))
    if OPENROUTER_API_KEY:
        providers.append(("OpenRouter", "Claude/Gemini", "openrouter"))
    return providers

def get_document_distribution():
    """Estrae la distribuzione reale dei tipi di documento dal database"""
    try:
        file_types = {
            "PDF": 0,
            "Word": 0,
            "Excel": 0,
            "Immagini": 0,
            "Altri": 0
        }
        
        if VECTOR_DB == "qdrant":
            from rag.qdrant_db import get_qdrant_collection
            client, collection_name = get_qdrant_collection()
            
            # Scroll tutti i punti
            points, _ = client.scroll(
                collection_name=collection_name,
                limit=100000  # Limite alto per ottenere tutti
            )
            
            # Analizza ogni punto
            seen_files = set()  # Per evitare duplicati (chunk dello stesso file)
            for point in points:
                payload = point.payload if point.payload else {}
                source = payload.get("source", "")
                if source:
                    # Usa solo il nome file base per evitare duplicati
                    file_key = source.split("/")[-1] if "/" in source else source
                    if file_key not in seen_files:
                        seen_files.add(file_key)
                        ext = source.lower().split(".")[-1] if "." in source else ""
                        if ext == "pdf":
                            file_types["PDF"] += 1
                        elif ext in ["doc", "docx"]:
                            file_types["Word"] += 1
                        elif ext in ["xls", "xlsx", "xlsm"]:
                            file_types["Excel"] += 1
                        elif ext in ["png", "jpg", "jpeg", "tif", "tiff", "bmp", "heic", "heif"]:
                            file_types["Immagini"] += 1
                        else:
                            file_types["Altri"] += 1
        else:
            # ChromaDB
            collection = get_chroma()
            all_data = collection.get()
            
            if all_data and "metadatas" in all_data:
                seen_files = set()
                for metadata in all_data["metadatas"]:
                    if metadata and "source" in metadata:
                        source = metadata["source"]
                        # Usa solo il nome file base per evitare duplicati
                        file_key = source.split("/")[-1] if "/" in source else source
                        if file_key not in seen_files:
                            seen_files.add(file_key)
                            ext = source.lower().split(".")[-1] if "." in source else ""
                            if ext == "pdf":
                                file_types["PDF"] += 1
                            elif ext in ["doc", "docx"]:
                                file_types["Word"] += 1
                            elif ext in ["xls", "xlsx", "xlsm"]:
                                file_types["Excel"] += 1
                            elif ext in ["png", "jpg", "jpeg", "tif", "tiff", "bmp", "heic", "heif"]:
                                file_types["Immagini"] += 1
                            else:
                                file_types["Altri"] += 1
        
        return file_types
    except Exception as e:
        # In caso di errore, ritorna dati vuoti
        return {"PDF": 0, "Word": 0, "Excel": 0, "Immagini": 0, "Altri": 0}

# ============================================================
# SIDEBAR - NAVIGAZIONE
# ============================================================

with st.sidebar:
    st.markdown("# Trillium RAG")
    st.markdown("---")
    
    page = st.radio(
        "Navigazione",
        ["🏠 Dashboard", "📁 Indicizza", "💬 Chat RAG", "🔍 Ricerca Cliente", "⚖️ Confronta Modelli", "⚙️ Configurazione"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # Statistiche rapide nella sidebar
    stats = get_db_stats()
    st.markdown("### 📊 Statistiche Rapide")
    st.metric("Documenti", stats["total_documents"])
    st.metric("Chunk", stats["total_chunks"])
    st.metric("File Letti", stats.get("files_read", 0))
    if stats.get("files_failed", 0) > 0:
        st.metric("File Non Letti", stats.get("files_failed", 0), delta=f"-{stats.get('files_failed', 0)}", delta_color="inverse")
    st.caption(f"DB: {stats['db_size']}")
    st.caption(f"Status: {stats['status']}")
    
    st.markdown("---")
    
    # Info sistema
    st.markdown("### ℹ️ Sistema")
    st.caption(f"Provider: {PROVIDER}")
    st.caption(f"Database: {VECTOR_DB.upper()}")
    if PARALLEL_WORKERS > 0:
        st.caption(f"⚡ Parallelo: {PARALLEL_WORKERS} worker")
    else:
        st.caption("📝 Sequenziale")

# ============================================================
# PAGINA: DASHBOARD
# ============================================================

if page == "🏠 Dashboard":
    st.markdown('<div class="main-header">Trillium RAG System</div>', unsafe_allow_html=True)
    
    # Statistiche principali
    stats = get_db_stats()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📄 Documenti", stats["total_documents"])
    
    with col2:
        st.metric("🧩 Chunk", stats["total_chunks"])
    
    with col3:
        st.metric("✅ File Letti", stats.get("files_read", 0))
    
    with col4:
        files_failed = stats.get("files_failed", 0)
        if files_failed > 0:
            st.metric("❌ File Non Letti", files_failed, delta=f"-{files_failed}", delta_color="inverse")
        else:
            st.metric("❌ File Non Letti", files_failed)
    
    with col5:
        status_color = "🟢" if "✓" in stats["status"] else "🔴"
        st.metric("Status", f"{status_color} {stats['status']}")
    
    # Seconda riga di metriche
    col6, col7 = st.columns(2)
    with col6:
        st.metric("💾 Database", stats["db_size"])
    
    with col7:
        # Percentuale successo
        total_files = stats.get("files_read", 0) + stats.get("files_failed", 0)
        if total_files > 0:
            success_rate = (stats.get("files_read", 0) / total_files) * 100
            st.metric("📊 Tasso Successo", f"{success_rate:.1f}%")
        else:
            st.metric("📊 Tasso Successo", "N/A")
    
    st.markdown("---")
    
    # Grafici e visualizzazioni
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📈 Distribuzione Documenti")
        
        # Estrai dati reali dal database
        file_distribution = get_document_distribution()
        total_files = sum(file_distribution.values())
        
        if total_files > 0:
            if PLOTLY_AVAILABLE:
                # Grafico a torta con dati reali
                labels = list(file_distribution.keys())
                values = list(file_distribution.values())
                
                # Filtra solo tipi con valori > 0
                filtered_data = [(l, v) for l, v in zip(labels, values) if v > 0]
                if filtered_data:
                    labels_filtered, values_filtered = zip(*filtered_data)
                    
                    fig_pie = go.Figure(data=[go.Pie(
                        labels=labels_filtered,
                        values=values_filtered,
                        hole=0.4
                    )])
                    fig_pie.update_layout(
                        height=300,
                        showlegend=True,
                        margin=dict(l=0, r=0, t=0, b=0)
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("📊 Nessun documento nel database")
            else:
                st.info("📊 Grafico non disponibile. Installa plotly per visualizzare i grafici: `pip install plotly`")
                # Mostra dati in formato tabella
                st.dataframe({
                    "Tipo": list(file_distribution.keys()),
                    "Quantità": list(file_distribution.values())
                }, use_container_width=True)
        else:
            st.info("📊 Nessun documento indicizzato. Indicizza alcuni documenti per vedere la distribuzione.")
    
    with col2:
        st.markdown("### 📊 Statistiche Database")
        
        # Mostra statistiche reali invece di timeline (non abbiamo timestamp nei metadati)
        if PLOTLY_AVAILABLE:
            # Grafico a barre con distribuzione documenti
            file_distribution = get_document_distribution()
            total_files = sum(file_distribution.values())
            
            if total_files > 0:
                labels = list(file_distribution.keys())
                values = list(file_distribution.values())
                
                # Filtra solo tipi con valori > 0
                filtered_data = [(l, v) for l, v in zip(labels, values) if v > 0]
                if filtered_data:
                    labels_filtered, values_filtered = zip(*filtered_data)
                    
                    fig_bar = px.bar(
                        x=labels_filtered,
                        y=values_filtered,
                        labels={"x": "Tipo Documento", "y": "Quantità"},
                        title="Documenti per Tipo"
                    )
                    fig_bar.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0))
                    st.plotly_chart(fig_bar, use_container_width=True)
                else:
                    st.metric("Documenti totali", stats["total_documents"])
            else:
                st.metric("Documenti totali", stats["total_documents"])
                st.info("📊 Indicizza documenti per vedere statistiche dettagliate")
        else:
            st.info("📊 Grafico non disponibile. Installa plotly per visualizzare i grafici: `pip install plotly`")
            st.metric("Documenti totali", stats["total_documents"])
            st.metric("Chunk totali", stats["total_chunks"])
    
    # Informazioni sistema
    st.markdown("---")
    st.markdown("### 🔧 Configurazione Sistema")
    
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

# ============================================================
# PAGINA: INDICIZZAZIONE
# ============================================================

elif page == "📁 Indicizza":
    st.markdown("# 📁 Indicizzazione Documenti")
    
    # Tabs per diversi metodi di indicizzazione
    tab1, tab2, tab3 = st.tabs(["📂 Cartella Locale", "☁️ SharePoint/OneDrive", "📦 Ordini API"])
    
    with tab1:
        st.markdown("### Indicizza da Cartella Locale")
        
        folder_path = st.text_input(
            "Percorso cartella",
            placeholder="/path/to/documents",
            help="Inserisci il percorso completo della cartella da indicizzare"
        )
        
        col1, col2 = st.columns([1, 4])
        with col1:
            index_button = st.button("▶️ Avvia Indicizzazione", type="primary", use_container_width=True)
        
        if index_button and folder_path:
            if os.path.exists(folder_path):
                st.session_state.indexing_in_progress = True
                
                # Container per progress
                with st.container():
                    st.markdown("### ⏳ Indicizzazione in corso...")
                    
                    # Info box
                    info_box = st.info("🔄 Preparazione indicizzazione...")
                    
                    # Progress bar
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Log area
                    log_expander = st.expander("📋 Log Indicizzazione", expanded=True)
                    log_placeholder = log_expander.empty()
                    
                    try:
                        status_text.text("🔄 Avvio indicizzazione...")
                        info_box.info("🔄 Indicizzazione in corso... Questo potrebbe richiedere alcuni minuti.")
                        
                        all_log_lines = []
                        with st.spinner("⏳ Indicizzazione in corso... Non chiudere questa pagina."):
                            stats_before = get_db_stats()
                            for progress, new_lines in index_folder_streaming(folder_path):
                                all_log_lines.extend(new_lines)
                                progress_bar.progress(min(1.0, progress))
                                if all_log_lines:
                                    log_placeholder.code("\n".join(all_log_lines), language=None)
                            stats_after = get_db_stats()
                            new_docs = stats_after["total_documents"] - stats_before["total_documents"]
                            if all_log_lines:
                                log_placeholder.code("\n".join(all_log_lines), language=None)
                        
                        progress_bar.progress(1.0)
                        status_text.success("✅ Indicizzazione completata!")
                        info_box.success(f"✅ Indicizzazione completata! Aggiunti {new_docs} nuovi documenti.")
                        
                        # Mostra risultati dettagliati
                        st.balloons()  # Animazione di successo!
                        
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
                        status_text.error(f"❌ Errore durante l'indicizzazione")
                        info_box.error(f"❌ Errore: {str(e)}")
                        log_placeholder.error(f"Errore: {str(e)}")
                        st.session_state.indexing_in_progress = False
            else:
                st.error("❌ Percorso non valido. Verifica che la cartella esista.")
    
    with tab2:
        st.markdown("### Indicizza da SharePoint/OneDrive")
        
        sharepoint_url = st.text_input(
            "URL SharePoint/OneDrive",
            placeholder="https://tenant-my.sharepoint.com/...",
            help="Incolla l'URL completo della cartella SharePoint/OneDrive"
        )
        
        col1, col2 = st.columns([1, 4])
        with col1:
            index_sharepoint_button = st.button("☁️ Avvia Indicizzazione", type="primary", use_container_width=True)
        
        if index_sharepoint_button and sharepoint_url:
            if sharepoint_url.startswith("http://") or sharepoint_url.startswith("https://"):
                st.session_state.indexing_in_progress = True
                
                info_box = st.info("🔐 Autenticazione in corso...")
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                log_expander_sp = st.expander("📋 Log Indicizzazione", expanded=True)
                log_placeholder_sp = log_expander_sp.empty()
                with st.spinner("🔐 Autenticazione e indicizzazione in corso... Questo potrebbe richiedere alcuni minuti."):
                    try:
                        status_text.text("🔐 Autenticazione con Microsoft...")
                        progress_bar.progress(0.1)
                        stats_before = get_db_stats()
                        all_log_lines = []
                        for progress, new_lines in index_folder_streaming(sharepoint_url):
                            all_log_lines.extend(new_lines)
                            progress_bar.progress(min(1.0, progress))
                            if all_log_lines:
                                log_placeholder_sp.code("\n".join(all_log_lines), language=None)
                        progress_bar.progress(1.0)
                        status_text.success("✅ Indicizzazione completata!")
                        stats_after = get_db_stats()
                        new_docs = stats_after["total_documents"] - stats_before["total_documents"]
                        if all_log_lines:
                            log_placeholder_sp.code("\n".join(all_log_lines), language=None)
                        info_box.success(f"✅ Indicizzazione da SharePoint/OneDrive completata! Aggiunti {new_docs} nuovi documenti.")
                        
                        st.balloons()
                        
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
                        status_text.error("❌ Errore durante l'indicizzazione")
                        info_box.error(f"❌ Errore: {str(e)}")
                        st.session_state.indexing_in_progress = False
            else:
                st.error("❌ URL non valido. Deve iniziare con http:// o https://")
    
    with tab3:
        st.markdown("### 📦 Indicizza Ordini da API")
        st.markdown("Recupera e indicizza ordini da PrestaShop e ShippyPro nel database vettoriale.")
        
        # Informazione importante
        st.info("""
        **📅 Indicizzazione Automatica Ultimi 6 Mesi**
        
        Per default, il sistema indicizza automaticamente solo gli ordini degli ultimi 6 mesi.
        Gli ordini più vecchi di 6 mesi verranno saltati con un avviso di contattare direttamente l'azienda.
        """)
        
        # Opzioni di indicizzazione
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🛒 PrestaShop")
            prestashop_enabled = st.checkbox("Includi ordini PrestaShop", value=True)
            st.caption("Recupererà TUTTI gli ordini degli ultimi 6 mesi")
        
        with col2:
            st.markdown("#### 🚚 ShippyPro")
            shippypro_enabled = st.checkbox("Includi ordini ShippyPro", value=True)
            st.caption("Recupererà TUTTI gli ordini degli ultimi 6 mesi")
        
        # Opzione indicizzazione automatica 6 mesi
        st.markdown("---")
        st.markdown("#### ⚙️ Opzioni Indicizzazione")
        auto_six_months = st.checkbox(
            "Limita agli ultimi 6 mesi (opzionale)",
            value=False,
            help="Se attivo, indica solo ordini degli ultimi 6 mesi. Se disattivo, indica TUTTI gli ordini disponibili."
        )
        
        # Filtri per data (opzionali, solo se auto_six_months è disattivato)
        use_date_filter = False
        date_from = None
        date_to = None
        
        if not auto_six_months:
            st.markdown("#### 📅 Filtri Data Personalizzati")
            use_date_filter = st.checkbox("Usa filtro per data personalizzato", value=False)
            
            if use_date_filter:
                col_date1, col_date2 = st.columns(2)
                with col_date1:
                    # Default: 2025-01-01
                    default_start = datetime(2025, 1, 1).date()
                    date_from = st.date_input("Data inizio", value=default_start, help="Formato: YYYY-MM-DD")
                with col_date2:
                    # Default: 2025-12-31
                    default_end = datetime(2025, 12, 31).date()
                    date_to = st.date_input("Data fine", value=default_end, help="Formato: YYYY-MM-DD")
                
                if date_from:
                    date_from = date_from.strftime("%Y-%m-%d")
                if date_to:
                    date_to = date_to.strftime("%Y-%m-%d")
        
        # Pulsante indicizzazione
        st.markdown("---")
        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            index_orders_button = st.button("📦 Avvia Indicizzazione Ordini", type="primary", use_container_width=True)
        
        if index_orders_button:
            if not prestashop_enabled and not shippypro_enabled:
                st.error("❌ Seleziona almeno una fonte (PrestaShop o ShippyPro)")
            else:
                st.session_state.indexing_in_progress = True
                
                # Container per progress
                with st.container():
                    st.markdown("### ⏳ Indicizzazione ordini in corso...")
                    
                    info_box = st.info("🔄 Recupero ordini dalle API...")
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Inizializza progress_state se non esiste
                    if 'progress_state' not in st.session_state:
                        st.session_state.progress_state = {
                            'source': None,
                            'order_id': None,
                            'order_date': None,
                            'date_display': None,
                            'progress': 0.0,
                            'total': 0
                        }
                    
                    # Container prominente per le informazioni sull'ordine corrente
                    st.markdown("---")
                    st.markdown("### 📊 Stato Elaborazione Ordine Corrente")
                    
                    # Container per le metriche dell'ordine corrente
                    order_metrics_container = st.container()
                    with order_metrics_container:
                        col_order1, col_order2, col_order3 = st.columns(3)
                        metric_order_id = col_order1.empty()
                        metric_source = col_order2.empty()
                        metric_date = col_order3.empty()
                        
                        # Salva i riferimenti alle metriche in session_state per accesso nel callback
                        st.session_state.metric_order_id = metric_order_id
                        st.session_state.metric_source = metric_source
                        st.session_state.metric_date = metric_date
                        
                        # Inizializza le metriche - usa session_state se disponibile
                        current_order_id = st.session_state.progress_state.get('order_id', '-')
                        current_source = st.session_state.progress_state.get('source', '-')
                        current_date = st.session_state.progress_state.get('date_display', st.session_state.progress_state.get('order_date', '-'))
                        
                        # Se abbiamo dati in session_state, usali, altrimenti usa "-"
                        if current_order_id and current_order_id != '-':
                            metric_order_id.metric("🔢 Numero Ordine", f"#{current_order_id}")
                        else:
                            metric_order_id.metric("🔢 Numero Ordine", "-")
                        
                        if current_source and current_source != '-':
                            metric_source.metric("📦 Fonte", current_source)
                        else:
                            metric_source.metric("📦 Fonte", "-")
                        
                        if current_date and current_date != '-':
                            metric_date.metric("📅 Data Ordine", current_date)
                        else:
                            metric_date.metric("📅 Data Ordine", "-")
                    
                    # Box informativo aggiuntivo
                    current_order_info = st.empty()
                    # Inizializza con un messaggio
                    current_order_info.info("⏳ In attesa di avviare l'elaborazione...")
                    
                    log_expander = st.expander("📋 Log Indicizzazione - Ordini Processati", expanded=True)
                    log_placeholder = log_expander.empty()
                    # Inizializza log messages
                    if 'log_messages' not in st.session_state:
                        st.session_state.log_messages = []
                    
                    # Mostra messaggio iniziale nel log
                    initial_log = "🔄 In attesa di iniziare l'elaborazione...\n"
                    log_placeholder.text(initial_log)
                    st.session_state.log_messages = [initial_log]
                    
                    # progress_state è già inizializzato sopra, quindi non serve reinizializzarlo qui
                    
                    def update_progress(source, order_id, order_date, progress, total):
                        """Callback per aggiornare il progresso in tempo reale"""
                        # Aggiorna lo stato in session_state (questo è persistente)
                        st.session_state.progress_state['source'] = source
                        st.session_state.progress_state['order_id'] = order_id
                        st.session_state.progress_state['order_date'] = order_date
                        st.session_state.progress_state['progress'] = progress
                        st.session_state.progress_state['total'] = total
                        
                        # Formatta la data per visualizzazione
                        date_display = order_date if order_date else "N/A"
                        if date_display and len(date_display) > 10:
                            date_display = date_display[:10]
                        
                        # Estrai l'anno dalla data
                        order_year = None
                        date_display_formatted = date_display
                        try:
                            if date_display and date_display != "N/A" and len(date_display) >= 10:
                                date_obj = datetime.strptime(date_display[:10], "%Y-%m-%d")
                                order_year = date_obj.year
                                date_display_formatted = date_obj.strftime("%d/%m/%Y")
                        except:
                            # Prova a estrarre l'anno direttamente dalla stringa
                            try:
                                if date_display and len(date_display) >= 4:
                                    order_year = int(date_display[:4])
                            except:
                                pass
                        
                        # Salva anche la data formattata in session_state
                        st.session_state.progress_state['date_display'] = date_display_formatted
                        st.session_state.progress_state['order_year'] = order_year
                        
                        # Aggiorna direttamente l'interfaccia usando write (più veloce di info)
                        try:
                            progress_percent = int(progress * 100)
                            current_count = int(progress * total) if total > 0 else 0
                            
                            # Aggiorna le metriche - usa session_state per accesso alle metriche
                            try:
                                # Aggiorna direttamente le metriche usando session_state
                                if 'metric_order_id' in st.session_state and st.session_state.metric_order_id is not None:
                                    # Mostra sempre il numero ordine
                                    display_order_id = f"#{order_id}"
                                    if order_year and order_year != 2025:
                                        display_order_id = f"#{order_id} ({order_year})"
                                    st.session_state.metric_order_id.metric("🔢 Numero Ordine", display_order_id)
                                    
                                if 'metric_source' in st.session_state and st.session_state.metric_source is not None:
                                    st.session_state.metric_source.metric("📦 Fonte", source)
                                    
                                if 'metric_date' in st.session_state and st.session_state.metric_date is not None:
                                    # Mostra sempre la data, ma evidenzia se è 2025
                                    if order_year == 2025:
                                        display_date = f"✅ {date_display_formatted}"
                                    elif order_year:
                                        display_date = f"{order_year} - {date_display_formatted if date_display_formatted != date_display else 'Elaborazione...'}"
                                    else:
                                        display_date = date_display_formatted
                                    st.session_state.metric_date.metric("📅 Data Ordine", display_date)
                                    
                                # Stampa anche per debug
                                print(f"[UI UPDATE] Ordine: #{order_id}, Fonte: {source}, Anno: {order_year}, Data: {date_display_formatted}")
                            except Exception as e:
                                # Se le variabili non sono disponibili, salva solo in session_state
                                print(f"[UI UPDATE ERROR] {e}")
                                pass
                            
                            # Usa write invece di info per aggiornamenti più frequenti
                            status_text.text(f"📦 Processando ordini da {source}...")
                            
                            # Crea un messaggio formattato più visibile con più dettagli
                            if order_year == 2025:
                                info_message = f"""
🔄 **ELABORAZIONE IN CORSO - ORDINI 2025** ✅

📦 **Ordine corrente:** #{order_id}  
📅 **Data:** {date_display_formatted}  
📊 **Progresso:** {progress_percent}% ({current_count}/{total} ordini processati)  
🔢 **Ordini trovati finora:** {current_count}
                                """
                            else:
                                info_message = f"""
🔄 **ELABORAZIONE IN CORSO**

📦 **Ordine corrente:** #{order_id}  
📅 **Anno:** {order_year if order_year else 'N/A'}  
📊 **Progresso:** {progress_percent}% ({current_count}/{total} ordini processati)  
⏳ **Cercando ordini del 2025...**
                                """
                            
                            # Usa info box per renderlo più visibile
                            try:
                                if order_year == 2025:
                                    current_order_info.success(info_message)  # Usa success per evidenziare il 2025
                                else:
                                    current_order_info.info(info_message)
                                progress_bar.progress(0.3 + (progress * 0.3))
                            except:
                                pass
                            
                        except Exception as e:
                            print(f"[ERROR] Errore aggiornamento UI: {e}")
                        
                        # Stampa nella console con formato chiaro e visibile
                        progress_percent = int(progress * 100)
                        current_count = int(progress * total) if total > 0 else 0
                        
                        # Formato console migliorato e più visibile
                        console_message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 ELABORAZIONE ORDINI - PROGRESSO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Sorgente:        {source}
   Ordine corrente: #{order_id}
   Data ordine:     {date_display}
   Progresso:       {progress_percent}% ({current_count}/{total} ordini)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                        print(console_message)
                        
                        # Aggiungi anche al log expander se possibile - con più dettagli
                        try:
                            timestamp = datetime.now().strftime("%H:%M:%S")
                            
                            # Se l'ordine è del 2025, mostra TUTTI i dettagli
                            if order_year == 2025:
                                log_message = f"[{timestamp}] ✅ 2025 - {source} - Ordine #{order_id} - Data: {date_display_formatted} - Progresso: {progress_percent}% ({current_count}/{total})\n"
                            elif order_year:
                                # Per ordini di altri anni, mostra almeno l'anno per sapere che sta lavorando
                                log_message = f"[{timestamp}] ⏳ Anno {order_year} - {source} - Ordine #{order_id} - Progresso: {progress_percent}% ({current_count}/{total})\n"
                            else:
                                # Se non riusciamo a estrarre l'anno, mostra comunque qualcosa
                                log_message = f"[{timestamp}] 📦 {source} - Ordine #{order_id} - Data: {date_display_formatted} - Progresso: {progress_percent}% ({current_count}/{total})\n"
                            
                            if 'log_messages' not in st.session_state:
                                st.session_state.log_messages = []
                            
                            st.session_state.log_messages.append(log_message)
                            
                            # Mostra gli ultimi 100 messaggi (aumentato per vedere più ordini)
                            if len(st.session_state.log_messages) > 100:
                                st.session_state.log_messages = st.session_state.log_messages[-100:]
                            
                            # Mostra gli ultimi 50 messaggi nel log (aumentato per vedere più ordini)
                            log_text = '\n'.join(st.session_state.log_messages[-50:])
                            log_placeholder.text(log_text)
                            
                            # Stampa anche nella console per debug
                            print(f"[LOG] {log_message.strip()}")
                        except Exception as e:
                            print(f"[LOG ERROR] {e}")
                            pass
                    
                    try:
                        status_text.text("🔄 Connessione alle API...")
                        progress_bar.progress(0.1)
                        current_order_info.empty()
                        
                        # Stats prima
                        stats_before = get_db_stats()
                        
                        # Recupera e formatta ordini
                        status_text.text("📥 Recupero ordini da PrestaShop e ShippyPro...")
                        progress_bar.progress(0.3)
                        
                        # Recupera ordini (senza limiti numerici - solo filtro temporale 6 mesi) (usa auto_six_months se non è stato specificato un filtro data personalizzato)
                        use_auto_six_months = auto_six_months and not use_date_filter
                        # Se auto_six_months è False e non c'è filtro personalizzato, usa il 2025 come default
                        if not use_auto_six_months and not use_date_filter:
                            date_from = "2025-01-01"
                            date_to = "2025-12-31"
                            # Mostra messaggio informativo
                            st.info(f"📅 **Filtro automatico 2025 attivo**: Verranno recuperati tutti gli ordini dal {date_from} al {date_to}")
                        elif not use_auto_six_months:
                            # Mantieni le date personalizzate se specificate
                            if date_from and date_to:
                                st.info(f"📅 **Filtro personalizzato**: Ordini dal {date_from} al {date_to}")
                            pass
                        
                        # Inizializza il batch processing se non esiste
                        if 'batch_processing' not in st.session_state:
                            st.session_state.batch_processing = {
                                'prestashop_enabled': prestashop_enabled,
                                'shippypro_enabled': shippypro_enabled,
                                'date_from': date_from if use_date_filter else None,
                                'date_to': date_to if use_date_filter else None,
                                'auto_six_months': use_auto_six_months,
                                'orders_data': {"texts": [], "metadatas": [], "ids": [], "count": 0, "old_orders_warnings": []},
                                'phase': 'retrieving',  # 'retrieving' o 'indexing'
                                'batch_size': 50  # Processa 50 ordini alla volta
                            }
                        
                        # Processa in batch per permettere aggiornamenti UI
                        batch_state = st.session_state.batch_processing
                        
                        # Fase 1: Recupero ordini (con aggiornamenti UI)
                        if batch_state['phase'] == 'retrieving':
                            status_text.text("📥 Recupero ordini da PrestaShop e ShippyPro...")
                            current_order_info.info("🔄 **Recupero ordini dalle API...**\n\nQuesta fase può richiedere alcuni minuti.")
                            
                            # Mostra informazioni sul filtro data nel log
                            date_info = ""
                            if batch_state.get('date_from') and batch_state.get('date_to'):
                                date_info = f"Filtro data: {batch_state['date_from']} - {batch_state['date_to']}"
                            elif batch_state.get('auto_six_months'):
                                date_info = "Filtro: Ultimi 6 mesi"
                            else:
                                date_info = "Filtro: Tutti gli ordini disponibili"
                            
                            start_log = f"🚀 Inizio recupero ordini...\n{date_info}\n{'='*60}\n"
                            if 'log_messages' not in st.session_state:
                                st.session_state.log_messages = []
                            st.session_state.log_messages.append(start_log)
                            log_placeholder.text('\n'.join(st.session_state.log_messages[-30:]))
                            
                            # Aggiorna le metriche prima di iniziare (leggendo da session_state)
                            progress_state = st.session_state.progress_state
                            if progress_state.get('order_id'):
                                metric_order_id.metric("🔢 Numero Ordine", f"#{progress_state['order_id']}")
                                metric_source.metric("📦 Fonte", progress_state.get('source', '-'))
                                metric_date.metric("📅 Data Ordine", progress_state.get('date_display', progress_state.get('order_date', '-')))
                            
                            # Recupera ordini (questa è la parte più lunga)
                            if prestashop_enabled and shippypro_enabled:
                                orders_data = index_all_orders(
                                    date_from=batch_state['date_from'],
                                    date_to=batch_state['date_to'],
                                    auto_six_months=batch_state['auto_six_months'],
                                    progress_callback=update_progress
                                )
                            elif prestashop_enabled:
                                orders_data = index_prestashop_orders(
                                    date_from=batch_state['date_from'],
                                    date_to=batch_state['date_to'],
                                    auto_six_months=batch_state['auto_six_months'],
                                    progress_callback=update_progress
                                )
                            elif shippypro_enabled:
                                orders_data = index_shippypro_orders(
                                    auto_six_months=batch_state['auto_six_months'],
                                    date_from=batch_state['date_from'],
                                    date_to=batch_state['date_to'],
                                    progress_callback=update_progress
                                )
                            else:
                                orders_data = {"texts": [], "metadatas": [], "ids": [], "count": 0, "old_orders_warnings": []}
                            
                            # Aggiorna le metriche finali dopo il recupero
                            progress_state = st.session_state.progress_state
                            if progress_state.get('order_id'):
                                metric_order_id.metric("🔢 Numero Ordine", f"#{progress_state['order_id']}")
                                metric_source.metric("📦 Fonte", progress_state.get('source', '-'))
                                metric_date.metric("📅 Data Ordine", progress_state.get('date_display', progress_state.get('order_date', '-')))
                            
                            batch_state['orders_data'] = orders_data
                            batch_state['phase'] = 'indexing'
                        
                        # Fase 2: Indicizzazione (già fatto sopra, quindi usa i dati)
                        orders_data = batch_state['orders_data']
                        
                        # Pulisci il batch state
                        if 'batch_processing' in st.session_state:
                            del st.session_state.batch_processing
                        
                        if orders_data["count"] == 0:
                            st.warning("⚠️ Nessun ordine trovato con i filtri selezionati.")
                            # Aggiorna le metriche per mostrare che non ci sono ordini
                            metric_order_id.metric("🔢 Numero Ordine", "Nessun ordine")
                            metric_source.metric("📦 Fonte", "-")
                            metric_date.metric("📅 Data Ordine", "-")
                            current_order_info.warning("⚠️ Nessun ordine trovato con i filtri selezionati.")
                            st.session_state.indexing_in_progress = False
                        else:
                            # Aggiorna le metriche per mostrare che il recupero è completato
                            metric_order_id.metric("🔢 Numero Ordine", f"{orders_data['count']} ordini")
                            metric_source.metric("📦 Fonte", "Completato")
                            metric_date.metric("📅 Data Ordine", "Recuperati")
                            
                            # Pulisci info ordine corrente (fase di indicizzazione nel DB)
                            current_order_info.empty()
                            
                            # Indicizza nel database con aggiornamento progresso
                            total_orders = orders_data['count']
                            status_text.text(f"💾 Indicizzazione {total_orders} ordini nel database...")
                            progress_bar.progress(0.6)
                            
                            # Aggiorna metriche per mostrare progresso indicizzazione
                            metric_order_id.metric("🔢 Numero Ordine", f"0/{total_orders}")
                            metric_source.metric("📦 Fonte", "Indicizzazione DB")
                            metric_date.metric("📅 Data Ordine", "In corso...")
                            
                            # Mostra info box con progresso
                            current_order_info.info(f"""
💾 **INDICIZZAZIONE IN CORSO**

📊 **Ordini da indicizzare:** {total_orders}  
⏳ **Stato:** Generazione embeddings e salvataggio nel database...  
⏱️ **Tempo stimato:** ~{int(total_orders * 0.5)} secondi ({int(total_orders * 0.5 / 60)} minuti)

Questa fase può richiedere diversi minuti per grandi quantità di ordini.
                            """)
                            
                            result = index_api_data(
                                texts=orders_data["texts"],
                                metadatas=orders_data["metadatas"],
                                ids=orders_data["ids"]
                            )
                            
                            # Aggiorna metriche finali
                            indexed_count = result.get('indexed', 0)
                            metric_order_id.metric("🔢 Numero Ordine", f"{indexed_count}/{total_orders}")
                            metric_source.metric("📦 Fonte", "Completato")
                            metric_date.metric("📅 Data Ordine", "✅")
                            
                            progress_bar.progress(1.0)
                            status_text.success("✅ Indicizzazione completata!")
                            
                            # Stats dopo
                            stats_after = get_db_stats()
                            new_docs = stats_after["total_documents"] - stats_before["total_documents"]
                            
                            # Mostra risultati
                            info_box.success(f"✅ Indicizzazione completata! Indicizzati {result.get('indexed', 0)} ordini.")
                            
                            st.balloons()
                            
                            # Statistiche principali
                            col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                            with col_stat1:
                                st.metric("Ordini recuperati", orders_data["count"])
                            with col_stat2:
                                st.metric("Ordini indicizzati", result.get("indexed", 0))
                            with col_stat3:
                                st.metric("Ordini saltati", result.get("skipped", 0))
                            with col_stat4:
                                st.metric("Nuovi documenti DB", new_docs, delta=new_docs)
                            
                            # Statistiche dettagliate per fonte
                            st.markdown("---")
                            st.markdown("#### 📊 Statistiche Dettagliate")
                            
                            col_det1, col_det2 = st.columns(2)
                            
                            with col_det1:
                                st.markdown("**🛒 PrestaShop**")
                                prestashop_count = orders_data.get('prestashop_count', 0)
                                prestashop_last = orders_data.get('prestashop_last_order_id', 'N/A')
                                prestashop_total = orders_data.get('prestashop_total_processed', 0)
                                st.metric("Ordini indicizzati", prestashop_count)
                                st.metric("Ordini processati", prestashop_total)
                                st.metric("Ultimo ordine ID", prestashop_last)
                            
                            with col_det2:
                                st.markdown("**🚚 ShippyPro**")
                                shippypro_count = orders_data.get('shippypro_count', 0)
                                shippypro_last = orders_data.get('shippypro_last_order_id', 'N/A')
                                shippypro_total = orders_data.get('shippypro_total_processed', 0)
                                st.metric("Ordini indicizzati", shippypro_count)
                                st.metric("Ordini processati", shippypro_total)
                                st.metric("Ultimo ordine ID", shippypro_last)
                            
                            # Dettagli
                            if prestashop_enabled and shippypro_enabled:
                                details_text = f"""
                                **Dettagli:**
                                - 📦 Ordini PrestaShop: {orders_data.get('prestashop_count', 0)}
                                - 🚚 Ordini ShippyPro: {orders_data.get('shippypro_count', 0)}
                                - ✅ Indicizzati: {result.get('indexed', 0)}
                                - ⏭ Saltati (già presenti): {result.get('skipped', 0)}
                                - ❌ Falliti: {result.get('failed', 0)}
                                """
                                
                                # Aggiungi avvisi ordini vecchi se presenti
                                old_warnings = orders_data.get('old_orders_warnings', [])
                                if old_warnings:
                                    details_text += f"\n- ⚠️ Ordini > 6 mesi saltati: {len(old_warnings)}"
                                
                                st.info(details_text)
                                
                                # Mostra avvisi dettagliati per ordini vecchi
                                if old_warnings:
                                    with st.expander(f"⚠️ Avvisi: {len(old_warnings)} ordini > 6 mesi saltati", expanded=False):
                                        st.warning("""
                                        **ATTENZIONE:** Gli ordini più vecchi di 6 mesi non vengono indicizzati automaticamente.
                                        Per informazioni su questi ordini, contattare direttamente l'azienda.
                                        """)
                                        for warning in old_warnings[:10]:  # Mostra max 10
                                            st.caption(f"• {warning.get('message', 'Ordine vecchio')}")
                                        if len(old_warnings) > 10:
                                            st.caption(f"... e altri {len(old_warnings) - 10} ordini")
                            
                            st.session_state.indexing_in_progress = False
                    
                    except Exception as e:
                        progress_bar.progress(0)
                        status_text.error("❌ Errore durante l'indicizzazione")
                        info_box.error(f"❌ Errore: {str(e)}")
                        log_placeholder.error(f"Errore: {str(e)}")
                        import traceback
                        with st.expander("🔍 Dettagli Errore"):
                            st.code(traceback.format_exc())
                        st.session_state.indexing_in_progress = False
    
    # Sezione reset database
    st.markdown("---")
    st.markdown("### ⚠️ Reset Database")
    
    # Mostra statistiche attuali
    current_stats = get_db_stats()
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.warning(f"""
        ⚠️ **ATTENZIONE: Reset Completo del Database**
        
        Questa azione **cancellerà PERMANENTEMENTE**:
        - 📄 **{current_stats['total_documents']} documenti** indicizzati
        - 🧩 **{current_stats['total_chunks']} chunk** di testo
        - 💾 Tutti i dati nel database vettoriale ({VECTOR_DB.upper()})
        
        **Questa azione è IRREVERSIBILE!** Dovrai re-indicizzare tutti i documenti.
        """)
    with col2:
        if st.button("🗑️ Reset Database", type="secondary", use_container_width=True):
            st.session_state.reset_confirm = True
    
    # Conferma reset
    if st.session_state.get('reset_confirm', False):
        st.error("⚠️ **ULTIMA CONFERMA RICHIESTA**")
        confirm_text = st.text_input(
            "Digita 'CONFERMO' per procedere con la cancellazione:",
            placeholder="CONFERMO",
            help="Devi digitare esattamente 'CONFERMO' per procedere"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Conferma Reset", type="primary"):
                if confirm_text == "CONFERMO":
                    try:
                        with st.spinner("🗑️ Cancellazione database in corso..."):
                            reset_database()
                        st.success("✅ Database resettato con successo!")
                        st.info("💡 Tutti i documenti sono stati cancellati. Puoi ora indicizzare nuovi documenti.")
                        st.session_state.reset_confirm = False
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Errore durante il reset: {str(e)}")
                        st.session_state.reset_confirm = False
                else:
                    st.warning("⚠️ Devi digitare esattamente 'CONFERMO' per procedere")
        
        with col2:
            if st.button("❌ Annulla", type="secondary"):
                st.session_state.reset_confirm = False
                st.rerun()

# ============================================================
# PAGINA: CHAT RAG
# ============================================================

elif page == "💬 Chat RAG":
    st.markdown("# 💬 Chat RAG Conversazionale")
    
    # Selezione provider LLM
    providers = get_available_providers()
    
    if not providers:
        st.error("❌ Nessun provider LLM configurato. Configura almeno una chiave API nel file .env")
        st.stop()
    
    # Selettore modello direttamente nella chat (più visibile)
    st.markdown("### 🤖 Seleziona Modello LLM")
    
    # Prepara le opzioni per il selectbox
    provider_options = [f"{name} ({model})" for name, model, _ in providers]
    selected_idx = 0
    for i, (_, _, code) in enumerate(providers):
        if code == st.session_state.selected_provider:
            selected_idx = i
            break
    
    # Selectbox per selezionare il modello
    col1, col2 = st.columns([3, 1])
    with col1:
        selected_provider_display = st.selectbox(
            "Scegli quale modello LLM usare per le risposte:",
            provider_options,
            index=selected_idx,
            label_visibility="visible",
            key="model_selector_chat"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Spazio per allineare
        if st.button("🔄 Aggiorna", key="refresh_model_selector"):
            st.rerun()
    
    # Estrai il codice provider selezionato
    selected_idx = provider_options.index(selected_provider_display)
    st.session_state.selected_provider = providers[selected_idx][2]
    
    # Mostra info sul modello selezionato
    selected_name, selected_model, _ = providers[selected_idx]
    st.info(f"📌 **Modello attivo:** {selected_name} ({selected_model})")
    
    # Opzione ricerca web
    col_web1, col_web2 = st.columns([3, 1])
    with col_web1:
        use_web_search = st.checkbox(
            "🌐 Integra ricerca web nelle risposte (opzionale)",
            value=st.session_state.get("use_web_search", False),
            help="Se attivato, il sistema cercherà informazioni sul web e le integrerà con i documenti indicizzati. La ricerca web viene eseguita DOPO la ricerca nei documenti e integra i risultati.",
            key="web_search_checkbox"
        )
        st.session_state.use_web_search = use_web_search
    
    with col_web2:
        st.caption("💡 La ricerca web integra informazioni aggiuntive dal web quando disponibili")
    
    # Opzione ragionamento di profondità (considerazione originale in fondo alla risposta)
    use_depth_reasoning = st.checkbox(
        "🧠 Ragionamento di profondità (aggiunta in fondo)",
        value=st.session_state.get("use_depth_reasoning", False),
        help="Se attivato, alla risposta basata sui documenti viene aggiunta in fondo una considerazione di approfondimento (ragionamento esteso). Utile per avere un confronto con una riflessione aggiuntiva.",
        key="depth_reasoning_checkbox"
    )
    st.session_state.use_depth_reasoning = use_depth_reasoning
    st.caption("💡 Il ragionamento di profondità appare in fondo alla risposta come «Aggiunta».")
    
    st.divider()
    
    # Sidebar per selezione provider (mantenuta per compatibilità)
    with st.sidebar:
        st.markdown("### Seleziona LLM (Sidebar)")
        st.caption("Puoi anche selezionare il modello nella chat principale sopra")
        provider_options_sidebar = [f"{name} ({model})" for name, model, _ in providers]
        selected_idx_sidebar = 0
        for i, (_, _, code) in enumerate(providers):
            if code == st.session_state.selected_provider:
                selected_idx_sidebar = i
                break
        
        selected_provider_display_sidebar = st.selectbox(
            "Provider",
            provider_options_sidebar,
            index=selected_idx_sidebar,
            key="model_selector_sidebar"
        )
        
        # Estrai il codice provider dalla sidebar
        selected_idx_sidebar = provider_options_sidebar.index(selected_provider_display_sidebar)
        st.session_state.selected_provider = providers[selected_idx_sidebar][2]
    
    # Mostra storia chat
    if not st.session_state.chat_history:
        st.info("👋 Ciao! Fai una domanda sui tuoi documenti indicizzati per iniziare la conversazione.")
    
    # Mostra messaggi esistenti
    for msg_idx, message in enumerate(st.session_state.chat_history):
        if message["role"] == "user":
            with st.chat_message("user"):
                st.write(message["content"])
        else:
            with st.chat_message("assistant"):
                st.write(message["content"])
                if "sources" in message and message["sources"]:
                    with st.expander("📥 Riferimenti documenti da scaricare"):
                        for idx, source in enumerate(message["sources"]):
                            if not source:
                                continue
                            is_url = source.strip().lower().startswith(("http://", "https://"))
                            label = source.split("/")[-1].split("\\")[-1] if not is_url else (source[:80] + "..." if len(source) > 80 else source)
                            if is_url:
                                st.markdown(f"• **{label}** — [Apri link]({source})")
                            else:
                                short = _short_path_for_display(source)
                                file_info = _get_file_for_download(source)
                                if file_info:
                                    data, name, mime = file_info
                                    st.download_button(
                                        f"📄 {short}",
                                        data=data,
                                        file_name=name,
                                        mime=mime,
                                        key=f"dl_hist_{msg_idx}_{idx}_{hash(source) % 10**8}"
                                    )
                                else:
                                    st.caption(f"• {short}")
                                    st.caption("(file non disponibile)")
    
    # Input utente
    user_input = st.chat_input("Fai una domanda sui tuoi documenti...")
    
    if user_input:
        # Aggiungi messaggio utente
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        
        # Mostra messaggio utente
        with st.chat_message("user"):
            st.write(user_input)
        
        # Genera risposta
        with st.chat_message("assistant"):
            use_web = st.session_state.get("use_web_search", False)
            spinner_text = "🤔 Cerco nei documenti e genero la risposta..."
            if use_web:
                spinner_text = "🤔 Cerco nei documenti, sul web e genero la risposta..."
            
            use_depth = st.session_state.get("use_depth_reasoning", False)
            if use_depth:
                spinner_text = spinner_text.replace("...", "") + " e ragionamento di profondità..."
            with st.spinner(spinner_text):
                try:
                    # Recupera documenti rilevanti
                    docs = retrieve_relevant_docs(user_input)
                    
                    # Debug: mostra quanti documenti sono stati recuperati
                    if not docs or len(docs) == 0:
                        st.warning("⚠️ Nessun documento rilevante trovato. Verifica che i documenti siano stati indicizzati correttamente.")
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": "⚠️ Nessun documento rilevante trovato nell'indice. Assicurati di aver indicizzato i documenti correttamente.",
                            "sources": []
                        })
                    else:
                        # Genera risposta (con ricerca web e/o ragionamento di profondità opzionali)
                        answer = rag_query(
                            user_input, 
                            provider_override=st.session_state.selected_provider,
                            use_web_search=use_web,
                            use_depth_reasoning=use_depth
                        )
                        
                        # Verifica che la risposta non sia vuota
                        if not answer or answer.strip() == "":
                            st.error("❌ La risposta generata è vuota. Potrebbe esserci un problema con il provider LLM o la configurazione.")
                            error_msg = "❌ Errore: La risposta generata è vuota. Verifica la configurazione del provider LLM."
                            _refs = list(dict.fromkeys([d.get("source", "") for d in docs if d.get("source")])) if docs else []
                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "content": error_msg,
                                "sources": _refs
                            })
                        else:
                            # Mostra la risposta
                            st.write(answer)
                            
                            # Riferimenti documenti da scaricare (elenco univoco, con link o pulsante Scarica)
                            if docs:
                                unique_sources = list(dict.fromkeys([d.get("source", "") for d in docs if d.get("source")]))
                                with st.expander("📥 Riferimenti documenti da scaricare", expanded=True):
                                    st.caption("Scarica il documento o apri il link. Per file locali usa il pulsante Scarica.")
                                    for i, source in enumerate(unique_sources):
                                        if not source:
                                            continue
                                        is_url = source.strip().lower().startswith(("http://", "https://"))
                                        label = source.split("/")[-1].split("\\")[-1] if not is_url else source[:80] + ("..." if len(source) > 80 else "")
                                        if is_url:
                                            st.markdown(f"• **{label}** — [Apri link]({source})")
                                        else:
                                            short = _short_path_for_display(source)
                                            file_info = _get_file_for_download(source)
                                            if file_info:
                                                data, name, mime = file_info
                                                st.download_button(
                                                    f"📄 {short}",
                                                    data=data,
                                                    file_name=name,
                                                    mime=mime,
                                                    key=f"dl_ref_{i}_{hash(source) % 10**8}"
                                                )
                                            else:
                                                st.caption(f"• {short}")
                                                st.caption("(file non disponibile per download)")
                            
                            # Salva nella storia (tutti i riferimenti univoci)
                            unique_sources = list(dict.fromkeys([d.get("source", "") for d in docs if d.get("source")])) if docs else []
                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "content": answer,
                                "sources": unique_sources
                            })
                    
                except Exception as e:
                    import traceback
                    error_msg = f"❌ Errore: {str(e)}"
                    st.error(error_msg)
                    # Mostra dettagli dell'errore in modalità debug
                    with st.expander("🔍 Dettagli errore (debug)"):
                        st.code(traceback.format_exc())
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": error_msg
                    })
        
        st.rerun()
    
    # Pulsante per pulire chat
    if st.session_state.chat_history:
        if st.button("🗑️ Pulisci Chat"):
            st.session_state.chat_history = []
            st.rerun()

# ============================================================
# PAGINA: CONFRONTO MODELLI
# ============================================================

elif page == "🔍 Ricerca Cliente":
    st.markdown("# 🔍 Ricerca Ordine Cliente")
    st.markdown("### Verifica i dettagli del tuo ordine inserendo le informazioni richieste")
    
    st.info("""
    **🔒 Ricerca Sicura per Clienti**
    
    Per proteggere la privacy, è necessario verificare la tua identità prima di visualizzare i dettagli dell'ordine.
    Inserisci tutte le informazioni richieste per accedere ai dettagli del tuo ordine.
    """)
    
    st.divider()
    
    # Form per ricerca cliente
    with st.form("customer_search_form", clear_on_submit=False):
        st.markdown("### 📋 Informazioni Ordine")
        
        col1, col2 = st.columns(2)
        
        with col1:
            order_number = st.text_input(
                "🔢 Numero Ordine *",
                placeholder="Es: 53515",
                help="Inserisci il numero dell'ordine che vuoi consultare"
            )
        
        with col2:
            order_reference = st.text_input(
                "📝 Riferimento Ordine (opzionale)",
                placeholder="Es: VZEKDZDHM",
                help="Riferimento dell'ordine se disponibile"
            )
        
        st.markdown("### 👤 Dati Cliente")
        
        col3, col4 = st.columns(2)
        
        with col3:
            customer_firstname = st.text_input(
                "Nome *",
                placeholder="Es: Michele",
                help="Inserisci il tuo nome"
            )
        
        with col4:
            customer_lastname = st.text_input(
                "Cognome *",
                placeholder="Es: Bassi",
                help="Inserisci il tuo cognome"
            )
        
        col5, col6 = st.columns(2)
        
        with col5:
            postal_code = st.text_input(
                "📮 CAP (Codice Postale) *",
                placeholder="Es: 20100",
                help="Inserisci il CAP dell'indirizzo di spedizione"
            )
        
        with col6:
            customer_email = st.text_input(
                "📧 Email (opzionale)",
                placeholder="Es: michele@example.com",
                help="Email utilizzata per l'ordine (opzionale, per verifica aggiuntiva)"
            )
        
        st.markdown("---")
        
        search_button = st.form_submit_button(
            "🔍 Cerca Ordine",
            type="primary",
            use_container_width=True
        )
    
    # Processa ricerca
    if search_button:
        # Validazione input
        if not order_number or not order_number.strip():
            st.error("❌ **Errore:** Il numero ordine è obbligatorio")
        elif not customer_firstname or not customer_firstname.strip():
            st.error("❌ **Errore:** Il nome è obbligatorio")
        elif not customer_lastname or not customer_lastname.strip():
            st.error("❌ **Errore:** Il cognome è obbligatorio")
        elif not postal_code or not postal_code.strip():
            st.error("❌ **Errore:** Il CAP è obbligatorio")
        else:
            # Cerca ordine
            with st.spinner("🔍 Verifica in corso..."):
                try:
                    # Importa client PrestaShop
                    import sys
                    import os
                    root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    sys.path.insert(0, root_path)
                    
                    from prestashop_client import PrestaShopClient
                    from config import BASE_URL, API_KEY
                    
                    client = PrestaShopClient(BASE_URL, API_KEY)
                    
                    # Cerca ordine per ID
                    try:
                        order_id = int(order_number.strip())
                        order_response = client.get_order(order_id)
                        
                        if not order_response or 'order' not in order_response:
                            st.error(f"❌ **Ordine non trovato:** L'ordine #{order_number} non esiste nel sistema.")
                        else:
                            order = order_response['order']
                            
                            # SICUREZZA: Estrai SOLO i dati già presenti nell'ordine per la verifica iniziale
                            # NON recuperare dati aggiuntivi tramite API prima della verifica
                            
                            # Prova prima da customer object (se presente nell'ordine)
                            customer_obj = order.get('customer', {})
                            order_firstname = ''
                            order_lastname = ''
                            order_email = ''
                            
                            if isinstance(customer_obj, dict) and customer_obj.get('firstname'):
                                order_firstname = customer_obj.get('firstname', '').strip().lower()
                                order_lastname = customer_obj.get('lastname', '').strip().lower()
                                order_email = customer_obj.get('email', '').strip().lower()
                            
                            # CAP e nome/cognome dall'indirizzo di consegna (se presente nell'ordine)
                            delivery_address = order.get('delivery_address', {})
                            order_postal_code = ''
                            delivery_firstname = ''
                            delivery_lastname = ''
                            
                            if isinstance(delivery_address, dict):
                                order_postal_code = delivery_address.get('postcode', '').strip()
                                delivery_firstname = delivery_address.get('firstname', '').strip().lower()
                                delivery_lastname = delivery_address.get('lastname', '').strip().lower()
                                
                                # Se non abbiamo nome/cognome da customer, usali dall'indirizzo
                                if not order_firstname and delivery_firstname:
                                    order_firstname = delivery_firstname
                                if not order_lastname and delivery_lastname:
                                    order_lastname = delivery_lastname
                            
                            # Riferimento ordine (sempre presente)
                            order_reference_actual = order.get('reference', '').strip()
                            
                            # Preparazione dati input per verifica
                            input_firstname = customer_firstname.strip().lower()
                            input_lastname = customer_lastname.strip().lower()
                            input_postal_code = postal_code.strip()
                            input_reference = order_reference.strip().upper() if order_reference else None
                            
                            # 🔒 VERIFICA INIZIALE: usa solo dati già presenti nell'ordine
                            # Se mancano dati, recuperali SOLO per verificare (non per esporre)
                            
                            # Se manca il CAP, recuperalo SOLO per verificare (non esporre)
                            if not order_postal_code:
                                address_id = order.get('id_address_delivery', '')
                                if address_id:
                                    try:
                                        address_response = client.get(f'addresses/{address_id}')
                                        if 'address' in address_response:
                                            address = address_response['address']
                                            retrieved_postcode = address.get('postcode', '').strip()
                                            # Usa il CAP recuperato SOLO per verifica
                                            if retrieved_postcode == input_postal_code:
                                                order_postal_code = retrieved_postcode
                                                # Recupera anche nome/cognome se mancanti
                                                if not order_firstname:
                                                    order_firstname = address.get('firstname', '').strip().lower()
                                                if not order_lastname:
                                                    order_lastname = address.get('lastname', '').strip().lower()
                                    except:
                                        pass
                            
                            # Se ancora mancano nome/cognome, recuperali SOLO se il CAP corrisponde
                            if (not order_firstname or not order_lastname) and order_postal_code == input_postal_code:
                                customer_id = order.get('id_customer', '')
                                if customer_id:
                                    try:
                                        customer_response = client.get_customer(int(customer_id))
                                        if 'customer' in customer_response:
                                            customer = customer_response['customer']
                                            retrieved_firstname = customer.get('firstname', '').strip().lower()
                                            retrieved_lastname = customer.get('lastname', '').strip().lower()
                                            
                                            # Verifica che corrispondano PRIMA di usarli
                                            if retrieved_firstname == input_firstname and retrieved_lastname == input_lastname:
                                                order_firstname = retrieved_firstname
                                                order_lastname = retrieved_lastname
                                                order_email = customer.get('email', '').strip().lower()
                                    except:
                                        pass
                            
                            # Verifica corrispondenza
                            name_match = (order_firstname == input_firstname and order_lastname == input_lastname)
                            postal_match = (order_postal_code == input_postal_code)
                            reference_match = True  # Se non fornito, non verifica
                            if input_reference:
                                reference_match = (order_reference_actual.upper() == input_reference)
                            
                            # Verifica email se fornita (opzionale)
                            email_match = True
                            if customer_email and customer_email.strip():
                                input_email = customer_email.strip().lower()
                                email_match = (order_email == input_email)
                            
                            # 🔒 Verifica completa - SOLO se tutti i dati corrispondono
                            if name_match and postal_match and reference_match and email_match:
                                # ✅ Verifica completata - mostra dettagli ordine
                                st.success("✅ **Verifica completata!** I dati corrispondono. Ecco i dettagli del tuo ordine:")
                                
                                st.markdown("---")
                                
                                # Mostra dettagli ordine
                                col_info1, col_info2 = st.columns(2)
                                
                                with col_info1:
                                    st.markdown("### 📦 Informazioni Ordine")
                                    st.markdown(f"**🔢 Numero Ordine:** #{order.get('id', 'N/A')}")
                                    st.markdown(f"**📝 Riferimento:** {order_reference_actual}")
                                    st.markdown(f"**📅 Data Ordine:** {order.get('date_add', 'N/A')}")
                                    st.markdown(f"**💰 Totale:** {order.get('total_paid', '0')} {order.get('currency', {}).get('iso_code', 'EUR') if isinstance(order.get('currency'), dict) else 'EUR'}")
                                    st.markdown(f"**💳 Metodo Pagamento:** {order.get('payment', 'N/A')}")
                                    st.markdown(f"**📊 Stato:** {order.get('current_state', 'N/A')}")
                                
                                with col_info2:
                                    st.markdown("### 👤 Informazioni Cliente")
                                    if order_firstname and order_lastname:
                                        st.markdown(f"**Nome:** {order_firstname.title()} {order_lastname.title()}")
                                    if order_email:
                                        st.markdown(f"**Email:** {order_email}")
                                    
                                    st.markdown("### 📍 Indirizzo Spedizione")
                                    if isinstance(full_address, dict):
                                        st.markdown(f"**Indirizzo:** {full_address.get('address1', 'N/A')}")
                                        if full_address.get('address2'):
                                            st.markdown(f"**Indirizzo 2:** {full_address.get('address2')}")
                                        st.markdown(f"**Città:** {full_address.get('city', 'N/A')}")
                                        st.markdown(f"**CAP:** {full_address.get('postcode', 'N/A')}")
                                        st.markdown(f"**Paese:** {full_address.get('country', 'N/A')}")
                                    else:
                                        st.markdown("Indirizzo non disponibile")
                                
                                # Prodotti ordinati
                                st.markdown("---")
                                st.markdown("### 🛒 Prodotti Ordinati")
                                
                                associations = order.get('associations', {})
                                order_rows = []
                                if isinstance(associations, dict):
                                    order_rows_data = associations.get('order_rows', [])
                                    if isinstance(order_rows_data, dict):
                                        if 'order_row' in order_rows_data:
                                            order_rows = order_rows_data['order_row'] if isinstance(order_rows_data['order_row'], list) else [order_rows_data['order_row']]
                                        else:
                                            order_rows = list(order_rows_data.values()) if order_rows_data else []
                                    elif isinstance(order_rows_data, list):
                                        order_rows = order_rows_data
                                
                                if order_rows:
                                    products_df_data = []
                                    for row in order_rows:
                                        if isinstance(row, dict):
                                            products_df_data.append({
                                                'Prodotto': row.get('product_name', 'N/A'),
                                                'Riferimento': row.get('product_reference', 'N/A'),
                                                'Quantità': row.get('product_quantity', '0'),
                                                'Prezzo Unitario': f"{row.get('unit_price_tax_incl', '0')} €",
                                                'Totale': f"{float(row.get('unit_price_tax_incl', '0')) * int(row.get('product_quantity', '0')):.2f} €"
                                            })
                                    
                                    if products_df_data:
                                        products_df = pd.DataFrame(products_df_data)
                                        st.dataframe(products_df, use_container_width=True, hide_index=True)
                                else:
                                    st.info("Nessun prodotto trovato per questo ordine.")
                                
                                # Tracking/spedizione se disponibile
                                shipping_number = order.get('shipping_number', '')
                                if shipping_number:
                                    st.markdown("---")
                                    st.markdown("### 🚚 Informazioni Spedizione")
                                    st.markdown(f"**Numero Spedizione:** {shipping_number}")
                                
                            else:
                                # ❌ Verifica fallita
                                st.error("❌ **Verifica fallita:** I dati inseriti non corrispondono all'ordine.")
                                st.warning("""
                                **Possibili cause:**
                                - Numero ordine errato
                                - Nome o cognome non corrispondenti
                                - CAP non corrispondente
                                - Riferimento ordine errato (se fornito)
                                
                                Verifica di aver inserito correttamente tutti i dati e riprova.
                                """)
                                
                                # Mostra cosa non corrisponde (per debug, opzionale)
                                with st.expander("🔍 Dettagli verifica (per assistenza)"):
                                    st.markdown(f"**Nome:** {'✅' if name_match else '❌'} (Ordine: {order_firstname.title()} {order_lastname.title()}, Inserito: {input_firstname.title()} {input_lastname.title()})")
                                    st.markdown(f"**CAP:** {'✅' if postal_match else '❌'} (Ordine: {order_postal_code}, Inserito: {input_postal_code})")
                                    if input_reference:
                                        st.markdown(f"**Riferimento:** {'✅' if reference_match else '❌'} (Ordine: {order_reference_actual}, Inserito: {input_reference})")
                                    if customer_email:
                                        st.markdown(f"**Email:** {'✅' if email_match else '❌'} (Ordine: {order_email}, Inserito: {input_email})")
                    
                    except ValueError:
                        st.error(f"❌ **Errore:** Il numero ordine deve essere un numero valido")
                    except Exception as e:
                        st.error(f"❌ **Errore durante la ricerca:** {str(e)}")
                        import traceback
                        with st.expander("🔍 Dettagli errore"):
                            st.code(traceback.format_exc())
                
                except ImportError as e:
                    st.error("❌ **Errore:** Impossibile importare il client PrestaShop. Verifica la configurazione.")
                    st.code(str(e))
                except Exception as e:
                    st.error(f"❌ **Errore generico:** {str(e)}")
                    import traceback
                    with st.expander("🔍 Dettagli errore"):
                        st.code(traceback.format_exc())

elif page == "⚖️ Confronta Modelli":
    st.markdown("# ⚖️ Confronto Modelli LLM")
    
    # Mostra risultati precedenti se esistono
    if 'compare_results' in st.session_state and st.session_state.compare_results:
        st.markdown("### 📊 Risultati Confronto Precedente")
        st.info(f"**Domanda:** {st.session_state.compare_question}")
        st.markdown("---")
    
    question = st.text_input(
        "Domanda da confrontare",
        placeholder="Inserisci una domanda per confrontare le risposte di diversi modelli...",
        help="Tutti i modelli configurati risponderanno a questa domanda usando lo stesso contesto RAG",
        value=st.session_state.get('compare_question', '')
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        compare_button = st.button("▶️ Confronta Modelli", type="primary", use_container_width=True)
    
    if compare_button:
        if question:
            # Salva la domanda
            st.session_state.compare_question = question
            
            # Container per progress
            progress_container = st.container()
            results_container = st.container()
            
            with progress_container:
                st.markdown("### 🔄 Confronto in corso...")
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    # Recupera documenti
                    status_text.info("📄 Recupero documenti rilevanti...")
                    progress_bar.progress(0.1)
                    
                    docs = retrieve_relevant_docs(question)
                    if not docs:
                        st.warning("⚠️ Nessun documento trovato per questa domanda.")
                        st.stop()
                    
                    # Costruisci contesto
                    prompt = build_context(question, docs)
                    
                    status_text.info(f"Contesto preparato con {len(docs)} documenti. Interrogo i modelli...")
                    progress_bar.progress(0.3)
                    
                    # Lista modelli disponibili
                    from rag.model_compare import MODEL_LIST, run_model
                    available_models = {}
                    
                    # Filtra solo modelli con chiavi API configurate
                    for model_name, cfg in MODEL_LIST.items():
                        provider = cfg["provider"]
                        if (provider == "openai" and OPENAI_API_KEY) or \
                           (provider == "anthropic" and ANTHROPIC_API_KEY) or \
                           (provider == "gemini" and GEMINI_API_KEY) or \
                           (provider == "openrouter" and OPENROUTER_API_KEY):
                            available_models[model_name] = cfg
                    
                    if not available_models:
                        st.error("❌ Nessun modello configurato. Configura almeno una chiave API nel file .env")
                        st.stop()
                    
                    # Esegui confronto per ogni modello
                    results = {}
                    total_models = len(available_models)
                    
                    for idx, (model_name, cfg) in enumerate(available_models.items()):
                        status_text.info(f"Interrogo {model_name}... ({idx + 1}/{total_models})")
                        progress = 0.3 + (idx + 1) / total_models * 0.7
                        progress_bar.progress(progress)
                        
                        answer = run_model(cfg["provider"], cfg["model"], prompt)
                        # Debug: verifica che la risposta non sia vuota
                        if not answer or answer.strip() == "":
                            answer = f"⚠️ Errore: Risposta vuota da {model_name}"
                        results[model_name] = answer
                    
                    # Salva risultati
                    st.session_state.compare_results = results
                    
                    progress_bar.progress(1.0)
                    status_text.success("✅ Confronto completato!")
                    
                    # Salva risultati PRIMA di mostrarli
                    st.session_state.compare_results = results
                    st.session_state.just_generated = True
                    
                    # Mostra risultati DOPO il progress
                    progress_bar.empty()
                    status_text.empty()
                    
                except Exception as e:
                    progress_bar.progress(0)
                    status_text.error(f"❌ Errore durante il confronto")
                    st.error(f"❌ Errore: {str(e)}")
                    import traceback
                    with st.expander("🔍 Dettagli Errore"):
                        st.code(traceback.format_exc())
            
            # Mostra risultati (fuori dal container progress)
            if st.session_state.get('compare_results'):
                st.markdown("---")
                st.markdown("### 📊 Risultati Confronto")
                
                # Mostra domanda
                st.markdown(f"**💬 Domanda:** {question}")
                st.markdown("---")
                
                results = st.session_state.compare_results
                
                # Mostra risposte in tabs o side-by-side
                if len(results) <= 2:
                    # Side-by-side per 2 modelli
                    cols = st.columns(len(results))
                    for idx, (model_name, answer) in enumerate(results.items()):
                        with cols[idx]:
                            st.markdown(f"#### {model_name}")
                            st.markdown("---")
                            # Usa st.write per contenuti che potrebbero avere problemi di formattazione
                            if answer:
                                st.write(answer)
                            else:
                                st.warning("⚠️ Risposta vuota o errore")
                else:
                    # Tabs per più modelli
                    tabs = st.tabs(list(results.keys()))
                    for idx, (model_name, answer) in enumerate(results.items()):
                        with tabs[idx]:
                            st.markdown(f"**Risposta di {model_name}:**")
                            st.markdown("---")
                            # Usa st.write invece di st.markdown per contenuti lunghi
                            if answer and answer.strip():
                                # Mostra la risposta in un container scrollabile
                                with st.container():
                                    st.write(answer)
                                # Debug info (collassabile)
                                with st.expander("🔍 Info Debug"):
                                    st.code(f"Lunghezza: {len(answer)} caratteri\nParole: {len(answer.split())}\nPrimi 100 caratteri: {answer[:100]}")
                            else:
                                st.error(f"⚠️ Risposta vuota o errore per {model_name}")
                                st.code(f"Risposta ricevuta: {repr(answer)}")
                
                # Tabella comparativa compatta
                st.markdown("---")
                st.markdown("### 📋 Tabella Comparativa")
                
                # Crea tabella
                comparison_data = {
                    "Modello": list(results.keys()),
                    "Anteprima Risposta": [answer[:200] + "..." if len(answer) > 200 else answer for answer in results.values()],
                    "Lunghezza (caratteri)": [len(answer) if answer else 0 for answer in results.values()],
                    "Parole": [len(answer.split()) if answer else 0 for answer in results.values()]
                }
                df = pd.DataFrame(comparison_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Metriche
                st.markdown("---")
                st.markdown("### 📈 Metriche")
                metric_cols = st.columns(len(results))
                for idx, (model_name, answer) in enumerate(results.items()):
                    with metric_cols[idx]:
                        if answer:
                            st.metric(
                                model_name.split()[0],  # Nome breve
                                f"{len(answer)} caratteri",
                                f"{len(answer.split())} parole"
                            )
                        else:
                            st.metric(model_name.split()[0], "0 caratteri", "Errore")
        else:
            st.warning("⚠️ Inserisci una domanda per confrontare i modelli")
    
    # Mostra risultati salvati se esistono e non c'è una nuova ricerca in corso
    if 'compare_results' in st.session_state and st.session_state.compare_results and not compare_button:
        # Evita di mostrare due volte se sono appena stati generati
        if not st.session_state.get('just_generated', False):
            st.markdown("---")
            st.markdown("### 📊 Risultati Confronto Precedente")
            st.markdown(f"**💬 Domanda:** {st.session_state.compare_question}")
            st.markdown("---")
            
            results = st.session_state.compare_results
            
            if len(results) <= 2:
                cols = st.columns(len(results))
                for idx, (model_name, answer) in enumerate(results.items()):
                    with cols[idx]:
                        st.markdown(f"#### {model_name}")
                        st.markdown("---")
                        if answer:
                            st.write(answer)
                        else:
                            st.warning("⚠️ Risposta vuota")
            else:
                tabs = st.tabs(list(results.keys()))
                for idx, (model_name, answer) in enumerate(results.items()):
                    with tabs[idx]:
                        st.markdown(f"**Risposta di {model_name}:**")
                        st.markdown("---")
                        if answer:
                            st.write(answer)
                        else:
                            st.warning("⚠️ Risposta vuota")
            
            # Pulsante per pulire risultati
            if st.button("🗑️ Pulisci Risultati"):
                st.session_state.compare_results = None
                st.session_state.compare_question = None
                st.session_state.just_generated = False
                st.rerun()
        else:
            # Reset flag dopo aver mostrato
            st.session_state.just_generated = False

# ============================================================
# PAGINA: CONFIGURAZIONE
# ============================================================

elif page == "⚙️ Configurazione":
    st.markdown("# ⚙️ Configurazione Sistema")
    
    # Informazioni database
    st.markdown("## 🗄️ Database Vettoriale")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"**Tipo:** {VECTOR_DB.upper()}")
        if VECTOR_DB == "chromadb":
            st.info(f"**Path:** {CHROMA_DB_PATH}")
        else:
            st.info(f"**Host:** {QDRANT_HOST}:{QDRANT_PORT}")
            st.info(f"**Collection:** {QDRANT_COLLECTION_NAME}")
    
    with col2:
        stats = get_db_stats()
        st.metric("Documenti", stats["total_documents"])
        st.metric("Chunk", stats["total_chunks"])
        st.metric("Dimensione", stats["db_size"])
    
    # Provider LLM
    st.markdown("## Provider LLM")
    
    providers = get_available_providers()
    
    if providers:
        for name, model, code in providers:
            status = "✅ Configurato" if True else "❌ Non configurato"
            st.success(f"**{name}** ({model}): {status}")
    else:
        st.warning("⚠️ Nessun provider LLM configurato")
    
    # Chiavi API
    st.markdown("## 🔑 Chiavi API")
    
    api_keys = {
        "OpenAI": OPENAI_API_KEY,
        "Anthropic": ANTHROPIC_API_KEY,
        "Gemini": GEMINI_API_KEY,
        "OpenRouter": OPENROUTER_API_KEY
    }
    
    for name, key in api_keys.items():
        if key:
            # Mostra solo i primi e ultimi caratteri per sicurezza
            masked_key = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "***"
            st.success(f"**{name}:** ✅ {masked_key}")
        else:
            st.error(f"**{name}:** ❌ Non configurata")
    
    # Performance
    st.markdown("## ⚡ Performance")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Parallel Workers", PARALLEL_WORKERS)
        st.caption("Numero di file processati in parallelo")
    
    with col2:
        st.metric("Batch Size", CHUNK_BATCH_SIZE)
        st.caption("Chunk processati insieme per batch")
    
    # Parametri di ricerca e contesto (solo lettura, per spiegazione)
    st.markdown("---")
    st.markdown("## 🔍 Parametri di ricerca e contesto")
    st.caption("Questi parametri influenzano come vengono cercati e scelti i documenti per rispondere alle domande. I valori mostrati sono quelli attualmente in uso (solo lettura).")
    
    r1, r2 = st.columns(2)
    
    with r1:
        with st.container():
            st.markdown("#### 📌 Termini aggiuntivi di ricerca")
            st.caption("Sinonimi o parole correlate che il sistema può includere nella ricerca per allargare i risultati (es. *long seal*, *bushing* per domande sulla boccola).")
            st.markdown("**Valore attuale:** *Non impostato — usa regole interne*")
        
        st.markdown("")
        
        with st.container():
            st.markdown("#### 📄 Documento / paragrafo preferito")
            st.caption("SOP o Mod da privilegiare per certi tipi di domanda, con eventuale paragrafo (es. *SOP-518 § 5.2.3 Long Seals*).")
            st.markdown("**Valore attuale:** *Non impostato — usa regole interne*")
    
    with r2:
        with st.container():
            st.markdown("#### 🔢 Documenti massimi da considerare")
            st.caption("Quanti documenti (chunk) recuperare dalla ricerca vettoriale per costruire il contesto della risposta. Più documenti = più contesto, ma risposta più lenta.")
            st.markdown(f"**Valore attuale:** `{TOP_K}`")
        
        st.markdown("")
        
        with st.container():
            st.markdown("#### 🌐 Espansione ricerca")
            st.caption("Se attiva, per alcune domande (es. analisi laterale + boccola) il sistema lancia anche una ricerca aggiuntiva mirata per includere documenti rilevanti (es. SOP-518 Long Seals).")
            st.markdown("**Valore attuale:** *Attiva — regole interne*")
    
    with st.expander("📋 Dettaglio regole interne (cosa fa il sistema oggi)"):
        st.markdown("""
**📌 Termini aggiuntivi di ricerca**  
- Non ci sono termini aggiuntivi impostabili dall’utente.  
- Il sistema, per **espansione ricerca** (vedi sotto), usa in automatico una query aggiuntiva con termini fissi quando riconosce certi tipi di domanda.

**📄 Documento / paragrafo preferito**  
- Per domande su **analisi laterale** e **posizionamento stazioni** in presenza di **boccola, bushing, long seal, wear ring**, il prompt istruisce il modello a:  
  - cercare nel contesto **SOP-518** e la sezione **§ 5.2.3 Long Seals**;  
  - basare la risposta su quella sezione e citarla in «Riferimenti documenti da scaricare»;  
  - se SOP-518 non è nei documenti recuperati, indicare comunque all’utente di consultare **SOP-518 § 5.2.3 Long Seals** per le regole sulle stazioni.

**🔢 Documenti massimi da considerare**  
- Valore letto da configurazione: **TOP_K** (es. 8).  
- È il numero massimo di chunk recuperati dalla ricerca vettoriale per costruire il contesto di ogni risposta.

**🌐 Espansione ricerca**  
- **Condizione:** la domanda contiene *analisi laterale* (o *lateral analysis*) **e** almeno uno tra: *boccola*, *stazioni*, *bending*, *long seal*, *wear ring*, *bushing*, *posizione*.  
- **Azione:** oltre alla ricerca normale, il sistema esegue una **seconda ricerca vettoriale** con la query:  
  *«SOP-518 Long Seals 5.2.3 stazioni posizionamento analisi laterale damped natural frequency boccola bushing»*.  
- I documenti trovati con questa seconda ricerca vengono aggiunti in cima alla lista (senza duplicati), così il modello vede prima il contesto su Long Seals / SOP-518.
        """)
    
    st.markdown("---")
    st.info("💡 Per modificare la configurazione, edita il file `.env` nella root del progetto e riavvia l'applicazione.")

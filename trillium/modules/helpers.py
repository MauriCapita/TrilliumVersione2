"""
Trillium RAG - Helper Functions
Funzioni condivise tra le pagine dell'applicazione.
"""

import os
from pathlib import Path
import streamlit as st

from rag.indexer import get_chroma, get_vector_db
from config import (
    PROVIDER, VECTOR_DB, CHROMA_DB_PATH,
    OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY,
    QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION_NAME,
    PARALLEL_WORKERS, CHUNK_BATCH_SIZE,
    TOP_K,
)

# Base path consentiti per il download (progetto Trillium e parent)
_TRILLIUM_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
_ALLOWED_DOWNLOAD_ROOTS = (_TRILLIUM_ROOT, os.path.abspath(os.path.join(_TRILLIUM_ROOT, os.pardir)))


def short_path_for_display(file_path: str, max_segments: int = 4) -> str:
    """Restituisce solo le ultime max_segments parti del percorso (es. ultime 3 cartelle + file)."""
    parts = Path(file_path).parts
    if len(parts) <= max_segments:
        return file_path.replace("\\", "/")
    return "…/" + "/".join(parts[-max_segments:])


def get_file_for_download(file_path: str):
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


def extract_doc_identifier(source_path: str) -> str:
    """
    Estrae un identificativo breve dal path del documento.
    Es: 'SOP-518 Rev.0 - ENG - ...pdf' → 'SOP-518'
        'Mod.497 - Bolts...xlsx' → 'Mod.497'
        'API 610.pdf' → 'API 610'
        Altrimenti restituisce il nome file.
    """
    import re
    basename = os.path.basename(source_path)

    # Cerca SOP-xxx
    match = re.search(r"(SOP[-\s]?\d{3,4})", basename, re.IGNORECASE)
    if match:
        return match.group(1).replace(" ", "-").upper()

    # Cerca Mod.xxx
    match = re.search(r"(Mod\.?\s?\d{3,4})", basename, re.IGNORECASE)
    if match:
        return match.group(1).replace(" ", "")

    # Cerca API/ASME/ISO standard
    match = re.search(r"((?:API|ASME|ISO)\s*\d+)", basename, re.IGNORECASE)
    if match:
        return match.group(1)

    # Fallback: nome file senza estensione, troncato
    name = os.path.splitext(basename)[0]
    if len(name) > 40:
        return name[:40] + "…"
    return name


@st.cache_data(ttl=60)
def get_db_stats():
    """Ottiene statistiche del database (cachato 60s per evitare scroll costosi ad ogni rerun)."""
    try:
        if VECTOR_DB == "qdrant":
            from qdrant_client import QdrantClient
            client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

            # La collection potrebbe non esistere ancora (database nuovo)
            try:
                collection_info = client.get_collection(QDRANT_COLLECTION_NAME)
                points_count = collection_info.points_count
            except Exception:
                return {
                    "total_documents": 0,
                    "total_chunks": 0,
                    "files_read": 0,
                    "files_failed": 0,
                    "db_size": "N/A (Qdrant)",
                    "status": "✓ Pronto (vuoto)"
                }

            # Conta file unici con scroll limitato (1000 punti invece di 100.000)
            # Sufficiente per avere una stima accurata dei file indicizzati
            points, _ = client.scroll(
                collection_name=QDRANT_COLLECTION_NAME,
                limit=1000,
                with_payload=["source"],  # scarica solo il campo source
                with_vectors=False,       # non scaricare i vettori (enorme risparmio)
            )
            unique_files = set()
            for point in points:
                payload = point.payload if point.payload else {}
                source = payload.get("source", "")
                if source:
                    file_key = source.split("/")[-1] if "/" in source else source
                    unique_files.add(file_key)

            return {
                "total_documents": points_count,
                "total_chunks": points_count,
                "files_read": len(unique_files),
                "files_failed": 0,
                "db_size": "N/A (Qdrant)",
                "status": "✓ Connesso"
            }
        else:
            # ChromaDB
            collection = get_chroma()
            count = collection.count()
            db_path = Path(CHROMA_DB_PATH)
            db_size = sum(f.stat().st_size for f in db_path.rglob('*') if f.is_file()) / (1024**3)

            all_data = collection.get()
            unique_files = set()
            if all_data and "metadatas" in all_data:
                for metadata in all_data["metadatas"]:
                    if metadata and "source" in metadata:
                        source = metadata["source"]
                        file_key = source.split("/")[-1] if "/" in source else source
                        unique_files.add(file_key)

            return {
                "total_documents": count,
                "total_chunks": count,
                "files_read": len(unique_files),
                "files_failed": 0,
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


@st.cache_data(ttl=60)
def get_document_distribution():
    """Estrae la distribuzione reale dei tipi di documento dal database (cachato 60s)."""
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
            try:
                client, collection_name = get_qdrant_collection()
                # Scroll limitato a 2000 punti (campione statisticamente sufficiente)
                # con solo il campo source e senza vettori per massima velocità
                points, _ = client.scroll(
                    collection_name=collection_name,
                    limit=2000,
                    with_payload=["source"],
                    with_vectors=False,
                )
            except Exception:
                return file_types
            
            seen_files = set()
            for point in points:
                payload = point.payload if point.payload else {}
                source = payload.get("source", "")
                if source:
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
            collection = get_chroma()
            all_data = collection.get()
            
            if all_data and "metadatas" in all_data:
                seen_files = set()
                for metadata in all_data["metadatas"]:
                    if metadata and "source" in metadata:
                        source = metadata["source"]
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
        return {"PDF": 0, "Word": 0, "Excel": 0, "Immagini": 0, "Altri": 0}

import os
import re
import sys
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from openai import OpenAI
from typing import List, Dict, Generator, Tuple
import threading
import atexit
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore
from config import (
    PROVIDER,
    CHROMA_DB_PATH,
    EMBEDDING_MODEL_OPENAI,
    EMBEDDING_MODEL_OPENROUTER,
    OPENAI_API_KEY,
    OPENROUTER_API_KEY,
    MAX_EMBEDDING_CHARS,
    USE_RAM_MODE,
    RAM_SAVE_INTERVAL,
    VECTOR_DB,
    PARALLEL_WORKERS,
    CHUNK_BATCH_SIZE,
)
from rag.extractor import extract_text, get_image_extraction_stats, clear_image_extraction_stats
from rag.enrich_document import enrich_fast, metadata_for_qdrant
from rich import print
from tqdm import tqdm

# Variabili globali per gestione RAM/Disk
_ram_collection = None
_disk_collection = None
_save_timer = None


# ============================================================
# EMBEDDING FUNCTION PERSONALIZZATA (compatibile OpenAI v1.0+)
# ============================================================

class CustomOpenAIEmbeddingFunction(embedding_functions.EmbeddingFunction):
    """Funzione embedding personalizzata per OpenAI v1.0+ con retry per rate limits"""
    
    # Semaforo globale per limitare richieste simultanee (max 3 alla volta per evitare rate limits)
    _semaphore = Semaphore(3)
    
    def __init__(self, api_key: str, model_name: str, base_url: str = None):
        self.api_key = api_key
        self.model_name = model_name
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url if base_url else None
        )
    
    def __call__(self, input: List[str], max_retries: int = 5) -> List[List[float]]:
        """Genera embeddings usando la nuova API di OpenAI con retry per rate limits"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Usa semaforo per limitare richieste simultanee (non bloccare completamente)
                with self._semaphore:
                    response = self.client.embeddings.create(
                        model=self.model_name,
                        input=input
                    )
                    return [item.embedding for item in response.data]
            except Exception as e:
                error_msg = str(e)
                last_error = e
                
                # Gestione errori specifici
                if "maximum context length" in error_msg or "8192 tokens" in error_msg:
                    # Auto sub-chunking: spezza input troppo lungo
                    sub_results = []
                    for text in input:
                        if len(text) > 2000:
                            # Spezza in sotto-chunk da 2000 chars
                            sub_chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
                            for sc in sub_chunks:
                                with self._semaphore:
                                    r = self.client.embeddings.create(model=self.model_name, input=[sc])
                                    sub_results.append(r.data[0].embedding)
                        else:
                            with self._semaphore:
                                r = self.client.embeddings.create(model=self.model_name, input=[text])
                                sub_results.append(r.data[0].embedding)
                    return sub_results
                
                # Rate limit (429): retry con backoff esponenziale
                if "429" in error_msg or "rate_limit" in error_msg.lower() or "tpm" in error_msg.lower():
                    if attempt < max_retries - 1:
                        # Backoff esponenziale: 2^attempt secondi (max 60 secondi)
                        wait_time = min(2 ** attempt, 60)
                        time.sleep(wait_time)
                        continue
                    else:
                        # Ultimo tentativo fallito
                        raise Exception(f"Rate limit raggiunto dopo {max_retries} tentativi. Attendi qualche minuto e riprova. Errore: {error_msg}")
                
                # Altri errori: rilanciamo immediatamente
                raise
        
        # Se arriviamo qui, tutti i tentativi sono falliti
        raise Exception(f"Impossibile generare embeddings dopo {max_retries} tentativi: {last_error}")


# ============================================================
# EMBEDDING FUNCTION (AUTO: OPENAI oppure OPENROUTER)
# ============================================================

def get_embedding_function():
    if PROVIDER == "openai":
        print("[cyan]Embedding provider: OpenAI[/cyan]")
        return CustomOpenAIEmbeddingFunction(
            api_key=OPENAI_API_KEY,
            model_name=EMBEDDING_MODEL_OPENAI
        )
    else:
        print("[cyan]Embedding provider: OpenRouter[/cyan]")
        return CustomOpenAIEmbeddingFunction(
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            model_name=EMBEDDING_MODEL_OPENROUTER
        )


# ============================================================
# GESTIONE SALVATAGGIO PERIODICO
# ============================================================

def _save_ram_to_disk():
    """Salva il database RAM su disco"""
    global _ram_collection, _disk_collection
    if _ram_collection is None or _disk_collection is None:
        return
    
    try:
        # Ottieni tutti i dati dalla collection RAM
        ram_data = _ram_collection.get()
        
        if not ram_data["ids"]:
            return
        
        # Pulisci la collection su disco e ricreala
        try:
            _disk_collection.delete()
        except:
            pass
        
        # Ricrea la collection su disco
        disk_client = chromadb.PersistentClient(
            path=CHROMA_DB_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
        _disk_collection = disk_client.get_or_create_collection(
            name="documents",
            embedding_function=get_embedding_function(),
            metadata={"hnsw:space": "cosine"}
        )
        
        # Copia tutti i dati da RAM a disco
        _disk_collection.add(
            ids=ram_data["ids"],
            documents=ram_data["documents"],
            metadatas=ram_data["metadatas"]
        )
        
        print(f"[cyan]💾 Database salvato su disco ({len(ram_data['ids'])} documenti)[/cyan]")
    except Exception as e:
        print(f"[yellow]⚠ Errore salvataggio su disco: {e}[/yellow]")

def _periodic_save():
    """Thread per salvataggio periodico"""
    global _save_timer
    _save_ram_to_disk()
    if _save_timer is not None:
        _save_timer = threading.Timer(RAM_SAVE_INTERVAL, _periodic_save)
        _save_timer.daemon = True
        _save_timer.start()

# Registra salvataggio all'uscita
atexit.register(_save_ram_to_disk)

# ============================================================
# CREAZIONE / CARICAMENTO DATABASE CHROMA
# ============================================================

def get_vector_db():
    """Ottiene il database vettoriale (ChromaDB o Qdrant)"""
    if VECTOR_DB == "qdrant":
        from rag.qdrant_db import get_qdrant_collection
        return get_qdrant_collection()
    else:
        return get_chroma()

def get_chroma():
    """Ottiene la collection ChromaDB (RAM o Disk in base alla configurazione)"""
    global _ram_collection, _disk_collection, _save_timer
    
    if USE_RAM_MODE:
        # Modalità RAM: carica tutto in memoria per velocità
        if _ram_collection is None:
            print("[cyan]🚀 Modalità RAM attiva - Caricamento database in memoria...[/cyan]")
            
            # Crea client RAM (in memoria)
            ram_client = chromadb.EphemeralClient()
            _ram_collection = ram_client.get_or_create_collection(
                name="documents",
                embedding_function=get_embedding_function(),
                metadata={"hnsw:space": "cosine"}
            )
            
            # Se esiste un database su disco, caricarlo in RAM
            if os.path.exists(CHROMA_DB_PATH):
                try:
                    disk_client = chromadb.PersistentClient(
                        path=CHROMA_DB_PATH,
                        settings=Settings(anonymized_telemetry=False)
                    )
                    disk_col = disk_client.get_or_create_collection(
                        name="documents",
                        embedding_function=get_embedding_function()
                    )
                    
                    # Carica tutti i dati da disco
                    disk_data = disk_col.get()
                    if disk_data["ids"]:
                        _ram_collection.add(
                            ids=disk_data["ids"],
                            documents=disk_data["documents"],
                            metadatas=disk_data["metadatas"]
                        )
                        print(f"[green]✓ Caricati {len(disk_data['ids'])} documenti da disco in RAM[/green]")
                    
                    _disk_collection = disk_col
                except Exception as e:
                    print(f"[yellow]⚠ Errore caricamento da disco: {e}[/yellow]")
                    _disk_collection = None
            else:
                _disk_collection = None
            
            # Avvia salvataggio periodico
            if _save_timer is None:
                _save_timer = threading.Timer(RAM_SAVE_INTERVAL, _periodic_save)
                _save_timer.daemon = True
                _save_timer.start()
                print(f"[cyan]💾 Salvataggio automatico ogni {RAM_SAVE_INTERVAL} secondi[/cyan]")
        
        return _ram_collection
    else:
        # Modalità Disk: usa database persistente (più lento ma persistente)
        if not os.path.exists(CHROMA_DB_PATH):
            os.makedirs(CHROMA_DB_PATH, mode=0o755)

        client = chromadb.PersistentClient(
            path=CHROMA_DB_PATH,
            settings=Settings(
                anonymized_telemetry=False
            )
        )

        collection = client.get_or_create_collection(
            name="documents",
            embedding_function=get_embedding_function(),
            metadata={"hnsw:space": "cosine"}
        )

        return collection


# ============================================================
# INDICIZZAZIONE SINGOLO FILE
# ============================================================

def _index_single_file(path: str, db_collection, check_exists_func, add_documents_func) -> dict:
    """
    Indicizza un singolo file.
    Restituisce un dict con: success, path, error, chunks_added
    """
    doc_id = path.replace("/", "_")
    _IMAGE_EXTS = (".tif", ".tiff", ".bmp", ".png", ".jpg", ".jpeg", ".heic", ".heif")
    is_image = os.path.splitext(path)[1].lower() in _IMAGE_EXTS

    # Controlla duplicati
    if check_exists_func(doc_id):
        return {"success": True, "path": path, "skipped": True, "message": "già indicizzato"}
    
    # Estrazione testo
    try:
        text = extract_text(path)
        if not text.strip():
            return {"success": False, "path": path, "error": "Nessun testo estratto"}
    except Exception as e:
        return {"success": False, "path": path, "error": f"Errore estrazione: {e}"}

    # Enrichment: estrai metadati strutturati (veloce, basato su regex)
    try:
        enrichment = enrich_fast(text, path)
        enrichment_meta = metadata_for_qdrant(enrichment)
    except Exception as e:
        print(f"[yellow]⚠ Enrichment fallito per {os.path.basename(path)}: {e}[/yellow]")
        enrichment_meta = {}

    # Gestione chunk
    if len(text) > MAX_EMBEDDING_CHARS:
        # Semantic chunking: dividi ai confini naturali del testo
        from config import CHUNK_SIZE, CHUNK_OVERLAP
        target_size = min(CHUNK_SIZE, MAX_EMBEDDING_CHARS)
        
        # 1. Trova confini semantici (sezioni, paragrafi, formule)
        import re as _re
        # Pattern di split: doppio newline, header, sezione numerata, fine tabella
        split_pattern = r"(?:\n\s*\n|\n(?=\d+[\.\)]\s)|(?<=\.\s)\n(?=[A-Z])|\n(?=[-—]{3,})|\n(?=Tabella|Figura|§))"
        segments = _re.split(split_pattern, text)
        segments = [s.strip() for s in segments if s and s.strip()]
        
        if not segments:
            segments = [text]
        
        # 2. Unisci segmenti piccoli fino a target_size con overlap
        chunks = []
        current_chunk = ""
        prev_tail = ""  # Per overlap
        
        for seg in segments:
            if len(current_chunk) + len(seg) + 1 <= target_size:
                current_chunk = (current_chunk + "\n\n" + seg).strip()
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                    # Overlap: prendi le ultime CHUNK_OVERLAP chars del chunk precedente
                    if CHUNK_OVERLAP > 0:
                        prev_tail = current_chunk[-CHUNK_OVERLAP:]
                    current_chunk = (prev_tail + "\n\n" + seg).strip() if prev_tail else seg
                else:
                    # Segmento singolo più grande del target
                    if len(seg) > target_size:
                        # Spezza a metà frase
                        for i in range(0, len(seg), target_size - CHUNK_OVERLAP):
                            chunk = seg[i:i + target_size]
                            chunks.append(chunk)
                        current_chunk = ""
                    else:
                        current_chunk = seg
        
        if current_chunk:
            chunks.append(current_chunk)
        
        # Fallback: se semantic chunking produce risultati anomali, usa fixed
        if len(chunks) < 1:
            chunks = []
            for i in range(0, len(text), target_size - CHUNK_OVERLAP):
                chunks.append(text[i:i + target_size])
        
        chunk_ids = []
        chunk_docs = []
        chunk_metas = []
        
        for idx, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_chunk{idx}"
            chunk_ids.append(chunk_id)
            chunk_docs.append(chunk)
            chunk_meta = {
                "source": path,
                "chunk": idx,
                "total_chunks": len(chunks),
                "is_image": is_image,
                "chunk_type": "semantic",
            }
            # Aggiungi metadati arricchiti
            chunk_meta.update(enrichment_meta)
            chunk_metas.append(chunk_meta)
        
        # Prova prima batch completo
        try:
            add_documents_func(chunk_ids, chunk_docs, chunk_metas)
            return {"success": True, "path": path, "chunks_added": len(chunks), "method": "batch_complete"}
        except Exception as e:
            error_msg = str(e)
            if "max_tokens" in error_msg.lower() or "300000" in error_msg or "token" in error_msg.lower():
                # Troppi chunk insieme: usa batch processing
                return _add_chunks_in_batches(chunk_ids, chunk_docs, chunk_metas, path, add_documents_func)
            else:
                return {"success": False, "path": path, "error": str(e)}
    else:
        # Documento normale: indicizza direttamente con retry per rate limits
        max_retries = 3
        for attempt in range(max_retries):
            try:
                doc_meta = {"source": path, "is_image": is_image}
                doc_meta.update(enrichment_meta)
                add_documents_func([doc_id], [text], [doc_meta])
                return {"success": True, "path": path, "chunks_added": 1, "method": "direct"}
            except Exception as e:
                error_msg = str(e)
                # Rate limit: aspetta e riprova
                if ("429" in error_msg or "rate_limit" in error_msg.lower() or "tpm" in error_msg.lower()) and attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 60)  # Backoff esponenziale
                    time.sleep(wait_time)
                    continue
                # Altri errori o ultimo tentativo fallito
                return {"success": False, "path": path, "error": str(e)}


def _add_chunks_in_batches(chunk_ids: List[str], chunk_docs: List[str], chunk_metas: List[dict], 
                           path: str, add_documents_func) -> dict:
    """
    Aggiunge chunk in batch più piccoli. Se fallisce, passa a chunk singoli.
    """
    total_chunks = len(chunk_ids)
    success_count = 0
    
    # Prova prima con batch di CHUNK_BATCH_SIZE
    batch_size = CHUNK_BATCH_SIZE
    max_batch_retries = 2
    
    for batch_retry in range(max_batch_retries):
        try:
            # Prova ad aggiungere in batch
            for i in range(0, total_chunks, batch_size):
                batch_ids = chunk_ids[i:i + batch_size]
                batch_docs = chunk_docs[i:i + batch_size]
                batch_metas = chunk_metas[i:i + batch_size]
                
                try:
                    add_documents_func(batch_ids, batch_docs, batch_metas)
                    success_count += len(batch_ids)
                except Exception as batch_error:
                    error_msg = str(batch_error)
                    # Se il batch è troppo grande, riduci la dimensione
                    if "max_tokens" in error_msg.lower() or "300000" in error_msg:
                        if batch_retry < max_batch_retries - 1:
                            # Riduci batch size e riprova
                            batch_size = max(10, batch_size // 2)
                            break
                        else:
                            # Ultimo tentativo: passa a chunk singoli
                            return _add_chunks_one_by_one(chunk_ids, chunk_docs, chunk_metas, path, add_documents_func, i)
                    # Rate limit (429): aspetta e riprova questo batch
                    elif "429" in error_msg or "rate_limit" in error_msg.lower() or "tpm" in error_msg.lower():
                        wait_time = min(2 ** batch_retry, 60)  # Backoff esponenziale
                        time.sleep(wait_time)
                        # Riprova questo batch
                        try:
                            add_documents_func(batch_ids, batch_docs, batch_metas)
                            success_count += len(batch_ids)
                        except:
                            # Se ancora fallisce, passa a chunk singoli per questo batch
                            for j in range(i, min(i + batch_size, total_chunks)):
                                success_count += _retry_add_single_chunk(
                                    chunk_ids[j], chunk_docs[j], chunk_metas[j], add_documents_func
                                )
                    else:
                        # Altro errore: passa a chunk singoli per questo batch
                        for j in range(i, min(i + batch_size, total_chunks)):
                            success_count += _retry_add_single_chunk(
                                chunk_ids[j], chunk_docs[j], chunk_metas[j], add_documents_func
                            )
            else:
                # Tutti i batch sono stati processati con successo
                return {"success": True, "path": path, "chunks_added": success_count, 
                       "method": f"batch_{batch_size}"}
        except Exception as e:
            if batch_retry < max_batch_retries - 1:
                batch_size = max(10, batch_size // 2)
                continue
            else:
                # Fallback a chunk singoli
                return _add_chunks_one_by_one(chunk_ids, chunk_docs, chunk_metas, path, add_documents_func, 0)
    
    return {"success": success_count > 0, "path": path, "chunks_added": success_count, 
           "method": "batch_fallback"}


def _retry_add_single_chunk(chunk_id: str, chunk_doc: str, chunk_meta: dict, 
                            add_documents_func, max_retries: int = 3) -> int:
    """
    Helper per aggiungere un singolo chunk con retry per rate limits.
    Restituisce 1 se successo, 0 se fallito.
    """
    for attempt in range(max_retries):
        try:
            add_documents_func([chunk_id], [chunk_doc], [chunk_meta])
            return 1
        except Exception as e:
            error_msg = str(e)
            # Rate limit: aspetta e riprova
            if ("429" in error_msg or "rate_limit" in error_msg.lower() or "tpm" in error_msg.lower()) and attempt < max_retries - 1:
                wait_time = min(2 ** attempt, 60)  # Backoff esponenziale
                time.sleep(wait_time)
                continue
            # Altri errori: riprova una volta se non è l'ultimo tentativo
            if attempt < max_retries - 1:
                continue
    return 0


def _add_chunks_one_by_one(chunk_ids: List[str], chunk_docs: List[str], chunk_metas: List[dict],
                           path: str, add_documents_func, start_idx: int = 0) -> dict:
    """
    Aggiunge chunk uno alla volta (lento ma garantito).
    Riprova ogni chunk fallito con retry per rate limits.
    """
    total_chunks = len(chunk_ids)
    success_count = 0
    failed_chunks = []
    
    print(f"[yellow]⚠ Troppi chunk da processare insieme. Passo alla modalità chunk-per-chunk (più lento ma garantito)...[/yellow]")
    
    for idx in range(start_idx, total_chunks):
        result = _retry_add_single_chunk(
            chunk_ids[idx], chunk_docs[idx], chunk_metas[idx], add_documents_func
        )
        if result == 1:
            success_count += 1
        else:
            failed_chunks.append(idx + 1)
        
        # Mostra progresso ogni 50 chunk
        if (idx + 1) % 50 == 0:
            print(f"[dim]  Progresso: {idx + 1}/{total_chunks} chunk indicizzati...[/dim]")
    
    result = {"success": success_count > 0, "path": path, "chunks_added": success_count, 
              "method": "one_by_one", "total_chunks": total_chunks}
    if failed_chunks:
        result["failed_chunks"] = failed_chunks
        result["failed_count"] = len(failed_chunks)
    return result


# ============================================================
# CATTURA LOG PER UI (STREAMLIT)
# ============================================================

# Regex per rimuovere codici ANSI (colori, stili)
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


class _LogCollector:
    """Accumula write() in una lista di righe, rimuovendo codici ANSI (per log in UI)."""

    def __init__(self, original_stdout):
        self._original = original_stdout
        self._buffer = []
        self._current = []

    def write(self, data: str):
        if not isinstance(data, str):
            data = str(data)
        self._original.write(data)
        clean = _ANSI_ESCAPE.sub("", data)
        for ch in clean:
            if ch == "\n":
                line = "".join(self._current).strip()
                if line:
                    self._buffer.append(line)
                self._current = []
            else:
                self._current.append(ch)

    def flush(self):
        self._original.flush()
        if self._current:
            line = "".join(self._current).strip()
            if line:
                self._buffer.append(line)
            self._current = []

    def get_and_clear_lines(self) -> List[str]:
        self.flush()
        out = list(self._buffer)
        self._buffer = []
        return out


def index_folder_streaming(folder_path: str) -> Generator[Tuple[float, List[str]], None, None]:
    """
    Indicizzazione come index_folder ma restituisce un generatore che a ogni passo
    cede (progress 0.0..1.0, lista di righe di log). Utile per mostrare i log in UI (Streamlit).
    In modalità streaming l'indicizzazione è sempre sequenziale (un file alla volta).
    """
    original_stdout = sys.stdout
    collector = _LogCollector(original_stdout)
    sys.stdout = collector

    try:
        # Stesso setup di index_folder (stampa iniziale va nel collector)
        if folder_path.startswith("http://") or folder_path.startswith("https://"):
            yield (0.0, collector.get_and_clear_lines())
            # index_folder gestisce SharePoint qui; per semplicità non duplichiamo
            # lo streaming con download: eseguiamo index_folder e catturiamo tutto a fine run
            sys.stdout = original_stdout
            collector = _LogCollector(original_stdout)
            sys.stdout = collector
            index_folder(folder_path)
            sys.stdout = original_stdout
            yield (1.0, collector.get_and_clear_lines())
            return

        if not os.path.exists(folder_path):
            print("[red]La cartella non esiste[/red]")
            yield (0.0, collector.get_and_clear_lines())
            return

        collection = get_chroma() if VECTOR_DB != "qdrant" else None
        file_list = []
        for root, dirs, files in os.walk(folder_path):
            for f in files:
                if f.lower().endswith((".pdf", ".tif", ".tiff", ".txt", ".xlsx", ".xls", ".xlsm", ".docx", ".doc", ".bmp", ".png", ".jpg", ".jpeg", ".heic", ".heif", ".log")):
                    file_list.append(os.path.join(root, f))

        if not file_list:
            print("[yellow]Nessun file indicizzabile trovato[/yellow]")
            yield (0.0, collector.get_and_clear_lines())
            return

        print(f"[cyan]Indicizzazione della cartella: {folder_path}[/cyan]")
        print(f"[green]Trovati {len(file_list)} file da indicizzare[/green]")
        print(f"[cyan]Database utilizzato: {VECTOR_DB.upper()}[/cyan]")
        clear_image_extraction_stats()
        print(f"[cyan]📝 Modalità sequenziale (log in UI)[/cyan]")
        yield (0.0, collector.get_and_clear_lines())

        if VECTOR_DB == "qdrant":
            from rag.qdrant_db import qdrant_check_document_exists, qdrant_add_documents
            def check_exists(doc_id):
                return qdrant_check_document_exists(doc_id)
            def add_documents(ids, docs, metas):
                qdrant_add_documents(ids, docs, metas)
            db_collection = None
        else:
            db_collection = get_chroma()
            def check_exists(doc_id):
                try:
                    existing = db_collection.get(ids=[doc_id])
                    return len(existing["ids"]) > 0
                except Exception:
                    return False
            def add_documents(ids, docs, metas):
                db_collection.add(ids=ids, documents=docs, metadatas=metas)

        total = len(file_list)
        results = []
        for i, path in enumerate(file_list):
            result = _index_single_file(path, db_collection, check_exists, add_documents)
            results.append(result)
            if result.get("skipped"):
                print(f"[yellow]⏭ Saltato: {os.path.basename(path)} (già indicizzato)[/yellow]")
            elif result.get("success"):
                chunks = result.get("chunks_added", 1)
                method = result.get("method", "unknown")
                if chunks > 1:
                    print(f"[green]✓ {os.path.basename(path)}: {chunks} chunk indicizzati ({method})[/green]")
                else:
                    print(f"[green]✓ {os.path.basename(path)} indicizzato[/green]")
            else:
                error = result.get("error", "Errore sconosciuto")
                print(f"[red]✗ {os.path.basename(path)}: {error}[/red]")
            progress = (i + 1) / total
            yield (progress, collector.get_and_clear_lines())

        # Statistiche finali (stesso blocco di index_folder)
        successful = sum(1 for r in results if r.get("success"))
        skipped = sum(1 for r in results if r.get("skipped"))
        failed = len(results) - successful - skipped
        total_chunks = sum(r.get("chunks_added", 0) for r in results if r.get("success"))
        total_expected_chunks = sum(
            r.get("total_chunks", r.get("chunks_added", 0))
            for r in results
            if r.get("success") and r.get("total_chunks")
        )
        failed_chunks = sum(r.get("failed_count", 0) for r in results)

        print(f"\n[bold green]✔ Indicizzazione completata![/bold green]")
        print(f"[green]  ✓ Indicizzati: {successful} file[/green]")
        if skipped > 0:
            print(f"[yellow]  ⏭ Saltati: {skipped} file (già indicizzati)[/yellow]")
        if failed > 0:
            print(f"[red]  ✗ Falliti: {failed} file[/red]")
        print(f"[cyan]  📊 Totale chunk indicizzati: {total_chunks}[/cyan]")
        if total_expected_chunks > total_chunks:
            missing = total_expected_chunks - total_chunks
            print(f"[yellow]  ⚠ Chunk mancanti: {missing} chunk non sono stati indicizzati[/yellow]")
        if failed_chunks > 0:
            print(f"[red]  ⚠ Chunk falliti dopo retry: {failed_chunks} chunk[/red]")
            files_with_failed = [r for r in results if r.get("failed_chunks")]
            if files_with_failed:
                print(f"[yellow]  File con chunk falliti:[/yellow]")
                for r in files_with_failed[:5]:
                    print(f"[dim]    - {os.path.basename(r['path'])}: {r.get('failed_count', 0)} chunk falliti[/dim]")
                if len(files_with_failed) > 5:
                    print(f"[dim]    ... e altri {len(files_with_failed) - 5} file[/dim]")
        try:
            img_stats = get_image_extraction_stats()
            if img_stats:
                by_method = {}
                for s in img_stats:
                    m = s.get("method", "unknown")
                    by_method[m] = by_method.get(m, 0) + 1
                print(f"[cyan]  🖼 Immagini: {len(img_stats)} totali (local: {by_method.get('local', 0)}, vision: {sum(by_method.get(k, 0) for k in by_method if k.startswith('vision'))}, fallback: {by_method.get('fallback', 0)})[/cyan]")
        except Exception:
            pass
        yield (1.0, collector.get_and_clear_lines())
    finally:
        sys.stdout = original_stdout


# ============================================================
# INDICIZZAZIONE FILE
# ============================================================

def index_folder(folder_path):
    """
    Legge tutti i file in una cartella o da SharePoint/OneDrive:
    - Se folder_path è un URL SharePoint/OneDrive, scarica i file
    - Estrae il testo (pipeline ibrida)
    - Crea embeddings
    - Salva in ChromaDB
    """

    print(f"[cyan]Indicizzazione della cartella: {folder_path}[/cyan]")

    # Controlla se è un URL SharePoint/OneDrive
    temp_dir = None
    if folder_path.startswith("http://") or folder_path.startswith("https://"):
        if "sharepoint.com" in folder_path or "onedrive" in folder_path.lower():
            from rag.sharepoint_connector import download_sharepoint_folder
            print("[cyan]🔗 Rilevato URL SharePoint/OneDrive[/cyan]")
            temp_dir = download_sharepoint_folder(folder_path)
            if not temp_dir:
                print("[red]Impossibile scaricare file da SharePoint/OneDrive[/red]")
                return
            folder_path = temp_dir
            print(f"[green]✓ File scaricati in: {folder_path}[/green]")

    if not os.path.exists(folder_path):
        print("[red]La cartella non esiste[/red]")
        return

    collection = get_chroma() if VECTOR_DB != "qdrant" else None

    file_list = []
    for root, dirs, files in os.walk(folder_path):
        for f in files:
            if f.lower().endswith((".pdf", ".tif", ".tiff", ".txt", ".xlsx", ".xls", ".xlsm", ".docx", ".doc", ".bmp", ".png", ".jpg", ".jpeg", ".heic", ".heif", ".log")):
                file_list.append(os.path.join(root, f))

    if not file_list:
        print("[yellow]Nessun file indicizzabile trovato[/yellow]")
        return

    print(f"[green]Trovati {len(file_list)} file da indicizzare[/green]")
    print(f"[cyan]Database utilizzato: {VECTOR_DB.upper()}[/cyan]")
    clear_image_extraction_stats()
    
    # Configura parallelizzazione
    if PARALLEL_WORKERS > 0:
        print(f"[cyan]🚀 Modalità parallela attiva: {PARALLEL_WORKERS} file processati contemporaneamente[/cyan]")
        print(f"[cyan]📦 Batch size chunk: {CHUNK_BATCH_SIZE} chunk per batch[/cyan]")
    else:
        print(f"[cyan]📝 Modalità sequenziale (PARALLEL_WORKERS=0)[/cyan]")

    # Ottieni il database corretto e funzioni helper
    if VECTOR_DB == "qdrant":
        from rag.qdrant_db import qdrant_check_document_exists, qdrant_add_documents
        
        def check_exists(doc_id):
            return qdrant_check_document_exists(doc_id)
        
        def add_documents(ids, docs, metas):
            qdrant_add_documents(ids, docs, metas)
        
        db_collection = None
    else:
        db_collection = get_chroma()
        
        def check_exists(doc_id):
            try:
                existing = db_collection.get(ids=[doc_id])
                return len(existing["ids"]) > 0
            except:
                return False
        
        def add_documents(ids, docs, metas):
            db_collection.add(ids=ids, documents=docs, metadatas=metas)
    
    # Processa file
    if PARALLEL_WORKERS > 0 and len(file_list) > 1:
        # Modalità parallela
        results = []
        active_tasks = 0
        with ThreadPoolExecutor(max_workers=PARALLEL_WORKERS) as executor:
            # Sottometti tutti i task
            future_to_path = {
                executor.submit(_index_single_file, path, db_collection, check_exists, add_documents): path
                for path in file_list
            }
            
            # Processa risultati con progress bar
            with tqdm(total=len(file_list), desc="Indicizzazione") as pbar:
                for future in as_completed(future_to_path):
                    path = future_to_path[future]
                    active_tasks = len([f for f in future_to_path.keys() if not f.done()])
                    try:
                        result = future.result()
                        results.append(result)
                        
                        # Mostra risultato con contatore file attivi
                        active_info = f"[{active_tasks} attivi]" if active_tasks > 0 else ""
                        if result.get("skipped"):
                            pbar.set_postfix_str(f"⏭ {os.path.basename(path)[:25]}... {active_info}")
                        elif result.get("success"):
                            chunks = result.get("chunks_added", 1)
                            method = result.get("method", "unknown")
                            pbar.set_postfix_str(f"✓ {os.path.basename(path)[:25]}... ({chunks} chunk) {active_info}")
                        else:
                            pbar.set_postfix_str(f"✗ {os.path.basename(path)[:25]}... {active_info}")
                    except Exception as e:
                        results.append({"success": False, "path": path, "error": str(e)})
                        pbar.set_postfix_str(f"✗ Errore: {str(e)[:25]}... [{active_tasks} attivi]")
                    finally:
                        pbar.update(1)
    else:
        # Modalità sequenziale (originale)
        results = []
        for path in tqdm(file_list, desc="Indicizzazione"):
            result = _index_single_file(path, db_collection, check_exists, add_documents)
            results.append(result)
            
            # Mostra risultato
            if result.get("skipped"):
                print(f"[yellow]⏭ Saltato: {os.path.basename(path)} (già indicizzato)[/yellow]")
            elif result.get("success"):
                chunks = result.get("chunks_added", 1)
                method = result.get("method", "unknown")
                if chunks > 1:
                    print(f"[green]✓ {os.path.basename(path)}: {chunks} chunk indicizzati ({method})[/green]")
                else:
                    print(f"[green]✓ {os.path.basename(path)} indicizzato[/green]")
            else:
                error = result.get("error", "Errore sconosciuto")
                print(f"[red]✗ {os.path.basename(path)}: {error}[/red]")
    
    # Statistiche finali
    successful = sum(1 for r in results if r.get("success"))
    skipped = sum(1 for r in results if r.get("skipped"))
    failed = len(results) - successful - skipped
    total_chunks = sum(r.get("chunks_added", 0) for r in results if r.get("success"))
    total_expected_chunks = sum(r.get("total_chunks", r.get("chunks_added", 0)) for r in results if r.get("success") and r.get("total_chunks"))
    failed_chunks = sum(r.get("failed_count", 0) for r in results)
    
    print(f"\n[bold green]✔ Indicizzazione completata![/bold green]")
    print(f"[green]  ✓ Indicizzati: {successful} file[/green]")
    if skipped > 0:
        print(f"[yellow]  ⏭ Saltati: {skipped} file (già indicizzati)[/yellow]")
    if failed > 0:
        print(f"[red]  ✗ Falliti: {failed} file[/red]")
    print(f"[cyan]  📊 Totale chunk indicizzati: {total_chunks}[/cyan]")
    if total_expected_chunks > total_chunks:
        missing = total_expected_chunks - total_chunks
        print(f"[yellow]  ⚠ Chunk mancanti: {missing} chunk non sono stati indicizzati[/yellow]")
    if failed_chunks > 0:
        print(f"[red]  ⚠ Chunk falliti dopo retry: {failed_chunks} chunk[/red]")
        # Mostra file con chunk falliti
        files_with_failed = [r for r in results if r.get("failed_chunks")]
        if files_with_failed:
            print(f"[yellow]  File con chunk falliti:[/yellow]")
            for r in files_with_failed[:5]:  # Mostra max 5 file
                print(f"[dim]    - {os.path.basename(r['path'])}: {r.get('failed_count', 0)} chunk falliti[/dim]")
            if len(files_with_failed) > 5:
                print(f"[dim]    ... e altri {len(files_with_failed) - 5} file[/dim]")
    
    # Statistiche estrazione immagini (local / vision / fallback)
    try:
        img_stats = get_image_extraction_stats()
        if img_stats:
            by_method = {}
            for s in img_stats:
                m = s.get("method", "unknown")
                by_method[m] = by_method.get(m, 0) + 1
            print(f"[cyan]  🖼 Immagini: {len(img_stats)} totali (local: {by_method.get('local', 0)}, vision: {sum(by_method.get(k, 0) for k in by_method if k.startswith('vision'))}, fallback: {by_method.get('fallback', 0)})[/cyan]")
    except Exception:
        pass
    
    # Pulisci cartella temporanea se creata da SharePoint
    if temp_dir:
        try:
            import shutil
            temp_base = tempfile.gettempdir()
            if temp_dir.startswith("/tmp") or temp_dir.startswith(temp_base):
                print(f"[cyan]🧹 Rimozione file temporanei da: {temp_dir}[/cyan]")
                shutil.rmtree(temp_dir)
                print("[green]✓ File temporanei rimossi[/green]")
        except Exception as e:
            print(f"[yellow]⚠ Impossibile rimuovere file temporanei: {e}[/yellow]")


# ============================================================
# RESET DEL DATABASE (UTILITÀ)
# ============================================================

def reset_database():
    """
    Cancella completamente il database vettoriale (ChromaDB o Qdrant).
    """
    import shutil
    global _ram_collection, _disk_collection
    
    if VECTOR_DB == "qdrant":
        from rag.qdrant_db import qdrant_delete_collection
        qdrant_delete_collection()
    else:
        # Reset collection RAM
        if _ram_collection is not None:
            try:
                all_ids = _ram_collection.get()["ids"]
                if all_ids:
                    _ram_collection.delete(ids=all_ids)
            except:
                pass
            _ram_collection = None
        
        # Reset collection Disk
        _disk_collection = None
        
        # Elimina file su disco
        if os.path.exists(CHROMA_DB_PATH):
            shutil.rmtree(CHROMA_DB_PATH)
            print("[yellow]Database ChromaDB eliminato (RAM e Disk)[/yellow]")
        else:
            print("[cyan]Database già vuoto[/cyan]")


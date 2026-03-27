"""
Implementazione Qdrant per database vettoriale
"""
import os
import threading
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from qdrant_client.http import models
from typing import List, Dict, Optional
from config import (
    QDRANT_HOST,
    QDRANT_PORT,
    QDRANT_COLLECTION_NAME,
    EMBEDDING_MODEL_OPENAI,
    EMBEDDING_MODEL_OPENROUTER,
    PROVIDER,
    OPENAI_API_KEY,
    OPENROUTER_API_KEY,
    MAX_EMBEDDING_CHARS,
)
from rag.indexer import get_embedding_function
from rich import print


# Variabile globale per il client Qdrant
_qdrant_client = None
_embedding_function = None
_embedding_dim = None
_embedding_dim_lock = threading.Lock()  # Lock per determinare dimensione embedding una sola volta


def get_qdrant_client():
    """Ottiene o crea il client Qdrant"""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    return _qdrant_client


def get_qdrant_collection():
    """Ottiene o crea la collection Qdrant"""
    global _embedding_function, _embedding_dim
    
    client = get_qdrant_client()
    
    # Inizializza embedding function se non già fatto
    if _embedding_function is None:
        _embedding_function = get_embedding_function()
    
    # Ottieni dimensione embedding (test con un esempio) - solo una volta con lock
    if _embedding_dim is None:
        with _embedding_dim_lock:
            # Double-check: potrebbe essere già stato impostato da un altro thread
            if _embedding_dim is None:
                try:
                    test_embedding = _embedding_function(["test"])
                    _embedding_dim = len(test_embedding[0])
                except Exception as e:
                    # Default per text-embedding-3-large
                    error_msg = str(e)
                    if "429" in error_msg or "rate_limit" in error_msg.lower():
                        print(f"[yellow]⚠ Rate limit durante determinazione dimensione embedding, uso default: 3072[/yellow]")
                    else:
                        print(f"[yellow]⚠ Impossibile determinare dimensione embedding, uso default: {e}[/yellow]")
                    _embedding_dim = 3072
    
    embedding_dim = _embedding_dim
    
    # Verifica se la collection esiste
    try:
        collections = client.get_collections()
        collection_exists = any(c.name == QDRANT_COLLECTION_NAME for c in collections.collections)
    except:
        collection_exists = False
    
    # Crea collection se non esiste
    if not collection_exists:
        print(f"[cyan]Creazione collection Qdrant: {QDRANT_COLLECTION_NAME}[/cyan]")
        try:
            client.create_collection(
                collection_name=QDRANT_COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=embedding_dim,
                    distance=Distance.COSINE
                )
            )
            print(f"[green]✓ Collection creata (dimensione embedding: {embedding_dim})[/green]")
        except Exception as e:
            # Se la collection esiste già (409 Conflict), è normale in modalità parallela
            error_str = str(e)
            if "409" in error_str or "already exists" in error_str.lower() or "Conflict" in error_str:
                print(f"[dim]Collection già esistente (normale in modalità parallela)[/dim]")
            else:
                # Altri errori sono problematici
                print(f"[red]Errore creazione collection: {e}[/red]")
                raise
    
    return client, QDRANT_COLLECTION_NAME


def qdrant_add_documents(ids: List[str], documents: List[str], metadatas: List[Dict]):
    """Aggiunge documenti a Qdrant"""
    client, collection_name = get_qdrant_collection()
    
    # Genera embeddings
    embeddings = _embedding_function(documents)
    
    # Prepara punti
    points = []
    for i, (doc_id, embedding, metadata) in enumerate(zip(ids, embeddings, metadatas)):
        points.append(
            PointStruct(
                id=hash(doc_id) % (2**63),  # Qdrant richiede int64
                vector=embedding,
                payload={
                    "text": documents[i],
                    "source": metadata.get("source", ""),
                    **{k: v for k, v in metadata.items() if k != "source"}
                }
            )
        )
    
    # Inserisci in batch
    client.upsert(
        collection_name=collection_name,
        points=points
    )


def qdrant_query(query_text: str, n_results: int = 5, filters: dict = None) -> List[Dict]:
    """Esegue una query su Qdrant con filtri opzionali sui metadati.
    
    Args:
        query_text: Testo della query
        n_results: Numero risultati
        filters: Dict opzionale con filtri metadati:
            - pump_family: str (es. "OH2")
            - doc_type: str (es. "parts_list")
            - has_weight: bool
            - flange_rating: int (es. 300)
            - material: str (cerca nei materiali)
    """
    global _embedding_function
    
    client, collection_name = get_qdrant_collection()
    
    # Inizializza embedding function se necessario
    if _embedding_function is None:
        _embedding_function = get_embedding_function()
    
    # Genera embedding della query
    query_embedding = _embedding_function([query_text])[0]
    
    # Costruisci filtri Qdrant
    query_filter = _build_qdrant_filter(filters) if filters else None
    
    # Esegui ricerca usando query_points (API corretta di Qdrant)
    try:
        # Prova con query_points passando direttamente il vettore
        query_result = client.query_points(
            collection_name=collection_name,
            query=query_embedding,
            query_filter=query_filter,
            limit=n_results
        )
        results = query_result.points
    except (TypeError, AttributeError) as e:
        # Fallback: usa QueryVector se necessario
        from qdrant_client.models import Query, QueryVector
        try:
            query_result = client.query_points(
                collection_name=collection_name,
                query=Query(vector=QueryVector(vector=query_embedding)),
                query_filter=query_filter,
                limit=n_results
            )
            results = query_result.points
        except Exception as e2:
            raise Exception(f"Errore query Qdrant: {e2}. Tentativo originale: {e}")
    
    # Converti risultati in formato compatibile con ChromaDB
    docs = []
    for point in results:
        payload = point.payload if point.payload else {}
        doc = {
            "id": str(point.id),
            "text": payload.get("text", ""),
            "source": payload.get("source", ""),
            "score": getattr(point, 'score', 0.0)
        }
        # Aggiungi TUTTI i metadati dal payload (inclusi dati estrattore componente)
        for key, value in payload.items():
            if key not in ("text", "source"):  # text e source già aggiunti sopra
                doc[key] = value
        docs.append(doc)
    
    return docs


def _build_qdrant_filter(filters: dict):
    """Costruisce un filtro Qdrant dai parametri."""
    if not filters:
        return None
    
    conditions = []
    
    if filters.get("pump_family"):
        conditions.append(
            models.FieldCondition(
                key="pump_family",
                match=models.MatchValue(value=filters["pump_family"])
            )
        )
    
    if filters.get("doc_type"):
        conditions.append(
            models.FieldCondition(
                key="doc_type",
                match=models.MatchValue(value=filters["doc_type"])
            )
        )
    
    if filters.get("has_weight") is True:
        conditions.append(
            models.FieldCondition(
                key="has_weight",
                match=models.MatchValue(value=True)
            )
        )
    
    if filters.get("flange_rating"):
        conditions.append(
            models.FieldCondition(
                key="flange_rating",
                match=models.MatchValue(value=filters["flange_rating"])
            )
        )
    
    if filters.get("material"):
        conditions.append(
            models.FieldCondition(
                key="materials",
                match=models.MatchAny(any=[filters["material"]])
            )
        )
    
    if not conditions:
        return None
    
    return models.Filter(must=conditions)


def qdrant_get_all() -> Dict:
    """Ottiene tutti i documenti (per migrazione/backup)"""
    client, collection_name = get_qdrant_collection()
    
    # Scroll tutti i punti
    points, _ = client.scroll(
        collection_name=collection_name,
        limit=10000  # Aumenta se necessario
    )
    
    ids = []
    documents = []
    metadatas = []
    
    for point in points:
        ids.append(str(point.id))
        documents.append(point.payload.get("text", ""))
        metadatas.append({
            "source": point.payload.get("source", ""),
            **{k: v for k, v in point.payload.items() if k not in ["text", "source"]}
        })
    
    return {
        "ids": ids,
        "documents": documents,
        "metadatas": metadatas
    }


def qdrant_delete_collection():
    """Cancella la collection Qdrant"""
    client = get_qdrant_client()
    try:
        client.delete_collection(collection_name=QDRANT_COLLECTION_NAME)
        print("[yellow]Collection Qdrant eliminata[/yellow]")
    except Exception as e:
        print(f"[yellow]Errore eliminazione collection: {e}[/yellow]")


def qdrant_check_document_exists(doc_id: str) -> bool:
    """Verifica se un documento esiste"""
    client, collection_name = get_qdrant_collection()
    
    try:
        point_id = hash(doc_id) % (2**63)
        result = client.retrieve(
            collection_name=collection_name,
            ids=[point_id]
        )
        return len(result) > 0
    except:
        return False


def qdrant_get_indexed_folders() -> Dict:
    """
    Restituisce le cartelle sorgente indicizzate con conteggi.
    Returns: {folder_path: {"files": set(), "chunks": int}}
    """
    client = get_qdrant_client()
    try:
        result = client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
            limit=10000,
            with_payload=True,
            with_vectors=False,
        )
        folders = {}
        for point in result[0]:
            payload = point.payload or {}
            source = payload.get("source", "")
            if not source:
                continue
            folder = os.path.dirname(source)
            if folder not in folders:
                folders[folder] = {"files": set(), "chunks": 0}
            folders[folder]["files"].add(os.path.basename(source))
            folders[folder]["chunks"] += 1
        # Converti set in count per serializzazione
        return {k: {"file_count": len(v["files"]), "chunks": v["chunks"]}
                for k, v in folders.items()}
    except Exception:
        return {}


def qdrant_delete_by_source_prefix(prefix: str) -> int:
    """
    Cancella tutti i punti il cui campo 'source' inizia con il prefix dato.
    Utile per cancellare selettivamente una cartella indicizzata.
    Returns: numero di punti cancellati
    """
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    client = get_qdrant_client()
    try:
        # Scroll tutti i punti per trovare quelli con source che inizia con prefix
        result = client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
            limit=10000,
            with_payload=True,
            with_vectors=False,
        )
        ids_to_delete = []
        for point in result[0]:
            payload = point.payload or {}
            source = payload.get("source", "")
            if source.startswith(prefix):
                ids_to_delete.append(point.id)

        if ids_to_delete:
            # Cancella in batch da 100
            for i in range(0, len(ids_to_delete), 100):
                batch = ids_to_delete[i:i + 100]
                client.delete(
                    collection_name=QDRANT_COLLECTION_NAME,
                    points_selector=batch,
                )
        return len(ids_to_delete)
    except Exception as e:
        print(f"Errore cancellazione selettiva: {e}")
        return 0


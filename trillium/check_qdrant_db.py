#!/usr/bin/env python3
"""Script per controllare il contenuto del database Qdrant (Docker)."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import VECTOR_DB, QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION_NAME

def main():
    if VECTOR_DB != "qdrant":
        print(f"Config VECTOR_DB={VECTOR_DB}. Per questo script usa Qdrant (VECTOR_DB=qdrant).")
        return
    from qdrant_client import QdrantClient
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    try:
        info = client.get_collection(QDRANT_COLLECTION_NAME)
    except Exception as e:
        print(f"Errore connessione Qdrant ({QDRANT_HOST}:{QDRANT_PORT}): {e}")
        return
    print(f"Collection: {QDRANT_COLLECTION_NAME}")
    print(f"Punti (chunk) totali: {info.points_count}")
    print()
    # Elenco sorgenti uniche (path file)
    offset = None
    sources = set()
    paths_list = []
    while True:
        points, offset = client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
            limit=1000,
            offset=offset,
            with_payload=["source"],
            with_vectors=False
        )
        for p in points:
            src = (p.payload or {}).get("source", "")
            if src:
                sources.add(src)
                paths_list.append(src)
        if offset is None:
            break
    print(f"File (sorgenti) unici: {len(sources)}")
    print()
    print("--- Ultimi 30 path (sample) ---")
    for path in list(sources)[:30]:
        print(path)
    if len(sources) > 30:
        print(f"... e altri {len(sources) - 30} file.")
    # Conta per cartella / Test02
    test02 = [s for s in sources if "Test02" in s or "test02" in s]
    tes01 = [s for s in sources if "Tes01" in s or "tes01" in s]
    print()
    print(f"Contenuto da cartelle:")
    print(f"  - Path che contengono 'Test02': {len(test02)}")
    print(f"  - Path che contengono 'Tes01': {len(tes01)}")

if __name__ == "__main__":
    main()

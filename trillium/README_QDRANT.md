# Setup Qdrant

## Installazione

### Opzione 1: Docker (Consigliato)
```bash
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

### Opzione 2: Binario
Scarica da: https://github.com/qdrant/qdrant/releases

## Configurazione

Aggiungi al file `.env`:
```
VECTOR_DB=qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=documents
```

## Uso

1. Avvia Qdrant (Docker o binario)
2. Imposta `VECTOR_DB=qdrant` nel `.env`
3. Usa il programma normalmente - indicizza e interroga come sempre

## Confronto Performance

Per confrontare ChromaDB vs Qdrant:
1. Indicizza con `VECTOR_DB=chromadb` → testa performance
2. Cambia a `VECTOR_DB=qdrant` → indicizza di nuovo → testa performance
3. Confronta i tempi di query

## Note

- Qdrant è ~3-5x più veloce di ChromaDB
- I database sono separati: ChromaDB usa `./rag_db`, Qdrant usa il server
- Puoi avere entrambi configurati e switchare cambiando `VECTOR_DB`


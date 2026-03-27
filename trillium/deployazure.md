# Trillium V2 — Deploy su Azure

*Preparato: 27 Marzo 2026*

---

## Infrastruttura Azure (Riutilizzata da TrilliumVersione1)

| Risorsa | Nome | Region | Costo |
|---------|------|--------|-------|
| Resource Group | `trillium-rg` | Italy North | €0 |
| App Service Plan | `ASP-trilliumrg-b74f` | Italy North | ~€13/mese |
| Web App | `trillium-app` | Italy North | (incluso) |
| Container Instance Qdrant | `trillium-qdrant` | Italy North | ~€15/mese |
| Container Registry | `trilliumregistry` | Italy North | ~€5/mese |
| Blob Storage | `trilliumdocs` | Italy North | ~€0/mese |
| **Totale** | | | **~€33/mese** |

---

## URL e Endpoint

| Servizio | URL |
|----------|-----|
| App Streamlit (Azure) | `https://trillium-app-hbcpbmbkajbjd3h2.italynorth-01.azurewebsites.net` |
| App Streamlit (locale) | `http://localhost:8501` |
| Qdrant Azure | `http://trillium-qdrant.dwdrb8d9edexagfz.italynorth.azurecontainer.io:6333` |
| Qdrant Health | `http://trillium-qdrant.dwdrb8d9edexagfz.italynorth.azurecontainer.io:6333/healthz` |
| Container Registry | `trilliumregistry.azurecr.io` |

---

## Credenziali

### Container Registry
```
Login Server:  trilliumregistry.azurecr.io
Username:      trilliumregistry
Password 1:    <VEDI AZURE PORTAL → Container Registry → Access Keys>
```

### Azure Blob Storage
```
Connection String: DefaultEndpointsProtocol=https;AccountName=trilliumdocs;AccountKey=<VEDI AZURE PORTAL>;EndpointSuffix=core.windows.net
Container:         documenti-tecnici
```

---

## File .env (locale — per test Azure Qdrant)

```env
PROVIDER=openai
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIzaSy...
VECTOR_DB=qdrant

# Qdrant AZURE (per test locale contro Azure):
QDRANT_HOST=trillium-qdrant.dwdrb8d9edexagfz.italynorth.azurecontainer.io
# Qdrant LOCALE (sviluppo):
# QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=trilliumdoc

AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=trilliumdocs;AccountKey=<VEDI AZURE PORTAL>;EndpointSuffix=core.windows.net
AZURE_STORAGE_CONTAINER=documenti-tecnici
```

---

## Variabili Ambiente su App Service (Azure Portal)

Impostare in: **App Service `trillium-app` → Settings → Environment variables**

| Variabile | Valore |
|-----------|--------|
| `WEBSITES_PORT` | `8501` |
| `PROVIDER` | `openai` |
| `OPENAI_API_KEY` | (chiave API OpenAI) |
| `ANTHROPIC_API_KEY` | (chiave API Anthropic) |
| `GEMINI_API_KEY` | (chiave API Gemini) |
| `VECTOR_DB` | `qdrant` |
| `QDRANT_HOST` | `trillium-qdrant.dwdrb8d9edexagfz.italynorth.azurecontainer.io` |
| `QDRANT_PORT` | `6333` |
| `QDRANT_COLLECTION_NAME` | `trilliumdoc` |
| `AZURE_STORAGE_CONNECTION_STRING` | (connection string storage) |
| `AZURE_STORAGE_CONTAINER` | `documenti-tecnici` |
| `TILE_VISION_PROVIDER` | `openai` |

---

## Migrazione Dati Qdrant: Locale → Azure (una volta sola)

> ⚠️ **Solo se Qdrant Azure è vuoto.** Se i vettori sono già stati migrati con V1, questo passo va saltato — la collezione `trilliumdoc` è già piena su Azure.

```bash
# Verifica se Qdrant Azure ha già i dati:
curl -s http://trillium-qdrant.dwdrb8d9edexagfz.italynorth.azurecontainer.io:6333/collections/trilliumdoc | python3 -m json.tool
```

Se `points_count > 0` → salta la migrazione. Altrimenti esegui:

```python
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

LOCAL = QdrantClient(host='localhost', port=6333, timeout=30)
REMOTE = QdrantClient(
    host='trillium-qdrant.dwdrb8d9edexagfz.italynorth.azurecontainer.io',
    port=6333, timeout=60
)

collection = 'trilliumdoc'
info = LOCAL.get_collection(collection)

try: REMOTE.delete_collection(collection)
except: pass
REMOTE.create_collection(
    collection_name=collection,
    vectors_config=VectorParams(size=info.config.params.vectors.size, distance=Distance.COSINE),
)

offset = None
total = 0
while True:
    points, next_offset = LOCAL.scroll(collection, limit=50, offset=offset,
                                        with_vectors=True, with_payload=True)
    if not points: break
    structs = [PointStruct(id=p.id, vector=p.vector, payload=p.payload) for p in points]
    REMOTE.upsert(collection_name=collection, points=structs)
    total += len(points)
    print(f'{total}/{info.points_count}')
    offset = next_offset
    if offset is None: break

print(f'Migrazione completata: {total} punti copiati.')
```

---

## Deploy: Come Aggiornare l'App su Azure

```bash
# 1. Vai nella root del progetto V2
cd "/Users/mauriziocapitanio/Documents/Alveo/Sviluppo copia/TrilliumVersione2"

# 2. Login al Container Registry
docker login trilliumregistry.azurecr.io \
  -u trilliumregistry \
  -p '<PASSWORD DA AZURE PORTAL → Container Registry → Access Keys>'

# 3. Build immagine (linux/amd64 obbligatorio per Azure App Service)
docker build --platform linux/amd64 \
  -t trilliumregistry.azurecr.io/trillium-app:latest .

# 4. Push al registry
docker push trilliumregistry.azurecr.io/trillium-app:latest

# 5. Restart dell'app (scegli uno dei due metodi)
# Metodo A — Azure CLI:
az webapp restart --name trillium-app --resource-group trillium-rg
# Metodo B — Azure Portal: trillium-app → Overview → Restart
```

> 💡 **Tempo stimato**: la build richiede ~5 min (tesseract + dipendenze Python), il push ~2 min.

---

## Comandi Utili

```bash
# Verifica stato Qdrant Azure
curl http://trillium-qdrant.dwdrb8d9edexagfz.italynorth.azurecontainer.io:6333/healthz

# Conta documenti nel Qdrant Azure
curl -s http://trillium-qdrant.dwdrb8d9edexagfz.italynorth.azurecontainer.io:6333/collections/trilliumdoc \
  | python3 -m json.tool

# Verifica che l'app Azure risponda
curl -s https://trillium-app-hbcpbmbkajbjd3h2.italynorth-01.azurewebsites.net

# Apri app nel browser
open https://trillium-app-hbcpbmbkajbjd3h2.italynorth-01.azurewebsites.net

# Commit e push su GitHub (se necessario)
git add -A && git commit -m "Deploy V2" && git push origin main
```

---

## File Creati per il Deploy

| File | Dove | Stato |
|------|------|-------|
| `Dockerfile` | root di TrilliumVersione2 | ✅ Creato |
| `.dockerignore` | root di TrilliumVersione2 | ✅ Creato |
| `trillium/requirements.txt` | aggiunto `azure-storage-blob` | ✅ Aggiornato |
| `deployazure.md` | `trillium/` | ✅ Questo file |

---

## Note Importanti

- **Il database Qdrant è condiviso** tra V1 e V2 (stessa collezione `trilliumdoc`). Non serve re-indicizzare.
- **L'App Service esiste già** — basta fare push dell'immagine V2 e restart. Non creare una nuova Web App.
- **Il tag dell'immagine** è sempre `:latest` — Azure App Service fa pull automaticamente all'avvio.
- **Senza `.env` nel container** (escluso da `.dockerignore`) — le API keys devono essere configurate come variabili d'ambiente nell'App Service.

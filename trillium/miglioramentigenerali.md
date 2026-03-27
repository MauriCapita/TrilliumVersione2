# Trillium V2 — Proposte di Miglioramento

*Analisi basata sulla lettura dei sorgenti — Marzo 2026*

---

## 🔍 Miglioramenti Ricerca Semantica

### 1. Embeddings più Specifici per il Dominio

Il sistema usa `text-embedding-3-large` (modello generico). Si potrebbe:

- **Fine-tuning degli embeddings** su terminologia pompe API 610 (Nq, OH2, BB5, ecc.) usando `matryoshka` loss con coppie (query, documento) reali estratte dai log
- **Embeddings multilingua** con `multilingual-e5-large` per gestire meglio la terminologia mista IT/EN già presente

### 2. Chunking Semantico Adattivo

Il chunking è fisso (1000 char, overlap 200). Si potrebbe:

- Usare **semantic chunking** (split ai cambi di topic invece che a lunghezza fissa) — librerie come `semantic-chunkers` o `chonkie`
- **Chunking strutturato per tipo documento**: per una SOP splittare per paragrafo/sezione, per Excel per riga/blocco dati, per disegni TIF per zona estratta (cartiglio, note, schema)

### 3. Late Interaction (ColBERT)

Invece di un singolo vettore per documento, **ColBERT** mantiene un vettore per token e fa matching a livello di token. Molto più accurato su query tecniche brevi come `"D2 OH2 acciaio inox"`. Qdrant supporta sparse vectors che si prestano a implementarlo.

### 4. Sparse + Dense Hybrid più Bilanciato

Ora BM25 e semantica sono sommati con pesi fissi. Si potrebbe:

- Usare **Reciprocal Rank Fusion (RRF)** invece della somma pesata — più robusto
- **Sparse vectors nativi Qdrant** (con SPLADE o BM42) invece di BM25 locale

### 5. Re-ranking più Efficiente

Il re-ranker usa GPT-4o-mini (costoso e lento). Alternative:

- **`cross-encoder/ms-marco-MiniLM-L-6-v2`** locale — veloce, gratuito, ottimo per re-ranking
- **Cohere Rerank API** — specializzato, ottimo rapporto qualità/costo

---

## 🖼️ Miglioramenti Ricerca Immagini (TIF/Disegni Tecnici)

### 1. Embeddings Visivi per i Disegni

Attualmente i TIF vengono convertiti in testo via OCR e poi embeddings testuali. Si potrebbe aggiungere:

- **CLIP embeddings** sui tile delle immagini (o sull'immagine intera ridimensionata) salvati come vettori separati in Qdrant — permetterebbe ricerca "immagine simile a questa"
- Qdrant supporta **named vectors** (es. `text` + `image` sullo stesso punto), si potrebbe fare retrieval ibrido testo+visivo

### 2. Estrazione Strutturata dal Disegno (non solo OCR grezzo)

Invece di passare tutto l'OCR come testo piatto:

- Estrarre **campi strutturati** dal cartiglio (tipo pompa, revisione, data, cliente) e metterli come **payload filtrabili** in Qdrant
- Usare GPT-4o Vision non per sostituire l'OCR ma per **compilare un JSON** con: `{pump_id, D2, b2, material, revision}` → chunk molto più precisi

### 3. Indicizzazione Zone Separate

Un disegno ha zone con semantica diversa (cartiglio, schema idraulico, note). Si potrebbe:

- Splittare ogni TIF in **chunk per zona** (cartiglio separato da schema, note separati) con metadati `zone: "title_block"` / `"hydraulic_schema"` / `"notes"`
- Questo migliora enormemente il retrieval perché oggi tutte le zone sono mescolate in un unico chunk

### 4. OCR con Modelli Specializzati

Tesseract è generico. Per disegni tecnici potrebbero funzionare meglio:

- **TrOCR** (Microsoft) fine-tuned su testi tecnici/ingegneristici
- **PaddleOCR** — migliore con testi in piccolo font e ruotati, comune nei disegni CAD

### 5. Deduplicazione Visiva

Se lo stesso disegno esiste in più revisioni, oggi vengono indicizzati come documenti separati con contenuto quasi identico, inquinando il retrieval. Si potrebbe:

- Calcolare **perceptual hash (pHash)** dei TIF all'indicizzazione
- Aggiungere metadato `revision_superseded: true` alle versioni vecchie e abbassarne il ranking

---

## 📊 Priorità Suggerita (Impatto / Effort)

| # | Proposta | Impatto | Effort |
|---|----------|---------|--------|
| 1 | Re-ranker locale (`cross-encoder`) | Alto | Basso |
| 2 | Chunking strutturato per zona disegno | Molto Alto | Medio |
| 3 | Sparse vectors nativi Qdrant (BM42) | Alto | Medio |
| 4 | Estrazione JSON strutturato da cartiglio | Molto Alto | Medio |
| 5 | ColBERT / Late Interaction | Alto | Alto |
| 6 | CLIP embeddings per ricerca visiva | Medio | Alto |

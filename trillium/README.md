# Trillium V2 — Sistema RAG per Stima Pesi Componenti Pompe

Sistema avanzato di **Retrieval-Augmented Generation (RAG)** sviluppato per **Trillium Pumps Italy S.p.A.**, progettato per l'indicizzazione e la ricerca semantica su disegni tecnici di pompe, per supportare la **stima AI dei pesi dei componenti principali**.

> **Ultimo aggiornamento:** 27 febbraio 2026 (Fase 14 — Trend Analysis)

> **Nota V2:** Questo progetto (TrilliumVersione2) condivide con TrilliumVersione1 il motore RAG core e lo stesso database vettoriale Qdrant (collezione `trilliumdoc`). L'obiettivo specifico di V2 è la stima dei pesi dei componenti di pompe centrifughe a partire da disegni tecnici storici e parametri di progetto.

## 📋 Indice

- [Panoramica](#panoramica)
- [Funzionalità Principali](#funzionalità-principali)
- [Formati Supportati](#formati-supportati)
- [Installazione](#installazione)
- [Configurazione](#configurazione)
- [Utilizzo](#utilizzo)
- [Architettura](#architettura)
- [Database Vettoriali](#database-vettoriali)
- [Provider LLM](#provider-llm)
- [Caratteristiche Avanzate](#caratteristiche-avanzate)
  - [Ottimizzazioni Performance](#-ottimizzazioni-performance)
- [Parametri di Configurazione](#-parametri-di-configurazione)
- [Troubleshooting](#-troubleshooting)

---

## 🎯 Panoramica

Trillium V2 è un sistema RAG completo specializzato nella **stima dei pesi dei componenti di pompe centrifughe**. Permette di:

- **Indicizzare** disegni tecnici e documenti di pompe in vari formati (PDF, Excel, TIF, immagini)
- **Estrarre testo** da disegni tecnici complessi usando OCR locale e servizi cloud (OpenAI Vision, Google Cloud Vision, Claude, Gemini)
- **Cercare semanticamente** pompe di riferimento con geometria e caratteristiche simili
- **Rispondere a domande** sui parametri di progetto usando LLM avanzati con contesto dai documenti indicizzati
- **Supportare la stima pesi** applicando formule di scaling (es. `pnew = pref × f^(2.3÷2.4) × ρnew/ρref`)
- **Chat conversazionale** stile ChatGPT con domande di follow-up automatiche

Il sistema è ottimizzato per disegni tecnici di pompe centrifughe, normative e documentazione ingegneristica. I documenti di riferimento includono ~164 file tra SOP (procedure), Mod (tool di calcolo Excel/Python), normative internazionali e letteratura tecnica.

---

## ✨ Funzionalità Principali

### 1. **Indicizzazione Multi-Formato**
- Supporto per PDF, Excel, Word, immagini (TIF, BMP, PNG, HEIC/HEIF), file di testo e log
- **Estrazione Excel avanzata**: Include formule, commenti, nomi definiti (named ranges) e struttura completa
- Estrazione ibrida: locale (veloce) + cloud (preciso)
- Chunking automatico per documenti grandi
- Gestione intelligente di file troppo grandi (>25MB)

### 2. **Ricerca Semantica**
- Ricerca vettoriale basata su embedding
- Recupero dei documenti più rilevanti per ogni query
- Supporto per database vettoriali multipli (ChromaDB, Qdrant)

### 3. **Query RAG Conversazionale**
- Modalità chat continua (stile ChatGPT)
- **Selezione modello LLM direttamente nella chat** - Scegli quale modello usare per ogni risposta
- **Ricerca web opzionale** - Integra informazioni dal web con i documenti indicizzati
- Generazione automatica di domande di follow-up
- Mantenimento della storia della conversazione
- **Risposte dettagliate e strutturate** - Spiegazioni complete step-by-step simili a ChatGPT

### 4. **Confronto Modelli**
- Confronta risposte di diversi LLM sulla stessa domanda
- Supporto per OpenAI, Anthropic, Google Gemini, OpenRouter

### 5. **Gestione Database**
- Reset completo del database
- Indicizzazione incrementale (evita duplicati)
- Modalità RAM/Disk ibrida per ChromaDB (velocità + persistenza)

### 6. **Ottimizzazioni Performance** ⚡
- **Parallelizzazione**: Processa più file contemporaneamente (3-5x più veloce)
- **Batch Processing**: Processa chunk multipli insieme per ridurre chiamate API
- **Gestione Rate Limits**: Retry automatico con backoff esponenziale per errori 429
- **Gestione Intelligente**: Fallback automatico da batch a chunk singoli per documenti molto grandi
- **Nessuna perdita di dati**: Tutti i chunk vengono tracciati e riprovati in caso di errori

### 7. **Premium Features (Fase 12)**
- **🎓 Onboarding Guidato** — Wizard 3 step per nuovi utenti (intro, stima di prova, spiegazione risultati)
- **🔔 Alert Intelligenti** — Copertura documentale automatica con barra 0-100% e suggerimenti
- **📂 Multi-Progetto** — Salva, carica e gestisci configurazioni di parametri con nome progetto
- **📝 Riferimento Editabile** — Inserisci pesi reali di pompe costruite per validare le stime
- **📊 Confronto Stima vs Reale** — Accuratezza automatica con badge 🟢/🟡/🔴
- **📘 Manuale Online** — Guida completa integrata con 7 tab, esempi pratici e FAQ

### 8. **Trend Analysis & Predizione Costi (Fase 14)**
- **📈 Dashboard Analytics** — KPI in tempo reale (stime totali, peso medio, costo medio, confidenza)
- **📊 Distribuzione** — Grafici interattivi per famiglia pompa e materiale
- **💰 Predizione Costi** — Stima costo materia prima (peso × €/kg per materiale)
- **🎯 Confronto vs Media** — Badge automatico se la stima è sopra/sotto la media della famiglia
- **📥 Export CSV** — Scarica tutti i dati storico per analisi esterna

---

## 📄 Formati Supportati

### Documenti
- **PDF** (`.pdf`) - Estratto con PyMuPDF
- **Word** (`.docx`, `.doc`) - Estratto con python-docx
- **Excel** (`.xlsx`, `.xls`, `.xlsm`) - Estratto con pandas/openpyxl
  - **Estrazione avanzata**: Include formule, commenti, nomi definiti (named ranges), valori calcolati
  - Mantiene la struttura delle tabelle e dei fogli multipli
- **Testo** (`.txt`) - Lettura diretta
- **Log** (`.log`) - Lettura diretta con supporto multi-encoding

### Immagini
- **TIF/TIFF** (`.tif`, `.tiff`) - OCR con Tesseract locale o servizi cloud
- **BMP** (`.bmp`) - OCR con Tesseract locale
- **PNG** (`.png`) - OCR con Tesseract locale o servizi cloud
- **HEIC/HEIF** (`.heic`, `.heif`) - OCR con Tesseract locale (richiede pillow-heif)

**Nota**: Per le immagini, il sistema usa una pipeline ibrida:
1. Prima prova OCR locale (Tesseract) - veloce e senza perdita qualità
2. Se insufficiente, prova servizi cloud che supportano il formato nativo:
   - Google Cloud Vision API (supporta TIF nativo)
   - Claude 3.5 Sonnet su OpenRouter (supporta TIF nativo)
   - Gemini su OpenRouter (supporta TIF nativo)
   - OpenAI Vision (solo PNG, JPEG, GIF, WEBP)

---

## 📦 Installazione

### Prerequisiti

- Python 3.10+
- Tesseract OCR (per OCR locale su immagini)
  ```bash
  # macOS
  brew install tesseract
  
  # Ubuntu/Debian
  sudo apt-get install tesseract-ocr
  
  # Windows
  # Scarica da: https://github.com/UB-Mannheim/tesseract/wiki
  ```

### Installazione Dipendenze

```bash
# Clona o naviga nella directory del progetto
cd trillium

# Installa le dipendenze
pip install -r requirements.txt
```

### Dipendenze Principali

- `chromadb` o `qdrant-client` - Database vettoriali
- `openai>=1.2.0` - API OpenAI
- `anthropic>=0.18.0` - API Anthropic (Claude)
- `google-genai>=0.2.0` - API Google Gemini
- `pymupdf` - Estrazione PDF
- `pytesseract` - OCR locale
- `pillow` - Elaborazione immagini
- `pandas`, `openpyxl` - Supporto Excel (con estrazione formule e commenti)
- `python-docx` - Supporto Word
- `pillow-heif` - Supporto HEIC/HEIF
- `google-cloud-vision` - Google Cloud Vision API
- `duckduckgo-search>=4.0.0` - Ricerca web opzionale
- `beautifulsoup4>=4.12.0` - Parsing HTML per ricerca web (fallback)
- `rich` - Output formattato
- `tqdm` - Progress bar
- `streamlit>=1.28.0` - Interfaccia grafica web
- `plotly>=5.17.0` - Grafici interattivi

---

## ⚙️ Configurazione

### 1. File `.env`

Crea un file `.env` nella root del progetto con le tue chiavi API:

```env
# Provider LLM principale (openai, openrouter, anthropic, gemini)
PROVIDER=openai

# Chiavi API OpenAI
OPENAI_API_KEY=sk-proj-...

# Chiavi API OpenRouter (per accedere a Claude/Gemini)
OPENROUTER_API_KEY=sk-or-...

# Chiavi API dirette
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIzaSy...

# Google Cloud Vision (opzionale, per OCR su immagini)
GOOGLE_CLOUD_VISION_KEY=...
GOOGLE_CLOUD_VISION_PROJECT=...

# Database vettoriale (chromadb o qdrant)
VECTOR_DB=chromadb

# Configurazione Qdrant (se usi Qdrant)
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=documents

# Configurazione ChromaDB
CHROMA_DB_PATH=./rag_db

# Modalità RAM per ChromaDB (true/false)
USE_RAM_MODE=true
RAM_SAVE_INTERVAL=300

# ============================================================
# OTTIMIZZAZIONI PERFORMANCE
# ============================================================

# Numero di file da processare in parallelo (0 = sequenziale, consigliato 5-10)
# Con 5 worker, 5 file vengono processati contemporaneamente
PARALLEL_WORKERS=5

# Dimensione batch per chunk (numero di chunk da processare insieme)
# Riduci se hai errori "max_tokens" o rate limits
CHUNK_BATCH_SIZE=50

# Configurazione SharePoint/OneDrive (opzionale)
# Se non configurate, verrà usata autenticazione interattiva (device code flow)
SHAREPOINT_CLIENT_ID=your_client_id
SHAREPOINT_TENANT_ID=your_tenant_id
SHAREPOINT_CLIENT_SECRET=your_client_secret  # Opzionale, per app-only auth
```

### 2. Configurazione SharePoint/OneDrive (opzionale)

Trillium supporta l'indicizzazione diretta da cartelle SharePoint/OneDrive. Puoi configurare le credenziali Azure AD nel file `.env`, oppure usare l'autenticazione interattiva.

#### Opzione A: Autenticazione Interattiva (Consigliata per uso personale)

Non serve configurare nulla. Quando indicizzi da SharePoint/OneDrive, verrà richiesto di autenticarti tramite device code flow:

1. Il sistema mostrerà un URL e un codice
2. Apri l'URL nel browser
3. Inserisci il codice
4. Autorizza l'applicazione

#### Opzione B: App Azure AD (Consigliata per uso aziendale)

1. **Registra un'app in Azure AD:**
   - Vai su [Azure Portal](https://portal.azure.com) → Azure Active Directory → App registrations
   - Crea una nuova registrazione
   - Aggiungi le seguenti API permissions:
     - `Files.Read.All` (Microsoft Graph)
     - `Sites.Read.All` (Microsoft Graph)
   - Se usi app-only auth, crea un client secret

2. **Configura nel `.env`:**
   ```env
   SHAREPOINT_CLIENT_ID=your_client_id
   SHAREPOINT_TENANT_ID=your_tenant_id
   SHAREPOINT_CLIENT_SECRET=your_client_secret  # Solo per app-only auth
   ```

#### Formati URL Supportati

- **OneDrive Personale:**
  ```
  https://[tenant]-my.sharepoint.com/personal/[user]/_layouts/15/onedrive.aspx?id=...
  ```

- **SharePoint Site:**
  ```
  https://[tenant].sharepoint.com/sites/[site]/Shared%20Documents/...
  ```

### 3. Avvio Database Vettoriale

Trillium supporta due database vettoriali: **ChromaDB** (default) e **Qdrant**. I dati sono **sempre persistenti** - quando esci e rientri nel programma, tutti i documenti indicizzati sono ancora disponibili.

#### Opzione A: ChromaDB (Default - Nessuna configurazione richiesta)

ChromaDB è il database di default e **non richiede configurazione**. Funziona immediatamente:

- **Modalità RAM** (default): Carica in memoria per velocità, salva automaticamente su disco ogni 5 minuti e all'uscita
- **Modalità Disk**: Salva direttamente su disco (più lento ma più sicuro)
- **Dati salvati in**: `./rag_db/` (cartella locale)

**Nessuna azione richiesta** - funziona subito! ✅

#### Opzione B: Qdrant (Consigliato per dataset grandi)

Qdrant è un database esterno più performante per dataset grandi (>1000 documenti). Richiede Docker.

**1. Verifica se Qdrant è già in esecuzione:**
```bash
docker ps | grep qdrant
```

**2. Se non è in esecuzione, avvialo:**

**Metodo 1 - Script automatico (consigliato):**
```bash
chmod +x start_qdrant.sh
./start_qdrant.sh
```

**Metodo 2 - Docker manuale:**
```bash
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

**3. Verifica che funzioni:**
```bash
# Controlla lo stato
docker ps | grep qdrant

# Testa la connessione
curl http://localhost:6333/health

# Apri la dashboard (opzionale)
open http://localhost:6333/dashboard
```

**4. Configura nel `.env` per usare Qdrant:**
```env
VECTOR_DB=qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=documents
```

**5. Riavvia il programma** - ora userà Qdrant!

**Comandi utili per Qdrant:**
```bash
# Ferma Qdrant
docker stop qdrant

# Riavvia Qdrant
docker start qdrant

# Rimuovi Qdrant (ATTENZIONE: cancella i dati!)
docker rm -f qdrant

# Vedi i log
docker logs qdrant
```

**Nota importante**: Se usi Qdrant, assicurati che sia sempre in esecuzione quando usi Trillium. Se Qdrant non è attivo, il programma non funzionerà.

### 4. Configurazione Modelli

I modelli di default sono configurati in `config.py`:

- **LLM**: GPT-4o (OpenAI, default), Claude 3.5 Sonnet (Anthropic), Gemini 2.5 Flash (Google)
- **Embedding**: text-embedding-3-large
- **Vision**: GPT-4o, Claude 3.5 Sonnet, Gemini 2.0 Flash

**Nota**: Il modello OpenAI di default è `gpt-4o` (più affidabile). Puoi cambiarlo in `config.py` o tramite variabile d'ambiente `LLM_MODEL_OPENAI`.

Puoi modificarli in `config.py` o tramite variabili d'ambiente.

---

## 💻 Utilizzo

### 🎨 Interfaccia Grafica Streamlit (Consigliata)

Trillium include un'interfaccia grafica moderna e intuitiva basata su Streamlit.

#### Avvio Interfaccia Streamlit

**Metodo 1 - Script automatico:**
```bash
./run_streamlit.sh
```

**Metodo 2 - Comando diretto:**
```bash
streamlit run streamlit_app.py
```

L'applicazione si aprirà automaticamente nel browser all'indirizzo `http://localhost:8501`

**Nota**: I grafici nella Dashboard mostrano **dati reali** estratti dal database. La distribuzione documenti viene calcolata analizzando i metadati di tutti i documenti indicizzati.

#### Funzionalità Interfaccia

1. **🏠 Dashboard**
   - Statistiche in tempo reale (documenti, chunk, dimensione DB)
   - **Grafici interattivi con dati reali**:
     - Distribuzione documenti per tipo (PDF, Word, Excel, Immagini, Altri) - dati estratti dal database
     - Grafico a barre con statistiche documenti
   - Informazioni sistema e configurazione
   - Metriche performance (parallel workers, batch size)

2. **📁 Indicizzazione**
   - **Cartella Locale**: Drag & drop o inserimento percorso
   - **SharePoint/OneDrive**: Inserimento URL con autenticazione automatica
   - Progress bar animata durante l'indicizzazione
   - Statistiche finali con confronto prima/dopo
   - Reset database con conferma

3. **💬 Chat RAG**
   - Interfaccia conversazionale stile ChatGPT
   - **Selezione modello LLM direttamente nella chat** - Scegli quale modello usare per ogni risposta
   - **Ricerca web opzionale** - Checkbox per integrare informazioni dal web
   - Storia conversazionale persistente
   - Visualizzazione documenti sorgente utilizzati
   - **Risposte dettagliate e strutturate** - Spiegazioni complete con sezioni numerate
   - Domande suggerite automatiche

4. **⚖️ Confronto Modelli**
   - Confronto side-by-side o in tabs di diversi LLM
   - Stessa domanda, risposte multiple con stesso contesto RAG
   - **Risultati visualizzati direttamente nell'interfaccia** (non più solo nella console)
   - Tabella comparativa con anteprima risposte
   - Metriche dettagliate (lunghezza caratteri, numero parole per modello)
   - Info debug per troubleshooting

5. **⚙️ Configurazione**
   - Visualizzazione stato database
   - Status provider LLM e chiavi API
   - Parametri performance
   - Informazioni sistema

6. **📘 Manuale Online**
   - Guida completa del sistema con 6 tab
   - Esempi pratici per ogni funzionalità
   - FAQ e troubleshooting
   - Workflow tipici e best practice

#### Vantaggi Interfaccia Streamlit

- ✅ **UI Moderna**: Interfaccia pulita e professionale
- ✅ **Real-time**: Aggiornamenti in tempo reale durante operazioni
- ✅ **Visualizzazioni**: Grafici interattivi con **dati reali** estratti dal database
- ✅ **User-friendly**: Navigazione intuitiva con sidebar
- ✅ **Responsive**: Funziona su desktop e tablet
- ✅ **Dati Veri**: I grafici mostrano statistiche reali dei documenti indicizzati
- ✅ **Progress Tracking**: Progress bar e feedback visivo durante operazioni lunghe
- ✅ **Risultati Persistenti**: I risultati del confronto modelli rimangono visibili anche dopo il refresh

### 📟 Modalità Interattiva CLI

```bash
python app.py
```

Ti apparirà un menu con le seguenti opzioni:

1. **Indicizza una cartella locale** - Aggiunge documenti da una cartella locale
2. **Indicizza da SharePoint/OneDrive (URL)** - Aggiunge documenti da SharePoint/OneDrive
3. **Fai una domanda (RAG)** - Modalità chat conversazionale
4. **Confronta modelli** - Confronta risposte di diversi LLM
5. **Reset database RAG** - Cancella tutti i documenti indicizzati
6. **Mostra configurazione attuale** - Visualizza le impostazioni
7. **Esci**

### 📟 Modalità da Linea di Comando

```bash
# Indicizza una cartella locale
python app.py index /path/to/documents

# Indicizza da SharePoint/OneDrive (URL)
python app.py index "https://tenant-my.sharepoint.com/personal/user/_layouts/15/onedrive.aspx?id=..."

# Fai una query
python app.py query "Qual è il sovrametallo da aggiungere sulle flange?"

# Confronta modelli
python app.py compare "Dimmi i dati delle pompe nei documenti"

# Reset database
python app.py reset

# Mostra configurazione
python app.py config
```

### Esempio di Sessione Chat

```
=== MENU PRINCIPALE ===
1) Indicizza una cartella
2) Fai una domanda (RAG)
...

Scelta: 2

💬 Modalità Chat RAG - Scrivi 'stop' per tornare al menu

Scegli quale LLM usare per questa sessione:
  1) OpenAI (GPT-5.1)
  2) Anthropic (Claude 3.5 Sonnet)
  3) Google Gemini (2.5 Flash)

Scelta: 1

Domanda: Qual è il sovrametallo da aggiungere sulle flange di unione?

→ Recupero documenti rilevanti...
✓ Documenti recuperati
→ Genero la risposta dal modello...

[RISPOSTA DEL MODELLO]

💡 Domande di approfondimento suggerite:
  1) Quali sono le specifiche tecniche per il sovrametallo?
  2) Come viene applicato il sovrametallo nella pratica?
  3) Ci sono differenze tra tipi di flange?

Domanda (o 'stop'): ...
```

---

## 🏗️ Architettura

### Componenti Principali

```
trillium/
├── app.py                 # Interfaccia CLI principale e menu
├── streamlit_app.py       # Interfaccia grafica Streamlit
├── run_streamlit.sh       # Script per avviare Streamlit
├── config.py              # Configurazione centralizzata
├── requirements.txt       # Dipendenze Python
│
└── rag/
    ├── extractor.py       # Estrazione testo da documenti (con supporto avanzato Excel)
    ├── indexer.py         # Indicizzazione e embedding
    ├── query.py           # Query RAG e generazione risposte (con ricerca web opzionale)
    ├── web_search.py      # Ricerca web opzionale (DuckDuckGo)
    ├── model_compare.py   # Confronto modelli LLM
    ├── qdrant_db.py       # Integrazione Qdrant
    └── sharepoint_connector.py  # Connettore SharePoint/OneDrive
```

### Pipeline di Estrazione

1. **Tentativo Locale** (veloce, senza API)
   - PDF → PyMuPDF
   - Excel → pandas/openpyxl
   - Word → python-docx
   - Immagini → Tesseract OCR
   - Log/TXT → lettura diretta

2. **Fallback Cloud** (se locale insufficiente)
   - Immagini → Google Cloud Vision, Claude, Gemini, OpenAI Vision
   - Supporto nativo per TIF (senza conversione)

### Pipeline RAG

1. **Indicizzazione**:
   - Estrazione testo (con formule/commenti per Excel) → Chunking (se >6000 caratteri) → Embedding → Salvataggio in DB

2. **Query**:
   - Query utente → Embedding query → Ricerca vettoriale → Recupero top-K documenti → (Opzionale) Ricerca web → Costruzione contesto → LLM → Risposta dettagliata e strutturata

---

## 🗄️ Database Vettoriali

### ⚠️ Persistenza dei Dati

**I dati sono sempre persistenti!** Quando esci e rientri nel programma, tutti i documenti indicizzati sono ancora disponibili. Non devi re-indicizzare ogni volta.

### ChromaDB (Default - Consigliato per iniziare)

**Nessuna configurazione richiesta** - funziona immediatamente! ✅

- **Modalità RAM/Disk Ibrida**: 
  - Carica in RAM per velocità durante l'uso
  - Salva automaticamente su disco ogni 5 minuti
  - Salva anche all'uscita del programma (garantito)
- **Persistenza**: Dati salvati in `./rag_db/` (cartella locale)
- **Caricamento automatico**: All'avvio, carica automaticamente tutti i dati da disco
- **Vantaggi**: Facile da usare, integrato, buone prestazioni per dataset medi (<1000 documenti)
- **Configurazione**: `VECTOR_DB=chromadb` in `.env` (default)

**Come funziona:**
1. Indicizzi i documenti → salvati in RAM e su disco
2. Esci dal programma → salvataggio automatico finale
3. Rientri nel programma → caricamento automatico da disco
4. Tutti i documenti sono ancora disponibili! 🎉

### Qdrant (Consigliato per dataset grandi)

**Richiede Docker** - più performante per dataset grandi (>1000 documenti)

- **Modalità Server**: Database esterno che deve essere sempre in esecuzione
- **Persistenza**: Dati salvati nel container/volume Docker (persistenti)
- **Vantaggi**: Scalabile, ottime prestazioni per dataset grandi, distribuito
- **Configurazione**: 
  ```env
  VECTOR_DB=qdrant
  QDRANT_HOST=localhost
  QDRANT_PORT=6333
  QDRANT_COLLECTION_NAME=documents
  ```

**Come attivare Qdrant:**

1. **Verifica se è già in esecuzione:**
   ```bash
   docker ps | grep qdrant
   ```

2. **Se non è in esecuzione, avvialo:**
   ```bash
   # Metodo 1: Script automatico (consigliato)
   ./start_qdrant.sh
   
   # Metodo 2: Docker manuale
   docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant
   ```

3. **Verifica che funzioni:**
   ```bash
   curl http://localhost:6333/health
   # Dovrebbe rispondere: {"status":"ok"}
   ```

4. **Configura nel `.env`** (vedi sopra)

5. **Riavvia Trillium** - ora userà Qdrant!

**Comandi utili:**
```bash
# Ferma Qdrant
docker stop qdrant

# Riavvia Qdrant
docker start qdrant

# Vedi i log
docker logs qdrant

# Dashboard web (opzionale)
open http://localhost:6333/dashboard
```

**⚠️ Importante**: Se usi Qdrant, assicurati che sia sempre in esecuzione quando usi Trillium. Se Qdrant non è attivo, il programma non funzionerà.

**Nota**: Puoi cambiare database in qualsiasi momento modificando `VECTOR_DB` in `.env`. I dati non vengono migrati automaticamente - devi re-indicizzare se cambi database.

---

## 🤖 Provider LLM

### OpenAI

- **Modelli**: GPT-4o (default, consigliato), GPT-4-turbo, GPT-4, GPT-3.5-turbo
- **Embedding**: text-embedding-3-large
- **Configurazione**: `OPENAI_API_KEY` in `.env`
- **Modello personalizzato**: Imposta `LLM_MODEL_OPENAI` in `.env` o `config.py`
- **Note**: 
  - Il sistema include fallback automatico se il modello configurato non è disponibile
  - Gestione errori migliorata con logging dettagliato
  - System message ottimizzato per risposte dettagliate e strutturate

### Anthropic (Claude)

- **Modelli**: Claude 3.5 Sonnet
- **Configurazione**: `ANTHROPIC_API_KEY` in `.env`
- **Nota**: Supporta immagini TIF nativamente

### Google Gemini

- **Modelli**: Gemini 2.5 Flash
- **Configurazione**: `GEMINI_API_KEY` in `.env`
- **Nota**: Supporta immagini TIF nativamente

### OpenRouter

- **Modelli**: Accesso a Claude, Gemini, GPT e altri tramite OpenRouter
- **Configurazione**: `OPENROUTER_API_KEY` in `.env`
- **Vantaggi**: Un'unica chiave per accedere a più modelli

---

## 🎨 Caratteristiche Avanzate

### ⚡ Ottimizzazioni Performance

Trillium include ottimizzazioni avanzate per indicizzare grandi quantità di documenti in modo efficiente:

#### 1. **Parallelizzazione Multi-File**
- **Processamento parallelo**: Più file vengono indicizzati contemporaneamente
- **Configurazione**: `PARALLEL_WORKERS=5` (default: 5 file in parallelo)
- **Vantaggi**: 
  - Indicizzazione 3-5x più veloce per cartelle con molti file
  - Utilizzo ottimale delle risorse CPU e I/O
  - Progress bar mostra file completati in ordine casuale (normale in modalità parallela)
- **Quando usare**: Consigliato per cartelle con >10 file
- **Quando disabilitare**: Imposta `PARALLEL_WORKERS=0` per modalità sequenziale (più lenta ma più stabile)

#### 2. **Batch Processing per Chunk**
- **Processamento in batch**: Chunk multipli vengono processati insieme
- **Configurazione**: `CHUNK_BATCH_SIZE=50` (default: 50 chunk per batch)
- **Vantaggi**:
  - Riduce il numero di chiamate API all'embedding model
  - Più veloce per documenti grandi con molti chunk
  - Gestione automatica se il batch è troppo grande
- **Fallback intelligente**: Se un batch fallisce per troppi token, passa automaticamente a batch più piccoli o chunk singoli

#### 3. **Gestione Rate Limits (429)**
- **Retry automatico**: Gli errori di rate limit vengono gestiti automaticamente
- **Backoff esponenziale**: Attesa progressiva (2s, 4s, 8s, fino a 60s) tra i retry
- **Semaforo per richieste simultanee**: Max 3 richieste embedding simultanee (evita rate limits)
- **Vantaggi**:
  - I file vengono indicizzati anche in caso di rate limit temporanei
  - Nessuna perdita di dati - tutti i chunk vengono riprovati automaticamente
  - Messaggi informativi invece di errori critici

#### 4. **Gestione Intelligente di Documenti Grandi**
- **Chunking automatico**: Documenti >6000 caratteri vengono divisi automaticamente
- **Batch dinamico**: Se troppi chunk insieme causano errori, passa automaticamente a batch più piccoli
- **Modalità chunk-per-chunk**: Fallback garantito per documenti molto grandi (es. 5000+ chunk)
- **Progress tracking**: Mostra progresso ogni 50 chunk per documenti grandi

#### Esempio di Output con Parallelizzazione

```
⚡ Modalità parallela attiva: 5 file processati contemporaneamente
📦 Batch size chunk: 50 chunk per batch

Indicizzazione: 15%|███▌ | 24/160 [00:06<00:25, 5.30it/s, ✓ file.pdf... (1 chunk) [4 attivi]]
```

Il contatore `[4 attivi]` mostra quanti file sono ancora in elaborazione simultanea.

#### Configurazione Consigliata per Dataset Grandi

Per indicizzare **5000 documenti da 1.5MB ciascuno**:

```env
# Parallelizzazione: 5-10 worker (aumenta se hai CPU potenti)
PARALLEL_WORKERS=8

# Batch size: 50-100 chunk (riduci se hai rate limits)
CHUNK_BATCH_SIZE=75

# Database: Qdrant per dataset grandi
VECTOR_DB=qdrant
```

**Tempi stimati**:
- **Sequenziale**: ~8-10 ore
- **Parallelo (8 worker)**: ~1-1.5 ore
- **Con Qdrant**: ~30-45 minuti (per query più veloci)

### Chunking Automatico

I documenti più grandi di 6000 caratteri vengono automaticamente divisi in chunk più piccoli prima dell'embedding, per evitare errori di limite token.

### Gestione File Grandi

- File immagini >25MB vengono **flagati** ma **non processati** (per preservare qualità)
- Messaggio di errore chiaro con dimensione file

### Modalità RAM per ChromaDB

- Carica il database in RAM all'avvio (se piccolo)
- Salva periodicamente su disco (default: ogni 5 minuti)
- Best of both worlds: velocità + persistenza

### Generazione Domande Follow-Up

Il sistema genera automaticamente 3-4 domande di approfondimento basate sulla risposta, per facilitare l'esplorazione dell'argomento.

### Indicizzazione Incrementale

- Controlla duplicati prima di indicizzare
- Puoi aggiungere documenti da cartelle diverse senza duplicati
- Supporto per re-indicizzazione selettiva
- **Nessuna perdita di dati**: Tutti i chunk vengono tracciati e riprovati in caso di errori

### Supporto Multi-Encoding

I file `.log` e `.txt` vengono letti con supporto per UTF-8, latin-1 e altri encoding comuni, con fallback automatico.

### 🌐 Ricerca Web Opzionale (Nuovo)

Trillium supporta l'integrazione opzionale di informazioni dal web nelle risposte RAG:

- **Attivazione**: Checkbox nell'interfaccia Chat RAG per abilitare/disabilitare la ricerca web
- **Funzionamento**: 
  - La ricerca web viene eseguita **DOPO** la ricerca nei documenti indicizzati
  - I risultati web vengono integrati nel contesto insieme ai documenti
  - I documenti indicizzati hanno sempre priorità sui risultati web
- **Tecnologia**: Usa DuckDuckGo (gratuito, senza API key richiesta)
- **Vantaggi**: 
  - Completa le informazioni quando i documenti non sono sufficienti
  - Fornisce contesto aggiuntivo su argomenti generali
  - Completamente opzionale - puoi attivarla solo quando necessario

**Come usare**:
1. Vai alla pagina "💬 Chat RAG"
2. Attiva il checkbox "🌐 Integra ricerca web nelle risposte"
3. Fai una domanda - il sistema cercherà prima nei documenti, poi sul web, e integrerà tutto nella risposta

---

## 📊 Parametri di Configurazione

In `config.py` puoi modificare:

### Parametri Query RAG
- `TOP_K = 8` - Numero documenti da recuperare per query (aumentato per più contesto)
- `MIN_TEXT_LENGTH = 30` - Soglia minima testo per considerare estrazione valida
- `CONTEXT_CHARS_PER_DOC = 4000` - Caratteri per documento nel contesto LLM (aumentato per risposte più dettagliate)
- `MAX_RESPONSE_TOKENS = 4000` - Limite token per risposta LLM (aumentato per risposte più complete)

**Nota**: Tutti questi parametri sono configurabili via variabili d'ambiente nel file `.env`.

### Parametri Indicizzazione
- `MAX_EMBEDDING_CHARS = 6000` - Max caratteri per embedding (chunking automatico)
- `USE_RAM_MODE = true` - Abilita modalità RAM per ChromaDB
- `RAM_SAVE_INTERVAL = 300` - Intervallo salvataggio su disco (secondi)

### Parametri Performance (Nuovi)
- `PARALLEL_WORKERS = 5` - Numero di file da processare in parallelo (0 = sequenziale)
  - **Consigliato**: 5-10 per la maggior parte dei casi
  - **Dataset grandi**: 8-10 per massima velocità
  - **Rate limits frequenti**: 3-5 per ridurre richieste simultanee
- `CHUNK_BATCH_SIZE = 50` - Numero di chunk da processare insieme in un batch
  - **Consigliato**: 50-100 per documenti normali
  - **Documenti molto grandi**: 25-50 per evitare errori "max_tokens"
  - **Rate limits**: 20-30 per ridurre richieste API

### Variabili d'Ambiente (.env)

Tutti questi parametri possono essere sovrascritti nel file `.env`:

```env
# Performance
PARALLEL_WORKERS=5
CHUNK_BATCH_SIZE=50

# Database
VECTOR_DB=chromadb
USE_RAM_MODE=true
RAM_SAVE_INTERVAL=300

# Query RAG
TOP_K=8
CONTEXT_CHARS_PER_DOC=4000
MAX_RESPONSE_TOKENS=4000

# Modelli LLM
LLM_MODEL_OPENAI=gpt-4o

# Embedding
MAX_EMBEDDING_CHARS=6000
```

---

## 🔧 Troubleshooting

### Errore: "OpenAI API key non configurata"
- Verifica che `OPENAI_API_KEY` sia presente in `.env`
- Controlla che il file `.env` sia nella root del progetto

### Errore: "File troppo grande: >25MB"
- I file >25MB non vengono processati per preservare qualità
- Considera di dividere il file o usare un servizio cloud che supporta file grandi

### Errore: "maximum context length exceeded"
- Il documento è troppo grande per l'embedding
- Il sistema dovrebbe fare chunking automatico, ma se persiste, riduci `MAX_EMBEDDING_CHARS` in `config.py`
- Riduci anche `CHUNK_BATCH_SIZE` se hai molti chunk insieme

### Errore: "Rate limit exceeded" (429)
- **Normale in modalità parallela**: Il sistema gestisce automaticamente con retry
- **Se persistente**: 
  - Riduci `PARALLEL_WORKERS` a 3-5
  - Riduci `CHUNK_BATCH_SIZE` a 20-30
  - Attendi qualche minuto e riprova (il sistema riproverà automaticamente)
- **Messaggio "Collection già esistente"**: Normale in modalità parallela, non è un errore

### Indicizzazione troppo lenta
- **Abilita parallelizzazione**: Imposta `PARALLEL_WORKERS=5-10` in `.env`
- **Usa Qdrant**: Più veloce per dataset grandi (>1000 documenti)
- **Aumenta batch size**: `CHUNK_BATCH_SIZE=75-100` (se non hai rate limits)
- **Verifica rate limits**: Se hai molti errori 429, riduci `PARALLEL_WORKERS`

### Chunk non vengono indicizzati
- **Controlla i log finali**: Il sistema mostra statistiche complete
- **Cerca "Chunk mancanti" o "Chunk falliti"**: Indica quali chunk non sono stati indicizzati
- **File con chunk falliti**: Vengono elencati alla fine dell'indicizzazione
- **Riprova l'indicizzazione**: I chunk falliti verranno riprovati automaticamente

### Qdrant non si connette
- Verifica che il container Docker sia avviato: `docker ps | grep qdrant`
- Controlla `QDRANT_HOST` e `QDRANT_PORT` in `.env`
- Riavvia Qdrant: `docker restart qdrant`

### OCR locale non funziona
- Verifica che Tesseract sia installato: `tesseract --version`
- Su macOS: `brew install tesseract`
- Su Linux: `sudo apt-get install tesseract-ocr`

### Ricerca web non funziona
- Installa le dipendenze: `pip install duckduckgo-search beautifulsoup4`
- Verifica la connessione internet
- Se DuckDuckGo non funziona, il sistema userà automaticamente un fallback con BeautifulSoup

---

## 📝 Note

- Il sistema è ottimizzato per documenti tecnici e ingegneristici
- Per dataset molto grandi (>1000 documenti), considera Qdrant per migliori prestazioni
- I file TIF vengono processati senza conversione per preservare qualità
- La modalità chat mantiene la storia della conversazione per contesto continuo
- **Interfaccia Streamlit**: I grafici mostrano dati reali estratti dal database, non dati di esempio
- **Confronto Modelli**: I risultati vengono visualizzati direttamente nell'interfaccia con tabs, tabelle comparative e metriche dettagliate
- **Estrazione Excel avanzata**: Include formule, commenti e nomi definiti per una comprensione completa dei fogli di calcolo
- **Risposte dettagliate**: Il sistema genera risposte strutturate e complete simili a ChatGPT, con spiegazioni step-by-step
- **Ricerca web opzionale**: Puoi integrare informazioni dal web quando necessario, mantenendo sempre la priorità sui documenti indicizzati

### Performance e Scalabilità

- **Dataset piccoli (<100 file)**: ChromaDB + sequenziale va bene
- **Dataset medi (100-1000 file)**: ChromaDB + parallelizzazione (5-8 worker)
- **Dataset grandi (>1000 file)**: Qdrant + parallelizzazione (8-10 worker) + batch processing
- **Documenti molto grandi (>10MB)**: Il sistema gestisce automaticamente con chunking e batch processing

### Garanzia di Integrità Dati

- **Nessuna perdita di dati**: Tutti i chunk vengono tracciati e riprovati in caso di errori
- **Statistiche complete**: Alla fine dell'indicizzazione vedi esattamente quanti chunk sono stati indicizzati
- **File con errori**: Vengono elencati con il numero di chunk falliti
- **Retry automatico**: Rate limits e errori temporanei vengono gestiti automaticamente

---

## 📄 Licenza

[Specifica la licenza del progetto]

---

## 🤝 Contributi

[Istruzioni per contribuire al progetto]

---

**Sviluppato per Trillium Pumps Italy S.p.A. — Stima AI pesi componenti pompe centrifughe (TrilliumVersione2). Ultimo aggiornamento: 26 febbraio 2026 (sera — Fase 12).**


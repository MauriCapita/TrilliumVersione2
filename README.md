# Trillium V2 — AI Weight Estimation System

Sistema di **stima pesi componenti pompe** basato su AI e RAG (Retrieval-Augmented Generation), sviluppato per **Trillium Pumps Italy S.p.A.**

> **Relazione con Trillium V1:** Questo progetto condivide con TrilliumVersione1 il motore RAG core e lo stesso database vettoriale Qdrant (collezione `trilliumdoc`). Si differenzia per l'obiettivo applicativo: V2 è specializzato nella stima dei pesi dei componenti di pompe a partire da disegni tecnici storici e parametri di progetto.

## 🎯 Obiettivo

Partendo dai parametri di progetto di una pompa, il sistema:
1. **Legge e analizza** disegni tecnici storici (TIF, PDF) tramite AI/RAG
2. **Identifica** pompe di riferimento con geometria e caratteristiche simili
3. **Applica formule di scaling** per stimare i pesi dei componenti principali
4. **Genera** un file Excel con la parts list e i pesi stimati

### Parametri di Input
- `pump_family` — Famiglia della pompa
- `Nq` — Velocità specifica
- `scale factor f` — Fattore di scala
- `pressure` — Pressione di progetto
- `temperature` — Temperatura di progetto
- `material` — Materiale
- `flange rating` — Rating flange
- `wall thickness` — Spessore parete

### Output
File Excel (`.xlsx`) salvato in SharePoint con:
- **Summary**: parametri usati, data/ora, utente, job ID, warning
- **PartsList**: per ogni componente: classe, peso di riferimento, materiale, fattori applicati, peso stimato, sorgente
- **Log**: traccia tecnica, assunzioni, righe escluse

## 🚀 Funzionalità Principali

- **📄 Indicizzazione Multi-Formato**: Supporta PDF, Excel, immagini (TIF, TIFF, BMP, PNG, HEIC) con OCR ibrido (locale + cloud)
- **💬 Chat RAG**: Domande conversazionali sui documenti tecnici delle pompe
- **☁️ SharePoint/OneDrive**: Indicizza documenti direttamente da SharePoint e OneDrive
- **⚖️ Confronto Modelli**: Confronta risposte di diversi LLM (GPT, Claude, Gemini)
- **🔍 Ricerca Web**: Integrazione DuckDuckGo per contesto aggiuntivo
- **📊 Dashboard**: Statistiche e visualizzazioni del database vettoriale

## ⚙️ Configurazione

### Variabili d'Ambiente

```env
# LLM Provider (openai, anthropic, gemini, openrouter)
PROVIDER=openai

# API Keys
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
GEMINI_API_KEY=...
OPENROUTER_API_KEY=...

# Vector Database (condiviso con TrilliumVersione1)
VECTOR_DB=qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

## 🎯 Avvio

### Streamlit (Interfaccia Web)

```bash
cd trillium
streamlit run streamlit_app.py
```

Apri il browser su **http://localhost:8501**

### CLI

```bash
cd trillium
python app.py
```

## 📁 Struttura Progetto

```
TrilliumVersione2/
├── Technical Documentation Project/   # Documentazione tecnica pompe (SOP, Mod, disegni)
└── trillium/
    ├── streamlit_app.py      # Interfaccia Streamlit
    ├── app.py                # CLI Trillium
    ├── config.py             # Configurazione
    ├── modules/              # Moduli UI (chat, dashboard, analytics, ecc.)
    └── rag/
        ├── extractor.py      # Pipeline OCR ibrida (ottimizzata per disegni tecnici)
        ├── indexer.py        # Indicizzazione documenti
        ├── query.py          # Pipeline RAG query (12 fasi)
        ├── model_compare.py  # Confronto modelli LLM
        ├── qdrant_db.py      # Integrazione Qdrant
        ├── web_search.py     # Ricerca web DuckDuckGo
        └── sharepoint_connector.py  # Connettore SharePoint/OneDrive
```

## 📋 Funzionalità

- **Dashboard**: Statistiche, distribuzione documenti, configurazione sistema
- **Indicizzazione**: Cartella locale (multiprocesso) e SharePoint/OneDrive (OAuth2)
- **Chat RAG**: Domande con contesto documentale su disegni e specifiche pompe
- **Confronto Modelli**: Confronta risposte di GPT, Claude, Gemini

## 📖 Documentazione

- [Trillium RAG System](trillium/README.md) - Documentazione dettagliata del sistema RAG
- [**Stato Progetto**](trillium/STATO_PROGETTO.md) - **Panoramica completa e aggiornata del progetto**
- [Registro Implementazioni](trillium/IMPLEMENTAZIONI.md) - Fasi di sviluppo (1–10)
- [Setup Qdrant](trillium/README_QDRANT.md) - Configurazione database vettoriale Qdrant
- [Analisi Indicizzazione Immagini](trillium/Test02_ANALISI_E_PROPOSTE_INDICIZZAZIONE_IMMAGINI.md) - Proposte per disegni TIF
- [AWS Deployment](AWS_DEPLOYMENT_GUIDE.md) - Guida deployment su AWS
- [Indice Documentazione](Technical%20Documentation%20Project/00_INDEX.md) - Indice dei 164+ documenti tecnici

## 📄 Licenza

[Specifica la licenza del progetto]

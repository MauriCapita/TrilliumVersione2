# Trillium V2 — Stato del Progetto

**Ultima revisione:** 27 febbraio 2026 (Fase 14 — Trend Analysis)  
**Progetto:** Trillium V2 — AI Weight Estimation System  
**Cliente:** Trillium Pumps Italy S.p.A.

---

## 1. Panoramica

Sistema avanzato di **Retrieval-Augmented Generation (RAG)** per la **stima AI dei pesi dei componenti di pompe centrifughe**, basato su:
- Disegni tecnici storici (TIF, PDF)
- Datasheet e parts list di pompe di riferimento
- Parametri di progetto (Nq, pressione, temperatura, materiale, flange rating)

L'applicazione usa **Streamlit** come frontend, **Qdrant** (o ChromaDB) come database vettoriale, e supporta multipli provider LLM (OpenAI, Anthropic, Google Gemini, OpenRouter).

---

## 2. Architettura del Sistema

```
TrilliumVersione2/
├── README.md                          # README principale progetto
├── AWS_DEPLOYMENT_GUIDE.md            # Guida deployment AWS
├── Technical Documentation Project/   # ~164 documenti tecnici pompe
│   ├── 00_INDEX.md                    # Indice completo dei documenti
│   └── REORGANIZATION_PROPOSAL.md     # Proposta riorganizzazione cartelle
│
└── trillium/                          # Applicazione principale
    ├── streamlit_app.py               # Entry point Streamlit (193 righe)
    ├── app.py                         # Entry point CLI
    ├── config.py                      # Configurazione centralizzata (119 righe)
    ├── auth.py                        # Autenticazione e ruoli (145 righe)
    ├── users.json                     # Credenziali utenti
    │
    ├── modules/                       # Pagine UI Streamlit
    │   ├── __init__.py
    │   ├── styles.py                  # CSS tema chiaro Bilancio Sostenibilità (~345 righe)
    │   ├── helpers.py                 # Funzioni condivise (260 righe)
    │   ├── dashboard.py               # Dashboard principale (132 righe)
    │   ├── weight_estimation.py       # Stima pesi pompe (~1600 righe) ★
    │   ├── pump_dashboard.py          # Dashboard pompe estratte (378 righe)
    │   ├── drawing_analysis.py        # Analisi disegni/inventario (~510 righe)
    │   ├── indexing.py                # Indicizzazione documenti (352 righe)
    │   ├── chat.py                    # Chat RAG conversazionale (641 righe)
    │   ├── compare.py                 # Confronto modelli LLM (214 righe)
    │   ├── doc_graph.py               # Grafo SOP ↔ Mod (122 righe)
    │   ├── analytics.py               # Analytics feedback/utilizzo (114 righe)
    │   ├── settings.py                # Configurazione sistema (206 righe)
    │   ├── onboarding.py              # Wizard onboarding 3 step (NEW)
    │   └── manual.py                  # Manuale online 6 tab (NEW)
    │
    ├── rag/                           # Motore RAG core
    │   ├── extractor.py               # Pipeline OCR ibrida (974 righe) ★
    │   ├── indexer.py                 # Indicizzazione e embedding (923 righe) ★
    │   ├── query.py                   # Pipeline RAG 12 fasi (786 righe) ★
    │   ├── qdrant_db.py               # Integrazione Qdrant
    │   ├── model_compare.py           # Confronto modelli LLM
    │   ├── web_search.py              # Ricerca web DuckDuckGo
    │   └── sharepoint_connector.py    # Connettore SharePoint/OneDrive
    │
    ├── query_rewriter.py              # Riscrittura query IT/EN
    ├── query_decomposer.py            # Decomposizione query complesse
    ├── query_router.py                # Routing strategia query
    ├── hyde.py                        # Hypothetical Document Embedding
    ├── reranker.py                    # Re-ranking con LLM
    ├── search_filters.py              # Filtri metadata + BM25 ibrida
    ├── semantic_cache.py              # Cache semantica (TTL 7 giorni)
    ├── context_compressor.py          # Compressione contesto
    ├── relevance_feedback.py          # Boost/penalty da feedback
    ├── citation_parser.py             # Parsing citazioni inline
    ├── confidence.py                  # Calcolo confidence score
    ├── feedback.py                    # Sistema feedback + domande suggerite
    ├── context_loader.py              # Loader domain_context.md
    ├── sop_mod_mapping.py             # Mappatura SOP → Mod
    ├── prompts.py                     # Prompt templates RAG
    ├── domain_context.md              # Conoscenza di base (formule, materiali, glossario)
    │
    ├── IMPLEMENTAZIONI.md             # Registro fasi sviluppo (Fasi 1–6)
    ├── STATO_PROGETTO.md              # ← QUESTO FILE
    ├── README.md                      # README dettagliato sistema RAG
    ├── README_QDRANT.md               # Setup Qdrant
    └── Test02_ANALISI_E_PROPOSTE_INDICIZZAZIONE_IMMAGINI.md
```

---

## 3. Pagine Streamlit (12 pagine)

| # | Pagina | File | Ruoli | Stato | Descrizione |
|---|--------|------|-------|-------|-------------|
| 1 | **Dashboard** | `dashboard.py` | tutti | ✅ Completa | Statistiche DB, distribuzione documenti, configurazione sistema |
| 2 | **Stima Pesi** | `weight_estimation.py` | tutti | ✅ Completa | Form parametri con help tooltip dettagliati, validazione real-time, grafici interattivi, confronto configurazioni, RAG search, download Excel, multi-progetto, alert intelligenti, confronto stima vs reale, riferimenti editabili |
| 3 | **Database Pompe** | `pump_dashboard.py` | tutti | ✅ Completa | Tabella pompe estratte, filtri, grafici distribuzione, dettaglio pompa |
| 4 | **Analisi Disegni** | `drawing_analysis.py` | tutti | ✅ Completa | Inventario documenti con tabella DataFrame, filtri combinati AND/OR multi-select, ricerca testo, selectbox dettaglio documento |
| 5 | **Indicizza Documenti** | `indexing.py` | admin | ✅ Completa | Indicizzazione cartella locale/SharePoint, progress bar streaming, reset DB |
| 6 | **Chat RAG** | `chat.py` | tutti | ✅ Completa | Chat conversazionale con citazioni, snippet, export Word, feedback, confidence, domande suggerite, selezione modello, ricerca web opzionale |
| 7 | **Confronta Modelli** | `compare.py` | admin | ✅ Completa | Confronto side-by-side o tab di più LLM sulla stessa query |
| 8 | **Grafo Documenti** | `doc_graph.py` | tutti | ✅ Completa | Network graph Plotly dei collegamenti SOP ↔ Mod (layout circolare) |
| 9 | **Analytics** | `analytics.py` | admin | ✅ Completa | Metriche soddisfazione, trend utilizzo, feedback negativi, argomenti frequenti |
| 10 | **Configurazione** | `settings.py` | tutti | ✅ Completa | Stato DB, provider LLM, parametri RAG, OCR config |
| 11 | **Trend Analysis** | `trend_analysis.py` | tutti | ✅ Completa | KPI, distribuzione per famiglia/materiale, costi materia prima, confronto vs media, export CSV |
| 12 | **Manuale** | `manual.py` | tutti | ✅ Completa | Guida completa 7 tab: Introduzione, Stima Pesi, Database & Analisi, Chat & Ricerca, Trend Analysis, Amministrazione, FAQ |

---

## 4. Motore RAG — Pipeline 12 Fasi

```
 1. Cache Semantica        → hit = risposta immediata
 2. Query Routing          → classifica query (formula/concetto/SOP/confronto)
 3. Query Decomposition    → spezza domande complesse in sotto-query
 4. Query Rewriting        → espansione sinonimi IT/EN e termini tecnici
 5. HyDE + Retrieval       → documento ipotetico + ricerca vettoriale
 6. Parent Document        → chunk adiacenti per contesto completo
 7. Filtri Metadata        → tipo documento, range SOP
 8. Hybrid Search          → BM25 keyword + score semantico
 9. Re-Ranking LLM         → GPT-4o-mini come cross-encoder
10. Relevance Feedback     → boost documenti da feedback positivi
11. Context Compression    → rimozione parti irrilevanti
12. Streaming Generation   → risposta token-per-token in tempo reale
```

### Ragionamento di profondità (opzionale)
Dopo la risposta RAG, l'utente può abilitare "Ragionamento di profondità" che invoca il modello LLM **senza contesto RAG** per produrre una considerazione originale e aggiunta alla risposta.

---

## 5. Pipeline Estrazione Testo (OCR)

### Formati supportati
| Formato | Estrattore locale | Fallback Cloud |
|---------|-------------------|----------------|
| PDF | PyMuPDF + OCR Tesseract | — |
| Excel (.xlsx/xlsm/xls) | pandas/openpyxl (con formule, commenti, named ranges) | — |
| Word (.docx) | python-docx | — |
| TIF/TIFF | Tesseract OCR (multi-pagina, bi-level, tile-based) | Google Vision, Claude, Gemini |
| BMP/PNG | Tesseract OCR | OpenAI Vision, OpenRouter |
| HEIC/HEIF | Tesseract (via pillow-heif) | — |
| TXT/LOG | Lettura diretta (multi-encoding) | — |

### Configurazione OCR attuale (`config.py`)
| Parametro | Valore | Descrizione |
|-----------|--------|-------------|
| `MIN_TEXT_LENGTH` | 30 | Soglia minima per testi generici |
| `MIN_TEXT_LENGTH_IMAGE` | 100 | Soglia per immagini (sotto → Vision) |
| `TESSERACT_LANG` | `ita+eng` | Lingua OCR |
| `IMAGE_EXTRACTION_STRATEGY` | `local_then_vision` | Strategia |
| `MAX_IMAGE_SIZE_MB` | 25 | Limite dimensione file |
| `MAX_IMAGE_SIDE_PX` | 4096 | Lato max prima di ridimensionamento |
| `USE_TILE_OCR` | true | OCR a zone per testo piccolo |
| `TILE_OVERLAP_PCT` | 0.10 | Overlap tra tile (10%) |
| `TITLE_BLOCK_ZOOM` | 2.0 | Zoom 2x su cartiglio |
| `TILE_VISION_PROVIDER` | none | Provider Vision per tile |

---

## 6. Provider LLM e Modelli

| Provider | Modello LLM | Modello Embedding | Modello Vision |
|----------|-------------|-------------------|----------------|
| **OpenAI** | gpt-4o (default) | text-embedding-3-large | gpt-4o |
| **Anthropic** | claude-3-5-sonnet-20241022 | — | claude-3.5-sonnet |
| **Google Gemini** | gemini-2.5-flash | — | gemini-2.0-flash |
| **OpenRouter** | anthropic/claude-3.5-sonnet | openai/text-embedding-3-large | vari |

---

## 7. Autenticazione e Ruoli

| Ruolo | Pagine accessibili |
|-------|-------------------|
| **viewer** | Dashboard, Stima Pesi, Database Pompe, Analisi Disegni, Chat RAG, Grafo Documenti, Configurazione |
| **admin** | Tutte le pagine del viewer + Indicizza, Confronta Modelli, Analytics |

Se `users.json` non esiste → accesso libero come admin. Le password sono hash SHA-256.

---

## 8. Database Vettoriale

| Parametro | Valore |
|-----------|--------|
| **DB attivo** | Configurabile: `chromadb` o `qdrant` (via `VECTOR_DB` in `.env`) |
| **Collezione Qdrant** | `trilliumdoc` (condivisa con V1) |
| **ChromaDB path** | `./rag_db/` |
| **Parametri RAG** | TOP_K=8, CHUNK_SIZE=1000, CHUNK_OVERLAP=200 |
| **Performance** | PARALLEL_WORKERS=5, CHUNK_BATCH_SIZE=50 |
| **MAX_RESPONSE_TOKENS** | 12000 |

---

## 9. Funzionalità Chiave per Modulo

### weight_estimation.py (1169 righe) — Stima Pesi
- Form input: pump_family, Nq, scale_factor, pressure, temperature, material, flange_rating, wall_thickness
- Validazione in tempo reale (coerenza rating/pressione, limiti materiale/temperatura, range f)
- Formule di scaling: casting (f^2.35 × ρ), pressurizzati (f² × ρ × S), geometria elementare
- Grafici interattivi Plotly: pie chart pesi, bar chart confidenza, breakdown
- Confronto configurazioni con materiale alternativo
- Auto-suggest pompe di riferimento da Qdrant
- Ricerca RAG per parametri correnti
- Confronto visivo Riferimento vs Stima
- Dashboard analytics storico stime
- Download Excel risultati

### drawing_analysis.py (479 righe) — Analisi Disegni
- Scansione tutti i documenti in Qdrant
- Analisi regex per 6 campi: pesi, materiali, dimensioni, famiglia pompa, rating flange, condizioni operative
- Matrice completezza: per ogni documento mostra ✅/❌ per ogni campo
- Filtri per completezza e per campo
- Cache risultati analisi

### pump_dashboard.py (357 righe) — Database Pompe
- Tabella interattiva tutte le pompe estratte
- Grafici distribuzione: per famiglia, per materiale, per rating
- Filtri multi-dimensionali
- Dettaglio singola pompa

### chat.py (554 righe) — Chat RAG
- Layout 70/30: chat a sinistra, pannello fonti a destra
- Pannello fonti: per ogni documento mostra score %, snippet, download
- Citazioni inline colorate (formato `[SOP-518 § 5.2.3]`, `[Mod.497]`)
- Multi-turno: ultimi 5 scambi nel contesto
- Selezione modello LLM nella chat
- Ricerca web opzionale (DuckDuckGo)
- Ragionamento di profondità (opzionale)
- Feedback 👍/👎 con commenti
- Domande suggerite (3 follow-up)
- Confidence score (0-100%)
- Export Word (.docx)

---

## 10. Documentazione Tecnica

| File | Contenuto | Stato |
|------|-----------|-------|
| `README.md` (root) | Panoramica progetto, struttura, configurazione, avvio | ✅ Aggiornato |
| `trillium/README.md` | Documentazione dettagliata sistema RAG (930 righe) | ✅ Aggiornato |
| `trillium/IMPLEMENTAZIONI.md` | Registro fasi sviluppo 1–6 | ⚠️ Copre solo fasi 1-6 (motore RAG core). Non documenta Stima Pesi, Analisi Disegni, Dashboard Pompe |
| `trillium/domain_context.md` | Contesto dominio: formule scaling, famiglie API 610, glossario, materiali, mapping documenti, regole validazione | ✅ Completo |
| `trillium/README_QDRANT.md` | Setup Qdrant | ✅ Aggiornato |
| `trillium/Test02_ANALISI_E_PROPOSTE_INDICIZZAZIONE_IMMAGINI.md` | Analisi cartella Test02, proposte miglioramento OCR (A–H) | ✅ Dettagliato |
| `AWS_DEPLOYMENT_GUIDE.md` | Guida deployment: Lightsail, EC2, App Runner, ECS Fargate + checklist | ✅ Completo |
| `Technical Documentation Project/00_INDEX.md` | Indice 164+ documenti tecnici (SOP, Mod, Standards, Literature) | ✅ Completo |
| `Technical Documentation Project/REORGANIZATION_PROPOSAL.md` | Proposta riorganizzazione cartelle (Opzioni A/B/C) | ✅ Completo |
| **`trillium/STATO_PROGETTO.md`** | **← QUESTO FILE — Stato completo aggiornato** | ✅ Nuovo |

---

## 11. Registro Fasi di Sviluppo

### Fasi 1–6: Motore RAG Core (documentate in IMPLEMENTAZIONI.md)
| Fase | Contenuto |
|------|-----------|
| Fase 1 | Anti-hallucination, citazioni, dual-panel UI, SOP↔Mod mapping, autenticazione, supporto immagini, design corporate |
| Fase 2 | Query rewriting, risposta per ruolo, citation parsing, multi-turno, snippet, export Word |
| Fase 3 | Feedback 👍/👎, domande suggerite, confidence score, grafo documenti, analytics |
| Fase 4 | Filtri metadata, re-ranking LLM, ricerca ibrida, chunk configurabile, filtri estensioni, anteprima chunking |
| Fase 5 | Streaming risposte, cache semantica, parent document retrieval, context compression, query decomposition, timing |
| Fase 6 | HyDE, query routing, relevance feedback, semantic chunking |

### Fase 7: Stima Pesi Componenti (NON documentata in IMPLEMENTAZIONI.md)
- Form input parametri pompa con validazione real-time
- Formule di scaling per ogni tipo componente
- Grafici interattivi, confronto configurazioni, auto-suggest
- RAG Search per parametri, confronto Riferimento vs Stima
- Dashboard analytics storico stime, download Excel

### Fase 8: Analisi Disegni e Database Pompe (NON documentata in IMPLEMENTAZIONI.md)
- Analisi strutturata documenti Qdrant (regex pattern matching su 6 campi)
- Dashboard pompe con tabella, grafici, filtri
- Cache risultati analisi

### Fase 9: Miglioramenti OCR (Parzialmente documentata in Test02)
- Tile-based OCR per disegni tecnici
- Supporto TIF multi-pagina
- Inversione bi-level (WhiteIsZero)
- Ridimensionamento immagini per API
- Fallback descrizione semantica
- Lingua OCR configurabile (ita+eng)
- Strategia estrazione configurabile

### Fase 10: Ragionamento di Profondità
- Opzione "Depth Reasoning" nella chat
- Invocazione LLM senza contesto RAG per considerazione originale
- Aggiunta alla risposta RAG come sezione separata

### Fase 11: UI Refinement e Help System (26/02/2026 pomeriggio)
- Redesign completo CSS: tema chiaro "Bilancio Sostenibilità" (verde primario, sfondo bianco)
- Fix CSS selettori troppo ampi che esponevano key interni Streamlit (overlap "key..." su expander/input)
- Migrazione Analisi Disegni: da `st.expander` a `st.dataframe` + `st.selectbox` per eliminare bug label
- Filtri combinati AND/OR: multi-select campi presenti/mancanti, ricerca testo nome documento
- Help tooltip dettagliati su tutti i parametri Stima Pesi (Famiglia, Nq, Scale Factor, Stadi, Pressione, Temperatura, Materiale, Spessore, Rating, Aspirazione, Mandata)
- Descrizioni contestuali sidebar: ogni voce menu mostra caption dinamica con spiegazione funzionalità
- Fix colori header, heatmap, e grafici per coerenza tema chiaro

### Fase 12: Premium Features + Manuale Online (26/02/2026 sera)
- **Onboarding Guidato** — Wizard 3 step: intro sistema, stima di prova con valori precompilati, spiegazione risultati. File: `modules/onboarding.py` (NEW)
- **Alert Intelligenti** — Query Qdrant per copertura documentale (famiglia + materiale), barra 0-100%, alert specifici con suggerimenti. Funzione `_render_smart_alerts()` in `weight_estimation.py`
- **Multi-Progetto** — Salva/carica/elimina configurazioni di parametri con nome progetto. File: `weight_engine/project_manager.py` (NEW). Selectbox carica + bottone salva + auto-fill form
- **Riferimento Editabile** — Inserimento pesi reali pompe costruite come reference data. File: `weight_engine/reference_weights.py` (NEW). Form inserimento + lista riferimenti per famiglia
- **Versioning Stime** — Ogni stima salvata con parametri completi, dettagli componenti, project_name, revision auto-increment. File: `weight_engine/estimation_history.py` (rewritten). Nuove funzioni: `get_estimation()`, `get_revisions()`
- **Confronto Stima vs Reale** — Cerca pompe simili in reference_weights + pump_database, calcola accuratezza %, badge 🟢/🟡/🔴. Funzione `_render_validation()` in `weight_estimation.py`
- **Manuale Online** — Pagina Streamlit con 6 tab: Introduzione, Stima Pesi (con esempio completo), Database & Analisi, Chat & Ricerca, Amministrazione, FAQ. File: `modules/manual.py` (NEW)
- **Help captions su tutte le pagine** — Dashboard, Indicizzazione, Database Pompe, Analisi Disegni, Chat RAG: ogni pagina ha caption ℹ️ con spiegazione e esempi pratici
- **Esempio compilazione form** — Expander con tabella completa "come compilare" con valori, formato e motivazione per ogni campo

### Fase 13: Integrazione Standards Aziendali (26/02/2026 sera)
- **Material_Database.xlsm → materials.py** — 114 materiali reali da database aziendale con Yield, UTS, tipo fornitura (casting/bar/forging/bolting). Sostituisce i precedenti 40 materiali semplificati
- **Curva Nq→b2/D2** — 26 punti empirici da `Curva nq-D2-b2.xlsx`. Interpolazione lineare. Auto-display sotto campo Nq. File: `weight_engine/nq_curve.py` (NEW)
- **SOP-569 spessore corpo** — Formula t=(P×D)/(2×S×E-1.2×P) + sovrametallo + spessori minimi fondibili. Expander calcolato automaticamente
- **SOP-546 spessore girante** — Formula t=k×D2×√(P/S) per disco posteriore e anteriore. Min spessori per D2
- **Formule scaling aggiornate** — D² per girante/corpo (non più f^2.35), D³ per coperchio, formula esatta albero
- **Display Yield/UTS** — Info materiale ora mostra Yield, UTS, T_max, tipo fornitura (non più castabilità)
- **Help captions aggiornate** — Caption Nq aggiornata con b2/D2, wall_thickness con SOP-569
- **Manuale aggiornato** — Formule corrette, FAQ Standard aziendali
- **Mod.463 — Selezione Nozzle** — Calcolo automatico DN aspirazione/mandata dalla portata (V=Q/(π/4×D²), limiti API 610). Expander nel form
- **Mod.496 — Dimensionamento Albero** — Calcolo diametro minimo API 610 (d=k×(P/n)^1/3, k=85 OH, 72 BB, 78 VS). Expander con potenza, coppia, d_min, d_standard
- **Part Codes Standard** — 20 codici componenti da Standard Part List OH2.xls (102=Corpo, 161=Coperchio, 230=Girante, 210=Albero...)

### Fase 14: Trend Analysis & Predizione Costi (27/02/2026)
- **Trend Analysis page** — `modules/trend_analysis.py` (NEW): dashboard analytics storico stime con KPI cards, distribuzione per famiglia/materiale, andamento temporale, tabella con costo stimato €, confronto vs media per famiglia (badge ↑/↓/≈), esportazione CSV
- **Costi materiale** — `MATERIAL_COST_EUR_KG` (70+ materiali) + `get_cost_per_kg()` in `weight_engine/materials.py`. Valori indicativi €/kg da letteratura industriale
- **Routing & auth** — Pagina Trend Analysis accessibile a tutti (viewer e admin)
- **Manuale aggiornato** — 7° tab "📈 Trend Analysis" + FAQ dedicata

---

## 12. File Sorgente — Inventario Completo

### Moduli UI (`modules/`)
| File | Righe | Funzioni principali |
|------|-------|---------------------|
| `styles.py` | ~345 | `setup_page()` — CSS tema chiaro Bilancio Sostenibilità (verde, sfondo bianco, no overlap) |
| `helpers.py` | 260 | `get_db_stats()`, `get_document_distribution()`, `get_available_providers()`, `short_path_for_display()`, `extract_doc_identifier()` |
| `dashboard.py` | 132 | `render()` — statistiche, grafici distribuzione, config sistema |
| `weight_estimation.py` | ~1600 | `render()`, `_validate_params()`, `_render_charts()`, `_render_comparison()`, `_render_auto_suggest()`, `_build_rag_query_from_params()`, `_render_rag_search()`, `_render_ref_vs_estimate()`, `_render_analytics()`, `_render_smart_alerts()`, `_render_validation()`, `_render_reference_weights_form()` — con help tooltips, multi-progetto, alert intelligenti |
| `pump_dashboard.py` | 357 | `render()` — tabella, grafici, filtri pompe |
| `drawing_analysis.py` | ~500 | `render()`, `analyze_document()`, `get_all_documents_from_qdrant()` — con DataFrame, filtri AND/OR, selectbox dettaglio |
| `indexing.py` | 348 | `render()` — indicizzazione locale/SharePoint, reset |
| `chat.py` | 554 | `render()`, `_render_source_panel()`, `_render_chat_history()`, `_export_chat_as_word()` |
| `compare.py` | 214 | `render()`, `_show_compare_results()` |
| `doc_graph.py` | 122 | `render()` — grafo Plotly SOP↔Mod |
| `analytics.py` | 114 | `render()` — feedback, trend, argomenti frequenti |
| `settings.py` | 206 | `render()` — status, parametri, OCR config |
| `onboarding.py` | ~200 | `render_onboarding()` — wizard 3 step: intro, stima di prova, risultati. `is_onboarding_done()`, `mark_onboarding_done()` |
| `manual.py` | ~460 | `render()` — manuale online 7 tab: Introduzione, Stima Pesi, Database, Chat, Trend Analysis, Admin, FAQ |
| `trend_analysis.py` | ~370 | `render()` — dashboard analytics storico stime: KPI, grafici distribuzione, tabella costi, confronto media, export CSV |

### RAG Core (`rag/`)
| File | Righe | Funzioni principali |
|------|-------|---------------------|
| `extractor.py` | 974 | `extract_text()`, estrattori per formato (PDF, TIF, Excel, Word, BMP/PNG, HEIC, TXT, LOG), Vision API (OpenAI, OpenRouter, Google), tile-based OCR |
| `indexer.py` | 923 | `index_folder()`, `index_folder_streaming()`, `reset_database()`, `get_chroma()`, `get_vector_db()`, chunking, batch processing, parallel workers |
| `query.py` | 786 | `rag_query()` (pipeline 12 fasi), `retrieve_relevant_docs()`, `build_context()`, `generate_answer()`, `generate_answer_stream()`, `get_depth_reasoning()` |
| `qdrant_db.py` | — | Integrazione Qdrant |
| `model_compare.py` | — | Confronto risposte LLM |
| `web_search.py` | — | Ricerca web DuckDuckGo |
| `sharepoint_connector.py` | — | Connettore SharePoint/OneDrive |

### Moduli Pipeline
| File | Descrizione |
|------|-------------|
| `query_rewriter.py` | Riscrittura query con sinonimi IT/EN |
| `query_decomposer.py` | Decomposizione query complesse |
| `query_router.py` | Classificazione e routing query |
| `hyde.py` | Hypothetical Document Embedding |
| `reranker.py` | Re-ranking cross-encoder con LLM |
| `search_filters.py` | Filtri metadata + ricerca ibrida BM25 |
| `semantic_cache.py` | Cache hash + Jaccard, TTL 7 giorni |
| `context_compressor.py` | Scoring e compressione contesto |
| `relevance_feedback.py` | Boost/penalty basato su feedback |
| `citation_parser.py` | Estrazione citazioni inline |
| `confidence.py` | Score 0-100% basato su qualità retrieval |
| `feedback.py` | Feedback 👍/👎, domande suggerite |
| `context_loader.py` | Loader per domain_context.md |
| `sop_mod_mapping.py` | Mappatura SOP → Mod |
| `prompts.py` | Template prompt per anti-hallucination, ruoli, citazioni |

### Infrastruttura
| File | Descrizione |
|------|-------------|
| `streamlit_app.py` | Entry point Streamlit (routing, sidebar con help contestuale, session state, onboarding) |
| `app.py` | Entry point CLI |
| `config.py` | Configurazione centralizzata (LLM, DB, RAG, OCR, SharePoint) |
| `auth.py` | Autenticazione, ruoli viewer/admin, login page |

### Weight Engine (`weight_engine/`)
| File | Descrizione |
|------|-------------|
| `estimator.py` | Motore di stima pesi componenti |
| `materials.py` | Database materiali con densità e limiti temperatura |
| `parts_list.py` | Template parti per famiglia pompa |
| `parts_list_extractor.py` | Estrazione BOM con GPT-4o |
| `pump_database.py` | Database pompe estratte dai disegni |
| `pump_data_extractor.py` | Estrazione dati pompa da documenti |
| `ai_matcher.py` | Matching AI componenti |
| `excel_generator.py` | Generazione file Excel risultati |
| `estimation_history.py` | Storico stime con versioning (parametri completi, componenti, revisioni) |
| `project_manager.py` | Gestione multi-progetto (save/load/list/delete) — NEW |
| `reference_weights.py` | Pesi reali di riferimento (add/get/find_similar) — NEW |

### Costi Materiali
| File | Descrizione |
|------|-------------|
| `MATERIAL_COST_EUR_KG` (in `materials.py`) | 70+ materiali con costo indicativo €/kg da letteratura industriale |

---

## 13. Proposte di Miglioramento Non Ancora Implementate

### Da Test02 (OCR miglioramenti, prioritizzati A→H)
| Priorità | Proposta | Stato |
|----------|----------|-------|
| ~~1~~ | ~~A. TIFF multi-pagina~~ | ✅ Implementato (in `extract_tif_local`) |
| ~~2~~ | ~~C. Soglia immagini~~ | ✅ Implementato (`MIN_TEXT_LENGTH_IMAGE=100`) |
| ~~3~~ | ~~E. Fallback descrizione~~ | ✅ Implementato (`_fallback_description_for_image`) |
| ~~4~~ | ~~B. OCR TIF bi-level~~ | ✅ Implementato (inversione WhiteIsZero) |
| ~~5~~ | ~~G. Lingua e strategia~~ | ✅ Implementato (`TESSERACT_LANG`, `IMAGE_EXTRACTION_STRATEGY`) |
| ~~6~~ | ~~D. Limite 25 MB~~ | ✅ Implementato (`MAX_IMAGE_SIZE_MB`, ridimensionamento) |
| ~~7~~ | ~~F. Ridimensionamento API~~ | ✅ Implementato (`MAX_IMAGE_SIDE_PX`, `_resize_image_if_needed`) |
| 8 | H. Log/statistiche immagini | ⚠️ Parziale (struttura `IMAGE_EXTRACTION_STATS` definita ma non completamente integrata nell'UI) |

### Da Reorganization Proposal (documenti tecnici)
| Implementato | Proposta |
|:---:|----------|
| ✅ | Opzione C: `00_INDEX.md` creato con indice completo |
| ❌ | Opzione A: Riorganizzazione per tipo (SOP/Mod/Design) — non ancora fatto |

---

## 14. Dipendenze Principali

```
streamlit>=1.28.0      # UI web
plotly>=5.17.0          # Grafici interattivi
openai>=1.2.0           # API OpenAI (LLM, embedding, vision)
anthropic>=0.18.0       # API Anthropic (Claude)
google-genai>=0.2.0     # API Google Gemini
qdrant-client           # Database vettoriale Qdrant
chromadb                # Database vettoriale ChromaDB (alternativa)
pymupdf                 # Estrazione PDF
pytesseract             # OCR locale
pillow                  # Elaborazione immagini
pillow-heif             # Supporto HEIC/HEIF
pandas, openpyxl        # Supporto Excel
python-docx             # Supporto Word + Export chat
google-cloud-vision     # Google Vision API (OCR cloud)
duckduckgo-search>=4.0  # Ricerca web
beautifulsoup4>=4.12    # Parsing HTML (fallback)
rich                    # Output formattato (CLI)
tqdm                    # Progress bar (CLI)
python-dotenv           # Variabili ambiente
```

---

## 15. Come Avviare

```bash
# 1. Assicurati che Qdrant sia attivo (se usato)
docker start qdrant

# 2. Avvia Streamlit
cd trillium
streamlit run streamlit_app.py

# 3. Apri il browser
open http://localhost:8501
```

---

## 16. Contesto di Dominio (domain_context.md)

Il file `domain_context.md` è letto automaticamente dal sistema RAG e contiene:
- **Formule di scaling**: casting (pref × f^2.35 × ρ), pressurizzati, geometria elementare, flange
- **Famiglie pompe API 610**: OH (1-5), BB (1-5), VS (1,4,6,7)
- **Glossario IT/EN**: 20+ termini con sinonimi
- **Materiali e densità**: 114 materiali dal Material_Database.xlsm con densità (kg/m³), Yield, UTS
- **Mapping documenti chiave**: per argomento → SOP/Mod di riferimento
- **Regole di validazione**: temperatura, rating, multistadio, f, Nq

---

*Documento generato il 27 febbraio 2026 (Fase 14 — Trend Analysis). Ultimo stato confermato: progetto funzionante con 12 pagine Streamlit, motore RAG a 12 fasi, pipeline OCR ibrida, autenticazione, supporto multi-provider LLM, tema UI chiaro "Bilancio Sostenibilità", help tooltips con esempi, filtri combinati AND/OR, onboarding, alert intelligenti, multi-progetto, riferimenti editabili, versioning, confronto stima vs reale, manuale online 7 tab, standards aziendali integrati (114 materiali, curva Nq, SOP-569/546), trend analysis con predizione costi.*

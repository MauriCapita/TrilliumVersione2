# Trillium V2 RAG — Registro Implementazioni

**Data:** 27 febbraio 2026 (aggiornato — Fase 14)  
**Progetto:** Trillium V2 — AI Weight Estimation System (stima pesi componenti pompe centrifughe)  
**Autore:** Sviluppo assistito AI

> **Nota:** Le fasi 1–6 documentano il motore RAG core, condiviso con TrilliumVersione1. L'obiettivo specifico di V2 (stima pesi componentipompe a partire da disegni tecnici storici) si basa su questo motore.

---

## Fase 1 — Allineamento Core

| Feature | File | Descrizione |
|---------|------|-------------|
| Anti-hallucination | `prompts.py` | Istruzioni LLM per non inventare formule/valori non presenti nei documenti |
| Citazioni inline obbligatorie | `prompts.py` | Formato `[SOP-518 § 5.2.3]`, `[Mod.497]`, `[API 610]` |
| Dual-panel UI | `modules/chat.py` | Layout 70/30: chat sinistra, fonti/bibliografia destra |
| SOP ↔ Mod mapping | `sop_mod_mapping.py` | Mappatura completa SOP → moduli di calcolo Excel |
| Autenticazione e ruoli | `auth.py` | Ruoli viewer/admin con hash SHA-256, pagine filtrate per ruolo |
| Supporto immagini | `rag/indexer.py` | Metadata immagini durante indicizzazione, thumbnail nel pannello |
| Database trilliumdoc | `config.py` | Collezione Qdrant `trilliumdoc`, gestione collection inesistente |
| UI professionale | `modules/styles.py` | Rimossi emoji e decorazioni, design corporate pulito |

---

## Fase 2 — RAG Enhancement

| Feature | File | Descrizione |
|---------|------|-------------|
| Query rewriting | `query_rewriter.py` | GPT-4o-mini riscrive la query con sinonimi IT/EN, numeri SOP/Mod, termini tecnici |
| Risposte per ruolo | `prompts.py` | Viewer: linguaggio accessibile · Admin: profondità tecnica completa |
| Citation parsing | `citation_parser.py` | Estrazione citazioni inline dalla risposta, match con documenti sorgente |
| Multi-turno | `prompts.py` + `modules/chat.py` | Ultimi 5 scambi inclusi nel prompt per contesto conversazione |
| Snippet documenti | `modules/chat.py` | Anteprima 150 caratteri per ogni fonte nel pannello destro |
| Export Word | `modules/chat.py` | Bottone "Esporta Word" genera .docx della conversazione (python-docx) |

---

## Fase 3 — Premium Features

| Feature | File | Descrizione |
|---------|------|-------------|
| Feedback 👍/👎 | `feedback.py` + `modules/chat.py` | Pulsanti sotto ogni risposta, commenti per feedback negativi, persistenza JSON |
| Domande suggerite | `feedback.py` + `modules/chat.py` | 3 follow-up generati da GPT-4o-mini, cliccabili per continuare la conversazione |
| Confidence score | `confidence.py` + `modules/chat.py` | Score 0-100% basato su: n° documenti, qualità testo, SOP/Mod, keyword match |
| Grafo documenti | `modules/doc_graph.py` | Network graph interattivo Plotly dei 40+ collegamenti SOP ↔ Mod |
| Analytics dashboard | `modules/analytics.py` | Metriche soddisfazione, trend utilizzo, feedback negativi, argomenti frequenti |

---

## Fase 4 — Precisione Motore

| Feature | File | Descrizione |
|---------|------|-------------|
| Filtri metadata query | `search_filters.py` + `modules/chat.py` | Filtra per tipo documento (SOP/Mod/Normative) e range SOP numerico |
| Re-ranking LLM | `reranker.py` + `rag/query.py` | GPT-4o-mini come cross-encoder ri-ordina documenti per rilevanza |
| Ricerca ibrida | `search_filters.py` + `rag/query.py` | BM25 keyword matching + score semantico combinati |
| Chunk size configurabile | `config.py` | `CHUNK_SIZE` (default 1000) e `CHUNK_OVERLAP` (200) in .env |
| Filtri estensioni file | `modules/indexing.py` | Multiselect estensioni (.pdf, .xlsx, .docx...) per indicizzazione selettiva |
| Anteprima chunking | `modules/indexing.py` | Stima file, dimensione totale, chunk attesi prima di indicizzare |
| Config motore visibile | `modules/settings.py` | Sezione "Motore RAG" con tutti i parametri: TOP_K, Chunk, Reranking, Hybrid |

---

## Fase 5 — Performance Avanzate

| Feature | File | Descrizione |
|---------|------|-------------|
| Streaming risposte | `rag/query.py` + `modules/chat.py` | Token-per-token via `st.write_stream`, niente più spinner |
| Semantic cache | `semantic_cache.py` | Cache hash + Jaccard similarity, JSON persistente, TTL 7 giorni, max 200 entry |
| Parent document retrieval | `rag/query.py` | Chunk adiacenti (prima/dopo) recuperati per contesto completo |
| Context compression | `context_compressor.py` | Scoring paragrafi per rilevanza, rimozione parti irrilevanti, meno token |
| Query decomposition | `query_decomposer.py` | Domande complesse → 2-3 sotto-query separate, retrieval indipendente, merge risultati |
| Response timing | `rag/query.py` + `modules/chat.py` | Tempo per ogni fase (cache, retrieval, rerank, LLM) mostrato sotto la risposta |

---

## Fase 6 — Ottimizzazione Ricerca

| Feature | File | Descrizione |
|---------|------|-------------|
| HyDE | `hyde.py` + `rag/query.py` | Genera documento ipotetico, usa il suo embedding per cercare → +20-30% retrieval |
| Query routing | `query_router.py` + `rag/query.py` | Classifica query (formula/concetto/confronto/SOP) → strategia BM25/semantica ottimale |
| Relevance feedback | `relevance_feedback.py` + `rag/query.py` | Boost/penalty documenti basato su feedback storico 👍/👎, migliora col tempo |
| Semantic chunking | `rag/indexer.py` | Spezza documenti ai confini naturali (paragrafi, sezioni, tabelle) con overlap configurabile |

---

## Pipeline RAG Completa (12 Fasi)

```
 1. Cache Semantica        → hit = risposta immediata
 2. Query Routing          → determina strategia (formula/concetto/SOP/confronto)
 3. Query Decomposition    → domande complesse spezzate in sotto-query
 4. Query Rewriting        → espansione sinonimi IT/EN e termini tecnici
 5. HyDE + Retrieval       → documento ipotetico + ricerca vettoriale
 6. Parent Document        → chunk adiacenti recuperati per contesto completo
 7. Filtri Metadata        → tipo documento, range SOP
 8. Hybrid Search          → BM25 keyword (peso adattivo) + score semantico
 9. Re-Ranking LLM         → GPT-4o-mini come cross-encoder
10. Relevance Feedback     → boost documenti da feedback positivi
11. Context Compression    → rimozione parti irrilevanti dai documenti
12. Streaming Generation   → risposta token-per-token in tempo reale
```

---

## File Creati/Modificati

### Nuovi moduli (16 file)
- `query_rewriter.py` — Riscrittura query
- `citation_parser.py` — Parsing citazioni inline
- `feedback.py` — Sistema feedback + domande suggerite
- `confidence.py` — Calcolo confidence score
- `reranker.py` — Re-ranking con LLM
- `search_filters.py` — Filtri metadata + ricerca ibrida BM25
- `semantic_cache.py` — Cache semantica
- `context_compressor.py` — Compressione contesto
- `query_decomposer.py` — Decomposizione query complesse
- `hyde.py` — Hypothetical Document Embedding
- `query_router.py` — Routing e strategia query
- `relevance_feedback.py` — Feedback loop con boost/penalty
- `modules/doc_graph.py` — Pagina grafo documenti interattivo
- `modules/analytics.py` — Pagina analytics dashboard
- `sop_mod_mapping.py` — Mappatura SOP ↔ Mod

### Modificati (9 file)
- `config.py` — Parametri CHUNK_SIZE, CHUNK_OVERLAP, USE_RERANKING, USE_HYBRID_SEARCH
- `prompts.py` — Istruzioni ruolo, anti-hallucination, multi-turno
- `auth.py` — Pagine per ruolo (Grafo Documenti, Analytics)
- `streamlit_app.py` — Routing nuove pagine, session state
- `rag/query.py` — Pipeline 9 fasi, streaming, parent retrieval, timing
- `modules/chat.py` — Streaming UI, feedback, confidence, filtri, export
- `modules/indexing.py` — Browser cartelle, filtri estensioni, anteprima chunking
- `modules/settings.py` — Sezione Motore RAG con parametri
- `modules/dashboard.py` — Statistiche aggiornate

---

## Configurazione (.env)

```env
# Parametri RAG Engine
TOP_K=8                    # Documenti recuperati
CHUNK_SIZE=1000           # Caratteri per chunk
CHUNK_OVERLAP=200         # Sovrapposizione chunk
USE_RERANKING=true        # Re-ranking con LLM cross-encoder
USE_HYBRID_SEARCH=true    # BM25 + semantica combinati
```

---

## Dipendenze

- `python-docx` — Export conversazioni in Word
- `plotly` — Grafici interattivi (Analytics, Grafo Documenti)
- `openai` — Query rewriting, re-ranking, domande suggerite, decomposition

---

## Fase 7 — Stima Pesi Componenti Pompe

**Data:** 25–26 febbraio 2026

| Feature | File | Descrizione |
|---------|------|-------------|
| Form parametri pompa | `modules/weight_estimation.py` | Input: pump_family, Nq, scale_factor, pressure, temperature, material, flange_rating, wall_thickness |
| Validazione real-time | `modules/weight_estimation.py` | Coerenza rating/pressione (ASME B16.5), limiti materiale/temperatura, range fattore scala |
| Formule di scaling | `domain_context.md` + `modules/weight_estimation.py` | Casting (f^2.35 × ρ), pressurizzati (f² × ρ × S), geometria elementare, flange da tabella |
| Grafici interattivi | `modules/weight_estimation.py` | Pie chart pesi, bar chart confidenza, breakdown per componente (Plotly) |
| Confronto configurazioni | `modules/weight_estimation.py` | Side-by-side con materiale alternativo, delta peso/costo |
| Auto-suggest riferimento | `modules/weight_estimation.py` | Ricerca RAG per pompe simili in Qdrant |
| Ricerca documenti | `modules/weight_estimation.py` | Costruisce query RAG ottimizzata dai parametri del form |
| Confronto Rif vs Stima | `modules/weight_estimation.py` | Confronto visivo tra dati pompa riferimento e stima calcolata |
| Analytics storico | `modules/weight_estimation.py` | Dashboard analytics sullo storico stime effettuate |
| Download Excel | `modules/weight_estimation.py` | Export risultati in file .xlsx |

---

## Fase 8 — Analisi Disegni e Database Pompe

**Data:** 25–26 febbraio 2026

| Feature | File | Descrizione |
|---------|------|-------------|
| Inventario documenti | `modules/drawing_analysis.py` | Scansione tutti i documenti Qdrant, analisi contenuto con regex |
| Pattern matching 6 campi | `modules/drawing_analysis.py` | Cerca: pesi (kg), materiali, dimensioni (mm/in), famiglia (OH/BB/VS), rating (class), condizioni (bar/°C) |
| Matrice completezza | `modules/drawing_analysis.py` | Per ogni documento: ✅/❌ per ogni campo, score completezza |
| Cache analisi | `modules/drawing_analysis.py` | Salvataggio risultati in `.drawing_analysis_cache.json` |
| Dashboard pompe | `modules/pump_dashboard.py` | Tabella interattiva tutte le pompe estratte, filtri multi-dimensionali |
| Grafici distribuzione | `modules/pump_dashboard.py` | Distribuzione per famiglia, materiale, rating (Plotly) |
| Auth — nuove pagine | `auth.py` | Aggiunta "Stima Pesi", "Database Pompe", "Analisi Disegni" ai ruoli viewer e admin |

---

## Fase 9 — Miglioramenti OCR per Disegni Tecnici

**Data:** 25–26 febbraio 2026

| Feature | File | Descrizione |
|---------|------|-------------|
| Tile-based OCR | `rag/extractor.py` + `config.py` | Divide il disegno in zone per leggere testo piccolo; zoom 2x su cartiglio |
| TIF multi-pagina | `rag/extractor.py` | Loop su `PIL.Image.Sequence` per indicizzare tutte le pagine |
| Inversione bi-level | `rag/extractor.py` | Per TIF con `WhiteIsZero`: inversione automatica per Tesseract |
| Ridimensionamento API | `rag/extractor.py` + `config.py` | `MAX_IMAGE_SIDE_PX=4096`, `MAX_IMAGE_SIZE_MB=25` con ridimensionamento automatico |
| Fallback descrizione | `rag/extractor.py` | Se OCR+Vision restano poveri → testo minimo da nome file + breve descrizione |
| Lingua OCR conf. | `config.py` | `TESSERACT_LANG=ita+eng` configurabile |
| Strategia estrazione | `config.py` | `IMAGE_EXTRACTION_STRATEGY`: local_then_vision / local_only / vision_only |
| Soglia immagini | `config.py` | `MIN_TEXT_LENGTH_IMAGE=100` (separata dalla soglia generica 30) |
| Config pagina | `modules/settings.py` | Sezione OCR/Immagini con tutti i parametri tile, zoom, provider |

---

## Fase 10 — Ragionamento di Profondità

**Data:** 25–26 febbraio 2026

| Feature | File | Descrizione |
|---------|------|-------------|
| Depth reasoning | `rag/query.py` | `get_depth_reasoning()`: invoca LLM senza contesto RAG per considerazione originale |
| UI checkbox | `modules/chat.py` | Checkbox "Ragionamento di profondità" nella chat |
| Session state | `streamlit_app.py` | `use_depth_reasoning` in session state |
| Sezione separata | `rag/query.py` | Aggiunta come `### Aggiunta – Ragionamento di profondità` alla risposta RAG |

---

## Fase 11 — UI Refinement e Help System

**Data:** 26 febbraio 2026 (pomeriggio)

| Feature | File | Descrizione |
|---------|------|-------------|
| Redesign CSS completo | `modules/styles.py` | Tema chiaro "Bilancio Sostenibilità": verde primario, sfondo bianco, tipografia Inter, ombre sottili, transizioni cubic-bezier |
| Fix CSS overlap "key" | `modules/styles.py` | Rimossi selettori troppo ampi (`*`, `span`, `label`, `div`) che forzavano colore su elementi interni Streamlit nascosti |
| Migrazione da expander a dataframe | `modules/drawing_analysis.py` | Sostituiti `st.expander` (bug label overlap irrisolvibile) con `st.dataframe` + `st.selectbox` per dettaglio documento |
| Filtri combinati AND/OR | `modules/drawing_analysis.py` | Multi-select campi presenti/mancanti, toggle AND/OR, ricerca testo nome documento, filtro completezza |
| Help tooltips parametri | `modules/weight_estimation.py` | Tooltip dettagliati su tutti i 11 parametri: Famiglia (API 610), Nq (formula), Scale Factor (f³), Stadi, Pressione, Temperatura (Charpy/creep), Materiale, Spessore, Rating (limiti bar), Aspirazione, Mandata |
| Descrizioni contestuali sidebar | `streamlit_app.py` | Caption dinamica sotto il menu che spiega la funzionalità della pagina selezionata (10 descrizioni) |
| Fix header/grafici | `pump_dashboard.py`, `weight_estimation.py`, `drawing_analysis.py` | Gradienti e colori aggiornati da tema scuro a tema chiaro (verde/bianco/azzurro) |
| Config Streamlit | `.streamlit/config.toml` | `primaryColor` aggiornato a `#1B9C4F` (verde sostenibilità) |

---

## Fase 12 — Premium Features + Manuale Online

**Data:** 26 febbraio 2026 (sera)

| Feature | File | Descrizione |
|---------|------|-------------|
| Onboarding Guidato | `modules/onboarding.py` (NEW) + `streamlit_app.py` | Wizard 3 step: intro sistema, stima di prova precompilata BB1, spiegazione risultati. Flag `.onboarding_complete` per non rimostrarlo |
| Alert Intelligenti | `modules/weight_estimation.py` | `_render_smart_alerts()`: query Qdrant per copertura documentale (famiglia + materiale), barra 0-100%, alert specifici con suggerimenti miglioramento |
| Multi-Progetto | `weight_engine/project_manager.py` (NEW) + `modules/weight_estimation.py` | Save/load/list/delete configurazioni parametri. Selectbox carica, bottone salva, tutti i default del form si auto-compilano da progetto |
| Riferimento Editabile | `weight_engine/reference_weights.py` (NEW) + `modules/weight_estimation.py` | CRUD pesi reali pompe costruite. Form inserimento con nome/famiglia/peso/note. `find_similar()` per confronto |
| Versioning Stime | `weight_engine/estimation_history.py` (rewritten) | Parametri completi + componenti dettagliati per ogni stima. Project_name, revision auto-increment. `get_estimation()`, `get_revisions()` |
| Confronto Stima vs Reale | `modules/weight_estimation.py` | `_render_validation()`: cerca pompe simili in ref_weights + pump_database, calcola accuratezza %, badge 🟢/🟡/🔴, delta per ogni riferimento |
| Manuale Online | `modules/manual.py` (NEW) + `streamlit_app.py` + `auth.py` | Pagina guida 6 tab: Introduzione, Stima Pesi (con esempio completo), Database & Analisi, Chat & Ricerca, Amministrazione, FAQ |
| Help captions globali | `dashboard.py`, `indexing.py`, `pump_dashboard.py`, `drawing_analysis.py`, `chat.py` | Ogni pagina ha caption ℹ️ con spiegazione funzionalità e esempio pratico |
| Esempio compilazione form | `modules/weight_estimation.py` | Expander "📖 Esempio: come compilare il form" con tabella completa valori/formato/motivazione |

---

## Fase 13 — Integrazione Standards Aziendali

**Data:** 26 febbraio 2026 (sera)

| Feature | File | Descrizione |
|---------|------|---------|
| Material Database reale | `weight_engine/materials.py` (rewritten) | 114 materiali da Material_Database.xlsm con Yield, UTS, tipo fornitura. Sostituisce i 40 manuali |
| Curva Nq→b2/D2 | `weight_engine/nq_curve.py` (NEW) | 26 punti empirici da Curva nq-D2-b2.xlsx, interpolazione lineare |
| Spessore corpo SOP-569 | `weight_engine/nq_curve.py` | `calc_casing_thickness()`: formula pressione + min fondibili (6/8/10/12mm) |
| Spessore girante SOP-546 | `weight_engine/nq_curve.py` | `calc_impeller_disc_thickness()`: k×D2×√(P/S), disco posteriore/anteriore |
| Formule scaling corrette | `weight_engine/nq_curve.py` | D² girante/corpo, D³ coperchio, π/4×D²×L×ρ albero |
| UI: b2 auto-calc | `modules/weight_estimation.py` | Sotto campo Nq: "Curva Nq→b2/D2: 0.091" auto-calcolato |
| UI: spessori SOP | `modules/weight_estimation.py` | Expander con SOP-569/546 calcolati (corpo + girante) |
| UI: Yield/UTS display | `modules/weight_estimation.py` | Info materiale mostra Yield, UTS, T_max, fornitura |
| Selezione Nozzle (Mod.463) | `weight_engine/nq_curve.py` + UI | `select_nozzle_size()`: V=Q/(π/4×D²), 18 DN standard, limiti API 610 |
| Dimensionamento Albero (Mod.496) | `weight_engine/nq_curve.py` + UI | `calc_shaft_diameter()`: d=k×(P/n)^1/3, diametri ISO standard |
| Part Codes Standard | `weight_engine/nq_curve.py` | 20 codici da Standard Part List OH2.xls (102→890) |
| Manuale aggiornato | `modules/manual.py` | Formule corrette da Flusso stima pesi.docx, FAQ Standard ampliata |

---

## Riepilogo File per Fase

| Fase | Nuovi file | File modificati |
|------|------------|-----------------|
| 1–6 | 16 moduli pipeline | 9 file core |
| 7 | — | `modules/weight_estimation.py` (nuovo), `auth.py`, `streamlit_app.py` |
| 8 | `modules/drawing_analysis.py`, `modules/pump_dashboard.py` | `auth.py`, `streamlit_app.py` |
| 9 | — | `rag/extractor.py`, `config.py`, `modules/settings.py` |
| 10 | — | `rag/query.py`, `modules/chat.py`, `streamlit_app.py` |
| 11 | — | `modules/styles.py`, `modules/weight_estimation.py`, `modules/drawing_analysis.py`, `modules/pump_dashboard.py`, `streamlit_app.py`, `.streamlit/config.toml` |
| 12 | `modules/onboarding.py`, `modules/manual.py`, `weight_engine/project_manager.py`, `weight_engine/reference_weights.py` | `modules/weight_estimation.py`, `weight_engine/estimation_history.py`, `streamlit_app.py`, `auth.py`, `modules/dashboard.py`, `modules/indexing.py`, `modules/pump_dashboard.py`, `modules/drawing_analysis.py`, `modules/chat.py` |
| 13 | `weight_engine/nq_curve.py` | `weight_engine/materials.py` (rewritten), `modules/weight_estimation.py`, `modules/manual.py` |
| 14 | `modules/trend_analysis.py` | `weight_engine/materials.py` (costi €/kg), `streamlit_app.py`, `auth.py`, `modules/manual.py` |

---

## Fase 14 — Trend Analysis & Predizione Costi

**Data:** 27 febbraio 2026

| Feature | File | Descrizione |
|---------|------|---------|
| Trend Analysis page | `modules/trend_analysis.py` (NEW) | Dashboard analytics storico stime: KPI cards, distribuzione per famiglia/materiale, andamento nel tempo, tabella con costi e confronto media, export CSV |
| Costi materiale | `weight_engine/materials.py` | Dizionario `MATERIAL_COST_EUR_KG` (70+ materiali) + `get_cost_per_kg()`. Valori indicativi €/kg da letteratura industriale |
| Confronto vs media | `modules/trend_analysis.py` | Badge automatico "↑ sopra media" / "↓ sotto media" / "≈ media" per ogni stima rispetto alla media della stessa famiglia |
| Grafici interattivi | `modules/trend_analysis.py` | 5 grafici Plotly: bar famiglie, pie materiali, time series, confronto famiglie, costo per materiale |
| Export CSV | `modules/trend_analysis.py` | Download CSV con tutti i dati + costo stimato, separatore `;`, compatibile Excel |
| Routing | `streamlit_app.py` | Import, PAGE_LABELS, PAGE_HELP, routing |
| Auth | `auth.py` | Trend Analysis aggiunta a PAGES_VIEWER e PAGES_ADMIN |
| Manuale aggiornato | `modules/manual.py` | 7° tab "📈 Trend Analysis" + FAQ "Come funziona il Trend Analysis?" |

---

## Stato Documentazione

| File | Descrizione | Stato |
|------|-------------|-------|
| `IMPLEMENTAZIONI.md` | Registro fasi 1–14 | ✅ Completo (aggiornato 27/02/2026) |
| `STATO_PROGETTO.md` | Panoramica completa progetto | ✅ Aggiornato (27/02/2026 — Fase 14) |
| `README.md` (root) | Panoramica e avvio | ✅ Aggiornato |
| `trillium/README.md` | Documentazione RAG | ✅ Aggiornato |
| `domain_context.md` | Contesto di dominio | ✅ Completo |


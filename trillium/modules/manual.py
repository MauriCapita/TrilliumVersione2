"""
Trillium V2 — Manuale Online
Pagina guida completa del sistema: spiega ogni funzionalità, con esempi pratici,
workflow tipici e FAQ. Serve come documentazione interna sempre aggiornata.
"""

import streamlit as st
from datetime import datetime


def render():
    st.markdown("""
    <div style="text-align: center; padding: 20px 0 10px;">
        <h1 style="color: #1B9C4F; margin-bottom: 5px;">📘 Manuale Trillium V2</h1>
        <p style="color: #64748B; font-size: 15px;">
            Guida completa al sistema AI per la stima pesi componenti pompe centrifughe
        </p>
        <p style="color: #94A3B8; font-size: 12px;">Ultimo aggiornamento: 27 febbraio 2026 (Fase 15 — Standard Part List OH2, D2, MAWP)</p>
    </div>
    """, unsafe_allow_html=True)

    # Indice
    tab_intro, tab_stima, tab_db, tab_chat, tab_trend, tab_admin, tab_faq = st.tabs([
        "🏠 Introduzione",
        "⚖️ Stima Pesi",
        "📊 Database & Analisi",
        "💬 Chat & Ricerca",
        "📈 Trend Analysis",
        "🔧 Amministrazione",
        "❓ FAQ",
    ])

    # ==========================================================
    # TAB 1: INTRODUZIONE
    # ==========================================================
    with tab_intro:
        st.markdown("### Cos'è Trillium V2?")
        st.markdown("""
**Trillium V2** è un sistema AI progettato per l'ufficio tecnico di Trillium Pumps Italy.
Permette di **stimare il peso dei componenti** di pompe centrifughe API 610 a partire
dai parametri di progetto, utilizzando:

- 🧮 **Formule di scaling** ingegneristiche (basate su f², f^2.35)
- 📄 **Dati estratti dai disegni** tecnici storici (PDF, Excel, TIF)
- 🤖 **Intelligenza artificiale** per ricerche avanzate e analisi documenti
        """)

        st.markdown("### Chi lo usa?")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
**👷 Project Engineer**
- Preventivi e offerte
- Stima pesi per trasporto
- Confronto configurazioni
            """)
        with col2:
            st.markdown("""
**🔧 Ufficio Tecnico**
- Verifica pesi in fase di design
- Validazione con dati storici
- Scelta materiali
            """)
        with col3:
            st.markdown("""
**📋 Procurement**
- Stime costo materiali
- Budget preliminare
- Analisi make/buy
            """)

        st.markdown("### Mappa delle Pagine")
        st.markdown("""
| Pagina | Icona | A cosa serve | Chi la usa |
|--------|-------|-------------|------------|
| **Dashboard** | 📊 | Panoramica: statistiche DB, documenti indicizzati, configurazione | Tutti |
| **Stima Pesi** | ⚖️ | Calcola il peso di ogni componente della pompa | Engineer |
| **Database Pompe** | 🏭 | Consulta componenti estratti automaticamente dai disegni | Tutti |
| **Analisi Disegni** | 📐 | Verifica la completezza dei dati per ogni documento indicizzato | Admin |
| **Indicizza Documenti** | 📁 | Carica nuovi documenti nel database vettoriale | Admin |
| **Chat RAG** | 💬 | Fai domande in linguaggio naturale sui documenti tecnici | Tutti |
| **Confronta Modelli** | 🔄 | Confronta risposte di diversi modelli AI sulla stessa domanda | Admin |
| **Grafo Documenti** | 🕸️ | Visualizza le relazioni tra documenti (SOP ↔ modelli) | Admin |
| **Analytics** | 📈 | Statistiche di utilizzo e feedback | Admin |
| **Trend Analysis** | 📈 | Analisi storico stime, pattern, costi materia prima, export | Tutti |
| **Configurazione** | ⚙️ | Parametri del sistema (provider LLM, DB, OCR) | Admin |
| **Manuale** | 📘 | Questa pagina — guida completa del sistema | Tutti |
        """)

        st.markdown("### Workflow Tipico")
        st.markdown("""
```
1. INDICIZZA     →  Carica i disegni tecnici (PDF, Excel, TIF)
2. VERIFICA      →  Controlla la completezza in "Analisi Disegni"
3. STIMA         →  Inserisci i parametri in "Stima Pesi" e calcola
4. CONFRONTA     →  Verifica la stima con il "Confronto Stima vs Reale"
5. SALVA         →  Salva il progetto e scarica l'Excel
6. ITERA         →  Modifica un parametro e ricalcola (versioning automatico)
```
        """)

    # ==========================================================
    # TAB 2: STIMA PESI
    # ==========================================================
    with tab_stima:
        st.markdown("### ⚖️ Stima Pesi — Guida Completa")

        st.markdown("#### Come funziona il calcolo")
        st.markdown("""
Il sistema calcola il peso di ogni componente usando queste informazioni:

1. **Standard Part List OH2** — 24 componenti con codici TPI (102=Corpo, 161=Coperchio,
   230=Girante, 210=Albero, 330=Supporto, ecc.). Ogni componente ha il flag `needs_weight_calc`
   che indica se richiede stima peso.
2. **D2 — Diametro girante (mm)** — Se inserito, il sistema:
   - Calcola automaticamente **b2** dalla curva Nq aziendale
   - Cerca nel database **disegni con D2 simile** (±30%) come riferimento
   - Calcola lo **scale factor** = D2_new / D2_ref
   - Usa il peso trovato come base per lo scaling
3. **Formule di scaling** (da Flusso stima pesi.docx):
   - Girante: `W_new = W_ref × (D2_new/D2_ref)² × (ρ_new/ρ_ref) × (t_new/t_ref)` — disco, scala D²
   - Corpo pompa: `W_new = W_ref × (D2_new/D2_ref)² × (ρ_new/ρ_ref) × (t_new/t_ref)` — shell, scala D²
   - Coperchio: `W_new = W_ref × (D2_new/D2_ref)³ × (ρ_new/ρ_ref)` — solido 3D, scala D³
   - Flange: calcolate esattamente da DN + rating (ASME B16.5)
   - Albero: `W = π/4 × D² × L × ρ` (barra grezza)
4. **Curva Nq→b2/D2** — Determina b2 girante automaticamente da Nq
   (box verde con ℹ️ sotto i campi Nq e D2)
5. **MAWP (Maximum Allowable Working Pressure)** — Influenza lo spessore
   calcolato per corpo e coperchi tramite SOP-569
6. **SOP-569** — Calcolo spessore corpo pompa (pressione + fondibilità)
7. **SOP-546** — Calcolo spessore dischi girante
8. **Material_Database.xlsm** — 114 materiali reali con Yield, UTS, tipo fornitura
        """)

        st.markdown("#### I 24 componenti OH2")
        st.markdown("""
La Standard Part List OH2 definisce **24 componenti** raggruppati per area:

| Gruppo | Componenti | Stima peso |
|--------|-----------|:-----------:|
| **Idraulica** (6) | Corpo con voluta, Coperchio corpo, Viteria corpo, Girante, Anelli usura fisso/rotante | Corpo ✓, Coperchio ✓, Girante ✓ |
| **Supporto** (4) | Supporto, Coperchi supp. int./est., Viteria coperchi | Supporto ✓ |
| **Meccanica** (2) | Albero, Camicia prot. albero | Albero ✓ |
| **Cuscinetti** (2) | Lato interno, Lato motore | Da catalogo |
| **Tenute** (4) | Premitreccia, Anello baderna, Boccole tenuta/fondo | Da catalogo |
| **Accoppiamento** (1) | Protezione giunto | Da catalogo |
| **Basamento** (2) | Piastra di base, Bulloni fondazione | Stima geometrica |
| **Accessori** (3) | Viteria varia 2%, Varie 2%, Conservazione | % forfettaria |

> Tutti i codici TPI (102, 161, 230, 210, 330...) e i modelli TPI/Legacy sono
> visualizzati sotto il dropdown "Famiglia Pompa".
        """)

        st.markdown("#### Esempio completo passo-passo")
        st.info("""
**Scenario:** Devo stimare il peso di una pompa OH2 con girante D2 = 350mm.

**Parametri dal datasheet:**
| Campo | Valore | Perché |
|-------|--------|--------|
| Famiglia | OH2 | Between bearings, overhung → 24 componenti |
| Nq | 30 | Dal datasheet: velocità specifica |
| **D2** | **350 mm** | Diametro girante dal disegno → auto-calcola b2, scale factor, cerca disegni simili |
| **MAWP** | **35 bar** | Maximum Allowable Working Pressure → spessore corpo aumentato |
| Temperatura | 180°C | Fluido caldo |
| Materiale | SS 316 | Per resistenza a corrosione |
| Rating | 300# | Perché 150# non basta per 35 bar |
| Aspirazione | 8" | Dal nozzle schedule |
| Mandata | 6" | Dal nozzle schedule |

**Cosa calcola il sistema:**
- Curva Nq: b2/D2 = 0.091 → b2 = 31.9 mm
- Cerca nel database disegni con D2 ≈ 350mm
- Stima **17/24 componenti** con peso totale ~2600 kg
        """)

        st.markdown("#### Gestione Progetti")
        st.markdown("""
**📂 Carica Progetto** — Se hai progetti salvati, selezionali dal dropdown in cima.
Tutti i parametri del form si compilano automaticamente.

**💾 Salva Progetto** — Dopo il calcolo, in fondo alla pagina puoi salvare
la configurazione con un nome. Se salvi con lo stesso nome, viene creata una
nuova revisione (Rev.1, Rev.2, Rev.3...).

> **Esempio nome progetto:** `BB1-8x6-Petrolchimico-Rev.A` o `Progetto-12345-Offerta`
        """)

        st.markdown("#### Alert Intelligenti")
        st.markdown("""
Dopo ogni stima, il sistema mostra automaticamente:

- **🟢 Copertura documentale alta (>70%):** "15 documenti trovati per BB1. Base dati solida."
- **🟡 Copertura media (40-70%):** "Solo 3 documenti per questa configurazione."
- **🔴 Copertura bassa (<40%):** "Nessun documento per SS316. Consiglio: indicizza i disegni del progetto XY."

La copertura si basa su: quanti documenti nel database contengono la stessa famiglia
e materiale che hai selezionato.
        """)

        st.markdown("#### Confronto Stima vs Reale")
        st.markdown("""
Il sistema cerca automaticamente pompe simili nel database dei pesi reali e calcola l'accuratezza:

```
La tua stima:    2450 kg
Media riferimenti: 2380 kg
Accuratezza:     97.2% 🟢 Eccellente
```

Per migliorare l'accuratezza:
1. **Inserisci pesi reali** delle pompe costruite (sezione "Inserisci Peso Reale")
2. **Indicizza più disegni** con dati di peso
3. **Usa parametri precisi** dal datasheet (non lasciare i default)
        """)

    # ==========================================================
    # TAB 3: DATABASE & ANALISI
    # ==========================================================
    with tab_db:
        st.markdown("### 📊 Database & Analisi — Guida")

        st.markdown("#### Database Pompe")
        st.markdown("""
La pagina **Database Pompe** mostra tutti i componenti estratti automaticamente
dai disegni tecnici indicizzati. Per ogni componente vengono estratti:

- Tipo componente (Cover, Casing, Impeller, Shaft...)
- Peso (se trovato nel disegno)
- Materiale
- Part Number
- Rating flange
- Revisione e formato disegno

**Come usarla:**
1. Filtra per famiglia, tipo componente o ricerca testo
2. Consulta la tabella — clicca su "Componente" per ordinare
3. Seleziona un componente dal dropdown "Dettaglio" per vedere tutti i dati

> **Esempio:** Filtra per "Cover" per vedere tutti i coperchi estratti,
> con peso e materiale di ciascuno.
        """)

        st.markdown("#### Analisi Disegni")
        st.markdown("""
La pagina **Analisi Disegni** verifica la **completezza dei metadati** per
ogni documento indicizzato. Mostra una tabella con:

| Colonna | Significato |
|---------|-------------|
| ✅ / ❌ Pesi | Il documento contiene informazioni sui pesi? |
| ✅ / ❌ Materiali | Contiene specifiche dei materiali? |
| ✅ / ❌ Dimensioni | Ci sono dimensioni/misure? |
| ✅ / ❌ Famiglia | È identificata la famiglia pompa? |
| Completezza | Percentuale di campi trovati (0-100%) |

**Filtri combinati (AND/OR):**
- **AND:** Il documento deve avere TUTTI i campi selezionati
- **OR:** Il documento deve avere ALMENO UNO dei campi selezionati
- **Ricerca testo:** Filtra per nome documento

> **Esempio:** Seleziona "Pesi" + "Materiali" in AND per trovare solo i disegni
> che hanno SIA peso CHE materiale specificati.
        """)

    # ==========================================================
    # TAB 4: CHAT & RICERCA
    # ==========================================================
    with tab_chat:
        st.markdown("### 💬 Chat RAG — Guida")

        st.markdown("""
La **Chat RAG** ti permette di fare domande in linguaggio naturale sui documenti
tecnici indicizzati. Il sistema:

1. Cerca nei documenti le informazioni più rilevanti
2. Passa i risultati all'AI
3. Genera una risposta con **citazioni** ai documenti sorgente

**Esempi di domande efficaci:**
        """)

        st.success("""
✅ **Buone domande:**
- "Qual è il peso del casing della pompa BB1 8×6×13?"
- "Che materiale viene usato per l'impeller delle pompe VS4?"
- "Quali sono le dimensioni delle flange 300# per pompa OH2?"
- "Confronta i pesi delle pompe BB1 vs BB2 con stesso Nq"
        """)

        st.error("""
❌ **Domande poco efficaci:**
- "Quanto pesa?" (troppo vaga — specifica QUALE componente di QUALE pompa)
- "Dimmi tutto" (troppo generica — il sistema cerca nei top 10 documenti)
- "Calcola il peso" (usa la pagina Stima Pesi, non la chat)
        """)

        st.markdown("""
**Opzioni avanzate:**
| Opzione | Cosa fa |
|---------|---------|
| 🔍 **Ricerca Web** | Aggiunge risultati da internet oltre ai documenti locali |
| 🧠 **Depth Reasoning** | L'AI ragiona in modo indipendente oltre ai dati RAG |
| 📊 **Filtri Smart** | Filtra per famiglia, materiale, tipo documento |
| 🔄 **Confronta Modelli** | Stessa domanda a GPT-4, Claude, Gemini — confronto side-by-side |
        """)

    # ==========================================================
    # TAB 5: TREND ANALYSIS
    # ==========================================================
    with tab_trend:
        st.markdown("### 📈 Trend Analysis — Guida")

        st.markdown("""
La pagina **Trend Analysis** analizza lo storico di tutte le stime salvate per
evidenziare pattern, confrontare con la media, e stimare i costi materia prima.

**Requisito:** Le stime devono essere **salvate** (bottone "💾 Salva Progetto" nella
pagina Stima Pesi). Più stime salvi, più i dati sono significativi.
        """)

        st.markdown("#### KPI in tempo reale")
        st.markdown("""
| KPI | Cosa mostra |
|-----|-------------|
| **Stime Totali** | Numero di stime salvate e quante famiglie diverse |
| **Peso Medio** | Media, minimo e massimo di tutte le stime |
| **Costo Medio MP** | Costo medio materia prima (peso × €/kg del materiale) |
| **Confidenza Media** | Percentuale media di componenti ad alta confidenza |
        """)

        st.markdown("#### Grafici")
        st.markdown("""
- **Distribuzione per Famiglia** — Quante stime per ogni famiglia pompa (OH1, BB1, VS4...)
- **Distribuzione per Materiale** — Quale materiale viene usato più spesso
- **Andamento nel Tempo** — Grafico lineare dei pesi con linea media tratteggiata
- **Confronto Famiglie** — Peso medio per famiglia (utile per scoprire quale famiglia è più pesante)
- **Costo per Materiale** — Costo medio materia prima per ogni materiale usato
        """)

        st.markdown("#### Tabella Storico")
        st.markdown("""
Tabella interattiva con tutte le stime. Per ogni stima mostra:

- **Parametri** — Famiglia, Nq, fattore scala, materiale, rating
- **Peso (kg)** — Peso totale stimato
- **Costo (€)** — Costo materia prima stimato (peso × €/kg)
- **vs Media** — Confronto con la media della stessa famiglia:
  - `↑ +15%` = sopra la media (badge giallo)
  - `↓ -10%` = sotto la media (badge verde)
  - `≈ media` = vicino alla media (badge azzurro)

Puoi filtrare per **famiglia** e **materiale** con i multiselect in cima.
        """)

        st.markdown("#### Export CSV")
        st.markdown("""
Bottone **⬇️ Scarica CSV** in fondo alla pagina. Il file contiene tutti i dati
delle stime in formato CSV (separatore `;`), apribile con Excel.

> **Nota sui costi:** I costi €/kg sono indicativi da letteratura industriale.
> Se servono costi reali, i valori si trovano in `weight_engine/materials.py`
> nel dizionario `MATERIAL_COST_EUR_KG`.
        """)

    # ==========================================================
    # TAB 6: AMMINISTRAZIONE
    # ==========================================================
    with tab_admin:
        st.markdown("### 🔧 Amministrazione — Guida")

        st.markdown("#### Indicizza Documenti")
        st.markdown("""
Per caricare nuovi documenti nel sistema:

1. Vai su **Indicizza Documenti**
2. Specifica il percorso cartella (locale o SharePoint)
3. Clicca **Avvia Indicizzazione**
4. Il sistema processa automaticamente: PDF, Excel, TIF, Word, immagini

**Formati supportati:**
| Formato | Tipo processamento |
|---------|-------------------|
| PDF | Estrazione testo + tabelle + OCR per scansioni |
| Excel (.xlsx) | Lettura tabelle e celle |
| TIF/TIFF | OCR (Tesseract o Google Vision) |
| Word (.docx) | Estrazione testo strutturato |
| Immagini (PNG, JPG) | OCR + descrizione AI |

**Consiglio:** Indicizza almeno **50-100 disegni** per avere una base dati
significativa. Il sistema migliora con più documenti.

> **Esempio:** Indicizza la cartella `Weight Estimation Project-2/` che contiene
> i disegni storici delle pompe. Dopo l'indicizzazione vedrai i nuovi documenti
> in Dashboard, Database Pompe e Analisi Disegni.
        """)

        st.markdown("#### Configurazione")
        st.markdown("""
La pagina **Configurazione** permette di impostare:

| Parametro | Default | Descrizione |
|-----------|---------|-------------|
| Provider LLM | OpenAI | Motore AI per chat e analisi |
| Vector DB | Qdrant | Database vettoriale per documenti |
| Parallel Workers | 4 | Thread paralleli per indicizzazione |
| Chunk Batch Size | 50 | Documenti per batch di indicizzazione |
| Lingua OCR | ita+eng | Lingue per riconoscimento testo |
        """)

    # ==========================================================
    # TAB 6: FAQ
    # ==========================================================
    with tab_faq:
        st.markdown("### ❓ FAQ — Domande Frequenti")

        with st.expander("Come posso migliorare l'accuratezza delle stime?"):
            st.markdown("""
1. **Indicizza più disegni** — Più documenti = più dati di riferimento
2. **Inserisci pesi reali** — Usa "Inserisci Peso Reale" dopo ogni stima
3. **Usa parametri precisi** — Non lasciare i default, inserisci i valori dal datasheet
4. **Verifica la copertura documentale** — Gli Alert Intelligenti ti dicono se hai abbastanza dati
            """)

        with st.expander("Come salvo e ricarico una configurazione?"):
            st.markdown("""
1. Dopo aver calcolato la stima, scorri fino a "💾 Salva Progetto"
2. Inserisci un nome (es. `BB1-Offerta-12345`)
3. La prossima volta, selezionalo dal dropdown "📂 Carica Progetto" in cima alla pagina
4. Tutti i parametri si compilano automaticamente

Se salvi con lo stesso nome, viene creata una **nuova revisione** (Rev.1 → Rev.2).
            """)

        with st.expander("Cosa significano i colori di confidenza?"):
            st.markdown("""
| Colore | Significato | Quando appare |
|--------|-------------|---------------|
| 🟢 **Alta** | Formula validata con dati reali | Componenti principali con molti riferimenti |
| 🟡 **Media** | Stima ragionevole ma non validata | Componenti secondari o con pochi dati |
| 🔴 **Bassa** | Approssimazione indicativa | Componenti rari o senza dati di riferimento |
            """)

        with st.expander("Come funziona il Confronto Stima vs Reale?"):
            st.markdown("""
Il sistema cerca nel database:
1. Pompe con la **stessa famiglia** (es. BB1)
2. Pompe con **peso reale noto** (inseriti manualmente o estratti dai disegni)
3. Calcola la **media dei pesi reali** e la confronta con la tua stima
4. Mostra l'**accuratezza** in percentuale

**Per avere il confronto:** inserisci almeno 2-3 pesi reali per la stessa famiglia.
            """)

        with st.expander("Posso usare il sistema offline?"):
            st.markdown("""
**Parzialmente.** Il sistema richiede:
- ✅ **Qdrant** può girare in locale (Docker `qdrant/qdrant`)
- ❌ **API LLM** richiedono connessione internet (OpenAI, Anthropic, Google)
- ✅ **Stima pesi** funziona offline (solo formule matematiche)
- ❌ **Chat RAG** richiede un provider LLM attivo
            """)

        with st.expander("Come resetto il database?"):
            st.markdown("""
1. Vai su **Indicizza Documenti**
2. Espandi "⚠️ Reset Database"
3. Conferma il reset — tutti i documenti vengono rimossi
4. Re-indicizza i documenti necessari

**Attenzione:** Il reset elimina TUTTI i documenti, non è possibile annullare.
            """)

        with st.expander("Cosa sono gli Standard aziendali integrati?"):
            st.markdown("""
Il sistema integra documenti standard dalla cartella `Standards/` e `Standard part list/`:

| Standard | Cosa fa |
|----------|---------|
| **Material_Database.xlsm** | 114 materiali reali con Yield, UTS, densità, tipo fornitura (casting/bar/forging/bolting) |
| **Curva nq-D2-b2.xlsx** | Rapporto b2/D2 in funzione di Nq (26 punti empirici). Es: Nq=30 → b2/D2=0.091. Visualizzato nel box verde ℹ️ sotto Nq/D2 |
| **SOP-569** | Formula spessore corpo pompa: `t = (P×D)/(2×S×E-1.2×P) + sovrametallo`. Usa il valore MAWP |
| **SOP-546** | Formula spessore disco girante: `t = k×D2×√(P/S)`. k=0.020 (posteriore), k=0.015 (anteriore) |
| **Mod.463** | Selezione DN nozzle dalla portata: `V = Q/(π/4×D²)`. Limiti: aspirazione ≤4.6 m/s, mandata ≤7.6 m/s |
| **Mod.496** | Dimensionamento albero API 610: `d = k×(P/n)^(1/3)`. k=85(OH), 72(BB), 78(VS) |
| **Standard Part List OH2.xls** | **24 componenti** con codici TPI (102=Corpo, 161=Coperchio, 230=Girante, 210=Albero, 330=Supporto, 890=Piastra base...), nomi italiani, flag stima peso, quantità. Include mapping modelli TPI (100AP-300AP) e Legacy (A, AM, AH, AL) |

Questi dati vengono usati automaticamente nel calcolo — non serve fare nulla!
            """)

        with st.expander("Come funziona il Trend Analysis?"):
            st.markdown("""
Il **Trend Analysis** analizza tutte le stime che hai salvato:

1. **Salva le stime** dopo ogni calcolo (bottone "💾 Salva Progetto")
2. **Vai su Trend Analysis** nel menu laterale
3. Visualizzi: KPI, grafici, tabella con costi e confronto media
4. **Export CSV** per analisi esterna in Excel

**Servono almeno 2-3 stime** per vedere grafici significativi.
Più stime fai, più i pattern diventano evidenti.

**Costi materia prima:** Calcolati come `peso × €/kg del materiale`.
I costi sono indicativi — puoi personalizzarli in `weight_engine/materials.py`.
            """)


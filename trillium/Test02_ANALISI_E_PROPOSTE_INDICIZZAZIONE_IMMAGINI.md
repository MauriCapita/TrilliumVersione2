# Analisi cartella Test02 e proposte per rafforzare l’indicizzazione immagini

> **Contesto TrilliumVersione2:** I disegni tecnici TIF in Test02 sono componenti di pompe centrifughe, e costituiscono parte della base dati per la **stima AI dei pesi dei componenti**. Una corretta indicizzazione di questi disegni è fondamentale per il recupero di pompe di riferimento simili durante il processo di weight estimation.

## 1. Analisi cartella Test02

- **Contenuto:** ~119 file `.tif` in `Test02/OneDrive_1_10-02-2026/` (sottocartelle tipo "OH2 database").
- **Dimensione totale:** ~54 MB.
- **Tipo di file:** disegni tecnici di componenti pompe (nomi tipo `230A74P10-REV00-A3.tif`, `502A79F20-REV00-A3.tif`).
- **Formato TIF:** TIFF bi-level (bianco/nero), compressione Group 4 (CCITT), `PhotometricInterpretation=WhiteIsZero`; alcune pagine con `height=0, width=0` (possibile multi‑pagina o IFD particolare); altre con risoluzione alta (es. 4960×3507 px).
- **Estensioni supportate oggi in pipeline:** `.tif`, `.tiff` → OCR locale (Tesseract) e, se testo insufficiente, Vision (Google, Claude, Gemini via OpenRouter). Limite file 25 MB per le API.

---

## 2. Comportamento attuale del motore (estratto da `rag/extractor.py`)

| Fase | Comportamento |
|------|----------------|
| **TIF in ingresso** | `extract_tif_local(path)` con Tesseract su `PIL.Image.open(path)` → **solo primo frame** se il TIF è multi‑pagina. |
| **Soglia “testo sufficiente”** | `MIN_TEXT_LENGTH = 30`: se il testo estratto ha ≥ 30 caratteri si considera OK e **non** si chiama Vision. |
| **Fallback Vision (solo per immagini)** | Se testo locale < 30 caratteri: 1) Google Cloud Vision, 2) Claude 3.5 Sonnet (OpenRouter), 3) Gemini 2.0 Flash (OpenRouter). Se nessuno configurato/disponibile → ritorna stringa vuota. |
| **Limite dimensione** | `encode_image_to_base64` e Vision: file > 25 MB → errore, nessuna elaborazione. |
| **OpenAI Vision** | Non usato per TIF (supporta solo PNG, JPEG, GIF, WEBP). |
| **Google Vision** | Legge il file binario e fa `text_detection`; **non** gestisce esplicitamente multi‑pagina (un solo `Image` per file). |

**Problemi rilevati:**

1. **TIFF multi‑pagina:** solo la prima pagina viene considerata (PIL/Tesseract e flusso Vision attuale).
2. **Disegni tecnici bi‑level:** Tesseract spesso restituisce poco testo → si passa a Vision; se non ci sono chiavi Google/OpenRouter l’immagine può restare senza testo indicizzato.
3. **Soglia 30 caratteri:** molto bassa; si può considerare “sufficiente” un OCR scarso e non chiamare Vision dove invece servirebbe una descrizione più ricca.
4. **File grandi:** TIF molto grandi (es. A0 ad alta risoluzione) possono superare 25 MB e essere scartati.
5. **Nessuna “descrizione semantica” di fallback:** se OCR e Vision restituiscono poco o nulla, non si genera comunque una descrizione per la ricerca semantica (es. “disegno tecnico pompa OH2, revisione A3”).
6. **Risoluzione per API:** alcune API hanno limiti su dimensioni immagine; TIF 4960×3507 potrebbero richiedere ridimensionamento prima dell’invio.
7. **Lingua Tesseract:** non configurata esplicitamente (default spesso `eng`); per etichette IT/EN potrebbe servire `ita+eng`.

---

## 3. Proposte di soluzione (da implementare)

### A. TIFF multi‑pagina

- **Obiettivo:** indicizzare tutte le pagine, non solo la prima.
- **Proposta:**
  - Per `.tif`/`.tiff`: usare `PIL.Image.open` in un loop su `Image.Sequence` (o su `n_frames` / `seek`) e per ogni frame estrarre testo (Tesseract) e/o inviare a Vision.
  - Aggregare il testo di tutte le pagine (es. con separatore `\n--- Page N ---\n`) in un unico testo da chunkare/indicizzare, mantenendo il `source` come path del file (eventualmente con metadato “multi‑page” se utile in futuro).
- **Dove:** `extract_tif_local` e, se si invia a Vision per fallback, estendere la logica a “una chiamata per pagina” (o batch dove le API lo consentono) e concatenare i risultati.

### B. Migliorare OCR locale per TIF tecnici

- **Obiettivo:** aumentare il testo estratto in locale per disegni bi‑level (meno dipendenza da Vision quando non configurata).
- **Proposta:**
  - Per TIF in modalità `1` (bianco/nero) o `L`: prima di passare a Tesseract, eventuale **inversione** se `WhiteIsZero` (così il testo nero su bianco è più riconoscibile da Tesseract).
  - Configurare Tesseract con `lang='ita+eng'` (o parametro configurabile in `config`) per le estrazioni locali.
  - Opzione in config: `PREFER_LOCAL_OCR_FOR_IMAGES = true` e soglia `MIN_TEXT_LENGTH` per immagini più alta (es. 100–200) prima di considerare “insufficiente” e passare a Vision, così si usa Vision solo quando l’OCR locale è chiaramente povero.

### C. Soglia e strategia “testo insufficiente”

- **Obiettivo:** usare Vision quando serve davvero; evitare di considerare “OK” un OCR con 30 caratteri su un disegno complesso.
- **Proposta:**
  - Introdurre in `config` una soglia dedicata alle immagini, es. `MIN_TEXT_LENGTH_IMAGE = 100` (o 200).
  - In `extract_text`, per `ext in [".tif", ".tiff", ".bmp", ".png", ...]`: usare `MIN_TEXT_LENGTH_IMAGE` invece di `MIN_TEXT_LENGTH` per decidere se il testo locale è sufficiente o passare a Vision.
  - Documentare in README/config che aumentando questo valore si forza di più l’uso di Vision (migliore qualità, più costo/latenza).

### D. Limite 25 MB e file grandi

- **Obiettivo:** non scartare TIF grandi; ridurre dimensione per le API senza perdere leggibilità del testo.
- **Proposta:**
  - Rendere il limite configurabile, es. `MAX_IMAGE_SIZE_MB = 25` in `config` (o `.env`).
  - Per file sopra la soglia: **ridimensionare** l’immagine (es. max 2048 px sul lato lungo, mantenendo aspect ratio) e usare quella per Vision/OCR; oppure, per TIF multi‑pagina, elaborare solo le prime N pagine sotto una dimensione totale stimata.
  - In alternativa: per file > 25 MB, usare **solo** OCR locale (Tesseract) su una versione ridimensionata in memoria, senza chiamate Vision, così almeno qualcosa viene indicizzato.

### E. Fallback “descrizione semantica” quando OCR/Vision restano poveri

- **Obiettivo:** anche con poco testo, avere un contenuto indicizzabile per ricerca semantica (es. per nome file e tipo documento).
- **Proposta:**
  - Dopo la pipeline attuale (locale + Vision), se il testo finale ha ancora lunghezza < soglia (es. < 100 caratteri):
    - Costruire un **testo di fallback** con: nome file, estensione, eventuale metadato (numero di pagine se multi‑page).
    - Opzionale: una sola chiamata Vision con prompt tipo “Describe briefly this technical drawing for search: part number, type of document, main content in one sentence” e concatenare quel testo al fallback.
  - Il testo così ottenuto viene usato per embedding/chunk come gli altri, così il file resta trovabile per nome/tipo anche se OCR è scarso.

### F. Ridimensionamento prima di invio a Vision

- **Obiettivo:** rispettare limiti di risoluzione/dimensione delle API e ridurre timeout/errori.
- **Proposta:**
  - Prima di `encode_image_to_base64` per OpenAI/OpenRouter/Google: se l’immagine (in pixel) supera una soglia (es. 4096 sul lato lungo), ridimensionarla con PIL mantenendo aspect ratio, poi codificare la versione ridotta.
  - Parametro in config: `MAX_IMAGE_SIDE_PX = 4096` (o per API specifiche se hanno limiti diversi).

### G. Configurazione lingua OCR e preferenza locale/cloud

- **Obiettivo:** adattare il motore a documentazione IT/EN e controllare costi.
- **Proposta:**
  - In `config` (o `.env`): `TESSERACT_LANG = ita+eng` (o `eng`).
  - In `config`: `IMAGE_EXTRACTION_STRATEGY = "local_then_vision"` | `"local_only"` | `"vision_only"` (per test o ambienti senza chiavi Vision).
  - Nel codice: usare `TESSERACT_LANG` in tutte le chiamate `pytesseract.image_to_string(..., lang=...)`; rispettare `IMAGE_EXTRACTION_STRATEGY` nella pipeline `extract_text` per immagini.

### H. Log e statistiche per immagini

- **Obiettivo:** capire quante immagini vengono indicizzate, con quale metodo (locale vs Vision) e quante falliscono.
- **Proposta:**
  - In fase di indicizzazione: contare per tipo (TIF, PNG, …) quanti file sono processati con successo con OCR locale, quanti con Vision, quanti con fallback “descrizione”, quanti scartati (dimensione, errore).
  - Scrivere in log (e opzionalmente in risposta Streamlit/CLI) un riepilogo tipo: `TIF: 80 local, 35 vision, 4 fallback, 0 skipped`.

---

## 4. Priorità suggerita

| Priorità | Proposta | Motivo |
|----------|----------|--------|
| 1 | **A. TIFF multi‑pagina** | Test02 e simili possono contenere TIF multi‑pagina; oggi solo pagina 1 viene indicizzata. |
| 2 | **C. Soglia immagini** | Usare una soglia più alta (es. 100–200) per le immagini fa sì che Vision venga usato quando l’OCR locale è davvero insufficiente. |
| 3 | **E. Fallback descrizione** | Evita che un’immagine resti “vuota” in indice; migliora la findability anche con OCR scarso. |
| 4 | **B. OCR TIF bi‑level** | Migliora la resa su disegni tecnici bianco/nero senza toccare le API. |
| 5 | **G. Lingua e strategia** | Configurabilità e supporto ita+eng. |
| 6 | **D. Limite 25 MB / ridimensionamento** | Abilita TIF grandi e riduce errori API (da combinare con F). |
| 7 | **F. Ridimensionamento per API** | Stabilità e rispetto limiti delle API. |
| 8 | **H. Log/statistiche** | Utile per monitoraggio e tuning. |

---

## 5. Riepilogo

- **Test02:** 119 TIF, disegni tecnici, possibile multi‑pagina e risoluzioni alte.
- **Punti critici attuali:** una sola pagina per TIF, soglia 30 caratteri troppo bassa per immagini, nessun fallback semantico, limite 25 MB e nessun ridimensionamento, OCR non ottimizzato per bi‑level e lingua.
- Le proposte A–H possono essere implementate in modo incrementale; partire da A, C ed E dà il massimo beneficio per “indicizzare il più possibile” le immagini, in particolare per cartelle come Test02.

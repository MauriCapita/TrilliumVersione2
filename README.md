# PrestaShop Dashboard - Sistema Completo

Sistema completo per la gestione di ordini PrestaShop con integrazione ShippyPro per il tracking delle spedizioni e Trillium RAG per la gestione documentale.

## 🚀 Funzionalità Principali

- **📦 Gestione Ordini PrestaShop**: Visualizza e cerca ordini con interfaccia web moderna
- **👥 Gestione Clienti**: Lista clienti con ricerca e filtri avanzati
- **📦 Tracking ShippyPro**: Integrazione completa con ShippyPro per dettagli di spedizione
- **📄 Trillium RAG**: Sistema RAG integrato per indicizzazione e ricerca documentale
- **🔄 Integrazione Ordini API nel RAG**: Indicizza e cerca ordini PrestaShop e ShippyPro nel sistema RAG (nuovo!)
- **🔄 Avvio Automatico**: Tutti i servizi partono automaticamente con un solo comando

---

## 📦 Installazione

### 1. Installa le dipendenze

```bash
pip install -r requirements.txt
```

### 2. Configurazione

Copia il file di esempio della configurazione:

```bash
cp config.py.example config.py
```

Modifica `config.py` con le tue credenziali:

```python
BASE_URL = "https://www.adesivisicurezza.it"
API_KEY = "KWYH69WBFHYCC24RZZNN5ANQXG36H1Q6"
SHIPPYPRO_API_KEY = "22aebf80a777a53aedd1f53206d6245e"
```

---

## 🎯 Utilizzo

### Avvio Rapido (Consigliato)

Avvia tutto con un solo comando:

```bash
python app.py
```

Questo avvierà automaticamente:
- **Flask Dashboard** su `http://localhost:8080`
- **Trillium RAG** su `http://localhost:8501`

### Interfaccia Web

Apri il browser e vai su:

**http://localhost:8080**

Troverai:

#### 📦 Tab Ordini
- Lista completa degli ordini PrestaShop
- Ricerca ordine per ID
- Dettagli completi di ogni ordine
- **Tracking ShippyPro**: Clicca sul numero di tracking per vedere tutti i dettagli della spedizione
- Visualizzazione dati JSON completi

#### 👥 Tab Clienti
- Lista completa dei clienti
- Ricerca in tempo reale per nome, cognome, email o azienda
- Dettagli completi di ogni cliente

#### 📄 Trillium RAG
- Link diretto nell'header per accedere a Trillium RAG
- Sistema completo per indicizzazione e ricerca documentale
- Chat conversazionale con i documenti indicizzati

---

## 🔧 API Endpoints

### PrestaShop

- `GET /api/orders` - Lista tutti gli ordini
- `GET /api/orders/search?id=<order_id>` - Cerca un ordine specifico
- `GET /api/customers` - Lista tutti i clienti

### ShippyPro Tracking

- `GET /api/shipping/<shipping_number>` - Dettagli completi di tracking ShippyPro

L'endpoint cerca automaticamente:
- Ordine PrestaShop associato al tracking number
- Informazioni corriere da PrestaShop
- Dettagli completi da ShippyPro usando vari metodi:
  - `GetTracking` (con codice e nome corriere)
  - `GetOrder` (se disponibile OrderID)
  - `GetLabelUrl` (se disponibile OrderID)

---

## 📦 Integrazione ShippyPro

Il sistema integra automaticamente ShippyPro per recuperare tutti i dettagli di tracking:

1. **Ricerca Ordine**: Cerca l'ordine PrestaShop associato al tracking number
2. **Recupero Corriere**: Ottiene il nome del corriere da PrestaShop
3. **Query ShippyPro**: Prova vari metodi API per ottenere tutti i dettagli disponibili
4. **Visualizzazione**: Mostra tutti i dati recuperati nell'interfaccia web

### Formato Richiesta ShippyPro

Il sistema usa il formato corretto dell'API ShippyPro:

```json
{
  "Method": "GetTracking",
  "Params": {
    "Code": "E9660603499",
    "CarrierName": "Nome Corriere"
  }
}
```

---

## 📄 Integrazione Trillium RAG

Trillium RAG è un sistema completo per:

- **Indicizzazione documenti**: PDF, Word, Excel, immagini con OCR
- **Indicizzazione ordini API**: PrestaShop e ShippyPro integrati nel RAG
- **Ricerca semantica**: Trova informazioni nei documenti e negli ordini usando AI
- **Chat conversazionale**: Fai domande sui documenti e ordini indicizzati
- **Confronto modelli**: Confronta risposte di diversi LLM

### Accesso Trillium

1. Clicca sul link **"📄 Trillium RAG"** nell'header della dashboard
2. Oppure vai direttamente su `http://localhost:8501`

### Funzionalità Trillium

- **Dashboard**: Statistiche e visualizzazioni
- **Indicizzazione**: 
  - Aggiungi documenti da cartella locale o SharePoint/OneDrive
  - **Indicizza ordini PrestaShop e ShippyPro** (nuovo!)
- **Chat RAG**: Fai domande conversazionali sui documenti e ordini
- **Confronto Modelli**: Confronta risposte di diversi LLM

### 🔄 Integrazione Ordini API nel RAG (Nuovo!)

Trillium RAG ora include l'integrazione completa con PrestaShop e ShippyPro per indicizzare e cercare ordini:

#### Funzionalità Ordini API

1. **Indicizzazione Ordini**:
   - **PrestaShop**: Recupera e indicizza tutti gli ordini (fino a ~53,561 ordini)
   - **ShippyPro**: Recupera e indicizza ordini/spedizioni da ShippyPro
   - **Payload Completo**: Tutti i campi dell'ordine vengono indicizzati (non solo un riepilogo)
   - **Associations**: Include tutti i prodotti ordinati con dettagli completi
   - **Filtri Data**: Opzionalmente filtra per ultimi 6 mesi o range personalizzato

2. **Ricerca Intelligente**:
   - Cerca ordini per ID, riferimento, cliente, prodotto, data, ecc.
   - La chat RAG può rispondere a domande come:
     - "Quanti ordini abbiamo a portafoglio?"
     - "Mostrami l'ordine 53515"
     - "Quali ordini sono stati spediti oggi?"
     - "Cerca ordini del cliente X"

3. **Fallback Automatico**:
   - Se un ordine non è trovato su PrestaShop, cerca automaticamente su ShippyPro
   - Supporta ricerca per OrderID e TransactionID

4. **Interfaccia Streamlit**:
   - Tab "Ordini API" nella pagina "Indicizza"
   - Checkbox per selezionare PrestaShop e/o ShippyPro
   - Statistiche dettagliate dopo l'indicizzazione:
     - Ordini recuperati
     - Ordini indicizzati
     - Ordini saltati (duplicati)
     - Ultimo ordine ID per ogni sorgente

#### Come Usare l'Indicizzazione Ordini

1. Vai su `http://localhost:8501`
2. Clicca su **"Indicizza"** nella sidebar
3. Vai al tab **"Ordini API"**
4. Seleziona:
   - ☑️ **PrestaShop** - per indicizzare ordini PrestaShop
   - ☑️ **ShippyPro** - per indicizzare ordini ShippyPro
5. (Opzionale) Seleziona **"Indicizza automaticamente solo ultimi 6 mesi"** per filtrare per data
6. Clicca **"Avvia Indicizzazione Ordini"**
7. Attendi il completamento (può richiedere alcuni minuti per migliaia di ordini)
8. Vai alla **"Chat RAG"** e fai domande sugli ordini!

#### Dettagli Tecnici

- **Recupero Completo**: Il sistema recupera TUTTI gli ordini iterando per ID range (1-53600)
- **Nessun Loop Infinito**: Controlli automatici per evitare loop infiniti
- **Gestione Duplicati**: Gli ordini già indicizzati vengono saltati automaticamente
- **Formato Dati**: Ogni ordine include:
  - Tutti i campi dell'ordine (ID, riferimento, date, totali, stato, ecc.)
  - Informazioni cliente complete
  - Indirizzi di spedizione e fatturazione
  - Lista prodotti ordinati con dettagli completi
  - Associations JSON completo
  - Payload JSON completo dell'ordine

#### Esempi di Query RAG sugli Ordini

```
"Quanti ordini abbiamo a portafoglio?"
"Mostrami i dettagli dell'ordine 53515"
"Quali ordini sono stati spediti oggi?"
"Cerca ordini del cliente con email X"
"Quali prodotti sono stati ordinati nell'ordine VZEKDZDHM?"
"Mostrami tutti gli ordini con totale superiore a 100 euro"
```

Per maggiori dettagli su Trillium RAG, consulta `trillium/README.md`

---

## 🛠️ Utilizzo Programmatico

### Client PrestaShop

```python
from prestashop_client import PrestaShopClient
from config import BASE_URL, API_KEY

# Inizializza il client
client = PrestaShopClient(BASE_URL, API_KEY)

# Ottieni la lista degli ordini
orders = client.get_orders({
    'display': 'full',
    'limit': 100
})

# Ottieni un ordine specifico
order = client.get_order(order_id=53190)

# Ottieni la lista dei clienti
customers = client.get_customers({
    'display': 'full',
    'limit': 100
})
```

### Client ShippyPro

```python
from shippypro_client import ShippyProClient
from config import SHIPPYPRO_API_KEY

# Inizializza il client
shippypro = ShippyProClient(SHIPPYPRO_API_KEY)

# Ottieni tracking
tracking = shippypro.get_tracking(
    tracking_code="E9660603499",
    carrier_name="Nome Corriere"
)
```

---

## 📋 Metodi Disponibili

### PrestaShopClient

- `get(endpoint, params=None)` - Richiesta GET
- `post(endpoint, data)` - Richiesta POST
- `put(endpoint, data)` - Richiesta PUT
- `delete(endpoint)` - Richiesta DELETE
- `get_products(params=None)` - Lista prodotti
- `get_product(product_id)` - Prodotto specifico
- `get_orders(params=None)` - Lista ordini
- `get_order(order_id)` - Ordine specifico
- `get_customers(params=None)` - Lista clienti
- `get_customer(customer_id)` - Cliente specifico

### ShippyProClient

- `make_request(method, data=None)` - Richiesta generica all'API ShippyPro
- `get_tracking(tracking_code, carrier_name=None)` - Ottieni tracking
- `get_order(order_id)` - Ottieni ordine ShippyPro
- `get_order_by_transaction_id(transaction_id)` - Cerca ordine per TransactionID

---

## ⚙️ Configurazione Avanzata

### Gestione Errori

Il sistema include gestione errori avanzata con messaggi user-friendly per:
- Errori SSL/Permessi
- Errori di connessione
- Errori di autenticazione (401)
- Errori risorsa non trovata (404)

### Verifica SSL

Il client PrestaShop disabilita la verifica SSL per default (`verify_ssl=False`) per evitare problemi di permessi. Per abilitarla:

```python
client = PrestaShopClient(BASE_URL, API_KEY, verify_ssl=True)
```

---

## 🚨 Troubleshooting

### Porta già in uso

Se vedi "Address already in use":

```bash
# Ferma tutti i processi
lsof -ti:8080 | xargs kill -9
lsof -ti:8501 | xargs kill -9

# Riavvia
python app.py
```

### Streamlit non parte

Se Streamlit non si avvia automaticamente:

```bash
cd trillium
streamlit run streamlit_app.py --server.port 8501
```

### Errori SSL

Se vedi errori SSL, il sistema li gestisce automaticamente. Se persistono, verifica:
- Connessione internet
- Certificati SSL del server PrestaShop
- Firewall/Proxy

### ShippyPro non restituisce dati

Il sistema prova automaticamente vari metodi. Se non trova dati:
- Verifica che il tracking number sia corretto
- Controlla che l'ordine esista in PrestaShop
- Verifica le credenziali API ShippyPro

---

## 📝 Note Importanti

1. **Abilitazione API REST**: Assicurati che l'API REST sia abilitata nel pannello PrestaShop:
   - Vai su Configurazione > Configurazione avanzata > API
   - Abilita l'API REST

2. **Sicurezza**: Non committare mai il file `config.py` con le credenziali reali nel repository Git.

3. **URL formato**: L'URL del negozio deve essere senza slash finale (es. `https://mio-store.com` e non `https://mio-store.com/`)

4. **Avvio Automatico**: Quando avvii `app.py`, entrambi i servizi (Flask e Streamlit) partono automaticamente. Se Streamlit non parte, puoi avviarlo manualmente.

5. **Indicizzazione Ordini RAG**: 
   - La prima indicizzazione di tutti gli ordini PrestaShop può richiedere diversi minuti (~53,561 ordini)
   - Il sistema recupera automaticamente tutti gli ordini iterando per ID range
   - Gli ordini già indicizzati vengono saltati (indicizzazione incrementale)
   - Puoi filtrare per data per indicizzare solo ordini recenti
   - Il sistema include controlli per evitare loop infiniti durante il recupero

---

## 📚 Documentazione

- **PrestaShop API**: https://devdocs.prestashop.com/1.7/webservice/
- **ShippyPro API**: https://www.shippypro.com/ShippyPro-API-Documentation
- **Trillium RAG**: Vedi `trillium/README.md` per documentazione completa

---

## 🏗️ Struttura Progetto

```
.
├── app.py                 # Server Flask principale
├── config.py              # Configurazione (credenziali API)
├── prestashop_client.py   # Client PrestaShop API
├── shippypro_client.py    # Client ShippyPro API
├── requirements.txt       # Dipendenze Python
├── templates/
│   └── index.html        # Interfaccia web
├── static/
│   ├── css/
│   │   └── style.css     # Stili
│   └── js/
│       └── app.js        # JavaScript frontend
└── trillium/             # Sistema RAG Trillium
    ├── streamlit_app.py  # Interfaccia Streamlit
    ├── app.py            # CLI Trillium
    └── rag/              # Moduli RAG
        ├── api_integration.py  # Integrazione PrestaShop/ShippyPro per RAG
        ├── indexer.py          # Indicizzazione documenti e ordini
        ├── query.py            # Query RAG e generazione risposte
        ├── extractor.py        # Estrazione testo da documenti
        ├── qdrant_db.py        # Integrazione Qdrant
        └── ...
```

---

## 📄 Licenza

[Specifica la licenza del progetto]

---

**Sviluppato per la gestione completa di ordini PrestaShop con integrazione ShippyPro e Trillium RAG.**

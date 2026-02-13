# 🔍 Documentazione Ricerca Ordini - Trillium RAG

## Panoramica

Il sistema Trillium RAG include **due tipi di ricerca ordini** separati per garantire sicurezza e funzionalità:

1. **💬 Chat RAG** - Ricerca interna per operatori/amministratori
2. **🔍 Ricerca Cliente** - Ricerca esterna per clienti con verifica dati

---

## 1. 💬 Chat RAG (Ricerca Interna)

### Scopo
Ricerca interna per operatori e amministratori che hanno accesso completo al sistema.

### Funzionalità
- **Ricerca vettoriale semantica**: Cerca ordini usando linguaggio naturale
- **Ricerca per ID ordine**: Es. "ordine #53515", "53515"
- **Ricerca per riferimento**: Es. "VZEKDZDHM"
- **Ricerca per nome cliente**: Es. "ordine di Michele Bassi", "ordini per Michele Bassi"
- **Fallback API**: Se non trova nei documenti indicizzati, cerca direttamente tramite API PrestaShop/ShippyPro

### Come Funziona

#### 1.1 Ricerca Vettoriale
- Usa embeddings per trovare ordini semanticamente simili alla query
- Cerca nei documenti indicizzati nel database Qdrant/ChromaDB
- Restituisce i documenti più rilevanti

#### 1.2 Ricerca per Matching Esatto
- Rileva automaticamente ID ordini (pattern: `#?(\d{4,})`)
- Rileva riferimenti alfanumerici (pattern: `([A-Z0-9]{8,})`)
- Rileva nomi clienti (pattern: `([A-Z][a-z]+\s+[A-Z][a-z]+)`)
- Cerca nei metadati e nel testo dei documenti

#### 1.3 Ricerca per Nome Cliente
- Rileva automaticamente nomi clienti nella query
- Cerca prima nei documenti indicizzati
- Se non trova, cerca tramite API PrestaShop:
  1. Cerca il cliente per nome e cognome
  2. Recupera gli ordini associati al cliente
  3. Include l'ordine nel contesto per la risposta

#### 1.4 Fallback API
- Se non trova nei documenti indicizzati, cerca direttamente tramite API
- Supporta ricerca per:
  - ID ordine PrestaShop
  - Riferimento ordine PrestaShop
  - TransactionID ShippyPro
  - Nome cliente (con ricerca cliente + ordini)

### Esempi di Query
```
"cercami ordine #53515"
"VZEKDZDHM"
"ordine di Michele Bassi"
"dammi informazioni sull'ordine intestato a Michele Bassi"
"cerca ordini per Michele Bassi"
```

### File Coinvolti
- `trillium/rag/query.py` - Logica di ricerca e query RAG
- `trillium/rag/api_integration.py` - Integrazione API PrestaShop/ShippyPro
- `trillium/streamlit_app.py` - Interfaccia Chat RAG

---

## 2. 🔍 Ricerca Cliente (Ricerca Esterna)

### Scopo
Ricerca sicura per clienti esterni che vogliono consultare i dettagli del proprio ordine.

### Requisiti di Sicurezza
- **Verifica obbligatoria**: Richiede numero ordine, nome, cognome e CAP
- **Verifica completa**: Tutti i dati devono corrispondere all'ordine
- **Nessuna esposizione dati**: I dati aggiuntivi vengono recuperati SOLO dopo verifica positiva

### Dati Richiesti
1. **🔢 Numero Ordine** (obbligatorio)
2. **📝 Riferimento Ordine** (opzionale, per verifica aggiuntiva)
3. **👤 Nome** (obbligatorio)
4. **👤 Cognome** (obbligatorio)
5. **📮 CAP** (obbligatorio)
6. **📧 Email** (opzionale, per verifica aggiuntiva)

### Flusso di Verifica

#### Fase 1: Recupero Ordine
1. Recupera l'ordine tramite ID ordine dall'API PrestaShop
2. Estrae i dati già presenti nell'ordine:
   - Dati cliente (se presenti in `customer` object)
   - Indirizzo di consegna (se presente in `delivery_address`)

#### Fase 2: Verifica Dati (Sicurezza)
1. **Verifica iniziale**: Usa SOLO i dati già presenti nell'ordine
2. **Recupero condizionale**: Se mancano dati:
   - Se manca il CAP: recupera indirizzo e verifica che il CAP corrisponda PRIMA di usarlo
   - Se mancano nome/cognome: recupera cliente SOLO se il CAP corrisponde già
   - Verifica che nome/cognome corrispondano PRIMA di usarli
3. **Verifica completa**: Controlla che:
   - Nome corrisponda
   - Cognome corrisponda
   - CAP corrisponda
   - Riferimento corrisponda (se fornito)
   - Email corrisponda (se fornita)

#### Fase 3: Visualizzazione (Solo se Verifica OK)
- **Solo dopo verifica positiva**: Recupera dati aggiuntivi per visualizzazione completa
- Mostra dettagli ordine:
  - Informazioni ordine (ID, riferimento, data, totale, pagamento, stato)
  - Informazioni cliente (nome, email)
  - Indirizzo spedizione completo
  - Prodotti ordinati
  - Informazioni spedizione (se disponibile)

### Logica di Sicurezza

```python
# 1. Verifica con dati presenti nell'ordine
order_firstname = order.get('customer', {}).get('firstname', '')
order_postal_code = order.get('delivery_address', {}).get('postcode', '')

# 2. Se mancano dati, recupera SOLO per verificare (non esporre)
if not order_postal_code:
    # Recupera indirizzo e verifica CAP PRIMA di usarlo
    if retrieved_postcode == input_postal_code:
        order_postal_code = retrieved_postcode

# 3. Se mancano nome/cognome, recupera SOLO se CAP corrisponde
if order_postal_code == input_postal_code:
    # Recupera cliente e verifica nome/cognome PRIMA di usarli
    if retrieved_firstname == input_firstname:
        order_firstname = retrieved_firstname

# 4. Verifica completa
if name_match and postal_match and reference_match:
    # ✅ Solo ora recupera dati completi per visualizzazione
```

### Esempio di Utilizzo

**Input:**
```
Numero Ordine: 53515
Riferimento: VZEKDZDHM
Nome: Michele
Cognome: Bassi
CAP: 50032
Email: mik.bassi@gmail.com (opzionale)
```

**Output (se verifica OK):**
- Dettagli completi ordine
- Informazioni cliente
- Indirizzo spedizione
- Prodotti ordinati
- Informazioni spedizione

**Output (se verifica fallisce):**
- Messaggio di errore
- Dettagli su cosa non corrisponde (per debug)

### File Coinvolti
- `trillium/streamlit_app.py` - Sezione "🔍 Ricerca Cliente"
- `prestashop_client.py` - Client API PrestaShop
- `config.py` - Configurazione BASE_URL e API_KEY

---

## 3. Differenze Chiave

| Caratteristica | Chat RAG (Interna) | Ricerca Cliente (Esterna) |
|---------------|---------------------|---------------------------|
| **Accesso** | Operatori/Admin | Clienti esterni |
| **Sicurezza** | Accesso completo | Verifica dati obbligatoria |
| **Ricerca** | Vettoriale + API | Solo API con verifica |
| **Dati Richiesti** | Query testuale | Numero ordine + Nome + Cognome + CAP |
| **Fallback** | Sì (API se non trova) | No (solo verifica) |
| **Esposizione Dati** | Completa | Solo dopo verifica positiva |

---

## 4. Configurazione

### Variabili d'Ambiente
```bash
# PrestaShop API
PRESTSHOP_BASE_URL=https://www.adesivisicurezza.it
PRESTSHOP_API_KEY=KWYH69WBFHYCC24RZZNN5ANQXG36H1Q6

# O nel file config.py
BASE_URL = "https://www.adesivisicurezza.it"
API_KEY = "KWYH69WBFHYCC24RZZNN5ANQXG36H1Q6"
```

### Dipendenze
- `prestashop_client.py` - Client per API PrestaShop
- `streamlit` - Interfaccia web
- `pandas` - Visualizzazione dati (opzionale)

---

## 5. Miglioramenti Implementati

### 5.1 Ricerca per Nome Cliente
- ✅ Rilevamento automatico nomi clienti nella query
- ✅ Ricerca nei documenti indicizzati
- ✅ Fallback tramite API PrestaShop
- ✅ Recupero ordini associati al cliente

### 5.2 Formattazione Ordini
- ✅ Nome cliente incluso nel testo indicizzato
- ✅ Recupero nome cliente da API se non presente nell'ordine
- ✅ Campi multipli per ricerca: "Nome Cliente", "Cognome Cliente", "Nome Completo Cliente"

### 5.3 Sicurezza Ricerca Cliente
- ✅ Verifica obbligatoria di tutti i dati
- ✅ Recupero dati aggiuntivi solo dopo verifica positiva
- ✅ Nessuna esposizione dati prima della verifica
- ✅ Verifica condizionale (recupera solo se necessario e solo dopo verifica parziale)

---

## 6. Troubleshooting

### Problema: Ordine non trovato nella Chat RAG
**Soluzione:**
- Verifica che l'ordine sia stato indicizzato nel database
- Controlla che il nome cliente sia presente nel testo indicizzato
- Usa ricerca per ID o riferimento se la ricerca vettoriale non funziona

### Problema: Verifica fallisce nella Ricerca Cliente
**Soluzione:**
- Verifica che tutti i dati corrispondano esattamente:
  - Nome e cognome (case-insensitive)
  - CAP (deve corrispondere esattamente)
  - Riferimento (se fornito, deve corrispondere)
- Controlla i dettagli verifica nell'expander per vedere cosa non corrisponde

### Problema: Dati cliente non presenti nell'ordine
**Soluzione:**
- Il sistema recupera automaticamente i dati tramite API se non presenti
- Verifica che l'API PrestaShop sia accessibile
- Controlla che l'ID cliente e ID indirizzo siano validi

---

## 7. Note Importanti

1. **Sicurezza**: La ricerca cliente NON espone dati prima della verifica completa
2. **Performance**: La ricerca vettoriale è più veloce ma meno precisa per ID esatti
3. **Fallback**: La Chat RAG ha fallback API, la Ricerca Cliente no (solo verifica)
4. **Indicizzazione**: Gli ordini devono essere indicizzati per essere trovati nella Chat RAG
5. **Dati Cliente**: Se gli ordini sono stati indicizzati prima delle modifiche, potrebbero non avere il nome cliente - re-indicizzarli per includere i nomi

---

## 8. Esempi di Test

### Test Chat RAG
```
Query: "cercami ordine #53515"
Query: "VZEKDZDHM"
Query: "ordine di Michele Bassi"
Query: "dammi informazioni sull'ordine intestato a Michele Bassi"
```

### Test Ricerca Cliente
```
Numero Ordine: 53515
Riferimento: VZEKDZDHM
Nome: Michele
Cognome: Bassi
CAP: 50032
Email: mik.bassi@gmail.com
```

---

## 9. File di Riferimento

- `trillium/streamlit_app.py` - Interfaccia principale (Chat RAG + Ricerca Cliente)
- `trillium/rag/query.py` - Logica ricerca RAG e matching esatto
- `trillium/rag/api_integration.py` - Formattazione ordini e integrazione API
- `trillium/rag/indexer.py` - Indicizzazione documenti
- `prestashop_client.py` - Client API PrestaShop
- `config.py` - Configurazione API

---

**Ultima modifica**: 2025-01-XX
**Versione**: 1.0


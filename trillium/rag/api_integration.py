"""
Integrazione API Presta22Shop e ShippyPro per il sistema RAGé
Recupera ordini e altre informazioni e le converte in formato indicizzabile
"""

import sys
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json

# Aggiungi il percorso root al path per importare i client
# Il file è in: trillium/rag/api_integration.py
# I client sono in: / (root del progetto)
current_file = os.path.abspath(__file__)
# Da trillium/rag/api_integration.py -> root del progetto
# trillium/rag/ -> trillium/ -> root
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))

# Aggiungi il percorso root al path se non è già presente
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Importa i client e la config dalla root del progetto
try:
    # Prova prima con il percorso root già aggiunto
    from prestashop_client import PrestaShopClient
    from shippypro_client import ShippyProClient
    # Importa config dalla root (non da trillium/config.py)
    import importlib.util
    config_path = os.path.join(project_root, 'config.py')
    if os.path.exists(config_path):
        spec = importlib.util.spec_from_file_location("root_config", config_path)
        root_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(root_config)
        BASE_URL = root_config.BASE_URL
        API_KEY = root_config.API_KEY
        SHIPPYPRO_API_KEY = root_config.SHIPPYPRO_API_KEY
    else:
        # Fallback: prova import normale (potrebbe prendere quello sbagliato)
        from config import BASE_URL, API_KEY, SHIPPYPRO_API_KEY
except ImportError as e:
    # Se i moduli non sono trovati, prova percorsi alternativi
    current_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        project_root,  # Root calcolato
        os.path.join(current_dir, '..', '..', '..'),  # trillium/rag/../../
        os.path.dirname(os.path.dirname(os.path.dirname(current_dir))),  # Root assoluto alternativo
    ]
    
    # Rimuovi duplicati e aggiungi tutti i percorsi
    for path in possible_paths:
        abs_path = os.path.abspath(path)
        if abs_path not in sys.path and os.path.exists(abs_path):
            sys.path.insert(0, abs_path)
    
    try:
        from prestashop_client import PrestaShopClient
        from shippypro_client import ShippyProClient
        # Importa config dalla root usando importlib
        config_path = os.path.join(project_root, 'config.py')
        if os.path.exists(config_path):
            import importlib.util
            spec = importlib.util.spec_from_file_location("root_config", config_path)
            root_config = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(root_config)
            BASE_URL = root_config.BASE_URL
            API_KEY = root_config.API_KEY
            SHIPPYPRO_API_KEY = root_config.SHIPPYPRO_API_KEY
        else:
            raise ImportError(f"File config.py non trovato in {project_root}")
    except ImportError as import_error:
        error_msg = f"Errore importazione client API: {import_error}"
        print(f"[red]{error_msg}[/red]")
        print(f"[yellow]Percorso file corrente: {current_file}[/yellow]")
        print(f"[yellow]Root progetto calcolato: {project_root}[/yellow]")
        print(f"[yellow]Config path cercato: {os.path.join(project_root, 'config.py')}[/yellow]")
        print(f"[yellow]Percorsi nel sys.path: {[p for p in sys.path if 'trillium' in p]}[/yellow]")
        raise ImportError(f"{error_msg}\nVerifica che i file prestashop_client.py, shippypro_client.py e config.py siano nella root del progetto.")

from rich import print


# ============================================================
# COSTANTI E UTILITY
# ============================================================

# Periodo di indicizzazione automatica (6 mesi)
INDEXING_MONTHS = 6

# Filtro predefinito per il 2025
DEFAULT_YEAR_START = "2025-01-01"
DEFAULT_YEAR_END = "2025-12-31"

def get_six_months_ago() -> str:
    """Restituisce la data di 6 mesi fa in formato YYYY-MM-DD"""
    six_months_ago = datetime.now() - timedelta(days=INDEXING_MONTHS * 30)
    return six_months_ago.strftime("%Y-%m-%d")

def get_today() -> str:
    """Restituisce la data di oggi in formato YYYY-MM-DD"""
    return datetime.now().strftime("%Y-%m-%d")

def get_default_year_range() -> tuple[str, str]:
    """Restituisce il range predefinito per il 2025"""
    return (DEFAULT_YEAR_START, DEFAULT_YEAR_END)

def is_order_older_than_six_months(order_date: str) -> bool:
    """
    Verifica se un ordine è più vecchio di 6 mesi.
    
    Args:
        order_date: Data dell'ordine (formato variabile)
    
    Returns:
        True se l'ordine è più vecchio di 6 mesi
    """
    try:
        # Prova diversi formati di data
        date_formats = [
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%d/%m/%Y",
            "%d-%m-%Y"
        ]
        
        order_dt = None
        for fmt in date_formats:
            try:
                order_dt = datetime.strptime(order_date.split()[0], fmt)
                break
            except:
                continue
        
        if order_dt is None:
            # Se non riesce a parsare, assume che sia vecchio
            return True
        
        six_months_ago = datetime.now() - timedelta(days=INDEXING_MONTHS * 30)
        return order_dt < six_months_ago
    
    except Exception as e:
        # In caso di errore, assume che sia vecchio per sicurezza
        print(f"[yellow]⚠ Errore verifica data ordine '{order_date}': {e}[/yellow]")
        return True


# ============================================================
# FUNZIONI DI CONVERSIONE DATI IN TESTO
# ============================================================

def format_prestashop_order(order_data: Dict[str, Any]) -> str:
    """
    Converte un ordine PrestaShop in formato testo indicizzabile.
    
    Args:
        order_data: Dati dell'ordine da PrestaShop API
    
    Returns:
        Testo formattato dell'ordine
    """
    try:
        # PrestaShop restituisce i dati in formato XML o JSON
        # Gestiamo entrambi i casi
        if isinstance(order_data, dict):
            order = order_data.get('order', order_data)
        else:
            order = order_data
        
        # Estrai informazioni principali
        order_id = order.get('id', order.get('@attributes', {}).get('id', 'N/A'))
        
        # Informazioni cliente - recupera da più fonti
        customer_id = order.get('id_customer', order.get('customer', {}).get('id', 'N/A'))
        
        # Prova a recuperare nome cliente da customer object
        customer_obj = order.get('customer', {})
        if isinstance(customer_obj, dict):
            customer_firstname = customer_obj.get('firstname', '')
            customer_lastname = customer_obj.get('lastname', '')
            customer_name = f"{customer_firstname} {customer_lastname}".strip()
            customer_email = customer_obj.get('email', 'N/A')
        else:
            # Se customer non è un dict, prova a recuperare da indirizzo di consegna
            delivery_address = order.get('delivery_address', {})
            if isinstance(delivery_address, dict):
                customer_firstname = delivery_address.get('firstname', '')
                customer_lastname = delivery_address.get('lastname', '')
                customer_name = f"{customer_firstname} {customer_lastname}".strip()
                customer_email = delivery_address.get('email', 'N/A')
            else:
                customer_name = ""
                customer_email = 'N/A'
        
        # Se ancora non abbiamo il nome, prova a recuperarlo dall'API se abbiamo l'ID cliente
        if not customer_name or customer_name.strip() == "":
            if customer_id and str(customer_id) != 'N/A':
                try:
                    from prestashop_client import PrestaShopClient
                    from config import BASE_URL, API_KEY
                    client = PrestaShopClient(BASE_URL, API_KEY)
                    customer_detail = client.get_customer(int(customer_id))
                    if 'customer' in customer_detail:
                        cust = customer_detail['customer']
                        customer_firstname = cust.get('firstname', '')
                        customer_lastname = cust.get('lastname', '')
                        customer_name = f"{customer_firstname} {customer_lastname}".strip()
                        customer_email = cust.get('email', 'N/A')
                except:
                    pass  # Se fallisce, continua senza nome
        
        # Informazioni ordine
        order_date = order.get('date_add', order.get('date', 'N/A'))
        total_paid = order.get('total_paid', order.get('total', '0'))
        currency = order.get('currency', {}).get('iso_code', 'EUR') if isinstance(order.get('currency'), dict) else 'EUR'
        payment = order.get('payment', 'N/A')
        order_status = order.get('current_state', order.get('status', 'N/A'))
        
        # Indirizzo di spedizione
        delivery_address = order.get('delivery_address', {})
        delivery_name = delivery_address.get('firstname', '') + ' ' + delivery_address.get('lastname', '') if isinstance(delivery_address, dict) else 'N/A'
        delivery_address_text = ''
        if isinstance(delivery_address, dict):
            delivery_address_text = f"{delivery_address.get('address1', '')}, {delivery_address.get('city', '')}, {delivery_address.get('postcode', '')}, {delivery_address.get('country', '')}"
        
        # Prodotti - gestisci correttamente le associations
        products_text = ''
        associations = order.get('associations', {})
        if isinstance(associations, dict):
            # PrestaShop può restituire order_rows come array diretto o come oggetto con order_row
            order_rows = associations.get('order_rows', [])
            
            # Se è un dict, potrebbe contenere 'order_row' come chiave
            if isinstance(order_rows, dict):
                if 'order_row' in order_rows:
                    order_rows = order_rows['order_row']
                else:
                    # Potrebbe essere già un array
                    order_rows = list(order_rows.values()) if order_rows else []
            
            if not isinstance(order_rows, list):
                order_rows = [order_rows] if order_rows else []
            
            products_list = []
            for row in order_rows:
                if isinstance(row, dict):
                    product_id = row.get('product_id', 'N/A')
                    product_name = row.get('product_name', 'N/A')
                    product_reference = row.get('product_reference', 'N/A')
                    product_quantity = row.get('product_quantity', '0')
                    product_price = row.get('product_price', '0')
                    unit_price_tax_excl = row.get('unit_price_tax_excl', '0')
                    unit_price_tax_incl = row.get('unit_price_tax_incl', '0')
                    product_ean13 = row.get('product_ean13', 'N/A')
                    product_attribute_id = row.get('product_attribute_id', 'N/A')
                    products_list.append(f"- ID Prodotto: {product_id}, Ref: {product_reference}, Nome: {product_name}, Qty: {product_quantity}, Prezzo: {product_price}, Prezzo (senza IVA): {unit_price_tax_excl}, Prezzo (con IVA): {unit_price_tax_incl}, EAN13: {product_ean13}, Attributo ID: {product_attribute_id}")
            
            if products_list:
                products_text = '\n'.join(products_list)
        
        # Costruisci testo formattato con informazioni principali + TUTTI i campi
        # Includi TUTTO l'oggetto order_data originale, non solo order
        full_order_data = order_data if isinstance(order_data, dict) else order
        
        # Estrai TUTTI i campi dell'ordine per renderli ricercabili
        all_fields_text = f"""
CAMPI ORDINE COMPLETI:
ID Ordine: {order.get('id', 'N/A')}
Riferimento: {order.get('reference', 'N/A')}
ID Cliente: {order.get('id_customer', 'N/A')}
ID Indirizzo Consegna: {order.get('id_address_delivery', 'N/A')}
ID Indirizzo Fattura: {order.get('id_address_invoice', 'N/A')}
ID Carrello: {order.get('id_cart', 'N/A')}
ID Corriere: {order.get('id_carrier', 'N/A')}
ID Valuta: {order.get('id_currency', 'N/A')}
ID Lingua: {order.get('id_lang', 'N/A')}
ID Negozio: {order.get('id_shop', 'N/A')}
ID Gruppo Negozio: {order.get('id_shop_group', 'N/A')}
Stato Corrente: {order.get('current_state', 'N/A')}
Data Aggiunta: {order.get('date_add', 'N/A')}
Data Aggiornamento: {order.get('date_upd', 'N/A')}
Data Consegna: {order.get('delivery_date', 'N/A')}
Numero Consegna: {order.get('delivery_number', 'N/A')}
Data Fattura: {order.get('invoice_date', 'N/A')}
Numero Fattura: {order.get('invoice_number', 'N/A')}
Metodo Pagamento: {order.get('payment', 'N/A')}
Modulo Pagamento: {order.get('module', 'N/A')}
Totale Pagato: {order.get('total_paid', 'N/A')}
Totale Pagato Reale: {order.get('total_paid_real', 'N/A')}
Totale Pagato (senza IVA): {order.get('total_paid_tax_excl', 'N/A')}
Totale Pagato (con IVA): {order.get('total_paid_tax_incl', 'N/A')}
Totale Prodotti: {order.get('total_products', 'N/A')}
Totale Prodotti (con IVA): {order.get('total_products_wt', 'N/A')}
Totale Spedizione: {order.get('total_shipping', 'N/A')}
Totale Spedizione (senza IVA): {order.get('total_shipping_tax_excl', 'N/A')}
Totale Spedizione (con IVA): {order.get('total_shipping_tax_incl', 'N/A')}
Totale Sconti: {order.get('total_discounts', 'N/A')}
Totale Sconti (senza IVA): {order.get('total_discounts_tax_excl', 'N/A')}
Totale Sconti (con IVA): {order.get('total_discounts_tax_incl', 'N/A')}
Totale Imballaggio: {order.get('total_wrapping', 'N/A')}
Totale Imballaggio (senza IVA): {order.get('total_wrapping_tax_excl', 'N/A')}
Totale Imballaggio (con IVA): {order.get('total_wrapping_tax_incl', 'N/A')}
Tasso IVA Corriere: {order.get('carrier_tax_rate', 'N/A')}
Tasso Conversione: {order.get('conversion_rate', 'N/A')}
Numero Spedizione: {order.get('shipping_number', 'N/A')}
Chiave Sicura: {order.get('secure_key', 'N/A')}
Regalo: {order.get('gift', 'N/A')}
Messaggio Regalo: {order.get('gift_message', 'N/A')}
Riciclabile: {order.get('recyclable', 'N/A')}
Valido: {order.get('valid', 'N/A')}
Modalità Arrotondamento: {order.get('round_mode', 'N/A')}
Tipo Arrotondamento: {order.get('round_type', 'N/A')}
Tema Mobile: {order.get('mobile_theme', 'N/A')}
Note: {order.get('note', 'Nessuna nota')}

PRODOTTI ORDINATI (ASSOCIATIONS):
{json.dumps(associations, indent=2, default=str, ensure_ascii=False) if associations else 'Nessun prodotto'}
"""
        
        # Assicurati che il nome cliente sia presente e ben formattato
        customer_name_display = customer_name.strip() if customer_name and customer_name.strip() else "N/A"
        if customer_name_display == "N/A":
            # Prova a recuperare da altre fonti
            if isinstance(order.get('customer'), dict):
                customer_name_display = f"{order.get('customer', {}).get('firstname', '')} {order.get('customer', {}).get('lastname', '')}".strip()
        
        text = f"""
ORDINE PRESTSHOP - ID: {order_id}
Riferimento: {order.get('reference', 'N/A')}
Data ordine: {order_date}
Cliente: {customer_name_display} (ID: {customer_id}, Email: {customer_email})
Nome Cliente: {customer_name_display}
Cognome Cliente: {order.get('customer', {}).get('lastname', 'N/A') if isinstance(order.get('customer'), dict) else 'N/A'}
Nome Completo Cliente: {customer_name_display}
Totale pagato: {total_paid} {currency}
Metodo di pagamento: {payment}
Stato ordine: {order_status}

INDIRIZZO DI SPEDIZIONE:
{delivery_name}
{delivery_address_text}

PRODOTTI ORDINATI (RIEPILOGO):
{products_text if products_text else 'Nessun prodotto trovato'}

{all_fields_text}

PRODOTTI ORDINATI - ASSOCIATIONS COMPLETE (JSON):
{json.dumps(associations, indent=2, default=str, ensure_ascii=False) if associations else 'Nessun prodotto'}

---
DATI COMPLETI ORDINE - PAYLOAD COMPLETO (JSON):
{json.dumps(full_order_data, indent=2, default=str, ensure_ascii=False)}
"""
        return text.strip()
    
    except Exception as e:
        print(f"[red]Errore formattazione ordine PrestaShop: {e}[/red]")
        # Fallback: restituisci JSON formattato completo
        return f"ORDINE PRESTSHOP:\n{json.dumps(order_data, indent=2, default=str, ensure_ascii=False)}"


def format_shippypro_order(order_data: Dict[str, Any]) -> str:
    """
    Converte un ordine/spedizione ShippyPro in formato testo indicizzabile.
    
    Args:
        order_data: Dati dell'ordine da ShippyPro API
    
    Returns:
        Testo formattato dell'ordine
    """
    try:
        # ShippyPro restituisce dati in formato diverso
        # Gestiamo il formato standard di GetOrder
        if 'Result' in order_data and order_data['Result'] != 'OK':
            return f"ERRORE SHIPPYPRO: {order_data.get('Error', 'Errore sconosciuto')}"
        
        order = order_data.get('Order', order_data)
        
        # Informazioni ordine
        order_id = order.get('OrderID', 'N/A')
        transaction_id = order.get('TransactionID', order.get('ShippingNumber', 'N/A'))
        tracking_number = order.get('TrackingNumber', 'N/A')
        carrier_name = order.get('CarrierName', 'N/A')
        service_name = order.get('ServiceName', 'N/A')
        
        # Informazioni cliente
        customer_name = order.get('CustomerName', 'N/A')
        customer_email = order.get('CustomerEmail', 'N/A')
        customer_phone = order.get('CustomerPhone', 'N/A')
        
        # Indirizzo
        address = order.get('Address', {})
        if isinstance(address, dict):
            address_text = f"{address.get('Address1', '')}, {address.get('City', '')}, {address.get('Zip', '')}, {address.get('Country', '')}"
        else:
            address_text = str(address)
        
        # Stato spedizione
        status = order.get('Status', 'N/A')
        date_shipped = order.get('DateShipped', 'N/A')
        date_delivered = order.get('DateDelivered', 'N/A')
        
        # Peso e dimensioni
        weight = order.get('Weight', 'N/A')
        dimensions = order.get('Dimensions', 'N/A')
        
        # Costi
        shipping_cost = order.get('ShippingCost', 'N/A')
        currency = order.get('Currency', 'EUR')
        
        # Costruisci testo formattato con informazioni principali + TUTTO il payload
        # Includi TUTTO l'oggetto order_data originale
        full_order_data = order_data
        
        text = f"""
ORDINE SHIPPYPRO - OrderID: {order_id}
Transaction ID: {transaction_id}
Tracking Number: {tracking_number}
Corriere: {carrier_name}
Servizio: {service_name}
Stato: {status}
Data spedizione: {date_shipped}
Data consegna: {date_delivered}

CLIENTE:
Nome: {customer_name}
Email: {customer_email}
Telefono: {customer_phone}

INDIRIZZO:
{address_text}

DETTAGLI SPEDIZIONE:
Peso: {weight}
Dimensioni: {dimensions}
Costo spedizione: {shipping_cost} {currency}

---
DATI COMPLETI ORDINE - PAYLOAD COMPLETO (JSON):
{json.dumps(full_order_data, indent=2, default=str, ensure_ascii=False)}
"""
        return text.strip()
    
    except Exception as e:
        print(f"[red]Errore formattazione ordine ShippyPro: {e}[/red]")
        # Fallback: restituisci JSON formattato completo
        return f"ORDINE SHIPPYPRO:\n{json.dumps(order_data, indent=2, default=str, ensure_ascii=False)}"


# ============================================================
# FUNZIONI DI RECUPERO DATI
# ============================================================

def get_prestashop_orders(date_from: Optional[str] = None, date_to: Optional[str] = None, 
                          progress_callback=None) -> List[Dict[str, Any]]:
    """
    Recupera ordini da PrestaShop.
    Recupera TUTTI gli ordini nel range di date specificato (senza limiti numerici).
    Usa recupero per ID range invece di paginazione (che non funziona correttamente).
    
    Args:
        date_from: Data inizio (formato YYYY-MM-DD)
        date_to: Data fine (formato YYYY-MM-DD)
        progress_callback: Callback opzionale (source, order_id, order_date, progress, total) chiamato durante il recupero
    
    Returns:
        Lista di ordini
    """
    try:
        client = PrestaShopClient(BASE_URL, API_KEY)
        
        all_orders = []
        seen_order_ids = set()  # Per rilevare duplicati
        MAX_ORDER_ID = 53600  # Limite massimo conosciuto (53561 + margine)
        BATCH_SIZE = 200  # Aumentato a 200 per essere più veloce
        
        print(f"[cyan]🔄 Recupero ordini PrestaShop per ID range...[/cyan]")
        if date_from or date_to:
            print(f"[cyan]   Filtro date: da {date_from or 'inizio'} a {date_to or 'oggi'}[/cyan]")
        
        # Strategia ottimizzata: se il filtro è per il 2025, inizia da un ID più alto
        # Gli ordini più recenti hanno ID più alti
        current_id = 1
        if date_from and date_from.startswith("2025"):
            # Se cerchiamo ordini del 2025, inizia da ID 50000 (circa)
            # Gli ordini del 2025 dovrebbero avere ID alti
            current_id = 50000
            print(f"[cyan]   ⚡ Ottimizzazione: Inizio da ID {current_id} per ordini del 2025[/cyan]")
        elif date_from and len(date_from) >= 4:
            # Estrai l'anno dalla data
            try:
                year = int(date_from[:4])
                if year >= 2024:
                    # Per anni recenti, inizia da ID più alto
                    start_id = 45000 + ((year - 2024) * 5000)
                    current_id = min(start_id, MAX_ORDER_ID - 1000)
                    print(f"[cyan]   ⚡ Ottimizzazione: Inizio da ID {current_id} per anno {year}[/cyan]")
            except:
                pass
        
        # Strategia: recupera ordini per range di ID invece di paginazione
        # PrestaShop ordina per ID, quindi possiamo iterare per ID
        consecutive_errors = 0
        max_consecutive_errors = 20  # Aumentato a 20 per saltare range vuoti più velocemente
        skip_range_size = 1000  # Salta 1000 ID alla volta quando troviamo molti errori
        
        while current_id <= MAX_ORDER_ID:
            batch_orders = []
            batch_start = current_id
            batch_end = min(current_id + BATCH_SIZE - 1, MAX_ORDER_ID)
            
            progress_pct = int((current_id / MAX_ORDER_ID) * 100) if MAX_ORDER_ID > 0 else 0
            print(f"[cyan]   📦 Batch ID {batch_start}-{batch_end}... Progresso: {progress_pct}% - Ordini trovati finora: {len(all_orders)}[/cyan]")
            
            # Recupera ordini in questo range
            for order_id in range(batch_start, batch_end + 1):
                try:
                    order_detail = client.get_order(order_id)
                    if 'order' in order_detail:
                        order = order_detail['order']
                        order_id_val = order.get('id')
                        
                        # Verifica duplicati
                        if order_id_val and str(order_id_val) not in seen_order_ids:
                            seen_order_ids.add(str(order_id_val))
                            
                            # Applica filtro data se specificato
                            order_date = order.get('date_add', '')
                            if date_from or date_to:
                                if order_date:
                                    # Formato: "2025-12-15 21:29:56"
                                    order_date_only = order_date.split(' ')[0] if ' ' in order_date else order_date
                                    if date_from and order_date_only < date_from:
                                        continue
                                    if date_to and order_date_only > date_to:
                                        continue
                            
                            batch_orders.append(order)
                            consecutive_errors = 0
                            
                            # Chiama callback di progresso se fornito (durante il recupero)
                            if progress_callback:
                                # Calcola progresso approssimativo basato su ID corrente
                                estimated_progress = (order_id / MAX_ORDER_ID) if MAX_ORDER_ID > 0 else 0
                                progress_callback("PrestaShop", order_id_val, order_date, estimated_progress, MAX_ORDER_ID)
                                # Stampa anche direttamente nella console per visibilità - con più dettagli
                                progress_pct = int(estimated_progress * 100)
                                print(f"[RECUPERO] PrestaShop - Ordine #{order_id_val} ({order_date[:10] if order_date else 'N/A'}) - ID range: {order_id}/{MAX_ORDER_ID} ({progress_pct}%) - Totale trovati: {len(all_orders)}")
                    else:
                        consecutive_errors += 1
                except Exception as e:
                    consecutive_errors += 1
                    # Se l'ordine non esiste (404), è normale, continua
                    if '404' not in str(e) and 'not found' not in str(e).lower():
                        # Solo logga errori non-404
                        if consecutive_errors <= 3:  # Logga solo i primi 3 errori
                            print(f"[yellow]⚠ Errore recupero ordine {order_id}: {e}[/yellow]")
                    continue
            
            if batch_orders:
                all_orders.extend(batch_orders)
                print(f"[cyan]   ✓ Recuperati {len(batch_orders)} ordini nel batch (totale: {len(all_orders)})[/cyan]")
            
            # Se abbiamo avuto troppi errori consecutivi, salta un range più grande
            if consecutive_errors >= max_consecutive_errors:
                # Se stiamo cercando ordini del 2025 e siamo ancora a ID bassi, continua
                if date_from and date_from.startswith("2025") and current_id < 50000:
                    print(f"[cyan]   ⏩ Saltando range vuoto, continuo verso ID più alti...[/cyan]")
                    current_id = 50000  # Salta direttamente a ID 50000
                    consecutive_errors = 0
                else:
                    print(f"[cyan]   ✓ Raggiunto limite errori consecutivi ({max_consecutive_errors}), fine recupero[/cyan]")
                    break
            else:
                # Se abbiamo trovato ordini, resetta il contatore
                if batch_orders:
                    consecutive_errors = 0
                # Se abbiamo molti errori ma non abbastanza per fermarci, salta un po'
                elif consecutive_errors >= 5:
                    # Salta 100 ID alla volta quando troviamo alcuni errori
                    current_id = batch_end + 100
                    continue
            
            current_id = batch_end + 1
            
            # Limite di sicurezza assoluto
            if len(all_orders) > MAX_ORDER_ID:
                print(f"[yellow]⚠ Raggiunto limite massimo ordini ({MAX_ORDER_ID}), interrompo[/yellow]")
                break
        
        print(f"[green]✓ Recuperati {len(all_orders)} ordini completi da PrestaShop[/green]")
        if len(all_orders) > 0:
            # Ordina per ID per avere un ordine logico
            all_orders.sort(key=lambda x: int(x.get('id', 0)) if isinstance(x, dict) and x.get('id') else 0)
            
            first_id = all_orders[0].get('id', 'N/A') if isinstance(all_orders[0], dict) else 'N/A'
            last_id = all_orders[-1].get('id', 'N/A') if isinstance(all_orders[-1], dict) else 'N/A'
            print(f"[cyan]   Primo ordine ID: {first_id}[/cyan]")
            print(f"[cyan]   Ultimo ordine ID: {last_id}[/cyan]")
            print(f"[cyan]   Ordini unici: {len(seen_order_ids)}[/cyan]")
            
            # Verifica se l'ordine 53515 è presente
            order_53515_found = any(
                (isinstance(o, dict) and str(o.get('id', '')) == '53515')
                for o in all_orders
            )
            if order_53515_found:
                print(f"[green]✓ Ordine 53515 trovato nella lista![/green]")
            else:
                print(f"[yellow]⚠ Ordine 53515 NON trovato nella lista recuperata[/yellow]")
        
        return all_orders
    
    except Exception as e:
        print(f"[red]Errore recupero ordini PrestaShop: {e}[/red]")
        import traceback
        traceback.print_exc()
        return []


def get_prestashop_order_by_id(order_id: int) -> Optional[Dict[str, Any]]:
    """
    Recupera un singolo ordine PrestaShop per ID.
    Se non trovato, cerca su ShippyPro come fallback.
    
    Args:
        order_id: ID dell'ordine
    
    Returns:
        Dati dell'ordine o None
    """
    try:
        client = PrestaShopClient(BASE_URL, API_KEY)
        order = client.get_order(order_id)
        
        # Verifica se l'ordine è stato trovato
        if order and (isinstance(order, dict) and order.get('order') or order):
            return order
        else:
            # Ordine non trovato su PrestaShop, cerca su ShippyPro
            print(f"[yellow]⚠ Ordine {order_id} non trovato su PrestaShop, cerco su ShippyPro...[/yellow]")
            return get_shippypro_order_by_id_or_transaction(str(order_id))
    
    except Exception as e:
        error_msg = str(e).lower()
        # Se l'ordine non esiste (404 o simile), cerca su ShippyPro
        if "404" in error_msg or "not found" in error_msg or "non trovato" in error_msg:
            print(f"[yellow]⚠ Ordine {order_id} non trovato su PrestaShop, cerco su ShippyPro...[/yellow]")
            return get_shippypro_order_by_id_or_transaction(str(order_id))
        else:
            print(f"[red]Errore recupero ordine PrestaShop {order_id}: {e}[/red]")
            return None


def get_shippypro_orders(limit: int = 100, date_from: Optional[str] = None, date_to: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Recupera ordini/spedizioni da ShippyPro.
    
    Args:
        limit: Numero massimo di ordini da recuperare
        date_from: Data inizio (formato YYYY-MM-DD) per filtrare ordini
        date_to: Data fine (formato YYYY-MM-DD) per filtrare ordini
    
    Returns:
        Lista di ordini filtrati per data se specificato
    """
    try:
        client = ShippyProClient(SHIPPYPRO_API_KEY)
        
        # ShippyPro: recupera pending orders
        pending_response = client.make_request('GetPendingOrders', data={})
        
        orders = []
        if pending_response.get('Result') == 'OK' and 'Orders' in pending_response:
            orders_list = pending_response['Orders']
            if isinstance(orders_list, list):
                orders = orders_list[:limit]
            else:
                orders = [orders_list] if orders_list else []
        
        # Per ogni ordine, recupera dettagli completi e applica filtro data
        detailed_orders = []
        for order in orders:
            order_id = order.get('OrderID')
            if order_id:
                try:
                    detailed = client.get_order(order_id)
                    if detailed.get('Result') == 'OK':
                        # Applica filtro data se specificato
                        if date_from or date_to:
                            order_data = detailed.get('Order', detailed)
                            order_date = order_data.get('DateShipped', order_data.get('DateCreated', order_data.get('Date', '')))
                            if order_date:
                                # Formato data ShippyPro può variare, prova a parsare
                                try:
                                    # Prova diversi formati
                                    if ' ' in order_date:
                                        order_date_only = order_date.split(' ')[0]
                                    else:
                                        order_date_only = order_date[:10] if len(order_date) >= 10 else order_date
                                    
                                    if date_from and order_date_only < date_from:
                                        continue
                                    if date_to and order_date_only > date_to:
                                        continue
                                except:
                                    # Se non riesce a parsare, include l'ordine
                                    pass
                        detailed_orders.append(detailed)
                except:
                    # Se fallisce, usa i dati base (solo se passa il filtro data)
                    if not (date_from or date_to):
                        detailed_orders.append(order)
        
        print(f"[green]✓ Recuperati {len(detailed_orders)} ordini da ShippyPro" + (f" (filtrati: {date_from} - {date_to})" if date_from or date_to else "") + "[/green]")
        return detailed_orders if detailed_orders else orders
    
    except Exception as e:
        print(f"[red]Errore recupero ordini ShippyPro: {e}[/red]")
        return []


def get_shippypro_order_by_id(order_id: int) -> Optional[Dict[str, Any]]:
    """
    Recupera un singolo ordine ShippyPro per ID.
    
    Args:
        order_id: ID dell'ordine
    
    Returns:
        Dati dell'ordine o None
    """
    try:
        client = ShippyProClient(SHIPPYPRO_API_KEY)
        order = client.get_order(order_id)
        if order.get('Result') == 'OK':
            return order
        return None
    except Exception as e:
        print(f"[red]Errore recupero ordine ShippyPro {order_id}: {e}[/red]")
        return None


def get_shippypro_order_by_id_or_transaction(identifier: str) -> Optional[Dict[str, Any]]:
    """
    Recupera un ordine ShippyPro per ID o TransactionID.
    Usato come fallback quando un ordine non è trovato su PrestaShop.
    
    Args:
        identifier: ID ordine o TransactionID
    
    Returns:
        Dati dell'ordine o None
    """
    try:
        client = ShippyProClient(SHIPPYPRO_API_KEY)
        
        # Prova prima con OrderID (se è numerico)
        try:
            order_id = int(identifier)
            order = client.get_order(order_id)
            if order.get('Result') == 'OK':
                print(f"[green]✓ Ordine trovato su ShippyPro con OrderID: {order_id}[/green]")
                return order
        except ValueError:
            pass
        
        # Se non funziona, prova con TransactionID
        order = client.get_order_by_transaction_id(identifier)
        if order and order.get('Result') != 'Error':
            print(f"[green]✓ Ordine trovato su ShippyPro con TransactionID: {identifier}[/green]")
            return order
        
        print(f"[yellow]⚠ Ordine {identifier} non trovato né su PrestaShop né su ShippyPro[/yellow]")
        return None
    
    except Exception as e:
        print(f"[red]Errore ricerca ordine ShippyPro {identifier}: {e}[/red]")
        return None


def search_order_with_fallback(order_identifier: str) -> Optional[Dict[str, Any]]:
    """
    Cerca un ordine con fallback automatico PrestaShop -> ShippyPro.
    Usato quando si cerca un ordine specifico nella chat.
    
    Args:
        order_identifier: ID ordine, TransactionID o altro identificatore
    
    Returns:
        Dati dell'ordine trovato o None
    """
    # Prova prima come ID numerico (PrestaShop)
    try:
        order_id = int(order_identifier)
        print(f"[cyan]🔍 Cerco ordine {order_id} su PrestaShop...[/cyan]")
        order = get_prestashop_order_by_id(order_id)
        if order:
            return order
    except ValueError:
        # Non è numerico, potrebbe essere TransactionID
        pass
    
    # Se non trovato su PrestaShop o non è numerico, cerca su ShippyPro
    print(f"[cyan]🔍 Cerco ordine {order_identifier} su ShippyPro...[/cyan]")
    order = get_shippypro_order_by_id_or_transaction(order_identifier)
    return order


# ============================================================
# FUNZIONI DI INDICIZZAZIONE
# ============================================================

def index_prestashop_orders(date_from: Optional[str] = None, date_to: Optional[str] = None, 
                           auto_six_months: bool = False, progress_callback=None) -> Dict[str, Any]:
    """
    Recupera e formatta ordini PrestaShop per l'indicizzazione.
    Se auto_six_months=True, indica automaticamente TUTTI gli ordini degli ultimi 6 mesi (senza limiti numerici).
    
    Args:
        date_from: Data inizio (YYYY-MM-DD) - ignorato se auto_six_months=True
        date_to: Data fine (YYYY-MM-DD) - ignorato se auto_six_months=True
        auto_six_months: Se True, indica automaticamente TUTTI gli ordini degli ultimi 6 mesi
        progress_callback: Funzione callback(opzione, ordine_id, data, progresso, totale) chiamata per ogni ordine
    
    Returns:
        Dict con lista di testi formattati e metadati
    """
    # Se auto_six_months è attivo, usa gli ultimi 6 mesi
    # Altrimenti, se non sono specificate date, usa il 2025 come default
    if auto_six_months:
        date_from = get_six_months_ago()
        date_to = get_today()
        print(f"[cyan]📅 Indicizzazione: TUTTI gli ordini degli ultimi 6 mesi ({date_from} - {date_to})[/cyan]")
    else:
        # Se non sono specificate date, usa il 2025 come default
        if date_from is None and date_to is None:
            date_from, date_to = get_default_year_range()
            print(f"[cyan]📅 Indicizzazione: Ordini del 2025 ({date_from} - {date_to})[/cyan]")
        elif date_from is None or date_to is None:
            # Se solo una data è specificata, usa il 2025 per quella mancante
            if date_from is None:
                date_from = DEFAULT_YEAR_START
            if date_to is None:
                date_to = DEFAULT_YEAR_END
            print(f"[cyan]📅 Indicizzazione: Ordini dal {date_from} al {date_to}[/cyan]")
        else:
            print(f"[cyan]📅 Indicizzazione: Ordini dal {date_from} al {date_to} (filtro personalizzato)[/cyan]")
    
    if date_from and date_to:
        print(f"[cyan]🔍 Recupero ordini PrestaShop dal {date_from} al {date_to}...[/cyan]")
    else:
        print(f"[cyan]🔍 Recupero TUTTI gli ordini PrestaShop disponibili...[/cyan]")
    orders = get_prestashop_orders(date_from=date_from, date_to=date_to, progress_callback=progress_callback)
    print(f"[cyan]📦 Ordini PrestaShop recuperati: {len(orders)} ordini[/cyan]")
    
    formatted_texts = []
    metadatas = []
    ids = []
    old_orders_warnings = []
    last_order_id = None
    order_ids_list = []
    
    for idx, order in enumerate(orders):
        try:
            # Estrai data ordine
            order_date = order.get('date_add', order.get('date', ''))
            
            # Estrai ID ordine
            order_id = order.get('id', order.get('@attributes', {}).get('id', f'unknown_{idx}'))
            
            # Chiama callback di progresso se fornito
            if progress_callback:
                progress = (idx + 1) / len(orders) if len(orders) > 0 else 0
                progress_callback("PrestaShop", order_id, order_date, progress, len(orders))
            
            # NON saltare ordini vecchi - indicizza TUTTI gli ordini
            # (rimosso il controllo dei 6 mesi per indicizzare tutto)
            
            # Formatta ordine
            text = format_prestashop_order(order)
            
            # Crea ID univoco per il documento
            doc_id = f"prestashop_order_{order_id}"
            
            formatted_texts.append(text)
            metadatas.append({
                "source": f"PrestaShop Order {order_id}",
                "type": "prestashop_order",
                "order_id": str(order_id),
                "date": order_date
            })
            ids.append(doc_id)
            
            # Traccia ID ordine per statistiche
            try:
                order_id_int = int(order_id) if str(order_id).isdigit() else None
                if order_id_int:
                    order_ids_list.append(order_id_int)
                    if last_order_id is None or order_id_int > last_order_id:
                        last_order_id = order_id_int
            except:
                pass
        
        except Exception as e:
            print(f"[yellow]⚠ Errore formattazione ordine {idx}: {e}[/yellow]")
            continue
    
    # Ordina gli ID per trovare il più alto
    if order_ids_list:
        order_ids_list.sort()
        last_order_id = order_ids_list[-1]
    
    # Mostra avvisi per ordini vecchi
    if old_orders_warnings:
        print(f"\n[yellow]⚠ ATTENZIONE: {len(old_orders_warnings)} ordini superano i 6 mesi e sono stati saltati:[/yellow]")
        for warning in old_orders_warnings[:5]:  # Mostra max 5
            print(f"[yellow]  - {warning['message']}[/yellow]")
        if len(old_orders_warnings) > 5:
            print(f"[yellow]  ... e altri {len(old_orders_warnings) - 5} ordini[/yellow]")
    
    return {
        "texts": formatted_texts,
        "metadatas": metadatas,
        "ids": ids,
        "count": len(formatted_texts),
        "old_orders_warnings": old_orders_warnings,
        "last_order_id": last_order_id,
        "total_orders_processed": len(orders)
    }


def index_shippypro_orders(auto_six_months: bool = False, date_from: Optional[str] = None, 
                           date_to: Optional[str] = None, progress_callback=None) -> Dict[str, Any]:
    """
    Recupera e formatta ordini ShippyPro per l'indicizzazione.
    Se auto_six_months=True, indica automaticamente TUTTI gli ordini degli ultimi 6 mesi (senza limiti numerici).
    
    Args:
        auto_six_months: Se True, indica automaticamente TUTTI gli ordini degli ultimi 6 mesi
        date_from: Data inizio (YYYY-MM-DD) - ignorato se auto_six_months=True
        date_to: Data fine (YYYY-MM-DD) - ignorato se auto_six_months=True
        progress_callback: Funzione callback(sorgente, ordine_id, data, progresso, totale) chiamata per ogni ordine
    
    Returns:
        Dict con lista di testi formattati e metadati
    """
    # Se auto_six_months è attivo, usa gli ultimi 6 mesi
    # Altrimenti, se non sono specificate date, usa il 2025 come default
    if auto_six_months:
        date_from = get_six_months_ago()
        date_to = get_today()
        print(f"[cyan]📅 Indicizzazione ShippyPro: TUTTI gli ordini degli ultimi 6 mesi ({date_from} - {date_to})[/cyan]")
    else:
        # Se non sono specificate date, usa il 2025 come default
        if date_from is None and date_to is None:
            date_from, date_to = get_default_year_range()
            print(f"[cyan]📅 Indicizzazione ShippyPro: Ordini del 2025 ({date_from} - {date_to})[/cyan]")
        elif date_from is None or date_to is None:
            # Se solo una data è specificata, usa il 2025 per quella mancante
            if date_from is None:
                date_from = DEFAULT_YEAR_START
            if date_to is None:
                date_to = DEFAULT_YEAR_END
            print(f"[cyan]📅 Indicizzazione ShippyPro: Ordini dal {date_from} al {date_to}[/cyan]")
        else:
            print(f"[cyan]📅 Indicizzazione ShippyPro: Ordini dal {date_from} al {date_to} (filtro personalizzato)[/cyan]")
    
    print(f"[cyan]🔍 Recupero ordini ShippyPro...[/cyan]")
    orders = get_shippypro_orders(date_from=date_from, date_to=date_to)
    print(f"[cyan]📦 Ordini ShippyPro recuperati: {len(orders)} ordini[/cyan]")
    
    formatted_texts = []
    metadatas = []
    ids = []
    old_orders_warnings = []
    last_order_id = None
    order_ids_list = []
    
    for idx, order in enumerate(orders):
        try:
            # Estrai dati ordine
            order_data = order.get('Order', order)
            order_id = order_data.get('OrderID', f'unknown_{idx}')
            
            # Estrai data ordine (può essere in diversi campi)
            order_date = order_data.get('DateShipped', order_data.get('DateCreated', order_data.get('Date', '')))
            
            # Chiama callback di progresso se fornito
            if progress_callback:
                progress = (idx + 1) / len(orders) if len(orders) > 0 else 0
                progress_callback("ShippyPro", order_id, order_date, progress, len(orders))
            
            # NON saltare ordini vecchi - indicizza TUTTI gli ordini
            # (rimosso il controllo dei 6 mesi per indicizzare tutto)
            
            # Formatta ordine
            text = format_shippypro_order(order)
            
            transaction_id = order_data.get('TransactionID', order_data.get('ShippingNumber', 'N/A'))
            
            # Crea ID univoco per il documento
            doc_id = f"shippypro_order_{order_id}"
            
            formatted_texts.append(text)
            metadatas.append({
                "source": f"ShippyPro Order {order_id}",
                "type": "shippypro_order",
                "order_id": str(order_id),
                "transaction_id": str(transaction_id),
                "tracking_number": order_data.get('TrackingNumber', 'N/A'),
                "date": order_date
            })
            ids.append(doc_id)
            
            # Traccia ID ordine per statistiche
            try:
                order_id_int = int(order_id) if str(order_id).isdigit() else None
                if order_id_int:
                    order_ids_list.append(order_id_int)
                    if last_order_id is None or order_id_int > last_order_id:
                        last_order_id = order_id_int
            except:
                pass
        
        except Exception as e:
            print(f"[yellow]⚠ Errore formattazione ordine {idx}: {e}[/yellow]")
            continue
    
    # Mostra avvisi per ordini vecchi
    if old_orders_warnings:
        print(f"\n[yellow]⚠ ATTENZIONE: {len(old_orders_warnings)} ordini ShippyPro superano i 6 mesi e sono stati saltati:[/yellow]")
        for warning in old_orders_warnings[:5]:  # Mostra max 5
            print(f"[yellow]  - {warning['message']}[/yellow]")
        if len(old_orders_warnings) > 5:
            print(f"[yellow]  ... e altri {len(old_orders_warnings) - 5} ordini[/yellow]")
    
    # Ordina gli ID per trovare il più alto
    if order_ids_list:
        order_ids_list.sort()
        last_order_id = order_ids_list[-1]
    
    return {
        "texts": formatted_texts,
        "metadatas": metadatas,
        "ids": ids,
        "count": len(formatted_texts),
        "old_orders_warnings": old_orders_warnings,
        "last_order_id": last_order_id,
        "total_orders_processed": len(orders)
    }


def index_all_orders(date_from: Optional[str] = None, date_to: Optional[str] = None,
                     auto_six_months: bool = False, progress_callback=None) -> Dict[str, Any]:
    """
    Recupera e formatta ordini da entrambe le API.
    Per default indica TUTTI gli ordini disponibili (senza filtri di data).
    
    Args:
        date_from: Data inizio (opzionale)
        date_to: Data fine (opzionale)
        progress_callback: Funzione callback(sorgente, ordine_id, data, progresso, totale) chiamata per ogni ordine
        auto_six_months: Se True, indica solo gli ultimi 6 mesi (default: False = tutti gli ordini)
    
    Returns:
        Dict con tutti i dati pronti per l'indicizzazione
    """
    if auto_six_months:
        print("[cyan]🔄 Recupero TUTTI gli ordini degli ultimi 6 mesi da PrestaShop e ShippyPro...[/cyan]")
    else:
        print("[cyan]🔄 Recupero TUTTI gli ordini disponibili da PrestaShop e ShippyPro (nessun filtro data)...[/cyan]")
    
    # Recupera da PrestaShop
    prestashop_data = index_prestashop_orders(
        date_from=date_from, 
        date_to=date_to,
        auto_six_months=auto_six_months,
        progress_callback=progress_callback
    )
    
    # Recupera da ShippyPro
    shippypro_data = index_shippypro_orders(
        auto_six_months=auto_six_months,
        date_from=date_from,
        date_to=date_to,
        progress_callback=progress_callback
    )
    
    # Combina risultati
    all_texts = prestashop_data["texts"] + shippypro_data["texts"]
    all_metadatas = prestashop_data["metadatas"] + shippypro_data["metadatas"]
    all_ids = prestashop_data["ids"] + shippypro_data["ids"]
    
    # Combina avvisi ordini vecchi
    all_warnings = prestashop_data.get("old_orders_warnings", []) + shippypro_data.get("old_orders_warnings", [])
    
    total_count = prestashop_data["count"] + shippypro_data["count"]
    
    print(f"[green]✓ Totale ordini recuperati: {total_count} ({prestashop_data['count']} PrestaShop + {shippypro_data['count']} ShippyPro)[/green]")
    
    if all_warnings:
        print(f"[yellow]⚠ Totale ordini saltati (>6 mesi): {len(all_warnings)}[/yellow]")
    
    # Statistiche dettagliate
    prestashop_last = prestashop_data.get('last_order_id', 'N/A')
    shippypro_last = shippypro_data.get('last_order_id', 'N/A')
    prestashop_total_processed = prestashop_data.get('total_orders_processed', 0)
    shippypro_total_processed = shippypro_data.get('total_orders_processed', 0)
    
    print(f"[cyan]📊 Statistiche PrestaShop: {prestashop_data['count']} indicizzati su {prestashop_total_processed} processati, ultimo ordine: {prestashop_last}[/cyan]")
    print(f"[cyan]📊 Statistiche ShippyPro: {shippypro_data['count']} indicizzati su {shippypro_total_processed} processati, ultimo ordine: {shippypro_last}[/cyan]")
    
    return {
        "texts": all_texts,
        "metadatas": all_metadatas,
        "ids": all_ids,
        "count": total_count,
        "prestashop_count": prestashop_data["count"],
        "shippypro_count": shippypro_data["count"],
        "old_orders_warnings": all_warnings,
        "prestashop_last_order_id": prestashop_last,
        "shippypro_last_order_id": shippypro_last,
        "prestashop_total_processed": prestashop_total_processed,
        "shippypro_total_processed": shippypro_total_processed
    }


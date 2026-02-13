"""
Server Flask per il frontend PrestaShop
Espone API per ordini e clienti con ricerca
"""

import os
# Disabilita il caricamento automatico di .env per evitare errori di permessi
os.environ['FLASK_SKIP_DOTENV'] = '1'

from flask import Flask, jsonify, render_template
from flask_cors import CORS
from prestashop_client import PrestaShopClient
from shippypro_client import ShippyProClient
from config import BASE_URL, API_KEY, SHIPPYPRO_API_KEY
import json
import subprocess
import threading
import time
import sys
import socket
from pathlib import Path

app = Flask(__name__)
CORS(app)

# Inizializza i client
client = PrestaShopClient(BASE_URL, API_KEY)
shippypro_client = ShippyProClient(SHIPPYPRO_API_KEY)


def format_error_message(error):
    """Formatta gli errori in messaggi user-friendly"""
    error_str = str(error)
    
    # Errori SSL/Permessi
    if 'SSLError' in error_str or 'Operation not permitted' in error_str:
        return {
            'user_message': 'Errore di connessione SSL: impossibile verificare il certificato del server PrestaShop. Verifica le impostazioni di rete o contatta l\'amministratore.',
            'technical_error': 'Errore SSL/Permessi: ' + error_str
        }
    
    # Errori di connessione
    if 'Connection' in error_str or 'Max retries exceeded' in error_str:
        return {
            'user_message': 'Impossibile connettersi al server PrestaShop. Verifica che il server sia raggiungibile e che le credenziali API siano corrette.',
            'technical_error': 'Errore di connessione: ' + error_str
        }
    
    # Errori 401 (Non autorizzato)
    if '401' in error_str or 'Unauthorized' in error_str:
        return {
            'user_message': 'Credenziali API non valide. Verifica la chiave API in config.py',
            'technical_error': 'Errore autenticazione: ' + error_str
        }
    
    # Errori 404 (Non trovato)
    if '404' in error_str or 'not found' in error_str.lower():
        return {
            'user_message': 'Risorsa non trovata sul server PrestaShop.',
            'technical_error': 'Errore 404: ' + error_str
        }
    
    # Errori generici
    return {
        'user_message': 'Si è verificato un errore durante la comunicazione con PrestaShop. Riprova più tardi.',
        'technical_error': error_str
    }


@app.route('/')
def index():
    """Pagina principale"""
    return render_template('index.html')


@app.route('/api/orders')
def get_orders():
    """Endpoint per ottenere tutti gli ordini"""
    try:
        print("📦 Richiesta lista ordini...")
        # Ottieni tutti gli ordini con dettagli completi
        orders_response = client.get_orders({
            'display': 'full',
            'limit': 200  # Ridotto per velocità
        })
        
        print(f"✅ Risposta ricevuta da PrestaShop, tipo: {type(orders_response)}")
        print(f"   Chiavi nella risposta: {list(orders_response.keys()) if isinstance(orders_response, dict) else 'N/A'}")
        
        # Estrai gli ordini dal formato PrestaShop
        orders = []
        if 'orders' in orders_response:
            orders_list = orders_response['orders']
            print(f"   Numero ordini nella risposta: {len(orders_list) if isinstance(orders_list, list) else 'N/A'}")
            
            # PrestaShop può restituire array di ID o oggetti completi
            if isinstance(orders_list, list):
                for idx, order_ref in enumerate(orders_list):
                    try:
                        if isinstance(order_ref, dict):
                            # Se è già un oggetto completo con più campi, usalo direttamente
                            if len(order_ref) > 1 or 'id' not in order_ref:
                                orders.append(order_ref)
                            # Altrimenti è solo un ID, recupera i dettagli
                            elif 'id' in order_ref:
                                try:
                                    order_detail = client.get_order(order_ref['id'])
                                    if 'order' in order_detail:
                                        orders.append(order_detail['order'])
                                except Exception as e:
                                    print(f"⚠️ Errore nel recupero ordine {order_ref['id']}: {e}")
                                    continue
                        elif isinstance(order_ref, str):
                            # Se è una stringa (ID), convertila e recupera i dettagli
                            try:
                                order_id = int(order_ref)
                                order_detail = client.get_order(order_id)
                                if 'order' in order_detail:
                                    orders.append(order_detail['order'])
                            except Exception as e:
                                print(f"⚠️ Errore nel recupero ordine {order_ref}: {e}")
                                continue
                    except Exception as e:
                        print(f"⚠️ Errore processando ordine {idx}: {e}")
                        continue
        
        print(f"✅ Totale ordini processati: {len(orders)}")
        return jsonify({
            'success': True,
            'orders': orders,
            'count': len(orders)
        })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        error_info = format_error_message(e)
        print(f"❌ ERRORE in /api/orders: {e}")
        print(f"   Messaggio utente: {error_info['user_message']}")
        print(f"   Traceback completo:\n{error_trace}")
        return jsonify({
            'success': False,
            'error': error_info['user_message'],
            'technical_error': error_info['technical_error']
        }), 500


@app.route('/api/orders/search')
def search_order():
    """Endpoint per cercare un ordine per ID"""
    from flask import request
    
    order_id = request.args.get('id', '').strip()
    
    if not order_id:
        return jsonify({
            'success': False,
            'error': 'ID ordine richiesto'
        }), 400
    
    try:
        # Verifica che sia un numero
        order_id_int = int(order_id)
        
        # Ottieni l'ordine specifico
        order_detail = client.get_order(order_id_int)
        
        if 'order' in order_detail:
            return jsonify({
                'success': True,
                'order': order_detail['order'],
                'count': 1
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Ordine non trovato'
            }), 404
            
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'ID ordine deve essere un numero'
        }), 400
    except Exception as e:
        error_info = format_error_message(e)
        error_msg = str(e)
        if '404' in error_msg or 'not found' in error_msg.lower():
            return jsonify({
                'success': False,
                'error': 'Ordine non trovato'
            }), 404
        return jsonify({
            'success': False,
            'error': error_info['user_message'],
            'technical_error': error_info['technical_error']
        }), 500


@app.route('/api/customers')
def get_customers():
    """Endpoint per ottenere tutti i clienti"""
    try:
        # Ottieni tutti i clienti con dettagli completi
        customers_response = client.get_customers({
            'display': 'full',
            'limit': 1000  # Aumenta se necessario
        })
        
        # Estrai i clienti dal formato PrestaShop
        customers = []
        if 'customers' in customers_response:
            # PrestaShop può restituire array di ID o oggetti completi
            if isinstance(customers_response['customers'], list):
                for customer_ref in customers_response['customers']:
                    if isinstance(customer_ref, dict):
                        # Se è già un oggetto completo con più campi, usalo direttamente
                        if len(customer_ref) > 1 or 'id' not in customer_ref:
                            customers.append(customer_ref)
                        # Altrimenti è solo un ID, recupera i dettagli
                        elif 'id' in customer_ref:
                            try:
                                customer_detail = client.get_customer(customer_ref['id'])
                                if 'customer' in customer_detail:
                                    customers.append(customer_detail['customer'])
                            except Exception as e:
                                print(f"Errore nel recupero cliente {customer_ref['id']}: {e}")
                                continue
        
        return jsonify({
            'success': True,
            'customers': customers,
            'count': len(customers)
        })
    except Exception as e:
        error_info = format_error_message(e)
        print(f"❌ ERRORE in /api/customers: {e}")
        return jsonify({
            'success': False,
            'error': error_info['user_message'],
            'technical_error': error_info['technical_error']
        }), 500


@app.route('/api/customers/search')
def search_customers():
    """Endpoint per cercare clienti per nome"""
    from flask import request
    
    query = request.args.get('q', '').lower().strip()
    
    if not query:
        return jsonify({
            'success': False,
            'error': 'Query di ricerca richiesta'
        }), 400
    
    try:
        # Ottieni tutti i clienti
        customers_response = client.get_customers({
            'display': 'full',
            'limit': 1000
        })
        
        # Filtra i clienti per nome
        matching_customers = []
        if 'customers' in customers_response:
            if isinstance(customers_response['customers'], list):
                for customer_ref in customers_response['customers']:
                    if isinstance(customer_ref, dict):
                        customer = customer_ref if len(customer_ref) > 1 else None
                        
                        # Se è solo un ID, recupera i dettagli completi
                        if not customer and 'id' in customer_ref:
                            try:
                                customer_detail = client.get_customer(customer_ref['id'])
                                if 'customer' in customer_detail:
                                    customer = customer_detail['customer']
                            except Exception as e:
                                continue
                        
                        if customer:
                            firstname = customer.get('firstname', '').lower()
                            lastname = customer.get('lastname', '').lower()
                            email = customer.get('email', '').lower()
                            company = customer.get('company', '').lower()
                            
                            if (query in firstname or 
                                query in lastname or 
                                query in email or 
                                query in company or
                                query in f"{firstname} {lastname}"):
                                matching_customers.append(customer)
        
        return jsonify({
            'success': True,
            'customers': matching_customers,
            'count': len(matching_customers),
            'query': query
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/shipping/<shipping_number>')
def get_shipping_info(shipping_number):
    """
    Endpoint per ottenere informazioni di spedizione.
    Cerca il tracking number negli ordini PrestaShop e prova vari metodi ShippyPro.
    """
    from flask import request
    
    try:
        if not shipping_number or shipping_number.strip() == '':
            return jsonify({
                'success': False,
                'error': 'Numero di spedizione richiesto'
            }), 400
        
        shipping_num = shipping_number.strip()
        errors = []
        info = {}
        prestashop_order_info = None
        
        # Cerca l'ordine PrestaShop che ha questo shipping_number
        # Cerchiamo in modo più aggressivo: tutti gli ordini e controllo manuale
        try:
            print(f"🔍 Cercando ordine con shipping_number: {shipping_num}")
            
            # Prima prova con filtro se supportato
            try:
                orders_response = client.get_orders({
                    'display': 'full',
                    'limit': 200,  # Limita a 200 ordini per velocità
                    'filter[shipping_number]': shipping_num
                })
            except:
                # Se il filtro non funziona, carica solo gli ordini più recenti
                orders_response = client.get_orders({
                    'display': 'full',
                    'limit': 200  # Limita a 200 ordini per velocità
                })
            
            # Cerca manualmente in tutti gli ordini
            if 'orders' in orders_response:
                orders_list = orders_response.get('orders', [])
                print(f"📦 Controllando {len(orders_list)} ordini...")
                
                # Prima cerca negli ordini già caricati (più veloce)
                for order_ref in orders_list:
                    if isinstance(order_ref, dict):
                        # Controlla se l'ordine ha già i dati completi
                        if len(order_ref) > 1:
                            order_shipping = str(order_ref.get('shipping_number', '')).strip()
                            order_tracking = str(order_ref.get('tracking_number', '')).strip()
                            if order_shipping == shipping_num or order_tracking == shipping_num:
                                print(f"✅ Trovato ordine #{order_ref.get('id')} con shipping_number nei dati completi!")
                                prestashop_order_info = order_ref
                                break
                
                # Se non trovato, cerca recuperando i dettagli completi
                # Prova prima con gli ordini più recenti (più probabili di avere tracking)
                if not prestashop_order_info:
                    # Estrai tutti gli ID degli ordini
                    order_ids = []
                    for order_ref in orders_list:
                        if isinstance(order_ref, dict):
                            order_id = order_ref.get('id')
                            if not order_id and len(order_ref) == 1:
                                order_id = list(order_ref.values())[0] if order_ref else None
                            if order_id:
                                try:
                                    order_ids.append(int(order_id))
                                except:
                                    pass
                    
                    # Ordina per ID (più recenti prima)
                    order_ids.sort(reverse=True)
                    
                    # Limita a solo i primi 50 ordini più recenti per velocità
                    max_to_check = min(50, len(order_ids))
                    print(f"🔍 Controllando dettagli dei primi {max_to_check} ordini più recenti...")
                    
                    for idx, order_id in enumerate(order_ids[:max_to_check]):
                        try:
                            order_detail = client.get_order(order_id)
                            if 'order' in order_detail:
                                order = order_detail['order']
                                order_shipping = str(order.get('shipping_number', '')).strip()
                                order_tracking = str(order.get('tracking_number', '')).strip()
                                if order_shipping == shipping_num or order_tracking == shipping_num:
                                    print(f"✅ Trovato ordine #{order_id} con shipping_number!")
                                    prestashop_order_info = order
                                    break
                                
                                # Log progress ogni 10 ordini
                                if (idx + 1) % 10 == 0:
                                    print(f"   Controllati {idx + 1}/{max_to_check} ordini... (shipping_number cercato: {shipping_num})")
                        except Exception as e:
                            if idx < 3:  # Log solo i primi errori
                                print(f"Errore recupero ordine {order_id}: {e}")
                            continue
        except Exception as e:
            print(f"Errore nella ricerca ordine PrestaShop: {e}")
            import traceback
            traceback.print_exc()
        
        # Prova a recuperare il nome del corriere da PrestaShop se disponibile
        carrier_name = None
        if prestashop_order_info:
            carrier_id = prestashop_order_info.get('id_carrier')
            if carrier_id:
                try:
                    carrier_info = client.get(f'carriers/{carrier_id}')
                    if 'carrier' in carrier_info:
                        carrier_name = carrier_info['carrier'].get('name', '')
                        print(f"📦 Corriere trovato: {carrier_name}")
                except Exception as e:
                    print(f"Errore recupero corriere {carrier_id}: {e}")
        
        # Prova vari metodi ShippyPro secondo la documentazione ufficiale
        # Prima cerca l'OrderID usando TransactionID/shipping_number
        shippypro_order_id = None
        try:
            print(f"🔍 Cercando ordine ShippyPro con TransactionID: {shipping_num}")
            order_search = shippypro_client.get_order_by_transaction_id(shipping_num)
            if 'OrderID' in order_search or 'Error' not in order_search:
                # Se abbiamo trovato l'ordine, ottieni l'OrderID
                if 'OrderID' in order_search:
                    shippypro_order_id = order_search['OrderID']
                else:
                    # Se abbiamo i dati dell'ordine, usa quello
                    info['getorder'] = order_search
            print(f"   Risultato ricerca: {order_search.get('Error', 'Order found')}")
        except Exception as e:
            print(f"   Errore ricerca ordine: {e}")
        
        methods_to_try = [
            # GetTracking richiede 'Code' (non TrackingNumber)
            ('GetTracking', {'Code': shipping_num, 'CarrierName': carrier_name}) if carrier_name else None,
            ('GetTracking', {'Code': shipping_num}),
            # Prova GetOrder se abbiamo trovato l'OrderID
            ('GetOrder', {'OrderID': shippypro_order_id}) if shippypro_order_id else None,
            # Prova GetLabelUrl che potrebbe avere tracking info (richiede OrderID)
            ('GetLabelUrl', {'OrderID': shippypro_order_id}) if shippypro_order_id else None,
        ]
        
        # Rimuovi None dalla lista
        methods_to_try = [m for m in methods_to_try if m is not None]
        
        for method_name, params in methods_to_try:
            try:
                print(f"🔍 Tentativo metodo: {method_name} con parametri: {params}")
                result = shippypro_client.make_request(method_name, data=params)
                if result:
                    # Se non c'è errore o se l'errore è diverso da "Method Not Found"
                    if 'Error' not in result:
                        print(f"✅ Successo con {method_name}!")
                        info[method_name.lower()] = result
                    elif result.get('Error') != 'Method Not Found':
                        error_type = result.get('Error', 'Unknown error')
                        errors.append(f"{method_name}: {error_type}")
                        print(f"⚠️ Errore {method_name}: {error_type}")
                else:
                    print(f"⚠️ Risposta vuota da {method_name}")
            except Exception as e:
                error_msg = str(e)
                if 'Method Not Found' not in error_msg and 'Authentication Failed' not in error_msg:
                    errors.append(f"{method_name}: {error_msg}")
                    print(f"❌ Eccezione {method_name}: {error_msg}")
        
        # Prepara la risposta
        response_data = {
            'success': True,
            'shipping_number': shipping_num,
        }
        
        # Aggiungi informazioni PrestaShop se trovate
        if prestashop_order_info:
            response_data['prestashop_order'] = {
                'id': prestashop_order_info.get('id'),
                'reference': prestashop_order_info.get('reference'),
                'id_carrier': prestashop_order_info.get('id_carrier'),
                'id_customer': prestashop_order_info.get('id_customer'),
                'current_state': prestashop_order_info.get('current_state'),
                'delivery_number': prestashop_order_info.get('delivery_number'),
                'delivery_date': prestashop_order_info.get('delivery_date'),
                'shipping_number': prestashop_order_info.get('shipping_number'),
                'tracking_number': prestashop_order_info.get('tracking_number'),
            }
            # Includi tutti i campi dell'ordine per riferimento completo
            response_data['prestashop_order_full'] = prestashop_order_info
            
            # Prova a recuperare informazioni sul corriere se disponibile
            carrier_id = prestashop_order_info.get('id_carrier')
            if carrier_id:
                try:
                    carrier_info = client.get(f'carriers/{carrier_id}')
                    if 'carrier' in carrier_info:
                        response_data['carrier_info'] = carrier_info['carrier']
                except Exception as e:
                    print(f"Errore recupero corriere {carrier_id}: {e}")
        
        # Aggiungi dati ShippyPro se trovati
        if info:
            response_data.update(info)
        
        # Stato ShippyPro
        response_data['shippypro_status'] = {
            'authenticated': True,
            'api_key_configured': True,
            'methods_available': len(info) > 0,
            'methods_tried': [m[0] for m in methods_to_try],
            'note': 'I metodi Get (GetTracking, GetOrder, GetShipment) non sono disponibili per questa API key. '
                   'ShippyPro espone principalmente metodi per creare/modificare ordini (PutOrder, Ship, Edit), '
                   'ma non metodi pubblici per recuperare dati di tracking. '
                   'I dati di tracking sono generalmente disponibili tramite webhook o direttamente dall\'API del corriere.'
        }
        
        # Se non abbiamo trovato dati, aggiungi note e suggerimenti
        if not info and not prestashop_order_info:
            response_data['note'] = f'⚠️ Non ho trovato dati da ShippyPro API (metodi Get non disponibili) e non ho trovato un ordine PrestaShop con shipping_number = {shipping_num}.'
            if 'orders_list' in locals():
                response_data['note'] += f' Ho cercato tra {len(orders_list)} ordini PrestaShop.'
            response_data['suggestions'] = [
                'Verifica che il shipping_number sia corretto',
                'I dati di tracking vengono generalmente recuperati tramite webhook di ShippyPro',
                'Oppure puoi usare direttamente l\'API del corriere specifico con il numero di tracking',
                'Verifica nella console API di ShippyPro quali metodi sono disponibili per la tua API key'
            ]
        elif prestashop_order_info:
            # Se abbiamo trovato l'ordine PrestaShop, evidenzialo
            response_data['note'] = f'✅ Ordine PrestaShop trovato! ID: {prestashop_order_info.get("id")}, Riferimento: {prestashop_order_info.get("reference")}'
            response_data['success_message'] = 'Dati dell\'ordine PrestaShop recuperati con successo. Tutti i dettagli sono disponibili qui sotto.'
            if not info:
                response_data['shippypro_note'] = '⚠️ ShippyPro API: I metodi Get non sono disponibili per recuperare dati di tracking. I dati mostrati provengono da PrestaShop.'
        
        if errors:
            response_data['errors'] = errors
        
        response_data['debug'] = {
            'api_key_configured': bool(SHIPPYPRO_API_KEY),
            'api_key_prefix': SHIPPYPRO_API_KEY[:10] + '...' if SHIPPYPRO_API_KEY else 'None',
            'prestashop_order_found': prestashop_order_info is not None
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        error_info = format_error_message(e)
        print(f"❌ ERRORE in /api/shipping: {e}")
        return jsonify({
            'success': False,
            'error': error_info['user_message'],
            'technical_error': error_info['technical_error']
        }), 500


def check_port_in_use(port):
    """Verifica se una porta è già in uso"""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(('localhost', port))
            return result == 0
    except:
        return False


def start_streamlit():
    """Avvia Streamlit per Trillium RAG in background"""
    try:
        # Verifica se la porta 8501 è già in uso
        if check_port_in_use(8501):
            print("ℹ️  Streamlit già in esecuzione su porta 8501")
            return
        
        # Trova il percorso della cartella trillium
        current_dir = Path(__file__).parent
        trillium_dir = current_dir / 'trillium'
        streamlit_app = trillium_dir / 'streamlit_app.py'
        
        if not streamlit_app.exists():
            print("⚠️  Trillium non trovato, salto l'avvio di Streamlit")
            return
        
        # Attendi un po' prima di avviare Streamlit
        time.sleep(2)
        
        print("🚀 Avvio Trillium RAG (Streamlit)...")
        
        # Avvia Streamlit in background
        process = subprocess.Popen(
            [sys.executable, '-m', 'streamlit', 'run', str(streamlit_app),
             '--server.port', '8501',
             '--server.address', 'localhost',
             '--server.headless', 'true',
             '--browser.gatherUsageStats', 'false'],
            cwd=str(trillium_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Attendi un attimo per verificare che sia partito
        time.sleep(5)
        if check_port_in_use(8501):
            print("✅ Trillium RAG disponibile su http://localhost:8501")
        else:
            print("⚠️  Trillium RAG potrebbe non essere partito correttamente")
            # Verifica se il processo è ancora attivo
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                if stderr:
                    print(f"   Errore: {stderr.decode()[:200]}")
                print("   Puoi avviarlo manualmente con: cd trillium && streamlit run streamlit_app.py")
    except FileNotFoundError:
        print("⚠️  Streamlit non installato. Installa con: pip install streamlit")
    except Exception as e:
        print(f"⚠️  Errore nell'avvio di Streamlit: {e}")
        import traceback
        print(f"   Dettagli: {traceback.format_exc()[:300]}")
        print("   Puoi avviarlo manualmente con: cd trillium && streamlit run streamlit_app.py")


if __name__ == '__main__':
    PORT = 8080
    STREAMLIT_PORT = 8501
    
    print("=" * 60)
    print("🚀 Avvio servizi...")
    print("=" * 60)
    
    # Avvia Streamlit in un thread separato
    streamlit_thread = threading.Thread(target=start_streamlit, daemon=True)
    streamlit_thread.start()
    
    print(f"📦 Server Flask avviato su http://localhost:{PORT}")
    print(f"🔗 Collegato a PrestaShop: {BASE_URL}")
    print(f"📄 Trillium RAG sarà disponibile su http://localhost:{STREAMLIT_PORT}")
    print("=" * 60)
    
    app.run(debug=True, host='127.0.0.1', port=PORT, use_reloader=False)


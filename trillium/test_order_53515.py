#!/usr/bin/env python3
"""
Script di test per verificare perché l'ordine 53515 non viene trovato
"""

import sys
import os

# Aggiungi il percorso root
root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_path)

from prestashop_client import PrestaShopClient
from shippypro_client import ShippyProClient
from config import BASE_URL, API_KEY, SHIPPYPRO_API_KEY
import json

print("=" * 60)
print("🔍 TEST ORDINE 53515")
print("=" * 60)

# Test 1: Recupera ordine specifico 53515
print("\n1️⃣ Test recupero ordine specifico 53515 da PrestaShop...")
try:
    client = PrestaShopClient(BASE_URL, API_KEY)
    order_detail = client.get_order(53515)
    
    if 'order' in order_detail:
        order = order_detail['order']
        print(f"✅ Ordine 53515 trovato!")
        print(f"   ID: {order.get('id', 'N/A')}")
        print(f"   Riferimento: {order.get('reference', 'N/A')}")
        print(f"   Data: {order.get('date_add', 'N/A')}")
        print(f"   Totale: {order.get('total_paid', 'N/A')}")
        print(f"   Stato: {order.get('current_state', 'N/A')}")
    else:
        print(f"⚠️ Risposta: {json.dumps(order_detail, indent=2, default=str)}")
except Exception as e:
    print(f"❌ Errore: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Recupera lista ordini e cerca 53515
print("\n2️⃣ Test recupero lista ordini e ricerca 53515...")
try:
    client = PrestaShopClient(BASE_URL, API_KEY)
    response = client.get_orders({
        'display': 'full',
        'limit': 1000
    })
    
    print(f"   Tipo risposta: {type(response)}")
    if isinstance(response, dict):
        print(f"   Chiavi: {list(response.keys())}")
        
        if 'orders' in response:
            orders_list = response['orders']
            print(f"   Tipo orders: {type(orders_list)}")
            
            if isinstance(orders_list, list):
                print(f"   Numero ordini nella lista: {len(orders_list)}")
                
                # Cerca ordine 53515
                found_53515 = False
                for idx, order_ref in enumerate(orders_list):
                    if isinstance(order_ref, dict):
                        order_id = order_ref.get('id', order_ref.get('@attributes', {}).get('id'))
                        if str(order_id) == '53515':
                            found_53515 = True
                            print(f"✅ Ordine 53515 trovato nella lista alla posizione {idx}!")
                            print(f"   Dati: {json.dumps(order_ref, indent=2, default=str)[:500]}")
                            break
                    elif isinstance(order_ref, (str, int)):
                        if str(order_ref) == '53515':
                            found_53515 = True
                            print(f"✅ Ordine 53515 trovato nella lista come ID alla posizione {idx}!")
                            break
                
                if not found_53515:
                    print(f"❌ Ordine 53515 NON trovato nella lista!")
                    print(f"   Mostro primi 10 ordini:")
                    for idx, order_ref in enumerate(orders_list[:10]):
                        if isinstance(order_ref, dict):
                            order_id = order_ref.get('id', order_ref.get('@attributes', {}).get('id'))
                            print(f"      [{idx}] ID: {order_id}, tipo: {type(order_ref)}, chiavi: {list(order_ref.keys())[:5]}")
                        else:
                            print(f"      [{idx}] Valore: {order_ref}, tipo: {type(order_ref)}")
            else:
                print(f"   orders non è una lista: {type(orders_list)}")
                print(f"   Contenuto: {json.dumps(orders_list, indent=2, default=str)[:500]}")
        else:
            print(f"   Chiave 'orders' non trovata nella risposta")
            print(f"   Risposta: {json.dumps(response, indent=2, default=str)[:1000]}")
    else:
        print(f"   Risposta non è un dict: {type(response)}")
        print(f"   Risposta: {str(response)[:500]}")
        
except Exception as e:
    print(f"❌ Errore: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Prova con ShippyPro
print("\n3️⃣ Test ricerca ordine 53515 su ShippyPro...")
try:
    shippypro_client = ShippyProClient(SHIPPYPRO_API_KEY)
    
    # Prova con OrderID
    order = shippypro_client.get_order(53515)
    if order.get('Result') == 'OK':
        print(f"✅ Ordine 53515 trovato su ShippyPro!")
        print(f"   Dati: {json.dumps(order, indent=2, default=str)[:500]}")
    else:
        print(f"⚠️ Ordine 53515 non trovato su ShippyPro con OrderID")
        print(f"   Risposta: {json.dumps(order, indent=2, default=str)[:500]}")
    
    # Prova con TransactionID (shipping_number)
    order_by_trans = shippypro_client.get_order_by_transaction_id("53515")
    if order_by_trans and order_by_trans.get('Result') != 'Error':
        print(f"✅ Ordine 53515 trovato su ShippyPro con TransactionID!")
        print(f"   Dati: {json.dumps(order_by_trans, indent=2, default=str)[:500]}")
    else:
        print(f"⚠️ Ordine 53515 non trovato su ShippyPro con TransactionID")
        
except Exception as e:
    print(f"❌ Errore: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Verifica quanti ordini vengono recuperati
print("\n4️⃣ Test conteggio ordini totali...")
try:
    client = PrestaShopClient(BASE_URL, API_KEY)
    response = client.get_orders({
        'display': 'full',
        'limit': 1000
    })
    
    if 'orders' in response:
        orders_list = response['orders']
        if isinstance(orders_list, list):
            print(f"✅ Totale ordini recuperati: {len(orders_list)}")
            
            # Mostra range di ID ordini
            order_ids = []
            for order_ref in orders_list:
                if isinstance(order_ref, dict):
                    order_id = order_ref.get('id', order_ref.get('@attributes', {}).get('id'))
                    if order_id:
                        try:
                            order_ids.append(int(order_id))
                        except:
                            pass
                elif isinstance(order_ref, (str, int)):
                    try:
                        order_ids.append(int(order_ref))
                    except:
                        pass
            
            if order_ids:
                order_ids.sort()
                print(f"   ID minimo: {min(order_ids)}")
                print(f"   ID massimo: {max(order_ids)}")
                print(f"   Ordine 53515 nel range? {'✅ SÌ' if 53515 in order_ids else '❌ NO'}")
        else:
            print(f"   orders non è una lista")
except Exception as e:
    print(f"❌ Errore: {e}")

print("\n" + "=" * 60)
print("✅ Test completato")
print("=" * 60)


#!/usr/bin/env python3
"""
Test ricerca ordine su ShippyPro
"""

import sys
import os

# Aggiungi il percorso root
root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_path)

from shippypro_client import ShippyProClient
from config import SHIPPYPRO_API_KEY
import json

print("=" * 60)
print("🔍 RICERCA ORDINE SHIPPYPRO: 306-4921134-1699535")
print("=" * 60)

client = ShippyProClient(SHIPPYPRO_API_KEY)

# Test 1: Cerca come TransactionID
print("\n1️⃣ Test ricerca come TransactionID...")
try:
    order = client.get_order_by_transaction_id("306-4921134-1699535")
    if order and order.get('Result') == 'OK':
        print(f"✅ Ordine trovato come TransactionID!")
        print(f"   Dati: {json.dumps(order, indent=2, default=str)[:1000]}")
    elif order:
        print(f"⚠️ Risposta ricevuta:")
        print(f"   Result: {order.get('Result', 'N/A')}")
        print(f"   Error: {order.get('Error', 'N/A')}")
        print(f"   Dati completi: {json.dumps(order, indent=2, default=str)[:500]}")
    else:
        print(f"❌ Nessuna risposta")
except Exception as e:
    print(f"❌ Errore: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Cerca come OrderID (prova a estrarre numeri)
print("\n2️⃣ Test ricerca come OrderID (estrazione numeri)...")
try:
    # Prova con l'ultimo numero
    order_id = 1699535
    order = client.get_order(order_id)
    if order and order.get('Result') == 'OK':
        print(f"✅ Ordine trovato con OrderID {order_id}!")
        print(f"   Dati: {json.dumps(order, indent=2, default=str)[:1000]}")
    else:
        print(f"⚠️ OrderID {order_id} non trovato")
        print(f"   Result: {order.get('Result', 'N/A') if order else 'N/A'}")
        print(f"   Error: {order.get('Error', 'N/A') if order else 'N/A'}")
except Exception as e:
    print(f"❌ Errore: {e}")

# Test 3: Cerca come Tracking Number
print("\n3️⃣ Test ricerca come Tracking Number...")
try:
    # ShippyPro potrebbe avere un metodo per cercare per tracking
    # Prova con GetOrder usando il TransactionID completo
    order = client.get_order_by_transaction_id("306-4921134-1699535")
    if order and order.get('Result') == 'OK':
        print(f"✅ Ordine trovato!")
        tracking = order.get('Order', {}).get('TrackingNumber', 'N/A')
        print(f"   Tracking Number: {tracking}")
        print(f"   Dati: {json.dumps(order, indent=2, default=str)[:1000]}")
    else:
        print(f"⚠️ Non trovato come Tracking Number")
except Exception as e:
    print(f"❌ Errore: {e}")

# Test 4: Cerca nei pending orders
print("\n4️⃣ Test ricerca nei Pending Orders...")
try:
    pending_response = client.make_request('GetPendingOrders', data={})
    if pending_response.get('Result') == 'OK' and 'Orders' in pending_response:
        orders_list = pending_response['Orders']
        if not isinstance(orders_list, list):
            orders_list = [orders_list] if orders_list else []
        
        print(f"   Trovati {len(orders_list)} pending orders")
        
        # Cerca l'ordine
        found = False
        for order in orders_list:
            transaction_id = order.get('TransactionID', '')
            order_id = order.get('OrderID', '')
            tracking = order.get('TrackingNumber', '')
            
            if (transaction_id == "306-4921134-1699535" or 
                str(order_id) == "1699535" or
                tracking == "306-4921134-1699535"):
                found = True
                print(f"✅ Ordine trovato nei pending orders!")
                print(f"   OrderID: {order_id}")
                print(f"   TransactionID: {transaction_id}")
                print(f"   TrackingNumber: {tracking}")
                print(f"   Dati completi: {json.dumps(order, indent=2, default=str)[:1000]}")
                break
        
        if not found:
            print(f"   ❌ Ordine non trovato nei pending orders")
            if orders_list:
                print(f"   Esempio primi 3 ordini:")
                for i, order in enumerate(orders_list[:3]):
                    print(f"      [{i+1}] OrderID: {order.get('OrderID', 'N/A')}, TransactionID: {order.get('TransactionID', 'N/A')}")
    else:
        print(f"⚠️ Errore nel recupero pending orders")
        print(f"   Result: {pending_response.get('Result', 'N/A')}")
        print(f"   Error: {pending_response.get('Error', 'N/A')}")
except Exception as e:
    print(f"❌ Errore: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Prova con parti dell'identificatore
print("\n5️⃣ Test ricerca con parti dell'identificatore...")
parts = ["306", "4921134", "1699535", "306-4921134", "4921134-1699535"]
for part in parts:
    try:
        print(f"   Provo con: {part}")
        order = client.get_order_by_transaction_id(part)
        if order and order.get('Result') == 'OK':
            print(f"   ✅ Trovato con '{part}'!")
            print(f"      Dati: {json.dumps(order, indent=2, default=str)[:500]}")
            break
        else:
            print(f"      ❌ Non trovato")
    except Exception as e:
        print(f"      ❌ Errore: {e}")

print("\n" + "=" * 60)
print("✅ Test completato")
print("=" * 60)


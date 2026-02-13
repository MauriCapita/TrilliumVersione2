#!/usr/bin/env python3
"""
Test paginazione PrestaShop per verificare se recupera tutti gli ordini incluso 53515
"""

import sys
import os

# Aggiungi il percorso root
root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_path)

# Aggiungi anche il percorso trillium/rag
trillium_rag_path = os.path.join(root_path, 'trillium', 'rag')
sys.path.insert(0, trillium_rag_path)

from rag.api_integration import get_prestashop_orders
import json

print("=" * 60)
print("🔍 TEST PAGINAZIONE PRESTSHOP")
print("=" * 60)

# Test senza filtri di data (tutti gli ordini)
print("\n1️⃣ Test recupero TUTTI gli ordini (senza filtri di data)...")
try:
    all_orders = get_prestashop_orders(date_from=None, date_to=None)
    
    print(f"\n✅ Totale ordini recuperati: {len(all_orders)}")
    
    if all_orders:
        # Trova range di ID
        order_ids = []
        for order in all_orders:
            if isinstance(order, dict) and 'id' in order:
                try:
                    order_ids.append(int(order['id']))
                except:
                    pass
        
        if order_ids:
            order_ids.sort()
            print(f"   ID minimo: {min(order_ids)}")
            print(f"   ID massimo: {max(order_ids)}")
            
            # Cerca ordine 53515
            if 53515 in order_ids:
                print(f"   ✅ Ordine 53515 TROVATO!")
                # Mostra dettagli ordine 53515
                for order in all_orders:
                    if isinstance(order, dict) and str(order.get('id', '')) == '53515':
                        print(f"\n   📦 Dettagli ordine 53515:")
                        print(f"      Riferimento: {order.get('reference', 'N/A')}")
                        print(f"      Data: {order.get('date_add', 'N/A')}")
                        print(f"      Totale: {order.get('total_paid', 'N/A')}")
                        break
            else:
                print(f"   ❌ Ordine 53515 NON trovato")
                print(f"   Verifica: ordini recuperati vanno da {min(order_ids)} a {max(order_ids)}")
        
        # Mostra alcuni esempi
        print(f"\n   Primi 5 ordini:")
        for i, order in enumerate(all_orders[:5]):
            if isinstance(order, dict):
                print(f"      [{i+1}] ID: {order.get('id', 'N/A')}, Ref: {order.get('reference', 'N/A')}, Data: {order.get('date_add', 'N/A')}")
        
        print(f"\n   Ultimi 5 ordini:")
        for i, order in enumerate(all_orders[-5:]):
            if isinstance(order, dict):
                print(f"      [{i+1}] ID: {order.get('id', 'N/A')}, Ref: {order.get('reference', 'N/A')}, Data: {order.get('date_add', 'N/A')}")
    else:
        print("   ⚠️ Nessun ordine recuperato")
        
except Exception as e:
    print(f"❌ Errore: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("✅ Test completato")
print("=" * 60)


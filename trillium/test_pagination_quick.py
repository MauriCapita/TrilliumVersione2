#!/usr/bin/env python3
"""
Test rapido per verificare se la paginazione recupera ordini diversi
"""

import sys
import os

root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_path)

from prestashop_client import PrestaShopClient
from config import BASE_URL, API_KEY

client = PrestaShopClient(BASE_URL, API_KEY)

print("Test paginazione PrestaShop - Verifica ordini diversi tra pagine\n")

# Pagina 1
print("📄 Pagina 1:")
response1 = client.get_orders({'display': 'full', 'limit': 100, 'p': 1})
if 'orders' in response1 and isinstance(response1['orders'], list):
    orders1 = response1['orders']
    print(f"   Ordini: {len(orders1)}")
    if orders1:
        first_id_1 = orders1[0].get('id', 'N/A') if isinstance(orders1[0], dict) else orders1[0]
        last_id_1 = orders1[-1].get('id', 'N/A') if isinstance(orders1[-1], dict) else orders1[-1]
        print(f"   Primo ID: {first_id_1}, Ultimo ID: {last_id_1}")

# Pagina 2
print("\n📄 Pagina 2:")
response2 = client.get_orders({'display': 'full', 'limit': 100, 'p': 2})
if 'orders' in response2 and isinstance(response2['orders'], list):
    orders2 = response2['orders']
    print(f"   Ordini: {len(orders2)}")
    if orders2:
        first_id_2 = orders2[0].get('id', 'N/A') if isinstance(orders2[0], dict) else orders2[0]
        last_id_2 = orders2[-1].get('id', 'N/A') if isinstance(orders2[-1], dict) else orders2[-1]
        print(f"   Primo ID: {first_id_2}, Ultimo ID: {last_id_2}")

# Pagina 54 (dovrebbe contenere ordini intorno a 5350-5450)
print("\n📄 Pagina 54 (dovrebbe contenere ordini intorno a 5350-5450):")
response54 = client.get_orders({'display': 'full', 'limit': 100, 'p': 54})
if 'orders' in response54 and isinstance(response54['orders'], list):
    orders54 = response54['orders']
    print(f"   Ordini: {len(orders54)}")
    if orders54:
        first_id_54 = orders54[0].get('id', 'N/A') if isinstance(orders54[0], dict) else orders54[0]
        last_id_54 = orders54[-1].get('id', 'N/A') if isinstance(orders54[-1], dict) else orders54[-1]
        print(f"   Primo ID: {first_id_54}, Ultimo ID: {last_id_54}")
        
        # Cerca ordine 53515
        found_53515 = False
        for order in orders54:
            order_id = order.get('id', 'N/A') if isinstance(order, dict) else order
            if str(order_id) == '53515':
                found_53515 = True
                print(f"   ✅ Ordine 53515 TROVATO in questa pagina!")
                break
        if not found_53515:
            print(f"   ❌ Ordine 53515 non in questa pagina")

# Pagina 536 (dovrebbe contenere ordine 53515)
print("\n📄 Pagina 536 (dovrebbe contenere ordine 53515):")
response536 = client.get_orders({'display': 'full', 'limit': 100, 'p': 536})
if 'orders' in response536 and isinstance(response536['orders'], list):
    orders536 = response536['orders']
    print(f"   Ordini: {len(orders536)}")
    if orders536:
        first_id_536 = orders536[0].get('id', 'N/A') if isinstance(orders536[0], dict) else orders536[0]
        last_id_536 = orders536[-1].get('id', 'N/A') if isinstance(orders536[-1], dict) else orders536[-1]
        print(f"   Primo ID: {first_id_536}, Ultimo ID: {last_id_536}")
        
        # Cerca ordine 53515
        found_53515 = False
        for order in orders536:
            order_id = order.get('id', 'N/A') if isinstance(order, dict) else order
            if str(order_id) == '53515':
                found_53515 = True
                print(f"   ✅ Ordine 53515 TROVATO in questa pagina!")
                if isinstance(order, dict):
                    print(f"      Riferimento: {order.get('reference', 'N/A')}")
                    print(f"      Data: {order.get('date_add', 'N/A')}")
                break
        if not found_53515:
            print(f"   ❌ Ordine 53515 non in questa pagina")

print("\n✅ Test completato")


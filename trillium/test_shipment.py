#!/usr/bin/env python3
"""
Test GetShipment per l'ordine 306-4921134-1699535
"""

import sys
import os

root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_path)

from shippypro_client import ShippyProClient
from config import SHIPPYPRO_API_KEY
import json

client = ShippyProClient(SHIPPYPRO_API_KEY)

print("Test GetShipment per: 306-4921134-1699535\n")

try:
    shipment = client.get_shipment("306-4921134-1699535")
    print(f"Risposta GetShipment:")
    print(json.dumps(shipment, indent=2, default=str))
except Exception as e:
    print(f"Errore: {e}")
    import traceback
    traceback.print_exc()


"""
Esempio di utilizzo del PrestaShop Client
"""

from prestashop_client import PrestaShopClient
from config import BASE_URL, API_KEY

# Inizializza il client
client = PrestaShopClient(BASE_URL, API_KEY)

print(f"Connessione a PrestaShop: {BASE_URL}")
print(f"API Key configurata: {API_KEY[:10]}...\n")

try:
    # Test di connessione
    print("Test di connessione in corso...")
    shop_info = client.get('')
    print("✓ Connessione riuscita!\n")
    
    # Esempio: ottieni i primi 5 prodotti
    print("--- Recupero prodotti ---")
    products = client.get_products({'limit': 5})
    print(f"Risultato: {products}\n")
    
    # Esempio: ottieni gli ordini
    print("--- Recupero ordini ---")
    orders = client.get_orders({'limit': 5})
    print(f"Risultato: {orders}\n")
    
except Exception as e:
    print(f"✗ Errore: {str(e)}\n")
    print("Verifica che:")
    print("1. L'URL del negozio in config.py sia corretto")
    print("2. L'API key sia valida")
    print("3. L'API REST sia abilitata nel pannello PrestaShop")



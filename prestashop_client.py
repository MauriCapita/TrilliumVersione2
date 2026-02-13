"""
PrestaShop API Client
Collegamento alle API di PrestaShop utilizzando la chiave API fornita.
"""

import requests
from typing import Dict, Any, Optional
import base64


class PrestaShopClient:
    """Client per interagire con le API REST di PrestaShop."""
    
    def __init__(self, base_url: str, api_key: str, verify_ssl: bool = False):
        """
        Inizializza il client PrestaShop.
        
        Args:
            base_url: URL base del negozio PrestaShop (es. https://mio-store.com)
            api_key: Chiave API di PrestaShop
            verify_ssl: Se True, verifica i certificati SSL. Default: False per evitare errori di permessi
        """
        # Rimuove lo slash finale se presente
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.api_url = f"{self.base_url}/api"
        self.verify_ssl = verify_ssl
        
        # Prepara l'autenticazione Basic Auth
        # PrestaShop usa il formato: API_KEY: (senza password)
        credentials = f"{api_key}:"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/json',
            'Output-Format': 'JSON'
        }
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Esegue una richiesta HTTP alle API di PrestaShop.
        
        Args:
            method: Metodo HTTP (GET, POST, PUT, DELETE)
            endpoint: Endpoint dell'API (es. '/products' o '/orders')
            data: Dati da inviare nel body (per POST/PUT)
            params: Parametri da aggiungere alla query string
        
        Returns:
            Risposta JSON dall'API
        """
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                params=params,
                timeout=30,
                verify=self.verify_ssl  # Disabilita verifica SSL se necessario
            )
            
            # Solleva un'eccezione per errori HTTP
            response.raise_for_status()
            
            # PrestaShop può restituire XML o JSON
            if response.headers.get('Content-Type', '').startswith('application/json'):
                return response.json()
            else:
                # Se è XML, prova a parsare comunque
                return {'raw_response': response.text}
                
        except requests.exceptions.HTTPError as e:
            error_detail = f"HTTP {e.response.status_code}: {e.response.reason}"
            try:
                error_body = e.response.text[:500]  # Limita a 500 caratteri
                error_detail += f"\nDettagli: {error_body}"
            except:
                pass
            raise Exception(f"Errore nella richiesta API: {error_detail}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Errore nella richiesta API: {str(e)}")
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Esegue una richiesta GET."""
        return self._make_request('GET', endpoint, params=params)
    
    def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Esegue una richiesta POST."""
        return self._make_request('POST', endpoint, data=data)
    
    def put(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Esegue una richiesta PUT."""
        return self._make_request('PUT', endpoint, data=data)
    
    def delete(self, endpoint: str) -> Dict[str, Any]:
        """Esegue una richiesta DELETE."""
        return self._make_request('DELETE', endpoint)
    
    # Metodi di convenienza per risorse comuni
    
    def get_products(self, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Ottiene la lista dei prodotti."""
        return self.get('products', params=params)
    
    def get_product(self, product_id: int) -> Dict[str, Any]:
        """Ottiene un prodotto specifico."""
        return self.get(f'products/{product_id}')
    
    def get_orders(self, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Ottiene la lista degli ordini."""
        return self.get('orders', params=params)
    
    def get_order(self, order_id: int) -> Dict[str, Any]:
        """Ottiene un ordine specifico."""
        return self.get(f'orders/{order_id}')
    
    def get_customers(self, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Ottiene la lista dei clienti."""
        return self.get('customers', params=params)
    
    def get_customer(self, customer_id: int) -> Dict[str, Any]:
        """Ottiene un cliente specifico."""
        return self.get(f'customers/{customer_id}')


# Esempio di utilizzo
if __name__ == "__main__":
    # Configurazione
    API_KEY = "KWYH69WBFHYCC24RZZNN5ANQXG36H1Q6"
    BASE_URL = input("Inserisci l'URL del tuo negozio PrestaShop (es. https://mio-store.com): ").strip()
    
    if not BASE_URL:
        print("Errore: URL del negozio richiesto")
        exit(1)
    
    # Crea il client
    client = PrestaShopClient(BASE_URL, API_KEY)
    
    # Test di connessione
    print(f"\nConnessione a: {BASE_URL}")
    print(f"API Key: {API_KEY[:10]}...")
    
    try:
        # Prova a ottenere le informazioni del negozio
        print("\nTest di connessione in corso...")
        shop_info = client.get('')
        print("✓ Connessione riuscita!")
        print(f"Risposta: {shop_info}")
        
        # Esempio: ottieni i primi prodotti
        print("\n--- Esempio: Lista prodotti ---")
        products = client.get_products({'limit': 5})
        print(products)
        
    except Exception as e:
        print(f"✗ Errore: {str(e)}")
        print("\nVerifica che:")
        print("1. L'URL del negozio sia corretto")
        print("2. L'API key sia valida")
        print("3. L'API REST sia abilitata nel pannello PrestaShop")


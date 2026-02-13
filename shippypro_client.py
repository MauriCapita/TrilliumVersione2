"""
ShippyPro API Client
Client per recuperare informazioni di spedizione da ShippyPro
"""

import requests
from requests.auth import HTTPBasicAuth
from typing import Dict, Any, Optional
import base64


class ShippyProClient:
    """Client per interagire con le API di ShippyPro."""
    
    def __init__(self, api_key: str):
        """
        Inizializza il client ShippyPro.
        
        Args:
            api_key: Chiave API di ShippyPro (usata come username, password vuoto)
        """
        self.api_key = api_key
        # ShippyPro API v1 - non serve specificare /v1 se è la prima versione
        self.base_url = "https://www.shippypro.com/api"
        # ShippyPro usa Basic Auth: username = APIKEY, password vuoto
        self.auth = HTTPBasicAuth(api_key, '')
        self.headers = {
            'Content-Type': 'application/json'
        }
    
    def make_request(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Metodo pubblico per fare richieste API.
        
        Args:
            endpoint: Nome dell'endpoint (es. 'PutOrder', 'Ship', 'Edit')
            data: Dati da inviare nel body
        
        Returns:
            Risposta JSON dall'API
        """
        return self._make_request('POST', endpoint, data=data)
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Esegue una richiesta HTTP alle API di ShippyPro.
        ShippyPro usa POST con Basic Auth e formato JSON con Method e Params.
        
        Args:
            method: Metodo HTTP (solo POST supportato per ShippyPro)
            endpoint: Nome del metodo API (es. 'GetOrder', 'GetShipment', 'GetTracking')
            data: Parametri da inviare (diventeranno 'Params' nel body)
            params: Parametri alternativi (non usati, tutti nel body come 'Params')
        
        Returns:
            Risposta JSON dall'API
        """
        url = self.base_url
        
        # ShippyPro richiede POST con formato JSON: {"Method": "GetOrder", "Params": {...}}
        # I parametri vanno nel campo "Params"
        request_data = {
            "Method": endpoint  # Il nome del metodo API
        }
        
        # Aggiungi i parametri nel campo "Params"
        params_data = {}
        if params:
            params_data.update(params)
        if data:
            params_data.update(data)
        
        if params_data:
            request_data["Params"] = params_data
        
        try:
            # ShippyPro usa sempre POST con Basic Auth
            response = requests.post(
                url, 
                json=request_data, 
                headers=self.headers,
                auth=self.auth,  # Basic Auth: username=APIKEY, password=''
                timeout=30
            )
            
            response.raise_for_status()
            
            # Prova a parsare come JSON
            try:
                return response.json()
            except:
                # Se non è JSON, restituisci il testo
                return {'raw_response': response.text}
                
        except requests.exceptions.HTTPError as e:
            error_detail = f"HTTP {e.response.status_code}: {e.response.reason}"
            try:
                error_body = e.response.text[:500]
                error_detail += f"\nDettagli: {error_body}"
                # Prova a parsare l'errore come JSON
                try:
                    error_json = e.response.json()
                    if 'Error' in error_json:
                        error_detail += f"\nErrore API: {error_json['Error']}"
                except:
                    pass
            except:
                pass
            raise Exception(f"Errore nella richiesta API ShippyPro: {error_detail}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Errore nella richiesta API ShippyPro: {str(e)}")
    
    def get_order(self, order_id: int) -> Dict[str, Any]:
        """
        Recupera informazioni su un ordine usando l'OrderID (deve essere un intero).
        
        Args:
            order_id: ID numerico dell'ordine in ShippyPro
        
        Returns:
            Dati dell'ordine
        """
        return self._make_request('POST', 'GetOrder', data={'OrderID': order_id})
    
    def get_order_by_transaction_id(self, transaction_id: str) -> Dict[str, Any]:
        """
        Cerca un ordine usando TransactionID o shipping_number.
        Prima cerca tra GetPendingOrders.
        
        Args:
            transaction_id: TransactionID o shipping_number
        
        Returns:
            Dati dell'ordine se trovato, altrimenti dict con Error
        """
        # Prova a cercare nei pending orders
        try:
            pending = self.make_request('GetPendingOrders', data={})
            if pending.get('Result') == 'OK' and 'Orders' in pending:
                for order in pending['Orders']:
                    # GetPendingOrders usa 'transaction_id' (minuscolo con underscore)
                    order_trans_id = order.get('transaction_id', '')
                    order_tracking = order.get('tracking_number', '')
                    
                    if (order_trans_id == transaction_id or 
                        order_tracking == transaction_id):
                        # Se abbiamo OrderID, usalo per GetOrder
                        if 'OrderID' in order:
                            return self.get_order(order['OrderID'])
                        # Altrimenti restituisci i dati dell'ordine trovato
                        return {'Result': 'Found', 'Order': order, 'TransactionID': transaction_id}
        except Exception as e:
            return {'Error': f'Error searching pending orders: {str(e)}', 'TransactionID': transaction_id}
        
        return {'Error': 'Order not found in pending orders', 'TransactionID': transaction_id}
    
    def get_shipment(self, transaction_id: str) -> Dict[str, Any]:
        """
        Recupera informazioni su una spedizione usando il TransactionID.
        
        Args:
            transaction_id: ID transazione (shipping_number) della spedizione
        
        Returns:
            Dati della spedizione e tracking
        """
        return self._make_request('POST', 'GetShipment', data={'TransactionID': transaction_id})
    
    def get_tracking(self, tracking_code: str, carrier_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Recupera informazioni di tracking per una spedizione.
        GetTracking richiede 'Code' (non TrackingNumber).
        
        Args:
            tracking_code: Codice di tracking
            carrier_name: Nome del corriere (opzionale)
        
        Returns:
            Informazioni di tracking
        """
        data = {'Code': tracking_code}
        if carrier_name:
            data['CarrierName'] = carrier_name
        
        return self._make_request('POST', 'GetTracking', data=data)


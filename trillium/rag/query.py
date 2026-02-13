import os
from typing import List, Dict, Optional
from openai import OpenAI
from config import (
    PROVIDER,
    LLM_MODEL_OPENAI,
    LLM_MODEL_OPENROUTER,
    LLM_MODEL_ANTHROPIC,
    LLM_MODEL_GEMINI,
    OPENAI_API_KEY,
    OPENROUTER_API_KEY,
    ANTHROPIC_API_KEY,
    GEMINI_API_KEY,
    TOP_K,
    CONTEXT_CHARS_PER_DOC,
    MAX_RESPONSE_TOKENS,
    VECTOR_DB,
)
from rag.indexer import get_chroma, get_vector_db
from rich import print
import re
import sys
import importlib.util

# Importa BASE_URL e API_KEY dalla root del progetto (come in api_integration.py)
try:
    # Calcola il percorso root del progetto
    current_file = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    
    # Carica config.py dalla root usando importlib
    config_path = os.path.join(project_root, 'config.py')
    if os.path.exists(config_path):
        spec = importlib.util.spec_from_file_location("root_config", config_path)
        root_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(root_config)
        BASE_URL = root_config.BASE_URL
        API_KEY = root_config.API_KEY
    else:
        # Fallback: prova import normale
        sys.path.insert(0, project_root)
        from config import BASE_URL, API_KEY
    
    # Importa PrestaShopClient
    sys.path.insert(0, project_root)
    from prestashop_client import PrestaShopClient
except (ImportError, AttributeError) as e:
    # Fallback: usa variabili d'ambiente
    BASE_URL = os.getenv("PRESTSHOP_BASE_URL", "")
    API_KEY = os.getenv("PRESTSHOP_API_KEY", "")
    PrestaShopClient = None
    print(f"[yellow]⚠ Impossibile importare BASE_URL/API_KEY: {e}[/yellow]")


# ============================================================
# CLIENTS
# ============================================================

def get_openai_client():
    return OpenAI(api_key=OPENAI_API_KEY)

def get_openrouter_client():
    return OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1"
    )

def get_anthropic_client():
    try:
        from anthropic import Anthropic
        return Anthropic(api_key=ANTHROPIC_API_KEY)
    except ImportError:
        raise ImportError("Libreria anthropic non installata. Installa con: pip install anthropic")

def get_gemini_client():
    try:
        from google import genai
        # Il client legge automaticamente GEMINI_API_KEY dall'ambiente
        # Se non è nell'ambiente, passalo esplicitamente
        if GEMINI_API_KEY:
            import os
            os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY
        return genai.Client()
    except ImportError:
        raise ImportError("Libreria google-genai non installata. Installa con: pip install google-genai")


# ============================================================
# RICERCA ORDINI TRAMITE API (FALLBACK)
# ============================================================

def search_order_in_apis(question: str) -> Optional[Dict]:
    """
    Cerca ordini specifici nella query tramite API PrestaShop/ShippyPro.
    Rileva ID ordini, riferimenti, o nomi clienti nella domanda.
    
    Args:
        question: La domanda dell'utente
    
    Returns:
        Dict con i dati dell'ordine trovato, o None
    """
    try:
        # Estrai possibili ID ordini o riferimenti dalla query
        # Cerca pattern come: #53515, 53515, VZEKDZDHM, ordine 53515, etc.
        order_patterns = [
            r'#?(\d{4,})',  # ID numerici (almeno 4 cifre)
            r'([A-Z0-9]{8,})',  # Riferimenti alfanumerici (almeno 8 caratteri)
        ]
        
        found_identifiers = []
        for pattern in order_patterns:
            matches = re.findall(pattern, question.upper())
            found_identifiers.extend(matches)
        
        # Cerca anche nomi clienti (pattern: "Michele Bassi", "Bassi Michele", etc.)
        # Pattern migliorati per rilevare nomi con più contesto
        customer_name_patterns = [
            r'(?:intestato\s+a|di|per|cliente|customer|nome)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',  # Con contesto (es: "intestato a Michele Bassi")
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)',  # Nome e cognome semplice (es: "Michele Bassi")
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',  # Pattern originale più flessibile
        ]
        
        customer_names = []
        for pattern in customer_name_patterns:
            matches = re.findall(pattern, question, re.IGNORECASE)
            customer_names.extend(matches)
        
        # Rimuovi duplicati mantenendo l'ordine
        seen = set()
        unique_customer_names = []
        for name in customer_names:
            name_lower = name.lower()
            if name_lower not in seen:
                seen.add(name_lower)
                unique_customer_names.append(name)
        
        # Se non ci sono ID/riferimenti ma c'è un nome cliente, cerca per nome
        if not found_identifiers and unique_customer_names:
            print(f"[cyan]🔍 Rilevato nome cliente nella query: {unique_customer_names[0]}[/cyan]")
            return search_orders_by_customer_name(unique_customer_names[0])
        
        if not found_identifiers:
            return None
        
        # Verifica che PrestaShopClient sia disponibile
        if PrestaShopClient is None:
            print(f"[yellow]⚠ PrestaShopClient non disponibile, impossibile cercare ordini tramite API[/yellow]")
            return None
        
        for identifier in found_identifiers:
            print(f"[cyan]🔍 Cerco ordine '{identifier}' tramite API...[/cyan]")
            
            # Se è alfanumerico (probabilmente un riferimento), prova filtro PrestaShop
            if not identifier.isdigit() and len(identifier) >= 8:
                try:
                    client = PrestaShopClient(BASE_URL, API_KEY)
                    orders = client.get_orders({
                        'display': 'full',
                        'filter[reference]': identifier,
                        'limit': 1
                    })
                    
                    if 'orders' in orders and isinstance(orders['orders'], list) and len(orders['orders']) > 0:
                        order_data = orders['orders'][0]
                        if isinstance(order_data, dict) and order_data.get('reference') == identifier:
                            print(f"[green]✓ Ordine '{identifier}' trovato su PrestaShop tramite riferimento![/green]")
                            return {'order': order_data}
                except Exception as e:
                    print(f"[yellow]⚠ Errore ricerca riferimento '{identifier}': {e}[/yellow]")
            
            # Prova con search_order_with_fallback (cerca per ID o TransactionID)
            try:
                from rag.api_integration import search_order_with_fallback
                order = search_order_with_fallback(identifier)
                if order:
                    print(f"[green]✓ Ordine '{identifier}' trovato tramite API![/green]")
                    return order
            except Exception as e:
                print(f"[yellow]⚠ Errore ricerca ordine '{identifier}': {e}[/yellow]")
                continue
        
        return None
    except Exception as e:
        print(f"[yellow]⚠ Errore ricerca ordini tramite API: {e}[/yellow]")
        return None


def search_orders_by_customer_name(customer_name: str) -> Optional[Dict]:
    """
    Cerca ordini per nome cliente tramite API PrestaShop.
    
    Args:
        customer_name: Nome completo del cliente (es: "Michele Bassi")
    
    Returns:
        Dict con i dati dell'ordine trovato, o None
    """
    try:
        # Verifica che PrestaShopClient sia disponibile
        if PrestaShopClient is None or not BASE_URL or not API_KEY:
            print(f"[yellow]⚠ PrestaShopClient non disponibile o credenziali mancanti[/yellow]")
            return None
        
        print(f"[cyan]🔍 Cerco ordini per cliente '{customer_name}' tramite API PrestaShop...[/cyan]")
        
        # Dividi nome e cognome
        name_parts = customer_name.strip().split()
        if len(name_parts) < 2:
            print(f"[yellow]⚠ Nome cliente incompleto: '{customer_name}'[/yellow]")
            return None
        
        firstname = name_parts[0]
        lastname = ' '.join(name_parts[1:])  # Gestisce cognomi composti
        
        # Cerca clienti per nome
        client = PrestaShopClient(BASE_URL, API_KEY)
        customers_response = client.get_customers({
            'display': 'full',
            'limit': 1000
        })
        
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
                            cust_firstname = customer.get('firstname', '').lower()
                            cust_lastname = customer.get('lastname', '').lower()
                            
                            # Match su nome e cognome
                            if (firstname.lower() in cust_firstname and lastname.lower() in cust_lastname) or \
                               (cust_firstname in firstname.lower() and cust_lastname in lastname.lower()):
                                matching_customers.append(customer)
        
        if not matching_customers:
            print(f"[yellow]⚠ Nessun cliente trovato con nome '{customer_name}'[/yellow]")
            return None
        
        print(f"[green]✓ Trovati {len(matching_customers)} clienti corrispondenti[/green]")
        
        # Per ogni cliente trovato, cerca i suoi ordini
        for customer in matching_customers:
            customer_id = customer.get('id', '')
            if not customer_id:
                continue
            
            print(f"[cyan]  🔍 Cerco ordini per cliente ID {customer_id}...[/cyan]")
            
            # Cerca ordini per ID cliente
            try:
                orders_response = client.get_orders({
                    'display': 'full',
                    'filter[id_customer]': customer_id,
                    'limit': 100
                })
                
                if 'orders' in orders_response and isinstance(orders_response['orders'], list):
                    orders = orders_response['orders']
                    if len(orders) > 0:
                        # Prendi l'ordine più recente o quello che corrisponde meglio
                        order_data = orders[0] if isinstance(orders[0], dict) else None
                        if order_data:
                            print(f"[green]✓ Trovato ordine per cliente '{customer_name}'[/green]")
                            return {'order': order_data}
            except Exception as e:
                print(f"[yellow]⚠ Errore ricerca ordini per cliente {customer_id}: {e}[/yellow]")
                continue
        
        print(f"[yellow]⚠ Nessun ordine trovato per cliente '{customer_name}'[/yellow]")
        return None
        
    except Exception as e:
        print(f"[yellow]⚠ Errore ricerca ordini per nome cliente: {e}[/yellow]")
        import traceback
        traceback.print_exc()
        return None


# ============================================================
# RICERCA RAG
# ============================================================

def retrieve_relevant_docs(query: str):
    """
    Recupera i documenti più rilevanti dal database vettoriale (ChromaDB o Qdrant).
    Prima cerca per matching esatto su ID ordine o riferimento, poi usa ricerca vettoriale.
    Se la query contiene un nome cliente, migliora la ricerca vettoriale.
    
    Returns:
        List[Dict]: Lista di documenti con formato {"id": str, "text": str, "source": str}
    """
    try:
        # Estrai nomi clienti dalla query per migliorare la ricerca
        customer_name_patterns = [
            r'(?:intestato\s+a|di|per|cliente|customer|nome|del\s+mio\s+ordine\s+intestato\s+a)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)',  # Pattern semplice
        ]
        customer_names = []
        for pattern in customer_name_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            customer_names.extend(matches)
        
        # Rimuovi duplicati e filtra nomi troppo comuni
        seen = set()
        unique_customer_names = []
        for name in customer_names:
            name_lower = name.lower()
            if name_lower not in seen and len(name.split()) >= 2 and name_lower not in ['del mio', 'ordine intestato']:
                seen.add(name_lower)
                unique_customer_names.append(name)
        
        # Se c'è un nome cliente, migliora la query vettoriale
        enhanced_query = query
        if unique_customer_names:
            customer_name = unique_customer_names[0]
            # Aggiungi il nome cliente alla query per migliorare la ricerca vettoriale
            enhanced_query = f"{query} cliente {customer_name} ordine PrestaShop"
            print(f"[cyan]🔍 Ricerca migliorata per cliente: {customer_name}[/cyan]")
        
        # Prima: cerca per matching esatto su ID ordine o riferimento
        exact_match_docs = search_exact_order_match(query)
        if exact_match_docs:
            print(f"[green]✓ Trovato ordine per matching esatto: {len(exact_match_docs)} documenti[/green]")
            # Aggiungi anche risultati vettoriali per contesto
            vector_docs = retrieve_vector_docs(enhanced_query)
            # Combina: prima matching esatto, poi vettoriale (evitando duplicati)
            seen_ids = {doc["id"] for doc in exact_match_docs}
            for doc in vector_docs:
                if doc["id"] not in seen_ids:
                    exact_match_docs.append(doc)
                    seen_ids.add(doc["id"])
            return exact_match_docs[:TOP_K]
        
        # Se non trova matching esatto, usa ricerca vettoriale migliorata
        vector_docs = retrieve_vector_docs(enhanced_query)
        
        # Espansione query per domande su analisi laterale + boccola/stazioni/bending (SOP-518 Long Seals)
        q_lower = query.lower()
        lateral_keywords = ("analisi laterale", "lateral analysis")
        component_keywords = ("boccola", "stazioni", "bending", "long seal", "wear ring", "bushing", "posizione", "posizioni")
        is_lateral_station_query = any(k in q_lower for k in lateral_keywords) and any(k in q_lower for k in component_keywords)
        if is_lateral_station_query:
            extra_query = "SOP-518 Long Seals 5.2.3 stazioni posizionamento analisi laterale damped natural frequency boccola bushing"
            extra_docs = retrieve_vector_docs(extra_query)
            if extra_docs:
                seen_ids = {d.get("id") for d in vector_docs}
                for d in extra_docs:
                    if d.get("id") not in seen_ids:
                        vector_docs.insert(0, d)
                        seen_ids.add(d.get("id"))
                print("[cyan]✓ Aggiunti documenti da ricerca estesa (SOP-518 / Long Seals)[/cyan]")
        
        # Se c'è un nome cliente e non trova risultati, prova anche ricerca diretta per nome
        if unique_customer_names and not vector_docs:
            customer_name = unique_customer_names[0]
            print(f"[cyan]🔍 Ricerca diretta per nome cliente nei documenti: {customer_name}[/cyan]")
            # Cerca direttamente nei documenti per nome cliente
            if VECTOR_DB == "qdrant":
                from rag.qdrant_db import get_qdrant_collection
                client, collection_name = get_qdrant_collection()
                
                # Scrolla e cerca per nome cliente
                offset = None
                while True:
                    scroll_result = client.scroll(
                        collection_name=collection_name,
                        limit=1000,
                        offset=offset,
                        with_payload=True,
                        with_vectors=False
                    )
                    points = scroll_result[0]
                    if not points:
                        break
                    
                    for point in points:
                        payload = point.payload if point.payload else {}
                        text = payload.get('text', '').lower()
                        # Cerca nome completo o parti del nome
                        name_parts = customer_name.lower().split()
                        if all(part in text for part in name_parts):
                            vector_docs.append({
                                "id": str(point.id),
                                "text": payload.get('text', ''),
                                "source": payload.get('source', ''),
                                "score": 1.0
                            })
                    
                    offset = scroll_result[1]
                    if offset is None:
                        break
                    
                    if vector_docs:  # Se trovato, esci
                        break
        
        return vector_docs[:TOP_K]
    except Exception as e:
        print(f"[red]❌ Errore durante il recupero documenti: {e}[/red]")
        import traceback
        print(f"[red]Traceback: {traceback.format_exc()}[/red]")
        return []


def search_exact_order_match(query: str) -> List[Dict]:
    """
    Cerca ordini per matching esatto su ID o riferimento usando i metadati (più veloce).
    """
    try:
        # Estrai possibili ID ordini o riferimenti dalla query
        order_patterns = [
            r'#?(\d{4,})',  # ID numerici (almeno 4 cifre)
            r'([A-Z0-9]{8,})',  # Riferimenti alfanumerici (almeno 8 caratteri)
        ]
        
        found_identifiers = []
        for pattern in order_patterns:
            matches = re.findall(pattern, query.upper())
            found_identifiers.extend(matches)
        
        if not found_identifiers:
            return []
        
        all_docs = []
        
        if VECTOR_DB == "qdrant":
            from rag.qdrant_db import get_qdrant_collection
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            client, collection_name = get_qdrant_collection()
            
            # Cerca usando filtri sui metadati (più veloce)
            for identifier in found_identifiers:
                try:
                    # Cerca per order_id nei payload (metadati sono nel payload in Qdrant)
                    # Scrolla e cerca nel payload
                    scroll_result = client.scroll(
                        collection_name=collection_name,
                        limit=5000,  # Limite ragionevole per ricerca
                        with_payload=True,
                        with_vectors=False
                    )
                    
                    for point in scroll_result[0]:
                        payload = point.payload if point.payload else {}
                        text = payload.get('text', '')
                        source = payload.get('source', '')
                        order_id_meta = payload.get('order_id', '')
                        
                        # Cerca per ID numerico
                        if identifier.isdigit():
                            # Cerca nei metadati o nel testo
                            if str(order_id_meta) == identifier:
                                all_docs.append({
                                    "id": str(point.id),
                                    "text": text,
                                    "source": source,
                                    "score": 1.0
                                })
                                break  # Trovato, passa al prossimo identifier
                            # Anche cerca nel testo per sicurezza
                            elif f'ID: {identifier}' in text or f'ID Ordine: {identifier}' in text or f'ORDINE PRESTSHOP - ID: {identifier}' in text:
                                all_docs.append({
                                    "id": str(point.id),
                                    "text": text,
                                    "source": source,
                                    "score": 1.0
                                })
                                break
                        else:
                            # Per riferimenti, cerca nel testo
                            if f'Riferimento: {identifier}' in text or f'Reference: {identifier}' in text:
                                all_docs.append({
                                    "id": str(point.id),
                                    "text": text,
                                    "source": source,
                                    "score": 1.0
                                })
                                break  # Trovato, passa al prossimo identifier
                except Exception as e:
                    print(f"[yellow]⚠ Errore ricerca Qdrant per '{identifier}': {e}[/yellow]")
                    continue
        else:
            # ChromaDB - cerca nei metadati
            collection = get_chroma()
            try:
                for identifier in found_identifiers:
                    if identifier.isdigit():
                        # Cerca per order_id nei metadati
                        results = collection.get(
                            where={"order_id": identifier},
                            limit=10
                        )
                        
                        if results and results.get('ids'):
                            for i, doc_id in enumerate(results['ids']):
                                text = results['documents'][i] if results.get('documents') else ''
                                metadata = results['metadatas'][i] if results.get('metadatas') else {}
                                source = metadata.get('source', '')
                                
                                all_docs.append({
                                    "id": doc_id,
                                    "text": text,
                                    "source": source,
                                    "score": 1.0
                                })
                    else:
                        # Per riferimenti, cerca nel testo
                        all_data = collection.get(limit=1000)
                        if all_data and all_data.get('ids'):
                            for i, doc_id in enumerate(all_data['ids']):
                                text = all_data['documents'][i] if all_data.get('documents') else ''
                                if f'Riferimento: {identifier}' in text or f'Reference: {identifier}' in text:
                                    metadata = all_data['metadatas'][i] if all_data.get('metadatas') else {}
                                    source = metadata.get('source', '')
                                    
                                    all_docs.append({
                                        "id": doc_id,
                                        "text": text,
                                        "source": source,
                                        "score": 1.0
                                    })
                                    break
            except Exception as e:
                print(f"[yellow]⚠ Errore ricerca ChromaDB: {e}[/yellow]")
        
        return all_docs
    except Exception as e:
        print(f"[yellow]⚠ Errore ricerca matching esatto: {e}[/yellow]")
        return []


def retrieve_vector_docs(query: str) -> List[Dict]:
    """
    Recupera documenti usando ricerca vettoriale (similarità semantica).
    """
    try:
        if VECTOR_DB == "qdrant":
            from rag.qdrant_db import qdrant_query
            try:
                docs = qdrant_query(query, n_results=TOP_K)
                # Verifica che docs sia una lista valida
                if docs is None:
                    print("[yellow]⚠ Qdrant ha restituito None[/yellow]")
                    return []
                if not isinstance(docs, list):
                    print(f"[yellow]⚠ Qdrant ha restituito un tipo non valido: {type(docs)}[/yellow]")
                    return []
                # Converti formato Qdrant a formato standard (già fatto in qdrant_query)
                return docs
            except Exception as e:
                print(f"[red]❌ Errore query Qdrant: {e}[/red]")
                import traceback
                print(f"[red]Traceback: {traceback.format_exc()}[/red]")
                return []
        else:
            collection = get_chroma()
            results = collection.query(
                query_texts=[query],
                n_results=TOP_K
            )

            # Verifica che ci siano risultati
            if not results or not results.get("documents") or len(results["documents"][0]) == 0:
                print("[yellow]⚠ Nessun documento trovato in ChromaDB[/yellow]")
                return []

            docs = []
            for i in range(len(results["documents"][0])):
                docs.append({
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "source": results["metadatas"][0][i]["source"]
                })

            return docs
    except Exception as e:
        print(f"[red]❌ Errore durante il recupero documenti vettoriali: {e}[/red]")
        import traceback
        print(f"[red]Traceback: {traceback.format_exc()}[/red]")
        return []


# ============================================================
# COSTRUZIONE DEL CONTESTO PER IL MODELLO
# ============================================================

def build_context(query: str, docs, web_results: Optional[List[Dict]] = None):
    """
    Combina query, documenti recuperati e (opzionalmente) risultati web in un unico contesto.
    
    Args:
        query: La domanda dell'utente
        docs: Documenti recuperati dal database vettoriale
        web_results: Opzionale, risultati da ricerca web
    """
    context_text = "CONTEXT FROM DOCUMENTS:\n"
    seen_sources = []
    for d in docs:
        src = d.get("source", "")
        context_text += f"\n--- SOURCE: {src} ---\n"
        context_text += d["text"][:CONTEXT_CHARS_PER_DOC]  # Limite caratteri per velocità
        context_text += "\n"
        if src and src not in seen_sources:
            seen_sources.append(src)
    
    # Elenco univoco dei riferimenti documento (percorso/URL) per la sezione "da scaricare"
    doc_refs_list = "\n".join([f"- {s}" for s in seen_sources])
    
    # Aggiungi risultati web se disponibili
    web_context = ""
    if web_results:
        from rag.web_search import format_web_results_for_prompt
        web_context = format_web_results_for_prompt(web_results)

    # Rileva se la query riguarda ordini
    is_order_query = any(keyword in query.lower() for keyword in [
        'ordine', 'order', 'spedizione', 'shipment', 'tracking', 'cliente', 'customer',
        'prestashop', 'shippypro', 'consegna', 'delivery', 'fattura', 'invoice'
    ])
    
    # Aggiungi contesto specifico per ordini se rilevato
    order_context = ""
    if is_order_query:
        order_context = """
IMPORTANT: The user is asking about orders, shipments, or customers. The context may include:
- PrestaShop orders (ORDINE PRESTSHOP)
- ShippyPro orders/shipments (ORDINE SHIPPYPRO)
- Customer information, shipping addresses, tracking numbers
- Order status, payment information, product details

When answering questions about orders:
- Provide specific order IDs, transaction IDs, or tracking numbers when available
- Include customer names, addresses, and contact information
- Mention order status, dates, and shipping details
- List products ordered with quantities and prices
- If information is missing, clearly state what is not available
"""
    
    final_prompt = f"""
You are an expert technical assistant specializing in engineering documents, technical calculations, Excel spreadsheets, manufacturing specifications, and order management (PrestaShop and ShippyPro orders).
Your role is to provide extremely detailed, comprehensive, and well-structured explanations that help users understand complex technical content and order information.

{order_context}

Here is the relevant context from the indexed documents and orders:

{context_text}
{web_context}

RIFERIMENTI DOCUMENTI (percorsi/URL da citare nella sezione finale "Riferimenti documenti da scaricare"):
{doc_refs_list}

USER QUESTION:
{query}

CRITICAL INSTRUCTIONS FOR YOUR RESPONSE:

1. STRUCTURE AND DETAIL:
   - Provide a comprehensive, step-by-step explanation that thoroughly addresses the question
   - Use clear sections with numbered points (1️⃣, 2️⃣, etc.) or bullet points for organization
   - Include ALL relevant technical details, formulas, calculations, and procedures found in the documents
   - Explain the "how" and "why" behind each step, not just the "what"
   - For Excel files or calculation sheets, explain the methodology, formulas used, input parameters, and output results
   - Connect different parts of the documents to provide a complete picture

2. TECHNICAL DEPTH:
   - Extract and explain formulas, equations, and mathematical relationships
   - Describe the workflow, process, or calculation methodology in detail
   - Include parameter definitions, units of measurement, and their significance
   - Explain relationships between different variables and how they affect the results
   - Reference specific sections, sheets, or parts of documents when relevant

3. CONTEXT AND SYNTHESIS:
   - If information comes from multiple sources (e.g., SOP document + Excel file), synthesize them into a coherent explanation
   - Show how different documents relate to each other (e.g., "The Excel file implements the method described in SOP-559")
   - If web search results are provided, integrate them with document information, prioritizing document information when available
   - Use web search results to supplement or clarify information from documents, but always prioritize document content
   - Provide background context and explain the purpose/objective of the calculation or procedure
   - Mention related concepts, standards, or methodologies when relevant

4. FORMATTING:
   - Use clear headings, subheadings, and structured formatting
   - Include tables when presenting structured data
   - Use mathematical notation clearly (e.g., ΔP_d, U_2, etc.)
   - Break down complex explanations into digestible sections
   - Use emojis or symbols (🔎, 📊, ⚙️, etc.) to make sections more readable

5. COMPLETENESS:
   - Don't just list facts - explain the reasoning and methodology
   - Include examples or specific values from the documents when available
   - Address potential follow-up questions proactively
   - If the question asks "how to calculate", provide a complete step-by-step procedure
   - If the question asks about a file, explain its purpose, structure, methodology, and usage

6. LANGUAGE:
   - Write in Italian (unless the user asks otherwise)
   - Use technical terminology correctly but explain complex concepts
   - Be conversational yet professional
   - Make the response engaging and easy to follow

7. IF INFORMATION IS MISSING:
   - Clearly state: "Non presente nei documenti indicizzati" for missing information
   - But still provide as much context as possible from what IS available

8. RIFERIMENTI DOCUMENTI DA SCARICARE (OBBLIGATORIO):
   - Alla fine della risposta DEVI includere una sezione "## Riferimenti documenti da scaricare".
   - In questa sezione elenca TUTTI i documenti usati, ciascuno con:
     • Nome/identificativo (es. SOP-521, Mod.497, nome file) e
     • Percorso completo o URL dove trovare/scaricare il documento (copia esattamente dal blocco "RIFERIMENTI DOCUMENTI" sopra).
     • Quando la risposta alla domanda si trova in un paragrafo o sezione specifica, indicarlo esplicitamente (es. "SOP-571 — paragrafo 4.3", "SOP-518 — § 5.2.3 Long Seals").
   - Nella risposta, quando citi un modulo (Mod.xxx) o una SOP, indica sempre dove si trova (percorso/URL) e, se applicabile, il paragrafo o sezione (es. "vedi SOP-571 paragrafo 4.3", "la procedura è in SOP-518 § 5.2.3 Long Seals").
   - Struttura consigliata della risposta:
     (1) Spiegazione riassuntiva di cosa viene calcolato / di cosa tratta la procedura / dove si trova la risposta
     (2) Se applicabile: riferimento al modulo di calcolo (Mod.xxx) con dove trovarlo, istruzioni di utilizzo ed esempio
     (3) Riferimento alla/e SOP o documenti correlate con indicazione del paragrafo dove è la risposta (es. paragrafo 4.3, § 5.2.3) e percorso/link per scaricare
     (4) Tutta la documentazione utilizzata con percorsi e, quando rilevante, paragrafo di riferimento

9. CITAZIONI PARAGRAFO/SEZIONE (OBBLIGATORIO quando applicabile):
   - Se la risposta alla domanda dell'utente è contenuta in un paragrafo o sezione specifica di un documento (es. "non-grout construction" e vincoli in SOP-571 par. 4.3; stazioni bending in SOP-518 § 5.2.3 Long Seals), DEVI:
     • Citare esplicitamente quel paragrafo/sezione nel corpo della risposta (es. "La risposta si trova nel paragrafo 4.3 della SOP-571", "Vedi SOP-518 § 5.2.3 Long Seals").
     • Nella sezione "Riferimenti documenti da scaricare" riportare per quel documento il paragrafo o sezione (es. "SOP-571 — paragrafo 4.3", "SOP-518 — § 5.2.3 Long Seals").
   - Cerca nel testo dei documenti forniti numeri di paragrafo, sezione o titoli (es. "4.3", "5.2.3", "Long Seals") e usali per indicare dove trovare la risposta.

10. QUANDO I DOCUMENTI RECUPERATI SONO POCHI O LA DOMANDA È CONCETTUALE:
   - Anche se il contesto sembra incompleto (es. ricerca "penetration factor" senza risultati diretti), usa TUTTI i documenti forniti per trovare contenuti correlati (altre SOP, normative, moduli).
   - Sintetizza una risposta coerente con la documentazione fornita; se il concetto è trattato in più documenti (es. SOP-460, SOP-557, normative), unisci le informazioni e cita ogni fonte con documento e paragrafo/sezione quando possibile.
   - Fornisci comunque: spiegazione riassuntiva, riferimenti ai documenti utilizzati con percorso/link e paragrafo dove applicabile, e la sezione "Riferimenti documenti da scaricare" con indicazione del paragrafo per ogni documento rilevante.

11. ANALISI LATERALE – POSIZIONAMENTO STAZIONI PER BOCOLA/BUSHING/LONG SEAL (OBBLIGATORIO):
   - Se la domanda riguarda DOVE aggiungere stazioni per l'analisi laterale in presenza di una boccola, bushing, wear ring, long seal o componente lungo (es. pompa BB5, lunghezza/diametro boccola), la risposta corretta si trova in SOP-518 (Level 2 Damped natural frequency analysis), in particolare nel paragrafo 5.2.3 "Long Seals".
   - Cerca nel contesto documenti/chunk che menzionano "SOP-518", "Long Seals", "5.2.3" o "long seal". Se presenti, basati PRINCIPALMENTE su quella sezione per rispondere su dove posizionare le stazioni e cita esplicitamente "SOP-518 § 5.2.3 Long Seals" con il percorso del documento e l'indicazione del paragrafo nella sezione "Riferimenti documenti da scaricare".
   - Se nel contesto trovi solo altri documenti (es. SOP-554 shaft deflection) ma NON SOP-518/Long Seals: fornisci comunque le informazioni utili da quei documenti, ma indica chiaramente che per le regole specifiche sul posizionamento delle stazioni per boccole/long seals la procedura di riferimento è SOP-518 § 5.2.3 Long Seals e che l'utente deve consultare quel documento (aggiungilo ai riferimenti se non già presente, con nota "consigliato per stazioni su long seal/boccola").
   - Non dare per scontato posizioni generiche (es. "estremità e centro") senza aver verificato se nel contesto c'è la regola specifica della SOP-518; se c'è, usala e citarla.

EXAMPLE OF GOOD RESPONSE STRUCTURE:
- Introduction: What the document/file is and its purpose (or where the answer is located, e.g. "La risposta è nel paragrafo 4.3 della SOP-571")
- Objective: What it calculates/does or what the user needs to know
- Methodology / Answer: Step-by-step or detailed explanation; cite paragraph/section when relevant (e.g. "come indicato in SOP-518 § 5.2.3 Long Seals")
- Key Parameters, Formulas, Process: as applicable
- **Riferimenti documenti da scaricare**: list each document with exact path/URL and, when the answer is in a specific section, add "— paragrafo X.Y" or "— § X.Y Titolo sezione"

Remember: Your goal is to provide a response so detailed that the user (1) understands the topic, (2) knows exactly which document and which paragraph/section to open (e.g. SOP-571 par. 4.3, SOP-518 § 5.2.3), and (3) can download or open each document from the path/URL. Be generous with paragraph-level references when the documents contain numbered sections.
"""

    return final_prompt


# ============================================================
# RAGIONAMENTO DI PROFONDITÀ (considerazione originale senza RAG)
# ============================================================

DEPTH_REASONING_HEADER = "\n\n---\n\n### Aggiunta – Ragionamento di profondità\n\n"

def get_depth_reasoning(question: str, provider_override: str = None) -> str:
    """
    Ottiene una considerazione originale e di approfondimento sulla domanda,
    senza contesto RAG (solo la domanda al modello LLM).
    Usato per l'opzione "Ragionamento di profondità" nella chat.
    """
    depth_prompt = f"""Fornisci una considerazione originale e di approfondimento sulla seguente domanda tecnica.
Rispondi in modo conciso ma completo, come riflessione aggiuntiva e ragionamento esteso.
Non fare riferimento a documenti specifici: si tratta di una considerazione autonoma.

DOMANDA:
{question}"""
    try:
        print("[cyan]→ Ragionamento di profondità in corso...[/cyan]")
        out = generate_answer(depth_prompt, provider_override=provider_override)
        if out and not out.strip().startswith("❌"):
            return out.strip()
        return ""
    except Exception as e:
        print(f"[yellow]⚠ Ragionamento di profondità non disponibile: {e}[/yellow]")
        return ""


# ============================================================
# GENERAZIONE RISPOSTA DAL MODELLO SCELTO
# ============================================================

def generate_answer(prompt: str, provider_override: str = None):
    """
    Usa il provider scelto (OpenAI/OpenRouter/Anthropic/Gemini) per generare la risposta.
    
    Args:
        prompt: Il prompt da inviare al modello
        provider_override: Provider da usare per questa query (None = usa PROVIDER da config)
    """
    
    # Usa provider_override se fornito, altrimenti usa quello di default
    provider_to_use = provider_override if provider_override else PROVIDER

    if provider_to_use == "openai":
        if not OPENAI_API_KEY:
            return "❌ Errore: OpenAI API key non configurata. Configura OPENAI_API_KEY nel file .env"
        print("[cyan]→ Uso modello OpenAI[/cyan]")
        client = get_openai_client()
        model = LLM_MODEL_OPENAI
        
        # Verifica che il modello sia valido, altrimenti usa un fallback
        valid_models = ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo", "gpt-5.1"]
        if model not in valid_models and "gpt-4" not in model.lower() and "gpt-3.5" not in model.lower():
            print(f"[yellow]⚠ Modello '{model}' potrebbe non essere valido. Provo comunque...[/yellow]")
        
        # System message più dettagliato per OpenAI (simile a Gemini)
        system_message = """You are an expert technical assistant specializing in engineering documents, technical calculations, Excel spreadsheets, and manufacturing specifications. 

Your role is to provide extremely detailed, comprehensive, and well-structured explanations that help users understand complex technical content.

CRITICAL INSTRUCTIONS:
- Provide step-by-step explanations with clear structure
- Use numbered points (1️⃣, 2️⃣, etc.) or bullet points for organization
- Include ALL relevant technical details, formulas, calculations, and procedures
- Explain the "how" and "why" behind each step, not just the "what"
- For Excel files or calculation sheets, explain methodology, formulas, input parameters, and output results
- Connect different parts of documents to provide a complete picture
- Write in Italian (unless the user asks otherwise)
- Be generous with details - provide comprehensive responses similar to ChatGPT

Remember: Your goal is to provide responses so detailed that the user fully understands the topic."""
        
        # Prepara i parametri della chiamata
        create_params = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,  # Bassa temperatura per risposte più coerenti
        }
        
        # Gestione max_tokens: prova prima max_completion_tokens per modelli nuovi, poi max_tokens
        try:
            if "gpt-5" in model.lower() or "o1" in model.lower():
                # Modelli più recenti potrebbero usare max_completion_tokens
                try:
                    create_params["max_completion_tokens"] = MAX_RESPONSE_TOKENS
                except:
                    create_params["max_tokens"] = MAX_RESPONSE_TOKENS
            else:
                # Modelli standard usano max_tokens
                create_params["max_tokens"] = MAX_RESPONSE_TOKENS
        except:
            # Fallback: usa sempre max_tokens
            create_params["max_tokens"] = MAX_RESPONSE_TOKENS
        
        try:
            print(f"[dim]→ Chiamata API OpenAI con modello: {model}, max_tokens: {create_params.get('max_tokens', create_params.get('max_completion_tokens', 'N/A'))}[/dim]")
            response = client.chat.completions.create(**create_params)
            
            # Debug: mostra informazioni sulla risposta
            print(f"[dim]→ Risposta ricevuta: {len(response.choices) if response.choices else 0} scelte[/dim]")
            
            if response.choices and len(response.choices) > 0:
                choice = response.choices[0]
                content = choice.message.content if choice.message else None
                
                if content:
                    content_stripped = content.strip()
                    if content_stripped:
                        print(f"[green]✓ Risposta generata: {len(content_stripped)} caratteri[/green]")
                        return content_stripped
                    else:
                        print("[yellow]⚠ Risposta vuota dopo strip[/yellow]")
                        return "❌ Errore: La risposta del modello è vuota (dopo strip)."
                else:
                    print("[yellow]⚠ Nessun contenuto nella risposta[/yellow]")
                    # Debug: mostra cosa c'è nella risposta
                    print(f"[dim]→ Debug response: {response.choices[0] if response.choices else 'Nessuna scelta'}[/dim]")
                    return "❌ Errore: La risposta del modello è vuota (nessun content)."
            else:
                print("[yellow]⚠ Nessuna scelta nella risposta[/yellow]")
                return "❌ Errore: Nessuna risposta dal modello OpenAI (nessuna scelta)."
        except Exception as e:
            error_msg = f"❌ Errore chiamata API OpenAI: {str(e)}"
            print(f"[red]{error_msg}[/red]")
            import traceback
            print(f"[red]Traceback completo: {traceback.format_exc()}[/red]")
            
            # Se il modello non è valido, prova con un fallback
            if ("model" in str(e).lower() or "invalid" in str(e).lower() or "not found" in str(e).lower()) and model != "gpt-4o":
                print(f"[yellow]⚠ Modello '{model}' non valido. Provo con fallback 'gpt-4o'...[/yellow]")
                try:
                    create_params_fallback = {
                        "model": "gpt-4o",
                        "messages": [
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": MAX_RESPONSE_TOKENS
                    }
                    response = client.chat.completions.create(**create_params_fallback)
                    if response.choices and len(response.choices) > 0:
                        content = response.choices[0].message.content
                        if content and content.strip():
                            print(f"[green]✓ Fallback riuscito con gpt-4o: {len(content.strip())} caratteri[/green]")
                            return content.strip()
                except Exception as e2:
                    print(f"[red]✗ Anche il fallback è fallito: {e2}[/red]")
            
            # Suggerimento per modelli non validi
            if "model" in str(e).lower() or "invalid" in str(e).lower():
                error_msg += f"\n\n💡 Suggerimento: Il modello '{model}' potrebbe non essere valido. Prova a cambiare LLM_MODEL_OPENAI in config.py con un modello valido come 'gpt-4o' o 'gpt-4-turbo'."
            
            return error_msg
        
    elif provider_to_use == "anthropic":
        if not ANTHROPIC_API_KEY:
            return "❌ Errore: Anthropic API key non configurata. Configura ANTHROPIC_API_KEY nel file .env"
        print("[cyan]→ Uso modello Anthropic (Claude)[/cyan]")
        client = get_anthropic_client()
        model = LLM_MODEL_ANTHROPIC
        
        # Anthropic usa un formato diverso
        try:
            response = client.messages.create(
                model=model,
                max_tokens=MAX_RESPONSE_TOKENS,
                system="You are a knowledgeable technical assistant specializing in engineering documents, technical drawings, and manufacturing specifications. You provide detailed, conversational responses that help users understand complex technical information.",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            if response.content and len(response.content) > 0:
                text = response.content[0].text
                if text:
                    return text.strip()
                else:
                    return "❌ Errore: La risposta del modello è vuota."
            else:
                return "❌ Errore: Nessuna risposta dal modello Anthropic."
        except Exception as e:
            error_msg = f"❌ Errore chiamata API Anthropic: {str(e)}"
            print(f"[red]{error_msg}[/red]")
            return error_msg
        
    elif provider_to_use == "gemini":
        if not GEMINI_API_KEY:
            return "❌ Errore: Gemini API key non configurata. Configura GEMINI_API_KEY nel file .env"
        print("[cyan]→ Uso modello Gemini[/cyan]")
        client = get_gemini_client()
        model = LLM_MODEL_GEMINI
        
        # Gemini usa un formato diverso
        # Combina system message e prompt nel contenuto
        full_content = f"You are a knowledgeable technical assistant specializing in engineering documents, technical drawings, and manufacturing specifications. You provide detailed, conversational responses that help users understand complex technical information.\n\n{prompt}"
        
        try:
            response = client.models.generate_content(
                model=model,
                contents=full_content
            )
            return response.text.strip()
        except Exception as e:
            # Fallback se l'API ha cambiato formato
            error_msg = str(e)
            if "config" in error_msg.lower() or "generate_content" in error_msg.lower():
                # Prova formato alternativo
                try:
                    from google.genai import types
                    response = client.models.generate_content(
                        model=model,
                        contents=full_content,
                        config=types.GenerateContentConfig(
                            temperature=0.3,
                            max_output_tokens=MAX_RESPONSE_TOKENS
                        )
                    )
                    return response.text.strip()
                except:
                    return f"❌ Errore chiamata API Gemini: {error_msg}"
            return f"❌ Errore API Gemini: {error_msg}"
        
    else:  # openrouter
        if not OPENROUTER_API_KEY:
            return "❌ Errore: OpenRouter API key non configurata. Configura OPENROUTER_API_KEY nel file .env"
        print("[cyan]→ Uso modello OpenRouter[/cyan]")
        client = get_openrouter_client()
        model = LLM_MODEL_OPENROUTER

        create_params = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a knowledgeable technical assistant specializing in engineering documents, technical drawings, and manufacturing specifications. You provide detailed, conversational responses that help users understand complex technical information."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": MAX_RESPONSE_TOKENS
        }
        
        try:
            response = client.chat.completions.create(**create_params)
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                if content:
                    return content.strip()
                else:
                    return "❌ Errore: La risposta del modello è vuota."
            else:
                return "❌ Errore: Nessuna risposta dal modello OpenRouter."
        except Exception as e:
            error_msg = f"❌ Errore chiamata API OpenRouter: {str(e)}"
            print(f"[red]{error_msg}[/red]")
            return error_msg


# ============================================================
# FUNZIONE PRINCIPALE DI QUERY RAG
# ============================================================

def rag_query(question: str, provider_override: str = None, use_web_search: bool = False, use_depth_reasoning: bool = False):
    """
    Funzione completa:
    1. Recupera i documenti
    2. (Opzionale) Cerca ordini specifici tramite API se non trovati
    3. (Opzionale) Cerca sul web se richiesto
    4. Costruisce il contesto
    5. Chiama il modello LLM
    6. (Opzionale) Aggiunge in fondo un "Ragionamento di profondità" (considerazione originale senza RAG)
    
    Args:
        question: La domanda dell'utente
        provider_override: Provider LLM da usare (None = usa PROVIDER da config)
        use_web_search: Se True, esegue anche una ricerca web e integra i risultati
        use_depth_reasoning: Se True, aggiunge in fondo una considerazione di approfondimento (LLM senza contesto RAG)
    
    Returns:
        str: La risposta generata dal modello, o un messaggio di errore
    """
    try:
        print("[cyan]→ Recupero documenti rilevanti...[/cyan]")
        docs = retrieve_relevant_docs(question)

        # Estrai nomi clienti dalla query PRIMA di cercare tramite API
        customer_name_patterns = [
            r'(?:intestato\s+a|di|per|cliente|customer|nome|del\s+mio\s+ordine\s+intestato\s+a)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)',  # Pattern semplice per nomi
        ]
        customer_names = []
        for pattern in customer_name_patterns:
            matches = re.findall(pattern, question, re.IGNORECASE)
            customer_names.extend(matches)
        
        # Rimuovi duplicati
        seen = set()
        unique_customer_names = []
        for name in customer_names:
            name_lower = name.lower()
            # Filtra nomi troppo corti o comuni
            if name_lower not in seen and len(name.split()) >= 2 and name_lower not in ['del mio', 'ordine intestato']:
                seen.add(name_lower)
                unique_customer_names.append(name)
        
        # Cerca sempre ordini specifici nella query (anche se ci sono documenti trovati)
        # Questo permette di trovare ordini non ancora indicizzati
        api_order = search_order_in_apis(question)
        
        # Se non trova tramite API ma c'è un nome cliente, cerca per nome cliente
        if not api_order and unique_customer_names:
            customer_name = unique_customer_names[0]
            print(f"[cyan]🔍 Cerco ordini per cliente '{customer_name}' tramite API...[/cyan]")
            api_order = search_orders_by_customer_name(customer_name)
            
            # Se non trova tramite API, cerca anche nei documenti indicizzati
            if not api_order and docs:
                print(f"[cyan]🔍 Cerco ordini per cliente '{customer_name}' nei documenti indicizzati...[/cyan]")
                # Filtra documenti che contengono il nome cliente
                filtered_docs = []
                for doc in docs:
                    text = doc.get('text', '').lower()
                    # Cerca nome completo o parti del nome
                    name_parts = customer_name.lower().split()
                    if all(part in text for part in name_parts):
                        filtered_docs.append(doc)
                
                if filtered_docs:
                    print(f"[green]✓ Trovati {len(filtered_docs)} ordini per cliente '{customer_name}' nei documenti indicizzati[/green]")
                    docs = filtered_docs
        
        if api_order:
            # Crea un documento fittizio con i dati dell'ordine trovato
            from rag.api_integration import format_prestashop_order, format_shippypro_order
            api_doc = None
            
            if api_order.get('order'):
                # Ordine PrestaShop
                order_text = format_prestashop_order(api_order.get('order'))
                api_doc = {
                    "id": f"api_order_{api_order.get('order', {}).get('id', 'unknown')}",
                    "text": order_text,
                    "source": f"PrestaShop Order {api_order.get('order', {}).get('id', 'unknown')} (recuperato via API)"
                }
            elif api_order.get('Order'):
                # Ordine ShippyPro
                order_text = format_shippypro_order(api_order)
                api_doc = {
                    "id": f"api_order_{api_order.get('Order', {}).get('OrderID', 'unknown')}",
                    "text": order_text,
                    "source": f"ShippyPro Order {api_order.get('Order', {}).get('OrderID', 'unknown')} (recuperato via API)"
                }
            
            if api_doc:
                # Aggiungi l'ordine trovato all'inizio della lista (priorità)
                if not docs:
                    docs = []
                docs.insert(0, api_doc)
                print(f"[green]✓ Ordine trovato tramite API e aggiunto al contesto (priorità alta)[/green]")
        
        # Se non trova documenti e nemmeno ordini tramite API
        if not docs or len(docs) == 0:
            return "⚠ Nessun documento rilevante trovato nell'indice. Verifica che i documenti siano stati indicizzati correttamente."

        print(f"[green]✓ Documenti recuperati: {len(docs)} documenti[/green]")

        # Ricerca web opzionale
        web_results = None
        if use_web_search:
            print("[cyan]→ Eseguo ricerca web...[/cyan]")
            try:
                from rag.web_search import search_web
                web_results = search_web(question, max_results=5)
                if web_results:
                    print(f"[green]✓ Risultati web trovati: {len(web_results)} risultati[/green]")
                else:
                    print("[yellow]⚠ Nessun risultato web trovato[/yellow]")
            except Exception as e:
                print(f"[yellow]⚠ Errore ricerca web: {e}[/yellow]")
                web_results = None

        prompt = build_context(question, docs, web_results=web_results)

        print("[cyan]→ Genero la risposta dal modello...[/cyan]")
        answer = generate_answer(prompt, provider_override=provider_override)
        
        # Verifica che la risposta non sia vuota
        if not answer or answer.strip() == "":
            return "❌ Errore: La risposta generata dal modello è vuota. Verifica la configurazione del provider LLM e le chiavi API."

        # Opzionale: aggiunta "Ragionamento di profondità" (considerazione originale senza RAG)
        if use_depth_reasoning:
            depth_text = get_depth_reasoning(question, provider_override=provider_override)
            if depth_text:
                answer = answer + DEPTH_REASONING_HEADER + depth_text

        return answer
        
    except Exception as e:
        error_msg = f"❌ Errore durante la generazione della risposta: {str(e)}"
        print(f"[red]{error_msg}[/red]")
        import traceback
        print(f"[red]Traceback: {traceback.format_exc()}[/red]")
        return error_msg


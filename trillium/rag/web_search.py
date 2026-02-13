"""
Funzione di ricerca web per integrare informazioni dal web nelle risposte RAG
"""
import os
from typing import List, Dict, Optional

def search_web(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Cerca informazioni sul web usando DuckDuckGo (gratuito, senza API key).
    
    Args:
        query: La query di ricerca
        max_results: Numero massimo di risultati da restituire
    
    Returns:
        List[Dict]: Lista di risultati con formato {"title": str, "snippet": str, "url": str}
    """
    try:
        # Prova prima con duckduckgo-search (più moderno)
        try:
            from duckduckgo_search import DDGS
            
            results = []
            with DDGS() as ddgs:
                # Cerca risultati
                search_results = ddgs.text(query, max_results=max_results)
                
                for result in search_results:
                    results.append({
                        "title": result.get("title", ""),
                        "snippet": result.get("body", ""),
                        "url": result.get("href", "")
                    })
            
            return results
            
        except ImportError:
            # Fallback: usa requests + BeautifulSoup per scraping diretto
            try:
                import requests
                from urllib.parse import quote_plus
                
                # DuckDuckGo HTML search (senza librerie esterne)
                search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                
                response = requests.get(search_url, headers=headers, timeout=10)
                response.raise_for_status()
                
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                results = []
                # DuckDuckGo HTML ha una struttura specifica
                for result in soup.find_all('div', class_='result', limit=max_results):
                    title_elem = result.find('a', class_='result__a')
                    snippet_elem = result.find('a', class_='result__snippet')
                    
                    if title_elem:
                        results.append({
                            "title": title_elem.get_text(strip=True),
                            "snippet": snippet_elem.get_text(strip=True) if snippet_elem else "",
                            "url": title_elem.get('href', '')
                        })
                
                return results
                
            except ImportError:
                print("[yellow]⚠ Librerie per ricerca web non installate. Installa con: pip install duckduckgo-search[/yellow]")
                return []
            except Exception as e:
                print(f"[yellow]⚠ Errore ricerca web (fallback): {e}[/yellow]")
                return []
                
    except Exception as e:
        print(f"[yellow]⚠ Errore ricerca web: {e}[/yellow]")
        return []


def format_web_results_for_prompt(web_results: List[Dict[str, str]]) -> str:
    """
    Formatta i risultati web per includerli nel prompt del modello.
    
    Args:
        web_results: Lista di risultati web
    
    Returns:
        str: Testo formattato da includere nel prompt
    """
    if not web_results:
        return ""
    
    formatted = "\n\nADDITIONAL CONTEXT FROM WEB SEARCH:\n"
    formatted += "=" * 50 + "\n"
    
    for i, result in enumerate(web_results, 1):
        formatted += f"\n[{i}] {result.get('title', 'N/A')}\n"
        formatted += f"URL: {result.get('url', 'N/A')}\n"
        formatted += f"Content: {result.get('snippet', 'N/A')}\n"
        formatted += "-" * 50 + "\n"
    
    return formatted

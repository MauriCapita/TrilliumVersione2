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
    USE_RERANKING,
    USE_HYBRID_SEARCH,
)
from rag.indexer import get_chroma, get_vector_db
from prompts import SYSTEM_MESSAGE, build_context_prompt, format_chat_history
from sop_mod_mapping import enrich_context_with_mappings
from query_rewriter import rewrite_query
from reranker import rerank_documents
from search_filters import filter_docs_by_type, filter_docs_by_sop_range, hybrid_rerank
from semantic_cache import cache_get, cache_set
from context_compressor import compress_context
from query_decomposer import decompose_query, merge_docs, should_decompose
from hyde import hyde_search
from query_router import classify_query
from relevance_feedback import apply_relevance_boosts
from rich import print
import re
import time as _time


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
# RICERCA RAG
# ============================================================

def retrieve_relevant_docs(query: str, metadata_filters: dict = None):
    """
    Recupera i documenti più rilevanti dal database vettoriale (ChromaDB o Qdrant).
    
    Args:
        query: La domanda dell'utente
        metadata_filters: Filtri opzionali sui metadati (pump_family, doc_type, etc.)
    
    Returns:
        List[Dict]: Lista di documenti con formato {"id": str, "text": str, "source": str}
    """
    try:
        # Query augmentation: arricchisci con sinonimi e codici documento
        # dal file domain_context.md (approccio 2)
        augmented_query = query
        try:
            from context_loader import augment_query
            augmented_query = augment_query(query)
            if augmented_query != query:
                print(f"[dim]  Query augmented con contesto di dominio[/dim]")
        except Exception:
            pass  # Se il modulo non è disponibile, usa la query originale

        # Usa ricerca vettoriale
        vector_docs = retrieve_vector_docs(augmented_query, metadata_filters=metadata_filters)
        
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
        
        return vector_docs[:TOP_K]
    except Exception as e:
        print(f"[red]❌ Errore durante il recupero documenti: {e}[/red]")
        import traceback
        print(f"[red]Traceback: {traceback.format_exc()}[/red]")
        return []





def retrieve_vector_docs(query: str, metadata_filters: dict = None) -> List[Dict]:
    """
    Recupera documenti usando ricerca vettoriale (similarità semantica).
    
    Args:
        query: Testo della query
        metadata_filters: Filtri opzionali sui metadati Qdrant
    """
    try:
        if VECTOR_DB == "qdrant":
            from rag.qdrant_db import qdrant_query
            try:
                docs = qdrant_query(query, n_results=TOP_K, filters=metadata_filters)
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


def retrieve_parent_chunks(docs: list, n_adjacent: int = 1) -> list:
    """
    Per ogni documento recuperato, aggiunge i chunk adiacenti (prima e dopo)
    per dare all'LLM più contesto.
    """
    if not docs:
        return docs

    try:
        if VECTOR_DB == "qdrant":
            return docs  # Qdrant: parent retrieval richiede query per chunk_id, skip per ora

        collection = get_chroma()
        enhanced = list(docs)
        seen_ids = {d.get("id", "") for d in docs}

        for doc in docs:
            doc_id = doc.get("id", "")
            source = doc.get("source", "")
            if not doc_id or not source:
                continue

            # Estrai indice chunk dal doc_id (formato: hash_chunkN)
            match = re.search(r"_chunk(\d+)$", doc_id)
            if not match:
                continue
            chunk_idx = int(match.group(1))
            base_id = doc_id[:match.start()]

            # Cerca chunk adiacenti
            for offset in range(-n_adjacent, n_adjacent + 1):
                if offset == 0:
                    continue
                adjacent_id = f"{base_id}_chunk{chunk_idx + offset}"
                if adjacent_id in seen_ids:
                    continue
                try:
                    result = collection.get(ids=[adjacent_id], include=["documents", "metadatas"])
                    if result and result["documents"] and result["documents"][0]:
                        enhanced.append({
                            "id": adjacent_id,
                            "text": result["documents"][0],
                            "source": result["metadatas"][0].get("source", source) if result["metadatas"] and result["metadatas"][0] else source,
                            "_parent": True,
                        })
                        seen_ids.add(adjacent_id)
                except Exception:
                    pass

        return enhanced
    except Exception:
        return docs


def generate_answer_stream(prompt: str, provider_override: str = None):
    """
    Versione streaming di generate_answer.
    Yield token per token per output in tempo reale.
    """
    provider_to_use = provider_override if provider_override else PROVIDER

    if provider_to_use == "openai":
        if not OPENAI_API_KEY:
            yield "Errore: OpenAI API key non configurata."
            return
        client = get_openai_client()
        model = LLM_MODEL_OPENAI

        try:
            stream = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_MESSAGE},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=MAX_RESPONSE_TOKENS,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"Errore streaming: {e}"

    elif provider_to_use == "anthropic":
        if not ANTHROPIC_API_KEY:
            yield "Errore: Anthropic API key non configurata."
            return
        client = get_anthropic_client()
        try:
            with client.messages.stream(
                model=LLM_MODEL_ANTHROPIC,
                max_tokens=MAX_RESPONSE_TOKENS,
                system=SYSTEM_MESSAGE,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except Exception as e:
            yield f"Errore streaming: {e}"

    else:
        # Fallback: non-streaming
        answer = generate_answer(prompt, provider_override)
        yield answer


# ============================================================
# COSTRUZIONE DEL CONTESTO PER IL MODELLO
# ============================================================

def build_context(query: str, docs, web_results: Optional[List[Dict]] = None,
                  user_role: str = "admin", chat_history: list = None):
    """
    Combina query, documenti recuperati e (opzionalmente) risultati web in un unico contesto.
    Usa i prompt modulari da prompts.py e i mapping SOP↔Mod da sop_mod_mapping.py.
    """
    # Costruisci contesto con etichette [DOC-N] per citazioni inline
    context_text = ""
    seen_sources = []
    for i, d in enumerate(docs, 1):
        src = d.get("source", "")
        context_text += f"\n--- [DOC-{i}]: {src} ---\n"
        context_text += d["text"][:CONTEXT_CHARS_PER_DOC]
        context_text += "\n"
        if src and src not in seen_sources:
            seen_sources.append(src)

    # Elenco univoco dei riferimenti documento
    doc_refs_list = "\n".join([f"- {s}" for s in seen_sources])

    # Mapping SOP↔Mod per i documenti recuperati
    doc_mappings = enrich_context_with_mappings(docs)

    # Risultati web opzionali
    web_context = ""
    if web_results:
        from rag.web_search import format_web_results_for_prompt
        web_context = format_web_results_for_prompt(web_results)

    # Formatta storia conversazione per multi-turno
    chat_history_text = format_chat_history(chat_history) if chat_history else ""

    return build_context_prompt(
        query=query,
        context_text=context_text,
        doc_refs_list=doc_refs_list,
        doc_mappings=doc_mappings,
        web_context=web_context,
        user_role=user_role,
        chat_history_text=chat_history_text,
    )


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
        
        # System message centralizzato da prompts.py
        system_message = SYSTEM_MESSAGE
        
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
                system=SYSTEM_MESSAGE,
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
        full_content = f"{SYSTEM_MESSAGE}\n\n{prompt}"
        
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
                {"role": "system", "content": SYSTEM_MESSAGE},
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

def rag_query(question: str, provider_override: str = None, use_web_search: bool = False,
              use_depth_reasoning: bool = False, user_role: str = "admin",
              chat_history: list = None, search_filters: dict = None,
              stream: bool = False):
    """
    Pipeline RAG completa con tutte le ottimizzazioni:
    1. Cache semantica (hit → risposta immediata)
    2. Query decomposition (per domande complesse)
    3. Query rewriting
    4. Document retrieval + parent chunks
    5. Filtri metadata
    6. Ricerca ibrida + Re-ranking
    7. Context compression
    8. Generazione risposta (streaming o batch)
    9. Timing di ogni fase
    
    Args:
        question: La domanda dell'utente
        provider_override: Provider LLM
        use_web_search: Ricerca web
        use_depth_reasoning: Approfondimento
        user_role: Ruolo utente
        chat_history: Storia conversazione
        search_filters: Filtri tipo/SOP
        stream: Se True, restituisce un generatore per streaming
    
    Returns:
        Se stream=False: tuple (answer: str, timing: dict)
        Se stream=True: tuple (generator, timing: dict) - timing parziale (pre-LLM)
    """
    timing = {}
    t_start = _time.time()

    try:
        # 1. Cache semantica
        t0 = _time.time()
        cached = cache_get(question, search_filters)
        timing["cache_lookup"] = round(_time.time() - t0, 3)
        if cached:
            answer, cached_docs = cached
            timing["total"] = round(_time.time() - t_start, 3)
            timing["cache_hit"] = True
            print(f"[green]✓ Cache HIT → risposta immediata ({timing['total']}s)[/green]")
            if stream:
                def _cached_gen():
                    yield answer
                return _cached_gen(), timing
            return answer, timing
        timing["cache_hit"] = False

        # 2. Query routing — determina strategia ottimale
        t0 = _time.time()
        route = classify_query(question)
        timing["routing"] = round(_time.time() - t0, 3)
        print(f"[dim]  Routing: {route['type']} (BM25={route['bm25_weight']})[/dim]")

        # Merge filtri dalla route con quelli UI
        if route.get("doc_filter") and not search_filters:
            search_filters = route["doc_filter"]

        # 3. Query decomposition (se route lo suggerisce o se è complessa)
        t0 = _time.time()
        if route.get("should_decompose"):
            sub_queries = decompose_query(question)
        else:
            sub_queries = [question]
        timing["decomposition"] = round(_time.time() - t0, 3)
        if len(sub_queries) > 1:
            print(f"[cyan]→ Query decomposta in {len(sub_queries)} sotto-query[/cyan]")

        # 4. Query rewriting + retrieval per ogni sotto-query
        t0 = _time.time()
        # Estrai smart filters per Qdrant (pump_family, doc_type, etc.)
        metadata_filters = None
        if search_filters:
            mf = {}
            for key in ["pump_family", "doc_type", "has_weight", "flange_rating", "material"]:
                if key in search_filters and search_filters[key]:
                    mf[key] = search_filters[key]
            if mf:
                metadata_filters = mf
                print(f"[cyan]🎯 Smart filters attivi: {mf}[/cyan]")

        all_docs_lists = []
        for sq in sub_queries:
            rewritten = rewrite_query(sq)
            # HyDE: se abilitato per questa route, usa documento ipotetico
            if route.get("hyde_enabled", False):
                docs = hyde_search(rewritten, retrieve_vector_docs)
            else:
                docs = retrieve_relevant_docs(rewritten, metadata_filters=metadata_filters)
            if docs:
                all_docs_lists.append(docs)

        # Merge risultati
        if len(all_docs_lists) > 1:
            docs = merge_docs(all_docs_lists)
        elif all_docs_lists:
            docs = all_docs_lists[0]
        else:
            docs = []
        timing["retrieval"] = round(_time.time() - t0, 3)

        if not docs:
            msg = "⚠ Nessun documento rilevante trovato."
            if stream:
                def _empty_gen():
                    yield msg
                return _empty_gen(), timing
            return msg, timing

        # 5. Parent document retrieval
        t0 = _time.time()
        docs = retrieve_parent_chunks(docs, n_adjacent=1)
        timing["parent_retrieval"] = round(_time.time() - t0, 3)

        # 6. Filtri metadata (legacy — basati su nome file)
        t0 = _time.time()
        if search_filters:
            doc_types = search_filters.get("doc_types", [])
            if doc_types:
                docs = filter_docs_by_type(docs, doc_types)
            sop_min = search_filters.get("sop_min")
            sop_max = search_filters.get("sop_max")
            if sop_min is not None and sop_max is not None:
                docs = filter_docs_by_sop_range(docs, sop_min, sop_max)
        timing["filtering"] = round(_time.time() - t0, 3)

        if not docs:
            msg = "⚠ Nessun documento trovato con i filtri selezionati."
            if stream:
                def _no_filter_gen():
                    yield msg
                return _no_filter_gen(), timing
            return msg, timing

        # 7. Ricerca ibrida (con peso BM25 dalla route) + Re-ranking
        t0 = _time.time()
        if USE_HYBRID_SEARCH:
            docs = hybrid_rerank(question, docs, bm25_weight=route["bm25_weight"])
        if USE_RERANKING and len(docs) > 2:
            docs = rerank_documents(question, docs)
        # 7b. Relevance feedback boost
        docs = apply_relevance_boosts(docs)
        timing["reranking"] = round(_time.time() - t0, 3)

        # 8. Context compression
        t0 = _time.time()
        docs = compress_context(question, docs)
        timing["compression"] = round(_time.time() - t0, 3)

        print(f"[green]✓ Pipeline pre-LLM: {len(docs)} docs in {round(_time.time() - t_start, 2)}s[/green]")

        # Ricerca web opzionale
        web_results = None
        if use_web_search:
            try:
                from rag.web_search import search_web
                web_results = search_web(question, max_results=5)
            except Exception:
                pass

        prompt = build_context(question, docs, web_results=web_results,
                              user_role=user_role, chat_history=chat_history)

        # 8. Generazione risposta
        t0 = _time.time()
        if stream:
            # Streaming: restituisci generatore + timing parziale
            timing["pre_llm_total"] = round(_time.time() - t_start, 3)
            
            def _stream_wrapper():
                full_answer = []
                for token in generate_answer_stream(prompt, provider_override):
                    full_answer.append(token)
                    yield token
                # Salva in cache alla fine dello stream
                complete = "".join(full_answer)
                cache_set(question, complete, docs)
            
            return _stream_wrapper(), timing

        # Non-streaming
        answer = generate_answer(prompt, provider_override=provider_override)
        timing["llm_generation"] = round(_time.time() - t0, 3)

        if not answer or answer.strip() == "":
            answer = "Errore: risposta vuota dal modello."

        # Depth reasoning
        if use_depth_reasoning:
            depth_text = get_depth_reasoning(question, provider_override=provider_override)
            if depth_text:
                answer = answer + DEPTH_REASONING_HEADER + depth_text

        # Salva in cache
        cache_set(question, answer, docs)
        
        timing["total"] = round(_time.time() - t_start, 3)
        print(f"[green]✓ Risposta completa in {timing['total']}s[/green]")
        return answer, timing

    except Exception as e:
        error_msg = f"Errore: {str(e)}"
        print(f"[red]{error_msg}[/red]")
        timing["total"] = round(_time.time() - t_start, 3)
        if stream:
            def _err_gen():
                yield error_msg
            return _err_gen(), timing
        return error_msg, timing


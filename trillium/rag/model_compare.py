from openai import OpenAI
from rag.indexer import get_chroma
from rag.query import retrieve_relevant_docs, build_context
from config import (
    OPENAI_API_KEY,
    OPENROUTER_API_KEY,
    ANTHROPIC_API_KEY,
    GEMINI_API_KEY,
    LLM_MODEL_ANTHROPIC,
    LLM_MODEL_GEMINI,
    MAX_RESPONSE_TOKENS
)
from rich.table import Table
from rich.console import Console
from rich import print

console = Console()


# ============================================================
# CLIENTS
# ============================================================

def get_openai_client():
    return OpenAI(api_key=OPENAI_API_KEY)

def get_openrouter_client():
    return OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")


# ============================================================
# LISTA MODELLI PER CONFRONTO
# ============================================================

MODEL_LIST = {
    "GPT-5.1 (OpenAI)": {
        "provider": "openai",
        "model": "gpt-5.1",
    },
    "Claude 3.5 Sonnet (Anthropic)": {
        "provider": "anthropic",
        "model": LLM_MODEL_ANTHROPIC
    },
    "Gemini 2.5 Flash (Google)": {
        "provider": "gemini",
        "model": LLM_MODEL_GEMINI
    }
}


# ============================================================
# GENERA RISPOSTA MODELLO INDIVIDUALE
# ============================================================

def run_model(provider, model, prompt):
    """
    Esegue una chiamata al modello specificato (OpenAI / Anthropic / Gemini / OpenRouter).
    """

    # Controlla se le chiavi API sono presenti
    if provider == "openai":
        if not OPENAI_API_KEY:
            return f"❌ Errore: OpenAI API key non configurata per {model}"
    elif provider == "anthropic":
        if not ANTHROPIC_API_KEY:
            return f"❌ Errore: Anthropic API key non configurata per {model}"
    elif provider == "gemini":
        if not GEMINI_API_KEY:
            return f"❌ Errore: Gemini API key non configurata per {model}"
    elif provider == "openrouter":
        if not OPENROUTER_API_KEY:
            return f"❌ Errore: OpenRouter API key non configurata per {model}"

    try:
        if provider == "openai":
            client = get_openai_client()
            create_params = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a knowledgeable technical assistant specializing in engineering documents, technical drawings, and manufacturing specifications. You provide detailed, conversational responses."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
            }
            if "gpt-5" in model.lower():
                create_params["max_completion_tokens"] = MAX_RESPONSE_TOKENS
            else:
                create_params["max_tokens"] = MAX_RESPONSE_TOKENS
            response = client.chat.completions.create(**create_params)
            return response.choices[0].message.content.strip()
            
        elif provider == "anthropic":
            from anthropic import Anthropic
            client = Anthropic(api_key=ANTHROPIC_API_KEY)
            response = client.messages.create(
                model=model,
                max_tokens=MAX_RESPONSE_TOKENS,
                system="You are a knowledgeable technical assistant specializing in engineering documents, technical drawings, and manufacturing specifications. You provide detailed, conversational responses.",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            return response.content[0].text.strip()
            
        elif provider == "gemini":
            from google import genai
            import os
            if GEMINI_API_KEY:
                os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY
            client = genai.Client()
            full_content = f"You are a knowledgeable technical assistant specializing in engineering documents, technical drawings, and manufacturing specifications. You provide detailed, conversational responses.\n\n{prompt}"
            response = client.models.generate_content(
                model=model,
                contents=full_content
            )
            return response.text.strip()
            
        else:  # openrouter
            client = get_openrouter_client()
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a knowledgeable technical assistant specializing in engineering documents, technical drawings, and manufacturing specifications. You provide detailed, conversational responses."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=MAX_RESPONSE_TOKENS
            )
            return response.choices[0].message.content.strip()

    except Exception as e:
        return f"❌ Errore modello {model}: {e}"


# ============================================================
# CONFRONTO MULTI-MODELLO
# ============================================================

def compare_models(question: str):
    """
    Passi:
    1. Recupero documenti RAG
    2. Costruisco contesto comune
    3. Interrogo tutti i modelli
    4. Mostro tabella comparativa
    """

    print("[cyan]→ Recupero documenti per confronto...[/cyan]")
    docs = retrieve_relevant_docs(question)

    if not docs:
        return "⚠ Nessun documento trovato per confronto modelli."

    prompt = build_context(question, docs)

    results = {}

    print("[green]✓ Documenti pronti, confronto modelli in corso...[/green]")

    for model_name, cfg in MODEL_LIST.items():
        print(f"[cyan]→ Modello: {model_name}[/cyan]")
        answer = run_model(cfg["provider"], cfg["model"], prompt)
        results[model_name] = answer

    # ============================================
    # TABELLONE DI CONFRONTO
    # ============================================

    table = Table(title="Confronto Risposte Modelli LLM")

    table.add_column("Modello", style="bold magenta")
    table.add_column("Risposta", style="white", overflow="fold")

    for model_name, answer in results.items():
        table.add_row(model_name, answer)

    console.print(table)

    return results


import os
import sys
from rag.indexer import index_folder, reset_database
from rag.query import rag_query, retrieve_relevant_docs, build_context, generate_answer
from rag.model_compare import compare_models
from config import PROVIDER, CHROMA_DB_PATH, VECTOR_DB
from rich import print

# ============================================================
# GENERAZIONE DOMANDE DI FOLLOW-UP
# ============================================================

def generate_follow_up_questions(original_question: str, answer: str, conversation_history: list):
    """
    Genera domande di approfondimento basate sulla domanda originale e la risposta.
    """
    from config import OPENAI_API_KEY, OPENROUTER_API_KEY, LLM_MODEL_OPENAI, LLM_MODEL_OPENROUTER
    from openai import OpenAI
    
    # Controlla quale provider usare
    if PROVIDER == "openai":
        if not OPENAI_API_KEY:
            return ["Non posso generare domande: OpenAI API key non configurata"]
        client = OpenAI(api_key=OPENAI_API_KEY)
        model = LLM_MODEL_OPENAI
    else:
        if not OPENROUTER_API_KEY:
            return ["Non posso generare domande: OpenRouter API key non configurata"]
        client = OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")
        model = LLM_MODEL_OPENROUTER
    
    # Costruisci il prompt per generare domande di follow-up
    history_text = "\n".join([f"{'Utente' if msg['role'] == 'user' else 'Assistente'}: {msg['content'][:200]}..." 
                              for msg in conversation_history[-4:]])  # Ultime 4 interazioni
    
    prompt = f"""Sei un assistente che aiuta a esplorare argomenti tecnici in modo approfondito.

DOMANDA ORIGINALE: {original_question}

RISPOSTA DATA: {answer[:500]}...

STORIA CONVERSAZIONE RECENTE:
{history_text}

Genera 3-4 domande di approfondimento brevi e specifiche (massimo 15 parole ciascuna) che aiuterebbero l'utente a:
- Approfondire dettagli tecnici menzionati nella risposta
- Esplorare aspetti correlati
- Chiarire punti specifici
- Ottenere informazioni aggiuntive utili

Rispondi SOLO con le domande, una per riga, senza numerazione, senza spiegazioni, senza prefissi.
Ogni domanda deve essere completa e comprensibile da sola."""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates follow-up questions to help users explore technical topics in depth."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=200
        )
        
        questions_text = response.choices[0].message.content.strip()
        # Estrai le domande (una per riga)
        questions = [q.strip() for q in questions_text.split('\n') if q.strip() and len(q.strip()) > 10]
        
        # Limita a 4 domande
        return questions[:4] if questions else [
            "Puoi darmi più dettagli su questo argomento?",
            "Ci sono altre specifiche tecniche correlate?",
            "Come si applica questo nella pratica?"
        ]
        
    except Exception as e:
        # Fallback: domande generiche
        return [
            "Puoi darmi più dettagli su questo argomento?",
            "Ci sono altre specifiche tecniche correlate?",
            "Come si applica questo nella pratica?"
        ]


# ============================================================
# MENU PRINCIPALE
# ============================================================

def print_menu():
    print("\n[bold cyan]=== MENU PRINCIPALE ===[/bold cyan]")
    print("1) Indicizza una cartella locale")
    print("2) Indicizza da SharePoint/OneDrive (URL)")
    print("3) Fai una domanda (RAG)")
    print("4) Confronta modelli (RAG + LLM multipli)")
    print("5) Reset database RAG")
    print("6) Mostra configurazione attuale")
    print("7) Esci")
    print()


# ============================================================
# MAIN LOOP
# ============================================================

def main():
    # Supporto per argomenti da linea di comando
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "index" and len(sys.argv) > 2:
            folder = sys.argv[2]
            # Supporta sia percorsi locali che URL SharePoint/OneDrive
            if os.path.exists(folder) or folder.startswith("http://") or folder.startswith("https://"):
                index_folder(folder)
            else:
                print(f"[red]Percorso non valido: {folder}[/red]")
            return
        
        elif command == "query" and len(sys.argv) > 2:
            question = " ".join(sys.argv[2:])
            answer = rag_query(question)
            print("\n[bold green]Risposta:[/bold green]")
            print(answer)
            return
        
        elif command == "compare" and len(sys.argv) > 2:
            question = " ".join(sys.argv[2:])
            compare_models(question)
            return
        
        elif command == "config":
            from config import ANTHROPIC_API_KEY, OPENAI_API_KEY, OPENROUTER_API_KEY, GEMINI_API_KEY
            print("\n[bold cyan]CONFIGURAZIONE ATTUALE[/bold cyan]")
            print(f"Provider LLM: [bold yellow]{PROVIDER}[/bold yellow]")
            print(f"Path database ChromaDB: [bold yellow]{CHROMA_DB_PATH}[/bold yellow]")
            if PROVIDER == "openai":
                key_status = "✓ Configurata" if OPENAI_API_KEY else "✗ Non configurata"
                print(f"OpenAI API Key: [bold yellow]{key_status}[/bold yellow]")
            elif PROVIDER == "anthropic":
                key_status = "✓ Configurata" if ANTHROPIC_API_KEY else "✗ Non configurata"
                print(f"Anthropic API Key: [bold yellow]{key_status}[/bold yellow]")
            elif PROVIDER == "gemini":
                key_status = "✓ Configurata" if GEMINI_API_KEY else "✗ Non configurata"
                print(f"Gemini API Key: [bold yellow]{key_status}[/bold yellow]")
            elif PROVIDER == "openrouter":
                key_status = "✓ Configurata" if OPENROUTER_API_KEY else "✗ Non configurata"
                print(f"OpenRouter API Key: [bold yellow]{key_status}[/bold yellow]")
            return
        
        elif command == "reset":
            reset_database()
            return
        
        else:
            print("[yellow]Uso: python app.py [index|query|compare|config|reset] [argomenti][/yellow]")
            print("[yellow]Oppure esegui senza argomenti per il menu interattivo[/yellow]")
            return
    
    # Modalità interattiva
    while True:
        try:
            print_menu()
            choice = input("Scelta: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[yellow]Uscita...[/yellow]")
            break

        # -------------------------------------------
        # 1) INDICIZZAZIONE CARTELLA LOCALE
        # -------------------------------------------
        if choice == "1":
            try:
                folder = input("Percorso cartella locale da indicizzare: ").strip()
                if os.path.exists(folder):
                    index_folder(folder)
                else:
                    print("[red]Percorso non valido[/red]")
            except (EOFError, KeyboardInterrupt):
                print("\n[yellow]Operazione annullata[/yellow]")
                continue

        # -------------------------------------------
        # 2) INDICIZZAZIONE DA SHAREPOINT/ONEDRIVE
        # -------------------------------------------
        elif choice == "2":
            try:
                url = input("URL SharePoint/OneDrive da indicizzare: ").strip()
                if url.startswith("http://") or url.startswith("https://"):
                    index_folder(url)
                else:
                    print("[red]URL non valido. Deve iniziare con http:// o https://[/red]")
            except (EOFError, KeyboardInterrupt):
                print("\n[yellow]Operazione annullata[/yellow]")
                continue

        # -------------------------------------------
        # 3) QUERY RAG CONVERSATIONALE (stile ChatGPT)
        # -------------------------------------------
        elif choice == "3":
            try:
                print("\n[bold cyan]💬 Modalità Chat RAG - Scrivi 'stop' per tornare al menu[/bold cyan]\n")
                
                # Mostra provider disponibili e chiedi quale usare
                from config import OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY
                available_providers = []
                
                if OPENAI_API_KEY:
                    available_providers.append(("1", "openai", "OpenAI (GPT-5.1)"))
                if ANTHROPIC_API_KEY:
                    available_providers.append(("2", "anthropic", "Anthropic (Claude 3.5 Sonnet)"))
                if GEMINI_API_KEY:
                    available_providers.append(("3", "gemini", "Google Gemini (2.5 Flash)"))
                if OPENROUTER_API_KEY:
                    available_providers.append(("4", "openrouter", "OpenRouter (Claude/Gemini)"))
                
                if not available_providers:
                    print("[red]❌ Nessun provider LLM configurato. Configura almeno una chiave API nel file .env[/red]")
                    continue
                
                print("[bold]Scegli quale LLM usare per questa sessione:[/bold]")
                for num, _, name in available_providers:
                    print(f"  {num}) {name}")
                
                selected_provider = None
                while selected_provider is None:
                    try:
                        choice_provider = input("\n👉 Scelta LLM (numero o Enter per default): ").strip()
                        if not choice_provider:
                            # Usa provider di default
                            selected_provider = PROVIDER
                            print(f"[cyan]Uso provider di default: {PROVIDER}[/cyan]\n")
                            break
                        
                        # Cerca per numero
                        for num, provider, name in available_providers:
                            if choice_provider == num:
                                selected_provider = provider
                                print(f"[green]✓ Selezionato: {name}[/green]\n")
                                break
                        
                        if selected_provider is None:
                            print("[yellow]Scelta non valida. Riprova.[/yellow]")
                    except (EOFError, KeyboardInterrupt):
                        print("\n[yellow]Operazione annullata[/yellow]")
                        return
                
                conversation_history = []
                first_question = True
                
                while True:
                    # Input utente
                    if first_question:
                        user_input = input("Tu: ").strip()
                        first_question = False
                    else:
                        user_input = input("\nTu: ").strip()
                    
                    # Controlla se vuole uscire
                    exit_phrases = ["stop", "basta", "fine", "esci", "exit", "quit", "menu"]
                    if user_input.lower() in exit_phrases:
                        print("\n[green]Torno al menu principale...[/green]")
                        break
                    
                    if not user_input:
                        continue
                    
                    # Fai la query RAG con il provider selezionato
                    print("\n[cyan]🤔 Cerco nei documenti...[/cyan]")
                    answer = rag_query(user_input, provider_override=selected_provider)
                    
                    # Mostra risposta
                    print("\n[bold green]Assistente:[/bold green]")
                    print(answer)
                    
                    # Aggiorna la storia della conversazione
                    conversation_history.append({"role": "user", "content": user_input})
                    conversation_history.append({"role": "assistant", "content": answer})
                    
                    # Suggerisci domande di follow-up (opzionale, ogni 2-3 scambi)
                    if len(conversation_history) % 4 == 0:  # Ogni 2 domande
                        try:
                            follow_ups = generate_follow_up_questions(
                                user_input, 
                                answer, 
                                conversation_history[-4:]  # Ultime 2 interazioni
                            )
                            if follow_ups and len(follow_ups) > 0:
                                print("\n[dim]💡 Suggerimenti:[/dim]")
                                for i, q in enumerate(follow_ups[:2], 1):  # Solo 2 suggerimenti
                                    print(f"  [dim]{i}) {q}[/dim]")
                        except:
                            pass  # Ignora errori nei suggerimenti
                    
            except (EOFError, KeyboardInterrupt):
                print("\n[yellow]Chat interrotta. Torno al menu...[/yellow]")
                continue

        # -------------------------------------------
        # 4) CONFRONTO MODELLI
        # -------------------------------------------
        elif choice == "4":
            try:
                question = input("Domanda da confrontare sui modelli: ").strip()
                compare_models(question)
            except (EOFError, KeyboardInterrupt):
                print("\n[yellow]Operazione annullata[/yellow]")
                continue

        # -------------------------------------------
        # 5) RESET DATABASE
        # -------------------------------------------
        elif choice == "5":
            try:
                confirm = input("Confermi cancellazione database (si/no)? ")
                if confirm.lower() == "si":
                    reset_database()
                else:
                    print("[yellow]Operazione annullata[/yellow]")
            except (EOFError, KeyboardInterrupt):
                print("\n[yellow]Operazione annullata[/yellow]")
                continue

        # -------------------------------------------
        # 6) MOSTRA CONFIGURAZIONE
        # -------------------------------------------
        elif choice == "6":
            from config import ANTHROPIC_API_KEY, OPENAI_API_KEY, OPENROUTER_API_KEY, GEMINI_API_KEY
            print("\n[bold cyan]CONFIGURAZIONE ATTUALE[/bold cyan]")
            print(f"Provider LLM: [bold yellow]{PROVIDER}[/bold yellow]")
            print(f"Database vettoriale: [bold yellow]{VECTOR_DB.upper()}[/bold yellow]")
            if VECTOR_DB == "chromadb":
                print(f"Path database ChromaDB: [bold yellow]{CHROMA_DB_PATH}[/bold yellow]")
            else:
                from config import QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION_NAME
                print(f"Qdrant Host: [bold yellow]{QDRANT_HOST}:{QDRANT_PORT}[/bold yellow]")
                print(f"Qdrant Collection: [bold yellow]{QDRANT_COLLECTION_NAME}[/bold yellow]")
            print("\n[bold]Chiavi API:[/bold]")
            if PROVIDER == "openai":
                key_status = "✓ Configurata" if OPENAI_API_KEY else "✗ Non configurata"
                print(f"  OpenAI API Key: [bold yellow]{key_status}[/bold yellow]")
            elif PROVIDER == "anthropic":
                key_status = "✓ Configurata" if ANTHROPIC_API_KEY else "✗ Non configurata"
                print(f"  Anthropic API Key: [bold yellow]{key_status}[/bold yellow]")
            elif PROVIDER == "gemini":
                key_status = "✓ Configurata" if GEMINI_API_KEY else "✗ Non configurata"
                print(f"  Gemini API Key: [bold yellow]{key_status}[/bold yellow]")
            elif PROVIDER == "openrouter":
                key_status = "✓ Configurata" if OPENROUTER_API_KEY else "✗ Non configurata"
                print(f"  OpenRouter API Key: [bold yellow]{key_status}[/bold yellow]")

        # -------------------------------------------
        # 7) USCITA
        # -------------------------------------------
        elif choice == "7":
            print("[green]Uscita...[/green]")
            break

        else:
            print("[red]Scelta non valida[/red]")


# ============================================================
# AVVIO PROGRAMMA
# ============================================================

if __name__ == "__main__":
    main()


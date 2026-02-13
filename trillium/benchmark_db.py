#!/usr/bin/env python3
"""
Script di benchmark per testare le performance di ChromaDB
e valutare se un cambio database sarebbe utile
"""

import time
import statistics
from rag.indexer import get_chroma
from rag.query import retrieve_relevant_docs
from config import TOP_K
from rich.console import Console
from rich.table import Table
from rich import print

console = Console()

def benchmark_query(query_text: str, num_tests: int = 10):
    """Testa la velocità delle query"""
    print(f"\n[bold cyan]🔍 Benchmark Query: '{query_text}'[/bold cyan]")
    print(f"Eseguendo {num_tests} test...\n")
    
    times = []
    for i in range(num_tests):
        start = time.time()
        docs = retrieve_relevant_docs(query_text)
        elapsed = time.time() - start
        times.append(elapsed * 1000)  # Converti in ms
        print(f"  Test {i+1}/{num_tests}: {elapsed*1000:.2f}ms - Trovati {len(docs)} documenti")
    
    avg_time = statistics.mean(times)
    median_time = statistics.median(times)
    min_time = min(times)
    max_time = max(times)
    std_dev = statistics.stdev(times) if len(times) > 1 else 0
    
    return {
        "avg": avg_time,
        "median": median_time,
        "min": min_time,
        "max": max_time,
        "std_dev": std_dev,
        "times": times
    }

def get_database_stats():
    """Ottiene statistiche sul database"""
    try:
        collection = get_chroma()
        all_data = collection.get()
        
        num_docs = len(all_data["ids"])
        
        # Calcola dimensione approssimativa
        total_chars = sum(len(doc) for doc in all_data["documents"])
        
        # Conta chunk
        chunk_count = sum(1 for meta in all_data["metadatas"] if "chunk" in meta)
        unique_docs = num_docs - chunk_count
        
        return {
            "total_entries": num_docs,
            "unique_documents": unique_docs,
            "chunks": chunk_count,
            "total_chars": total_chars,
            "avg_chars_per_doc": total_chars / num_docs if num_docs > 0 else 0
        }
    except Exception as e:
        print(f"[red]Errore recupero statistiche: {e}[/red]")
        return None

def benchmark_insertion():
    """Testa la velocità di inserimento (simulato)"""
    print(f"\n[bold cyan]📝 Benchmark Inserimento[/bold cyan]")
    print("Nota: Questo è un test teorico basato sulle dimensioni del database\n")
    
    stats = get_database_stats()
    if not stats:
        return None
    
    # Stima basata su dimensioni
    if stats["total_entries"] == 0:
        print("[yellow]⚠ Database vuoto - impossibile stimare performance inserimento[/yellow]")
        return None
    
    # ChromaDB tipicamente impiega 20-100ms per inserimento
    estimated_insert_time = 50  # ms (stima conservativa)
    
    return {
        "estimated_ms": estimated_insert_time,
        "docs_per_second": 1000 / estimated_insert_time
    }

def print_results(query_results, insert_results, stats):
    """Stampa i risultati in una tabella"""
    
    table = Table(title="📊 Benchmark Performance ChromaDB", show_header=True, header_style="bold magenta")
    
    table.add_column("Metrica", style="cyan", width=30)
    table.add_column("Valore", style="green", width=25)
    table.add_column("Note", style="yellow", width=40)
    
    # Statistiche Database
    if stats:
        table.add_row("📚 Documenti totali", f"{stats['total_entries']}", "Inclusi chunk")
        table.add_row("📄 Documenti unici", f"{stats['unique_documents']}", "Senza chunk")
        table.add_row("🧩 Chunk", f"{stats['chunks']}", "Documenti divisi")
        table.add_row("📝 Caratteri totali", f"{stats['total_chars']:,}", "Testo indicizzato")
        table.add_row("", "", "")
    
    # Performance Query
    if query_results:
        table.add_row("⚡ Query - Media", f"{query_results['avg']:.2f}ms", "Tempo medio")
        table.add_row("⚡ Query - Mediana", f"{query_results['median']:.2f}ms", "Tempo mediano")
        table.add_row("⚡ Query - Min", f"{query_results['min']:.2f}ms", "Migliore")
        table.add_row("⚡ Query - Max", f"{query_results['max']:.2f}ms", "Peggiore")
        table.add_row("⚡ Query - Dev. Std", f"{query_results['std_dev']:.2f}ms", "Variabilità")
        table.add_row("", "", "")
    
    # Performance Inserimento
    if insert_results:
        table.add_row("📥 Inserimento stimato", f"{insert_results['estimated_ms']:.2f}ms", "Per documento")
        table.add_row("📥 Velocità inserimento", f"{insert_results['docs_per_second']:.1f} doc/s", "Throughput")
        table.add_row("", "", "")
    
    # Raccomandazioni
    if query_results:
        avg = query_results['avg']
        if avg < 50:
            recommendation = "✅ Eccellente - Nessun cambio necessario"
        elif avg < 100:
            recommendation = "✅ Buono - Cambio opzionale"
        elif avg < 200:
            recommendation = "⚠️  Accettabile - Considera Qdrant"
        elif avg < 500:
            recommendation = "⚠️  Lento - Cambia a Qdrant/FAISS"
        else:
            recommendation = "❌ Molto lento - Cambia database!"
        
        table.add_row("💡 Raccomandazione", recommendation, "Basata su performance")
    
    console.print(table)
    
    # Confronto teorico
    if query_results:
        print("\n[bold cyan]📈 Confronto Teorico con Altri Database:[/bold cyan]\n")
        
        comp_table = Table(show_header=True, header_style="bold")
        comp_table.add_column("Database", style="cyan")
        comp_table.add_column("Tempo Stimato", style="green")
        comp_table.add_column("Miglioramento", style="yellow")
        
        current_time = query_results['avg']
        
        comp_table.add_row("ChromaDB (Attuale)", f"{current_time:.2f}ms", "Baseline")
        comp_table.add_row("Qdrant", f"{current_time * 0.3:.2f}ms", f"~{current_time * 0.7:.0f}ms più veloce (3x)")
        comp_table.add_row("Weaviate", f"{current_time * 0.4:.2f}ms", f"~{current_time * 0.6:.0f}ms più veloce (2.5x)")
        comp_table.add_row("FAISS (RAM)", f"{current_time * 0.1:.2f}ms", f"~{current_time * 0.9:.0f}ms più veloce (10x)")
        comp_table.add_row("Milvus", f"{current_time * 0.2:.2f}ms", f"~{current_time * 0.8:.0f}ms più veloce (5x)")
        
        console.print(comp_table)

def main():
    print("[bold green]🚀 Benchmark Performance Database RAG[/bold green]\n")
    
    # Statistiche database
    print("[cyan]📊 Analisi database...[/cyan]")
    stats = get_database_stats()
    
    if not stats or stats["total_entries"] == 0:
        print("[red]❌ Database vuoto! Indicizza prima alcuni documenti.[/red]")
        print("[yellow]💡 Usa: python app.py index <cartella>[/yellow]")
        return
    
    print(f"[green]✓ Database contiene {stats['total_entries']} voci[/green]\n")
    
    # Test query
    test_queries = [
        "pressione",
        "temperatura",
        "calcolo"
    ]
    
    all_query_results = []
    for query in test_queries:
        try:
            results = benchmark_query(query, num_tests=5)
            all_query_results.append(results)
        except Exception as e:
            print(f"[red]Errore test query '{query}': {e}[/red]")
    
    # Media di tutti i test
    if all_query_results:
        avg_query_time = statistics.mean([r['avg'] for r in all_query_results])
        query_results = {
            "avg": avg_query_time,
            "median": statistics.median([r['median'] for r in all_query_results]),
            "min": min([r['min'] for r in all_query_results]),
            "max": max([r['max'] for r in all_query_results]),
            "std_dev": statistics.mean([r['std_dev'] for r in all_query_results])
        }
    else:
        query_results = None
    
    # Test inserimento
    insert_results = benchmark_insertion()
    
    # Stampa risultati
    print_results(query_results, insert_results, stats)
    
    print("\n[bold green]✅ Benchmark completato![/bold green]")

if __name__ == "__main__":
    main()


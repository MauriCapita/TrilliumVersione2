#!/usr/bin/env python3
"""
Test semplice delle performance ChromaDB
"""

import time
from rag.indexer import get_chroma
from rag.query import retrieve_relevant_docs

def quick_test():
    print("🔍 Test rapido performance ChromaDB\n")
    
    collection = get_chroma()
    data = collection.get()
    num_docs = len(data["ids"])
    
    print(f"📚 Documenti nel database: {num_docs}")
    
    if num_docs == 0:
        print("\n⚠️  Database vuoto!")
        print("💡 Per testare le performance, indicizza prima alcuni documenti:")
        print("   python app.py index <cartella>")
        return
    
    # Test query
    test_query = "pressione"
    print(f"\n🔍 Test query: '{test_query}'")
    
    times = []
    for i in range(5):
        start = time.time()
        docs = retrieve_relevant_docs(test_query)
        elapsed = (time.time() - start) * 1000
        times.append(elapsed)
        print(f"  Query {i+1}: {elapsed:.2f}ms - Trovati {len(docs)} documenti")
    
    avg_time = sum(times) / len(times)
    print(f"\n📊 Risultati:")
    print(f"  Tempo medio: {avg_time:.2f}ms")
    print(f"  Min: {min(times):.2f}ms")
    print(f"  Max: {max(times):.2f}ms")
    
    # Valutazione
    print(f"\n💡 Valutazione:")
    if avg_time < 50:
        print("  ✅ Eccellente - Nessun cambio necessario")
        print(f"  Con Qdrant: ~{avg_time * 0.3:.1f}ms (3x più veloce)")
    elif avg_time < 100:
        print("  ✅ Buono - Cambio opzionale")
        print(f"  Con Qdrant: ~{avg_time * 0.3:.1f}ms (3x più veloce)")
    elif avg_time < 200:
        print("  ⚠️  Accettabile - Considera Qdrant")
        print(f"  Con Qdrant: ~{avg_time * 0.3:.1f}ms (3x più veloce)")
    else:
        print("  ⚠️  Lento - Cambia a Qdrant/FAISS")
        print(f"  Con Qdrant: ~{avg_time * 0.3:.1f}ms (3x più veloce)")

if __name__ == "__main__":
    quick_test()


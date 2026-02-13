#!/usr/bin/env python3
"""
Script per forzare il salvataggio del database RAM su disco
"""

from rag.indexer import _save_ram_to_disk, _ram_collection, get_chroma

print("💾 Forzo salvataggio database RAM su disco...\n")

# Forza inizializzazione se non già fatto
if _ram_collection is None:
    collection = get_chroma()
    print("✅ Collection inizializzata")

if _ram_collection:
    try:
        data = _ram_collection.get()
        num_docs = len(data["ids"])
        print(f"📚 Documenti in RAM: {num_docs}")
        
        if num_docs > 0:
            _save_ram_to_disk()
            print(f"✅ Salvati {num_docs} documenti su disco")
        else:
            print("⚠️  RAM vuota - nessun documento da salvare")
    except Exception as e:
        print(f"❌ Errore: {e}")
        import traceback
        traceback.print_exc()
else:
    print("⚠️  Collection RAM non disponibile")


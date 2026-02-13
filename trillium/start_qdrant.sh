#!/bin/bash
# Script per avviare Qdrant

echo "🚀 Avvio Qdrant..."

# Verifica se Docker è in esecuzione
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker non è in esecuzione!"
    echo "   Avvia Docker Desktop e riprova."
    exit 1
fi

# Verifica se Qdrant è già in esecuzione
if docker ps | grep -q qdrant; then
    echo "✅ Qdrant è già in esecuzione"
    docker ps | grep qdrant
else
    # Avvia Qdrant
    echo "📦 Avvio container Qdrant..."
    docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant
    
    # Attendi che sia pronto
    echo "⏳ Attendo che Qdrant sia pronto..."
    sleep 3
    
    # Verifica
    if curl -s http://localhost:6333/health > /dev/null; then
        echo "✅ Qdrant avviato e pronto!"
        echo "   Dashboard: http://localhost:6333/dashboard"
    else
        echo "⚠️  Qdrant potrebbe non essere ancora pronto. Attendi qualche secondo."
    fi
fi


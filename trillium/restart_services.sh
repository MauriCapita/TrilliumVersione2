#!/bin/bash
# Script per riavviare tutti i servizi del sistema Trillium RAG

echo "🔄 Riavvio servizi Trillium RAG System..."
echo ""

# Colori per output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Funzione per fermare processi
stop_service() {
    local service_name=$1
    local pattern=$2
    
    echo -e "${YELLOW}⏹️  Fermo $service_name...${NC}"
    
    # Cerca processi
    pids=$(pgrep -f "$pattern" 2>/dev/null)
    
    if [ -n "$pids" ]; then
        echo "$pids" | xargs kill -9 2>/dev/null
        echo -e "${GREEN}✓ $service_name fermato${NC}"
    else
        echo -e "${YELLOW}⚠ $service_name non era in esecuzione${NC}"
    fi
}

# 1. Ferma Streamlit
stop_service "Streamlit" "streamlit.*streamlit_app.py"

# 2. Ferma Qdrant (se usato)
if docker ps | grep -q qdrant 2>/dev/null; then
    echo -e "${YELLOW}⏹️  Fermo Qdrant...${NC}"
    docker stop qdrant 2>/dev/null
    docker rm qdrant 2>/dev/null
    echo -e "${GREEN}✓ Qdrant fermato${NC}"
else
    echo -e "${YELLOW}⚠ Qdrant non era in esecuzione${NC}"
fi

echo ""
echo -e "${GREEN}✅ Tutti i servizi sono stati fermati${NC}"
echo ""
echo "Per riavviare i servizi:"
echo "  1. Qdrant: ./start_qdrant.sh"
echo "  2. Streamlit: ./run_streamlit.sh"
echo ""
echo "Oppure esegui: ./start_all_services.sh (se esiste)"
echo ""


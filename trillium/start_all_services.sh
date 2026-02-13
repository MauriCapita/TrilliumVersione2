#!/bin/bash
# Script per avviare tutti i servizi del sistema Trillium RAG

echo "🚀 Avvio servizi Trillium RAG System..."
echo ""

# Colori per output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Verifica che siamo nella directory corretta
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 1. Avvia Qdrant (se configurato per usarlo)
echo -e "${BLUE}📦 Verifica configurazione database...${NC}"
if grep -q 'VECTOR_DB.*qdrant' config.py 2>/dev/null || [ "$VECTOR_DB" = "qdrant" ]; then
    echo -e "${YELLOW}🔄 Avvio Qdrant...${NC}"
    if [ -f "./start_qdrant.sh" ]; then
        bash ./start_qdrant.sh
    else
        echo -e "${RED}❌ Script start_qdrant.sh non trovato${NC}"
    fi
    echo ""
else
    echo -e "${GREEN}✓ Usando ChromaDB (non serve Qdrant)${NC}"
    echo ""
fi

# 2. Avvia Streamlit
echo -e "${BLUE}🌐 Avvio Streamlit...${NC}"
if [ -f "./run_streamlit.sh" ]; then
    echo -e "${GREEN}✓ Avvio interfaccia Streamlit...${NC}"
    echo -e "${YELLOW}   L'app sarà disponibile su: http://localhost:8501${NC}"
    echo ""
    bash ./run_streamlit.sh
else
    echo -e "${RED}❌ Script run_streamlit.sh non trovato${NC}"
    echo -e "${YELLOW}   Avvio manuale di Streamlit...${NC}"
    streamlit run streamlit_app.py --server.port 8501 --server.address localhost
fi


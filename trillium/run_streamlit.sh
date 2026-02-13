#!/bin/bash
# Script per avviare l'applicazione Streamlit

echo "🚀 Avvio Trillium RAG System - Interfaccia Streamlit"
echo ""

# Verifica che streamlit sia installato
if ! command -v streamlit &> /dev/null; then
    echo "❌ Streamlit non trovato. Installazione in corso..."
    pip install streamlit plotly
fi

# Avvia l'app
streamlit run streamlit_app.py --server.port 8501 --server.address localhost

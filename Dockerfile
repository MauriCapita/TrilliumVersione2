FROM python:3.10-slim

# Installa dipendenze di sistema (tesseract per OCR)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-ita \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Directory di lavoro
WORKDIR /app

# Copia requirements e installa dipendenze Python
COPY trillium/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il codice dell'app (tutti i moduli di V2)
COPY trillium/ .

# Esponi la porta Streamlit
EXPOSE 8501

# Healthcheck
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Avvia Streamlit
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]

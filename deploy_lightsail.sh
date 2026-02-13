#!/bin/bash
# Script di deploy automatico per AWS Lightsail
# Utilizzo: sudo bash deploy_lightsail.sh

set -e  # Exit on error

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Deploy su AWS Lightsail - Trillium RAG System"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Colori
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Verifica che lo script sia eseguito come root o con sudo
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Questo script deve essere eseguito come root o con sudo${NC}"
    exit 1
fi

# 1. Aggiorna sistema
echo -e "${BLUE}📦 Aggiornamento sistema...${NC}"
apt update
apt upgrade -y

# 2. Installa dipendenze base
echo -e "${BLUE}📦 Installazione dipendenze...${NC}"
apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    wget \
    docker.io \
    docker-compose \
    nginx \
    certbot \
    python3-certbot-nginx \
    ufw \
    htop \
    nano

# 3. Configura Docker
echo -e "${BLUE}🐳 Configurazione Docker...${NC}"
systemctl enable docker
systemctl start docker
usermod -aG docker ubuntu 2>/dev/null || usermod -aG docker $SUDO_USER

# 4. Crea utente per applicazione
echo -e "${BLUE}👤 Creazione utente applicazione...${NC}"
if ! id "appuser" &>/dev/null; then
    useradd -m -s /bin/bash appuser
    echo -e "${GREEN}✓ Utente appuser creato${NC}"
else
    echo -e "${YELLOW}⚠ Utente appuser già esistente${NC}"
fi

# 5. Crea directory applicazione
echo -e "${BLUE}📁 Creazione directory applicazione...${NC}"
APP_DIR="/home/appuser/app"
mkdir -p $APP_DIR
chown appuser:appuser $APP_DIR

# 6. Chiedi URL repository Git
echo -e "${YELLOW}📥 Inserisci l'URL del repository Git (o premi Enter per saltare):${NC}"
read -r GIT_REPO

if [ -n "$GIT_REPO" ]; then
    echo -e "${BLUE}📥 Clonazione repository...${NC}"
    sudo -u appuser bash <<EOF
cd $APP_DIR
git clone $GIT_REPO .
EOF
    echo -e "${GREEN}✓ Repository clonato${NC}"
else
    echo -e "${YELLOW}⚠ Repository non specificato. Dovrai caricare i file manualmente in $APP_DIR${NC}"
fi

# 7. Crea virtual environment
echo -e "${BLUE}🐍 Creazione virtual environment...${NC}"
sudo -u appuser bash <<EOF
cd $APP_DIR
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
EOF
echo -e "${GREEN}✓ Virtual environment creato${NC}"

# 8. Installa dipendenze Python
echo -e "${BLUE}📦 Installazione dipendenze Python...${NC}"
if [ -f "$APP_DIR/requirements.txt" ]; then
    sudo -u appuser bash <<EOF
cd $APP_DIR
source venv/bin/activate
pip install -r requirements.txt
EOF
    echo -e "${GREEN}✓ Dipendenze root installate${NC}"
fi

if [ -f "$APP_DIR/trillium/requirements.txt" ]; then
    sudo -u appuser bash <<EOF
cd $APP_DIR
source venv/bin/activate
pip install -r trillium/requirements.txt
EOF
    echo -e "${GREEN}✓ Dipendenze Trillium installate${NC}"
fi

# 9. Configura .env
echo -e "${BLUE}⚙️  Configurazione variabili ambiente...${NC}"
if [ -f "$APP_DIR/.env.example" ]; then
    sudo -u appuser cp $APP_DIR/.env.example $APP_DIR/.env
    echo -e "${YELLOW}⚠ Modifica $APP_DIR/.env con le tue credenziali!${NC}"
else
    echo -e "${YELLOW}⚠ File .env.example non trovato. Crea manualmente $APP_DIR/.env${NC}"
fi

# 10. Avvia Qdrant (se docker-compose.yml esiste)
echo -e "${BLUE}🗄️  Configurazione Qdrant...${NC}"
if [ -f "$APP_DIR/docker-compose.yml" ]; then
    cd $APP_DIR
    docker-compose up -d
    echo -e "${GREEN}✓ Qdrant avviato${NC}"
else
    echo -e "${YELLOW}⚠ docker-compose.yml non trovato. Qdrant non verrà avviato${NC}"
fi

# 11. Crea servizio systemd per Flask
echo -e "${BLUE}🔧 Creazione servizio systemd Flask...${NC}"
cat > /etc/systemd/system/flask-app.service <<EOF
[Unit]
Description=Flask PrestaShop Dashboard
After=network.target

[Service]
Type=simple
User=appuser
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/python $APP_DIR/app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 12. Crea servizio systemd per Streamlit
echo -e "${BLUE}🔧 Creazione servizio systemd Streamlit...${NC}"
cat > /etc/systemd/system/streamlit-app.service <<EOF
[Unit]
Description=Streamlit Trillium RAG
After=network.target

[Service]
Type=simple
User=appuser
WorkingDirectory=$APP_DIR/trillium
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 13. Abilita e avvia servizi
echo -e "${BLUE}🚀 Avvio servizi...${NC}"
systemctl daemon-reload
systemctl enable flask-app streamlit-app
systemctl start flask-app streamlit-app
echo -e "${GREEN}✓ Servizi avviati${NC}"

# 14. Configura Nginx
echo -e "${BLUE}🌐 Configurazione Nginx...${NC}"
cat > /etc/nginx/sites-available/app <<EOF
server {
    listen 80;
    server_name _;

    # Flask Dashboard
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Streamlit RAG
    location /rag {
        proxy_pass http://localhost:8501;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
EOF

# Abilita compressione
sed -i '/http {/a\    gzip on;\n    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;' /etc/nginx/nginx.conf

ln -sf /etc/nginx/sites-available/app /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx
echo -e "${GREEN}✓ Nginx configurato${NC}"

# 15. Configura firewall
echo -e "${BLUE}🔥 Configurazione firewall...${NC}"
ufw --force enable
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
echo -e "${GREEN}✓ Firewall configurato${NC}"

# 16. Ottieni IP pubblico
PUBLIC_IP=$(curl -s ifconfig.me || curl -s ipinfo.io/ip)

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ Deploy completato con successo!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🌐 Accesso applicazione:"
echo "   • Flask Dashboard: http://$PUBLIC_IP/"
echo "   • Streamlit RAG: http://$PUBLIC_IP/rag"
echo ""
echo "📋 Prossimi passi:"
echo "   1. Modifica $APP_DIR/.env con le tue credenziali"
echo "   2. Riavvia i servizi: sudo systemctl restart flask-app streamlit-app"
echo "   3. Configura dominio e SSL: sudo certbot --nginx -d yourdomain.com"
echo ""
echo "🔍 Verifica stato servizi:"
echo "   • sudo systemctl status flask-app"
echo "   • sudo systemctl status streamlit-app"
echo "   • sudo systemctl status nginx"
echo ""
echo "📝 Log servizi:"
echo "   • sudo journalctl -u flask-app -f"
echo "   • sudo journalctl -u streamlit-app -f"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


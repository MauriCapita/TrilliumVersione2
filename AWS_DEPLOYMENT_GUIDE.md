# 🚀 Guida Deployment AWS - Soluzione Cost-Effective

## 📊 Architettura Attuale

- **Flask App** (PrestaShop Dashboard) - Porta 8080
- **Streamlit App** (Trillium RAG) - Porta 8501
- **Qdrant/ChromaDB** (Vector Database)
- **Storage** per documenti e database vettoriale

---

## 💰 Opzioni AWS (Ordinate per Costo)

### 🥇 **OPZIONE 1: AWS Lightsail** ⭐ CONSIGLIATA

**Costo: ~$10-20/mese**

#### Architettura
```
Lightsail Instance (2GB RAM, 1 vCPU, 60GB SSD)
├── Flask App (porta 8080)
├── Streamlit App (porta 8501)
├── Qdrant (Docker) o ChromaDB
└── Storage locale per documenti
```

#### Vantaggi
- ✅ **Prezzo fisso e prevedibile** ($10-20/mese)
- ✅ **Tutto-in-uno**: un'unica istanza
- ✅ **Facile da gestire**: pannello semplificato
- ✅ **Backup automatico incluso** (opzionale, +$2/mese)
- ✅ **IP statico incluso**
- ✅ **SSL gratuito** con Let's Encrypt

#### Configurazione
1. **Crea istanza Lightsail**:
   - OS: Ubuntu 22.04 LTS
   - Plan: $10/mese (2GB RAM, 1 vCPU, 60GB SSD)
   - Aggiungi script di avvio automatico

2. **Installa dipendenze**:
   ```bash
   sudo apt update
   sudo apt install -y python3-pip python3-venv docker.io docker-compose
   ```

3. **Deploy applicazione**:
   ```bash
   git clone <your-repo>
   cd <project>
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install -r trillium/requirements.txt
   ```

4. **Configura reverse proxy** (Nginx):
   ```nginx
   # Flask Dashboard
   server {
       listen 80;
       server_name dashboard.yourdomain.com;
       location / {
           proxy_pass http://localhost:8080;
       }
   }
   
   # Streamlit RAG
   server {
       listen 80;
       server_name rag.yourdomain.com;
       location / {
           proxy_pass http://localhost:8501;
       }
   }
   ```

5. **Avvia servizi**:
   ```bash
   # Qdrant (se usato)
   docker-compose up -d
   
   # Flask + Streamlit (con systemd o screen)
   screen -S flask python app.py
   screen -S streamlit cd trillium && streamlit run streamlit_app.py
   ```

#### Costo Mensile Stimato
- Lightsail 2GB: **$10/mese**
- Backup automatico (opzionale): **+$2/mese**
- **TOTALE: $10-12/mese**

---

### 🥈 **OPZIONE 2: AWS EC2 t3.micro (Free Tier)** 

**Costo: $0-10/mese** (primo anno gratuito con Free Tier)

#### Architettura
```
EC2 t3.micro (1 vCPU, 1GB RAM)
├── Flask App
├── Streamlit App
├── Qdrant/ChromaDB
└── EBS Volume (20GB) per storage
```

#### Vantaggi
- ✅ **GRATIS per 12 mesi** (Free Tier)
- ✅ Dopo il primo anno: ~$7-10/mese
- ✅ Più controllo rispetto a Lightsail
- ✅ Scalabile in futuro

#### Limitazioni
- ⚠️ Solo 1GB RAM (potrebbe essere limitante per Qdrant)
- ⚠️ Consigliato t3.small (2GB RAM) per produzione: ~$15/mese

#### Costo Mensile Stimato
- **Anno 1 (Free Tier)**: **$0/mese** (solo costi dati)
- **Dopo Free Tier**: **$7-15/mese** (t3.micro o t3.small)

---

### 🥉 **OPZIONE 3: AWS App Runner** 

**Costo: ~$15-25/mese** (pay-per-use)

#### Architettura
```
App Runner (Container-based)
├── Container Flask
├── Container Streamlit
└── RDS/ElastiCache per Qdrant (opzionale)
```

#### Vantaggi
- ✅ **Serverless**: scala automaticamente
- ✅ **Pay-per-use**: paghi solo per le richieste
- ✅ Gestione automatica dei container

#### Svantaggi
- ⚠️ Più complesso da configurare
- ⚠️ Costi variabili (dipendono dal traffico)
- ⚠️ Richiede containerizzazione (Docker)

#### Costo Mensile Stimato
- App Runner: **$0.007/vCPU-ora** + **$0.0008/GB-ora**
- Stima media: **$15-25/mese** (uso moderato)

---

### 🏅 **OPZIONE 4: AWS ECS Fargate Spot**

**Costo: ~$8-15/mese** (con Spot instances)

#### Architettura
```
ECS Fargate Spot
├── Task Flask (0.5 vCPU, 1GB RAM)
├── Task Streamlit (0.5 vCPU, 1GB RAM)
└── Task Qdrant (0.5 vCPU, 1GB RAM)
```

#### Vantaggi
- ✅ **Molto economico** con Spot (fino a 90% sconto)
- ✅ Scalabile
- ✅ Container-based

#### Svantaggi
- ⚠️ Spot instances possono essere interrotte
- ⚠️ Più complesso da gestire
- ⚠️ Richiede ALB (Application Load Balancer): +$16/mese

#### Costo Mensile Stimato
- ECS Fargate Spot: **$8-15/mese**
- ALB: **+$16/mese**
- **TOTALE: $24-31/mese**

---

## 🎯 **RACCOMANDAZIONE FINALE**

### Per il Minor Costo Immediato:
**AWS Lightsail 2GB - $10/mese** ⭐

**Perché:**
- Prezzo fisso e prevedibile
- Facile da configurare e gestire
- Abbastanza potente per la tua applicazione
- Include backup, IP statico, SSL
- Nessuna sorpresa nei costi

### Per Massima Economia (Primo Anno):
**AWS EC2 t3.micro Free Tier - $0/mese** (primo anno)

**Perché:**
- Gratis per 12 mesi
- Dopo: upgrade a t3.small ($15/mese) se necessario

---

## 📋 Checklist Deployment Lightsail (Consigliato)

### 1. Preparazione
- [ ] Account AWS attivo
- [ ] Dominio (opzionale, ma consigliato)
- [ ] Chiavi SSH generate

### 2. Creazione Istanza
- [ ] Crea istanza Lightsail Ubuntu 22.04
- [ ] Seleziona plan 2GB RAM ($10/mese)
- [ ] Configura IP statico
- [ ] Aggiungi script di avvio

### 3. Configurazione Server
- [ ] Connetti via SSH
- [ ] Installa dipendenze (Python, Docker, Nginx)
- [ ] Clona repository
- [ ] Configura variabili ambiente (.env)
- [ ] Installa dipendenze Python

### 4. Deploy Applicazione
- [ ] Avvia Qdrant (se usato) con Docker
- [ ] Configura Nginx come reverse proxy
- [ ] Crea servizi systemd per Flask e Streamlit
- [ ] Configura SSL con Let's Encrypt

### 5. Backup e Monitoraggio
- [ ] Abilita backup automatico Lightsail
- [ ] Configura CloudWatch per monitoraggio (opzionale)
- [ ] Testa accesso da browser

---

## 🔧 Script di Deploy Automatico

Crea `deploy_lightsail.sh`:

```bash
#!/bin/bash
# Script di deploy automatico per AWS Lightsail

echo "🚀 Deploy su AWS Lightsail..."

# 1. Installa dipendenze
sudo apt update
sudo apt install -y python3-pip python3-venv docker.io docker-compose nginx

# 2. Crea utente per applicazione
sudo useradd -m -s /bin/bash appuser

# 3. Clona repository (sostituisci con il tuo)
cd /home/appuser
git clone <your-repo-url> app
cd app

# 4. Crea virtual environment
python3 -m venv venv
source venv/bin/activate

# 5. Installa dipendenze
pip install -r requirements.txt
pip install -r trillium/requirements.txt

# 6. Configura .env
cp .env.example .env
# Modifica .env con le tue credenziali

# 7. Avvia Qdrant (se usato)
docker-compose up -d

# 8. Crea servizi systemd
sudo tee /etc/systemd/system/flask-app.service > /dev/null <<EOF
[Unit]
Description=Flask PrestaShop Dashboard
After=network.target

[Service]
User=appuser
WorkingDirectory=/home/appuser/app
Environment="PATH=/home/appuser/app/venv/bin"
ExecStart=/home/appuser/app/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/streamlit-app.service > /dev/null <<EOF
[Unit]
Description=Streamlit Trillium RAG
After=network.target

[Service]
User=appuser
WorkingDirectory=/home/appuser/app/trillium
Environment="PATH=/home/appuser/app/venv/bin"
ExecStart=/home/appuser/app/venv/bin/streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 9. Avvia servizi
sudo systemctl daemon-reload
sudo systemctl enable flask-app streamlit-app
sudo systemctl start flask-app streamlit-app

# 10. Configura Nginx
sudo tee /etc/nginx/sites-available/app > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    # Flask Dashboard
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    # Streamlit RAG
    location /rag {
        proxy_pass http://localhost:8501;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

echo "✅ Deploy completato!"
echo "🌐 Accedi a: http://$(curl -s ifconfig.me)"
```

---

## 💡 Ottimizzazioni Costo

1. **Usa ChromaDB invece di Qdrant** (se possibile)
   - ChromaDB è embedded, non richiede Docker
   - Risparmia risorse CPU/RAM

2. **Abilita compressione Nginx**:
   ```nginx
   gzip on;
   gzip_types text/plain application/json;
   ```

3. **Usa CloudFront** (opzionale, per CDN):
   - Primi 1TB gratis/mese
   - Migliora performance

4. **Monitora costi con AWS Cost Explorer**:
   - Tieni traccia dei costi mensili
   - Imposta alert per superamento budget

---

## 📞 Supporto

Per domande o problemi durante il deploy, consulta:
- [AWS Lightsail Documentation](https://docs.aws.amazon.com/lightsail/)
- [AWS EC2 Documentation](https://docs.aws.amazon.com/ec2/)

---

## ✅ Prossimi Passi

1. Scegli l'opzione (consigliato: Lightsail)
2. Crea account AWS (se non ce l'hai)
3. Segui la checklist di deployment
4. Testa l'applicazione
5. Configura dominio e SSL
6. Monitora costi e performance

**Buon deploy! 🚀**


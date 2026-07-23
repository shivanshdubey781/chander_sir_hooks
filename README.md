# Chander Sir Hooks — Chartlink to Telegram Webhook Bridge

FastAPI service that receives POST alerts from Chartlink stock screener webhooks, logs them into an SQLite database (`reports.db`), displays them on a web dashboard, and forwards formatted alerts to a Telegram channel/group via a Telegram bot.

---

## 📁 Repository Structure

```
.
├── main.py                     # FastAPI application endpoints
├── database.py                 # SQLite database helper functions
├── templates/
│   └── index.html              # Simple web dashboard
├── chander_sir_hooks.service   # Systemd service unit file
├── .env.example                # Template for environment variables
└── requirements.txt            # Python dependencies
```

---

## 🚀 Deployment to VPS (`195.35.23.125`)

### Step 1: Create Directory on VPS
```bash
ssh root@195.35.23.125 "mkdir -p /var/www/chander_sir_hooks"
```

### Step 2: Upload Files via SCP (from local PowerShell)
```powershell
scp main.py database.py requirements.txt chander_sir_hooks.service root@195.35.23.125:/var/www/chander_sir_hooks/
scp -r templates root@195.35.23.125:/var/www/chander_sir_hooks/
```

### Step 3: Setup Virtual Environment & `.env` on VPS
```bash
ssh root@195.35.23.125
cd /var/www/chander_sir_hooks
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create environment file
nano .env
```

Add your real variables in `.env`:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
WEBHOOK_SECRET=your_secret_key_here
```

### Step 4: Configure systemd Service (`chander_sir_hooks.service`)
```bash
sudo cp chander_sir_hooks.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now chander_sir_hooks
sudo systemctl status chander_sir_hooks
```

### Step 5: Open Firewall Port
```bash
sudo ufw allow 7012/tcp
```

---

## 🔗 Endpoints & Webhook URL for Client

- **Webhook URL for Chartlink**:
  `http://195.35.23.125:7012/webhook/chartlink?key=<YOUR_WEBHOOK_SECRET>`

- **Live Web Dashboard**:
  `http://195.35.23.125:7012/`

- **REST API Endpoint**:
  `http://195.35.23.125:7012/api/reports`

- **Health Check**:
  `http://195.35.23.125:7012/health`

# WahlplakatGame - Web-Version 🗳️

Eine Web-basierte Version des WahlplakatGame - ein Multiplayer-Quiz-Spiel rund um deutsche Wahlplakate und Wahlsprüche.

## 📋 Features

- **Web-basiert:** Spielbar im Browser (Desktop & Mobile)
- **Multiplayer:** Echtzeit-Spiel über WebSockets
- **Responsive:** Optimiert für alle Bildschirmgrößen
- **Sound-Effekte:** Auditive Rückmeldungen
- **Leaderboard:** Globale Bestenliste
- **Quellen:** Überprüfbare Originalquellen

## 🏗️ Technologie-Stack

- **Backend:** Flask + Flask-SocketIO (Python 3)
- **Frontend:** HTML5, CSS3, Vanilla JavaScript
- **Datenbank:** PostgreSQL
- **WebSockets:** Socket.IO
- **Server:** Gunicorn + Eventlet
- **Reverse Proxy:** Apache

## 🚀 Installation auf Raspbian

### Voraussetzungen

- Raspbian OS (Debian-basiert)
- Python 3.8+
- PostgreSQL
- Apache2
- Root/Sudo-Zugriff

### Automatische Installation

```bash
# Repository klonen
cd /home/pi
git clone <repository-url> wahlplakatgame-web
cd wahlplakatgame-web

# Deploy-Script ausführbar machen
chmod +x deploy.sh

# Installation starten
./deploy.sh
```

Das Script führt folgendes aus:
1. System-Updates
2. Installation der Dependencies
3. Python Virtual Environment erstellen
4. PostgreSQL Setup
5. Environment Variables konfigurieren
6. Apache Module aktivieren
7. Systemd Service installieren
8. Optional: Wahlsprüche importieren

### Manuelle Installation

#### 1. System Dependencies

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv postgresql apache2
```

#### 2. PostgreSQL Setup

```bash
sudo -u postgres psql

# In psql:
CREATE DATABASE wahlplakatgame;
CREATE USER wahlplakatgame WITH ENCRYPTED PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE wahlplakatgame TO wahlplakatgame;
ALTER DATABASE wahlplakatgame OWNER TO wahlplakatgame;
\q
```

#### 3. Python Environment

```bash
cd /home/pi/wahlplakatgame-web
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 4. Environment Variables

Erstelle `.env` im Backend-Ordner:

```bash
DATABASE_URL=postgresql://wahlplakatgame:your-password@localhost:5432/wahlplakatgame
SECRET_KEY=your-secret-key-hier-einfuegen
FLASK_ENV=production
PORT=5001
```

#### 5. Apache Reverse Proxy

```bash
# Module aktivieren
sudo a2enmod proxy proxy_http proxy_wstunnel rewrite ssl

# Config bearbeiten
sudo nano /etc/apache2/sites-available/000-default.conf
```

Füge diese Zeilen ein:

```apache
# WahlplakatGame
ProxyPreserveHost On
ProxyPass /wahlplakatgame http://localhost:5001/
ProxyPassReverse /wahlplakatgame http://localhost:5001/

# WebSocket Support
RewriteEngine On
RewriteCond %{REQUEST_URI} ^/wahlplakatgame/socket.io [NC]
RewriteCond %{QUERY_STRING} transport=websocket [NC]
RewriteRule /(.*) ws://localhost:5001/$1 [P,L]

ProxyPass /wahlplakatgame/socket.io http://localhost:5001/socket.io
ProxyPassReverse /wahlplakatgame/socket.io http://localhost:5001/socket.io
```

```bash
# Apache neu laden
sudo systemctl reload apache2
```

#### 6. Systemd Service

```bash
sudo cp wahlplakatgame.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable wahlplakatgame
sudo systemctl start wahlplakatgame
```

#### 7. Wahlsprüche importieren

```bash
cd backend
source ../venv/bin/activate

# Import-Script erstellen und ausführen
# (siehe Original-Code WahlspruchImporter.py)
```

## 📱 Assets kopieren

Kopiere die Sound-Dateien aus dem Original-Projekt:

```bash
mkdir -p frontend/assets/sounds
cp /path/to/old/assets/*.mp3 frontend/assets/sounds/
cp /path/to/old/assets/icon.ico frontend/assets/
```

Benötigte Dateien:
- `correct_answer.mp3`
- `incorrect_answer.mp3`
- `player_join.mp3`
- `player_leave.mp3`
- `lock_answer.mp3`
- `icon.ico`

## 🔧 Konfiguration

### Backend Port ändern

In `.env`:
```
PORT=5001
```

In `wahlplakatgame.service`:
```
ExecStart=.../gunicorn ... --bind 0.0.0.0:5001 app:app
```

### Database URL

In `.env`:
```
DATABASE_URL=postgresql://user:password@host:port/database
```

## 📊 Monitoring

### Logs anzeigen

```bash
# Service Logs
sudo journalctl -u wahlplakatgame -f

# Apache Logs
sudo tail -f /var/log/apache2/error.log
```

### Status prüfen

```bash
# Service Status
sudo systemctl status wahlplakatgame

# Apache Status
sudo systemctl status apache2

# PostgreSQL Status
sudo systemctl status postgresql
```

## 🛠️ Wartung

### Service neu starten

```bash
sudo systemctl restart wahlplakatgame
```

### Code aktualisieren

```bash
cd /home/pi/wahlplakatgame-web
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart wahlplakatgame
```

### Datenbank Backup

```bash
pg_dump -U wahlplakatgame wahlplakatgame > backup_$(date +%Y%m%d).sql
```

## 🐛 Troubleshooting

### Service startet nicht

```bash
# Logs prüfen
sudo journalctl -u wahlplakatgame --no-pager

# Manuell starten zum Debuggen
cd /home/pi/wahlplakatgame-web/backend
source ../venv/bin/activate
python app.py
```

### WebSocket Probleme

- Prüfe ob Apache Module aktiviert sind: `proxy_wstunnel`, `rewrite`
- Prüfe Apache Config: `/etc/apache2/sites-available/`
- Prüfe Browser Console auf Fehler

### Database Connection Fehler

```bash
# PostgreSQL läuft?
sudo systemctl status postgresql

# Connection testen
psql -U wahlplakatgame -d wahlplakatgame -h localhost
```

## 🔒 Sicherheit

- **Firewall:** Nur Port 80/443 öffnen, Port 5001 intern lassen
- **SECRET_KEY:** Sicheren Key in `.env` verwenden
- **PostgreSQL:** Nur localhost-Verbindungen erlauben
- **SSL:** Let's Encrypt für HTTPS einrichten

### SSL mit Let's Encrypt

```bash
sudo apt-get install certbot python3-certbot-apache
sudo certbot --apache -d ilollek.net
```

## 📞 Support

Bei Fragen oder Problemen:
- **E-Mail:** loris-dante(at)web.de
- **GitHub Issues:** https://github.com/iLollek/WahlplakatGame/issues

## 📝 Lizenz

Siehe LICENSE Datei im Repository.

---

**Viel Spaß beim Spielen! 🎉**

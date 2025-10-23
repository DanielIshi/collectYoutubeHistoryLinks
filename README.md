# YouTube History Collector

Automatisches Scraping der YouTube-Historie und Speicherung in Supabase mit Untertiteln.

## 🎯 Workflow

1. **Chrome öffnen** im Debug-Modus
2. **YouTube-Historie scrapen** (Selenium)
3. **Neue URLs identifizieren** (Abgleich mit Supabase)
4. **Untertitel abrufen** (pytubefix: DE/EN)
5. **Zu Supabase hochladen** mit Metadaten

## 🚀 Schnellstart

### Voraussetzungen

```bash
# Python 3.12+ mit Virtual Environment
python -m venv .venv
.venv\Scripts\activate

# Dependencies installieren
pip install -r requirements.txt

# Environment-Variable setzen (einmalig)
setx SUPABASE_SERVICE_KEY "your-service-role-key"
```

### Ausführung

**Option 1: PowerShell-Skript (empfohlen)**
```powershell
.\run_youtube_script.ps1
```

**Option 2: Python direkt**
```bash
python run_youtube_history_scraper.py --lang de --source manual-run
```

## 📁 Projektstruktur

```
├── run_youtube_history_scraper.py   # ⭐ HAUPTSKRIPT (Chrome + Scraping + Supabase)
├── run_youtube_script.ps1           # PowerShell-Starter mit Environment-Checks
├── batch_ytsubs_to_supabase.py      # Nachträgliche Untertitel-Verarbeitung
├── requirements.txt                 # Python-Dependencies
├── youtube_links.csv                # Backup der letzten Scraping-Session
│
├── src/                             # Legacy: Django-basierte Version (optional)
│   ├── main.py                      # Alte Version mit Django + Filter
│   ├── video_filter.py              # KI/Tech-Filter
│   └── ...
│
├── collector/                       # Django-App (für src/main.py)
├── youtube_collector/               # Django-Settings
└── .venv/                          # Virtual Environment (nicht versioniert)
```

## 🔧 Konfiguration

### Chrome-Einstellungen
```python
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA_DIR = r"C:\ChromeData\chromeprofile"  # Dein Chrome-Profil (Login erforderlich)
DEBUG_PORT = "9222"
```

### Supabase
```python
SUPABASE_URL = "http://148.230.71.150:8000/rest/v1"
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
```

**Tabelle: `youtube_urls`**
- `url` (primary key)
- `processed` (boolean)
- `processed_at` (timestamp)
- `subtitles` (text)
- `source` (varchar)
- `priority` (integer)
- `added_at` (timestamp)

## 📋 Verwendung

### Standard-Workflow (PowerShell)
```powershell
.\run_youtube_script.ps1
```
- Aktiviert `.venv`
- Prüft `SUPABASE_SERVICE_KEY`
- Startet Chrome + Scraping + Upload

### Python-Skript mit Optionen
```bash
# Deutsche Untertitel (Standard)
python run_youtube_history_scraper.py --lang de

# Englische Untertitel
python run_youtube_history_scraper.py --lang en

# Benutzerdefinierte Quelle
python run_youtube_history_scraper.py --source "cron-job-daily" --priority 5
```

### Batch-Verarbeitung existierender URLs
Falls URLs bereits in Supabase sind, aber ohne Untertitel:
```bash
python batch_ytsubs_to_supabase.py --lang de --source vm-cron
```

## 🛠️ Troubleshooting

### Chrome startet nicht
- Prüfe `CHROME_PATH` in `run_youtube_history_scraper.py`
- Stelle sicher, dass Chrome installiert ist
- Port 9222 muss frei sein

### Keine Untertitel gefunden
- Video ist privat/gelöscht
- Keine Untertitel verfügbar
- API-Limits erreicht (YouTube)

### Environment-Variable fehlt
```powershell
# Setzen (User-Level)
setx SUPABASE_SERVICE_KEY "your-key"

# Prüfen
$env:SUPABASE_SERVICE_KEY
```

### Import-Fehler
```bash
# Virtual Environment aktivieren
.venv\Scripts\activate

# Dependencies neu installieren
pip install --upgrade -r requirements.txt
```

## 🔄 Automatisierung

### Windows Task Scheduler
```powershell
# Task erstellen (täglich um 22:00 Uhr)
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-ExecutionPolicy Bypass -File C:\Users\Daniel\PycharmProjects\collectYoutubeHistoryLinks\run_youtube_script.ps1"

$trigger = New-ScheduledTaskTrigger -Daily -At 22:00

Register-ScheduledTask -TaskName "YouTube History Scraper" `
    -Action $action -Trigger $trigger -Description "Scraped YouTube-Historie täglich"
```

## 📊 Monitoring

### Logs prüfen
Das Skript gibt detaillierte Logs aus:
```
[1/3] ✓ Chrome bereit
[2/3] ✓ 42 YouTube-Links gesammelt
[3/3] ✓ 12 neue URLs gefunden

[1/12] https://www.youtube.com/watch?v=...
  ✓ Untertitel: 15234 Zeichen

✅ FERTIG! 12/12 URLs erfolgreich verarbeitet
```

### Supabase-Abfrage
```sql
-- Heute verarbeitete URLs
SELECT url, processed_at, LENGTH(subtitles) as subtitle_length
FROM youtube_urls
WHERE DATE(processed_at) = CURRENT_DATE
ORDER BY processed_at DESC;

-- Unverarbeitete URLs
SELECT COUNT(*) FROM youtube_urls WHERE processed = false;
```

## 📚 Legacy: Django-Version (src/main.py)

Die alte Version mit Django und KI-Filter ist noch vorhanden:
- **Vorteil**: KI-basierte Relevanz-Filterung, Web-Interface
- **Nachteil**: Komplex, benötigt Django-Setup und manage.py

**Nutzung (optional):**
```bash
cd src
python main.py
```
Öffne dann http://localhost:8000 für das Web-Interface.

## 🤝 Mitwirkende

- Entwickelt für automatisierte YouTube-Wissensarchivierung
- Basierend auf pytubefix, Selenium, Supabase

## 📝 Lizenz

Privates Projekt.

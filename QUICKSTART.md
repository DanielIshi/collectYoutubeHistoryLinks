# 🚀 Quickstart Guide

## Sofort starten (3 Schritte)

### 1️⃣ Chrome vorbereiten
Stelle sicher, dass Du in Chrome **bei YouTube eingeloggt** bist:
- Öffne Chrome normal
- Gehe zu https://youtube.com
- Logge Dich ein (falls nötig)
- Schließe Chrome **komplett**

### 2️⃣ PowerShell-Skript starten
```powershell
.\run_youtube_script.ps1
```

### 3️⃣ Fertig!
Das Skript:
- ✅ Öffnet Chrome automatisch im Debug-Modus
- ✅ Scraped Deine YouTube-Historie
- ✅ Lädt neue URLs zu Supabase hoch
- ✅ Holt Untertitel für jedes Video

## Was passiert im Detail?

```
============================================================================
  YouTube History Scraper to Supabase
============================================================================

[1/3] Aktiviere Virtual Environment...
      ✓ Virtual Environment aktiviert

[2/3] Prüfe Environment-Variablen...
      ✓ SUPABASE_SERVICE_KEY gesetzt (180 Zeichen)

[3/3] Starte YouTube History Scraper...
============================================================================

🎬 YouTube History Scraper to Supabase
================================================================================
🔧 Starte Chrome im Debug-Modus...
⏳ Warte auf Debug-Port...
✓ Chrome bereit

📺 Verbinde mit Chrome via Selenium...
🔍 Navigiere zu YouTube-Historie...
📋 Extrahiere Video-URLs...
✓ 42 YouTube-Links gesammelt
💾 Backup gespeichert: youtube_links.csv

🔄 Gleiche mit Supabase ab...
ℹ️  612 URLs bereits in Supabase vorhanden.
✨ 12 neue URLs gefunden

📥 Verarbeite 12 neue URLs...

[1/12] https://www.youtube.com/watch?v=xyz123
  ✓ Untertitel: 15234 Zeichen

[2/12] https://www.youtube.com/watch?v=abc456
  ✓ Untertitel: 8912 Zeichen

...

================================================================================
✅ FERTIG!
📊 12/12 URLs erfolgreich verarbeitet
================================================================================

  ✓ ERFOLGREICH ABGESCHLOSSEN
============================================================================
```

## Erste Schritte nach der Installation

### Prüfe ob alles funktioniert
```powershell
# Test: Zeige Hilfe
python run_youtube_history_scraper.py --help

# Test: Prüfe Environment-Variable
python -c "import os; print('✓ OK' if os.environ.get('SUPABASE_SERVICE_KEY') else '✗ FEHLT')"
```

### Manuelle Ausführung (ohne PowerShell)
```bash
# Virtual Environment aktivieren
.venv\Scripts\activate

# Skript starten
python run_youtube_history_scraper.py --lang de --source manual-run
```

## Häufige Probleme & Lösungen

### ❌ "Chrome ist nicht erreichbar"
**Lösung:** Chrome läuft bereits im normalen Modus.
```powershell
# Schließe Chrome komplett (auch im Hintergrund)
taskkill /F /IM chrome.exe

# Starte Skript erneut
.\run_youtube_script.ps1
```

### ❌ "SUPABASE_SERVICE_KEY nicht gesetzt"
**Lösung:** Environment-Variable fehlt.
```powershell
setx SUPABASE_SERVICE_KEY "dein-key-hier"

# WICHTIG: PowerShell neu starten (damit Variable geladen wird)
```

### ❌ "Keine neuen URLs gefunden"
**Lösung:** Alle Videos sind bereits in Supabase.
- Das ist **normal**, wenn Du das Skript regelmäßig ausführst
- Schaue Dir neue Videos an, dann erneut starten

### ❌ "selenium.common.exceptions..."
**Lösung:** ChromeDriver fehlt oder ist veraltet.
```bash
# Virtual Environment aktivieren
.venv\Scripts\activate

# Dependencies aktualisieren
pip install --upgrade selenium
```

## Nächste Schritte

### 1. Automatisierung einrichten
Siehe `README.md` → Abschnitt "🔄 Automatisierung"
- Windows Task Scheduler (täglich um 22:00 Uhr)

### 2. Daten in Supabase prüfen
```sql
-- Letzte 10 verarbeitete Videos
SELECT url, processed_at, LENGTH(subtitles) as chars
FROM youtube_urls
WHERE processed = true
ORDER BY processed_at DESC
LIMIT 10;
```

### 3. Alte URLs nachträglich verarbeiten
Falls Du alte URLs ohne Untertitel hast:
```bash
python batch_ytsubs_to_supabase.py --lang de
```

## Support

Bei Problemen:
1. Prüfe `youtube_links.csv` (wurde Scraping erfolgreich?)
2. Prüfe Supabase-Datenbank (sind URLs da?)
3. Siehe `README.md` für detaillierte Troubleshooting-Tipps

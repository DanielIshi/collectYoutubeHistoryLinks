import os
import re
import subprocess
import time
import pandas as pd
import requests
from pytubefix import YouTube
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from .video_filter import VideoFilter
import django
import sys
from pathlib import Path

# Django Setup
sys.path.append(str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'youtube_collector.settings')
django.setup()

from collector.models import VideoEntry

# --- Datenstrukturen für Ergebnisse ---
class ProcessingResults:
    def __init__(self):
        self.videos = []

    def add_video(self, url: str, title: str, score: float, method: str, is_relevant: bool):
        video_info = {
            'url': url,
            'title': title,
            'score': score,
            'method': method,
            'selected': is_relevant  # Standardmäßig ausgewählt wenn relevant
        }
        self.videos.append(video_info)

        # Speichere in Django-Datenbank
        VideoEntry.objects.create(**video_info)

    def print_summary(self):
        print("\n" + "="*100)
        print("VERARBEITUNGSERGEBNISSE")
        print("="*100)

        relevant = [v for v in self.videos if v['score'] >= 0.3]
        filtered = [v for v in self.videos if v['score'] < 0.3]

        print(f"\nGESAMT: {len(self.videos)} Videos verarbeitet")
        print(f"RELEVANT: {len(relevant)} Videos")
        print(f"GEFILTERT: {len(filtered)} Videos")
        print("\nÖffnen Sie http://localhost:8000 im Browser, um die Videos zu überprüfen und auszuwählen.")

# --- Konfiguration ---
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA_DIR = r"C:\ChromeData\chromeprofile"
DEBUG_PORT = "9222"
WAIT_TIMEOUT = 15

# Filter-Konfiguration
USE_FILTER = True  # Schaltet den KI/Tech-Filter ein/aus
USE_AI_CLASSIFICATION = False  # Nutzt KI für unsichere Fälle (benötigt API-Key)

SUPABASE_URL = "http://148.230.71.150:8000/rest/v1"
SUPABASE_TABLE = "youtube_urls"
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("Umgebungsvariable SUPABASE_SERVICE_KEY fehlt.")

# --- Supabase-Header ---
HDRS = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates,return=representation",
}
def clean_subtitle_text(srt_text):
    # Entfernt Zeitstempel, Nummerierung und Leerzeilen → macht Fließtext
    lines = srt_text.splitlines()
    cleaned_lines = []
    for line in lines:
        if re.match(r"^\d+$", line):  # Zeilennummer
            continue
        if re.match(r"^\d\d:\d\d:\d\d", line):  # Zeitstempel
            continue
        if line.strip() == "":
            continue
        cleaned_lines.append(line.strip())
    return " ".join(cleaned_lines)
def fetch_with_pytubefix(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        yt = YouTube(url)
        title = yt.title

        subs = yt.captions
        text = None
        if subs:
            key = next(iter(subs.keys()))
            caption = subs[key.code]
            srt_text = caption.generate_srt_captions()
            text = clean_subtitle_text(srt_text)
        print(f"  Untertitel: {len(text) if text else 0} Zeichen")
        return title, text
    except Exception as e:
        print(f"  Fehler beim Abrufen: {e}")
        return None, None
def fetch_unprocessed_ids():
    url = f"{SUPABASE_URL}/{SUPABASE_TABLE}?processed=eq.FALSE&processed_at=is.NULL&select=id"
    response = requests.get(url, headers=HDRS, timeout=30)
    if not response.ok:
        raise RuntimeError(f"Supabase-Abfrage fehlgeschlagen: {response.status_code} {response.text}")
    data = response.json()
    ids = [row["id"] for row in data]
    print(f"{len(ids)} unprocessed IDs fetched.")
    return ids
# --- Funktion: YouTube-Links upserten ---
def upsert_urls(links: list[str]):
    payload = [{"url": link} for link in links]

    response = requests.post(
        f"{SUPABASE_URL}/{SUPABASE_TABLE}?on_conflict=url",
        headers=HDRS,
        json=payload,
        timeout=30
    )

    if not response.ok:
        raise RuntimeError(f"Supabase-Upsert fehlgeschlagen: {response.status_code} {response.text}")
    print(f"✅ {len(links)} Links erfolgreich an Supabase gesendet.")



import json

# --- Vorhandene URLs aus Supabase holen ---
def fetch_existing_urls() -> set[str]:
    url = f"{SUPABASE_URL}/{SUPABASE_TABLE}?select=url"
    response = requests.get(url, headers=HDRS, timeout=30)
    if not response.ok:
        raise RuntimeError(f"Supabase-Query fehlgeschlagen: {response.status_code} {response.text}")
    data = response.json()
    existing = {row["url"] for row in data if row.get("url")}
    print(f"{len(existing)} URLs bereits in Supabase vorhanden.")
    return existing

def extract_video_id(url: str) -> str:
    import re
    from urllib.parse import urlparse, parse_qs
    # Versucht, die ID aus verschiedenen YouTube-URL-Formaten zu extrahieren
    parsed = urlparse(url)
    if parsed.hostname in ["www.youtube.com", "youtube.com"]:
        query = parse_qs(parsed.query)
        return query.get("v", [""])[0]
    elif parsed.hostname in ["youtu.be"]:
        return parsed.path.lstrip("/")
    else:
        return ""
# --- YouTube-Links upserten ---
def upsert_urls(links: list[str], video_filter: VideoFilter = None) -> ProcessingResults:
    if not links:
        print("Keine neuen Links zum Einfügen.")
        return ProcessingResults()

    results = ProcessingResults()

    for i, link in enumerate(links, 1):
        video_id = extract_video_id(link)
        print(f"\nVerarbeite [{i}/{len(links)}]: {link}")

        title, subtitles = fetch_with_pytubefix(video_id)
        
        if not title:
            print("  [WARNUNG] Konnte Video-Informationen nicht abrufen")
            continue
        
        # Filter anwenden wenn aktiviert
        if USE_FILTER and video_filter:
            is_relevant, score, method = video_filter.is_relevant(
                title, subtitles, use_ai=USE_AI_CLASSIFICATION
            )
            
            # Füge Ergebnis zu unseren gesammelten Ergebnissen hinzu
            results.add_video(link, title, score, method, is_relevant)
            print(f"  Verarbeitet: '{title[:50]}...' (Score: {score:.2f})")

    return results

def main():
    # --- Django-Server starten ---
    print("Starte Django-Server...")
    django_process = subprocess.Popen([
        'python', 'manage.py', 'runserver',
        '--noreload'  # Verhindert doppeltes Ausführen
    ])

    try:
        # --- Chrome starten (Debug-Modus) ---
        chrome_cmd = [
            CHROME_PATH,
            f"--remote-debugging-port={DEBUG_PORT}",
            f"--user-data-dir={USER_DATA_DIR}"
        ]
        subprocess.Popen(chrome_cmd)

        # --- Warten bis DevTools-Port erreichbar ---
        print("Warte auf Debug-Port...")
        for _ in range(WAIT_TIMEOUT):
            try:
                res = requests.get(f"http://localhost:{DEBUG_PORT}/json/version")
                if res.status_code == 200:
                    print("Chrome bereit.")
                    break
            except requests.exceptions.ConnectionError:
                pass
            time.sleep(1)
        else:
            raise RuntimeError("Chrome ist nicht erreichbar (DevTools-Port).")

        # --- Selenium mit laufender Chrome-Instanz verbinden ---
        options = Options()
        options.add_experimental_option("debuggerAddress", f"localhost:{DEBUG_PORT}")
        driver = webdriver.Chrome(options=options)

        # --- YouTube-Verlauf aufrufen ---
        driver.get("https://www.youtube.com/feed/history")
        time.sleep(5)

        # --- Links extrahieren ---
        elements = driver.find_elements("css selector", 'a[href*="/watch"]')
        links = list({el.get_attribute("href") for el in elements})
        print(f"{len(links)} YouTube-Links gesammelt.")

        # --- CSV speichern ---
        df = pd.DataFrame(links, columns=["url"])
        output_path = r"C:\Users\Daniel\PycharmProjects\collectYoutubeHistoryLinks\youtube_links.csv"
        df.to_csv(output_path, index=False)
        print("youtube_links.csv gespeichert.")

        # --- Vorhandene URLs abgleichen ---
        existing = fetch_existing_urls()
        new_links = [link for link in links if link not in existing]
        print(f"{len(new_links)} neue Links gefunden.")

        # --- Filter initialisieren wenn aktiviert ---
        video_filter = VideoFilter() if USE_FILTER else None
        if USE_FILTER:
            print("[FILTER] KI/Tech-Filter ist aktiviert")
            if USE_AI_CLASSIFICATION:
                print("[KI] KI-Klassifikation ist aktiviert")

        # --- Links verarbeiten und Ergebnisse sammeln ---
        results = upsert_urls(new_links, video_filter)

        # --- Ergebnisse ausgeben ---
        results.print_summary()

        print("\nDrücken Sie Strg+C zum Beenden...")
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nBeende Programm...")
    finally:
        driver.quit()
        django_process.terminate()
        django_process.wait()

if __name__ == "__main__":
    main()

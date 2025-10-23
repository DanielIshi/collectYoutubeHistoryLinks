#!/usr/bin/env python3
"""
YouTube History Scraper to Supabase
====================================
Kompletter Workflow ohne Django:
1. Chrome im Debug-Modus öffnen
2. YouTube-Historie scrapen (Selenium)
3. Neue URLs zu Supabase hochladen
4. Untertitel sofort abrufen (pytubefix)

Aufruf: python run_youtube_history_scraper.py [--lang de|en] [--source source-name]
"""
import os
import sys
import time
import argparse
import datetime
import re
from typing import Optional, Tuple, Set, List
import subprocess
from pathlib import Path

import requests
import pandas as pd
from pytubefix import YouTube
from pytubefix.cli import on_progress
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv

# --- .env laden ---
env_path = Path(__file__).parent / '.env'
if not env_path.exists():
    print("❌ FEHLER: .env Datei nicht gefunden!")
    print(f"   Erwarteter Pfad: {env_path}")
    print("   Erstelle .env aus .env.example und fülle die Werte aus.")
    sys.exit(1)

load_dotenv(env_path)

# --- Konfiguration aus Environment-Variablen ---
CHROME_PATH = os.getenv("CHROME_PATH", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
USER_DATA_DIR = os.getenv("CHROME_USER_DATA_DIR", r"C:\ChromeData\chromeprofile")
DEBUG_PORT = os.getenv("CHROME_DEBUG_PORT", "9222")
WAIT_TIMEOUT = int(os.getenv("CHROME_WAIT_TIMEOUT", "15"))

# Supabase-Konfiguration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_TABLE = os.getenv("SUPABASE_TABLE", "youtube_urls")

# Validierung
if not SUPABASE_URL:
    print("❌ FEHLER: SUPABASE_URL nicht in .env gesetzt!")
    sys.exit(1)

if not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ FEHLER: SUPABASE_SERVICE_KEY nicht in .env gesetzt!")
    sys.exit(1)

REST_URL = f"{SUPABASE_URL}/rest/v1"
HDRS = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates,return=representation",
}

# --- Hilfsfunktionen für Untertitel ---
def clean_srt_to_text(srt_text: str) -> str:
    """Entfernt SRT-Formatierung und erstellt Fließtext"""
    out = []
    for line in srt_text.splitlines():
        if re.match(r"^\d+$", line):            # SRT-Index
            continue
        if re.match(r"^\d\d:\d\d:\d\d", line):  # Zeitstempel
            continue
        if not line.strip():
            continue
        out.append(line.strip())
    return " ".join(out)


def pick_caption(yt: YouTube, prefer: Optional[str]) -> Optional[object]:
    """Wählt die beste verfügbare Caption-Spur aus"""
    subs = yt.captions or {}
    if not subs:
        return None

    by_code = {}
    for k in subs.keys():
        try:
            code = getattr(k, "code", None) or str(k)
            by_code[code] = subs[k.code]
        except Exception:
            pass

    # Bevorzugte Sprache
    if prefer and prefer in by_code:
        return by_code[prefer]

    # Fallback: de, dann en
    for fb in ("de", "en"):
        if fb in by_code:
            return by_code[fb]

    # Letzte Option: irgendeine Caption
    return next(iter(by_code.values())) if by_code else None


def fetch_subtitles(url: str, lang: Optional[str]) -> Tuple[str, Optional[str]]:
    """
    Versucht Untertitel für ein YouTube-Video abzurufen.
    Probiert erst ANDROID, dann WEB-Client.

    Returns: (title, subtitle_text)
    """
    # Versuch 1: ANDROID
    try:
        yt = YouTube(url, on_progress_callback=on_progress)
        title = yt.title or url
        cap = pick_caption(yt, lang)
        if cap:
            srt = cap.generate_srt_captions()
            return title, clean_srt_to_text(srt)
    except Exception as e:
        print(f"  [WARN] ANDROID failed: {e}", file=sys.stderr)

    # Versuch 2: WEB
    try:
        yt = YouTube(url, on_progress_callback=on_progress, client="WEB")
        title = yt.title or url
        cap = pick_caption(yt, lang)
        if cap:
            srt = cap.generate_srt_captions()
            return title, clean_srt_to_text(srt)
    except Exception as e:
        print(f"  [WARN] WEB failed: {e}", file=sys.stderr)

    return url, None


# --- Supabase-Funktionen ---
def fetch_existing_urls() -> Set[str]:
    """Holt alle existierenden URLs aus Supabase"""
    url = f"{REST_URL}/{SUPABASE_TABLE}?select=url"
    response = requests.get(url, headers=HDRS, timeout=30)
    if not response.ok:
        raise RuntimeError(f"Supabase-Query fehlgeschlagen: {response.status_code} {response.text}")

    data = response.json()
    existing = {row["url"] for row in data if row.get("url")}
    print(f"ℹ️  {len(existing)} URLs bereits in Supabase vorhanden.")
    return existing


def upsert_url_with_subtitles(url: str, title: str, text: Optional[str], source: str, priority: int):
    """Fügt URL mit Untertiteln in Supabase ein/aktualisiert sie"""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    payload = {
        "url": url,
        "processed": bool(text),
        "processed_at": now if text else None,
        "source": source,
        "priority": priority,
    }

    if text:
        payload["subtitles"] = text

    r = requests.post(
        f"{REST_URL}/{SUPABASE_TABLE}?on_conflict=url",
        headers=HDRS,
        json=[payload],
        timeout=30
    )

    if not r.ok:
        raise RuntimeError(f"Supabase upsert failed: {r.status_code} {r.text}")


# --- Chrome & Selenium ---
def start_chrome_debug_mode():
    """Startet Chrome im Debug-Modus (falls nicht schon läuft)"""
    # Prüfe ob Chrome bereits läuft
    try:
        res = requests.get(f"http://localhost:{DEBUG_PORT}/json/version", timeout=2)
        if res.status_code == 200:
            print("✓ Chrome läuft bereits im Debug-Modus")
            return
    except requests.exceptions.ConnectionError:
        pass

    print("🔧 Starte Chrome im Debug-Modus...")
    chrome_cmd = [
        CHROME_PATH,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={USER_DATA_DIR}"
    ]
    subprocess.Popen(chrome_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Warte bis Chrome bereit ist
    print("⏳ Warte auf Debug-Port...")
    for _ in range(WAIT_TIMEOUT):
        try:
            res = requests.get(f"http://localhost:{DEBUG_PORT}/json/version")
            if res.status_code == 200:
                print("✓ Chrome bereit")
                return
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)

    raise RuntimeError("❌ Chrome ist nicht erreichbar (DevTools-Port).")


def scrape_youtube_history() -> List[str]:
    """
    Verbindet sich mit Chrome via Selenium und scraped YouTube-Historie.
    Returns: Liste von YouTube-URLs
    """
    print("\n📺 Verbinde mit Chrome via Selenium...")
    options = Options()
    options.add_experimental_option("debuggerAddress", f"localhost:{DEBUG_PORT}")
    driver = webdriver.Chrome(options=options)

    try:
        print("🔍 Navigiere zu YouTube-Historie...")
        driver.get("https://www.youtube.com/feed/history")
        time.sleep(5)  # Warte bis Seite geladen ist

        print("📋 Extrahiere Video-URLs...")
        elements = driver.find_elements("css selector", 'a[href*="/watch"]')
        links = list({el.get_attribute("href") for el in elements})
        print(f"✓ {len(links)} YouTube-Links gesammelt")

        # CSV-Backup speichern
        df = pd.DataFrame(links, columns=["url"])
        output_path = "youtube_links.csv"
        df.to_csv(output_path, index=False)
        print(f"💾 Backup gespeichert: {output_path}")

        return links

    finally:
        driver.quit()


# --- Hauptlogik ---
def main():
    parser = argparse.ArgumentParser(
        description="YouTube History Scraper -> Supabase (mit Untertiteln)"
    )
    parser.add_argument(
        "--lang",
        default=os.getenv("DEFAULT_SUBTITLE_LANG", "de"),
        help="Bevorzugte Sprachspur (de/en)"
    )
    parser.add_argument(
        "--source",
        default=os.getenv("DEFAULT_SOURCE", "powershell-run"),
        help="Wert für Spalte 'source'"
    )
    parser.add_argument(
        "--priority",
        type=int,
        default=int(os.getenv("DEFAULT_PRIORITY", "0")),
        help="Priorität der URLs"
    )
    args = parser.parse_args()

    print("="*80)
    print("🎬 YouTube History Scraper to Supabase")
    print("="*80)

    try:
        # 1. Chrome starten
        start_chrome_debug_mode()

        # 2. YouTube-Historie scrapen
        scraped_urls = scrape_youtube_history()

        # 3. Mit Supabase abgleichen
        print("\n🔄 Gleiche mit Supabase ab...")
        existing_urls = fetch_existing_urls()
        new_urls = [url for url in scraped_urls if url not in existing_urls]
        print(f"✨ {len(new_urls)} neue URLs gefunden")

        if not new_urls:
            print("\n✅ Keine neuen URLs. Fertig!")
            return

        # 4. Für jede neue URL: Untertitel holen und uploaden
        print(f"\n📥 Verarbeite {len(new_urls)} neue URLs...")
        success_count = 0

        for i, url in enumerate(new_urls, 1):
            print(f"\n[{i}/{len(new_urls)}] {url}")

            # Untertitel abrufen
            title, subtitles = fetch_subtitles(url, args.lang)

            if subtitles:
                print(f"  ✓ Untertitel: {len(subtitles)} Zeichen")
            else:
                print(f"  ⚠️  Keine Untertitel verfügbar")

            # Zu Supabase hochladen
            try:
                upsert_url_with_subtitles(url, title, subtitles, args.source, args.priority)
                success_count += 1
            except Exception as e:
                print(f"  ❌ Supabase-Fehler: {e}", file=sys.stderr)

        # 5. Zusammenfassung
        print("\n" + "="*80)
        print("✅ FERTIG!")
        print(f"📊 {success_count}/{len(new_urls)} URLs erfolgreich verarbeitet")
        print("="*80)

    except KeyboardInterrupt:
        print("\n\n⚠️  Abbruch durch Benutzer")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ FEHLER: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

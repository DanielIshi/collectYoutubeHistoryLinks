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
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import SessionNotCreatedException, WebDriverException
from dotenv import load_dotenv
import platform
import zipfile
import shutil
import io

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
    driver = _create_chrome_driver(options)

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


def _get_chrome_major_version() -> int:
    """Ermittelt die installierte Chrome-Hauptversion (z. B. 141)."""
    try:
        res = requests.get(f"http://localhost:{DEBUG_PORT}/json/version", timeout=2)
        if res.ok:
            data = res.json()
            browser = data.get("Browser", "")
            m = re.search(r"Chrome/(\d+)", browser)
            if m:
                return int(m.group(1))
    except Exception:
        pass
    try:
        out = subprocess.check_output([CHROME_PATH, "--version"], stderr=subprocess.STDOUT, text=True, timeout=5)
        m = re.search(r"(Chrome|Chromium)\s+(\d+)", out)
        if m:
            return int(m.group(2))
    except Exception:
        pass
    raise RuntimeError("Konnte Chrome-Version nicht ermitteln.")


def _get_chromedriver_major_version(driver_path: Path) -> int:
    try:
        out = subprocess.check_output([str(driver_path), "--version"], stderr=subprocess.STDOUT, text=True, timeout=5)
        m = re.search(r"ChromeDriver\s+(\d+)", out)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return -1


def _download_chromedriver_for_major(major: int, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    arch = "win64" if "64" in platform.machine() else "win32"
    meta_url = "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"
    r = requests.get(meta_url, timeout=20)
    r.raise_for_status()
    data = r.json()
    target = None
    for v in data.get("versions", [])[::-1]:
        ver = v.get("version", "")
        if ver.startswith(f"{major}."):
            for item in v.get("downloads", {}).get("chromedriver", []):
                if item.get("platform") == ("win64" if arch == "win64" else "win32"):
                    target = (ver, item.get("url"))
                    break
        if target:
            break
    if not target:
        raise RuntimeError(f"Kein ChromeDriver-Download für Chrome {major} gefunden.")
    ver, url = target
    zip_path = dest_dir / f"chromedriver-{ver}-{arch}.zip"
    resp = requests.get(url, stream=True, timeout=60)
    resp.raise_for_status()
    with open(zip_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    import zipfile, shutil
    with zipfile.ZipFile(zip_path, "r") as zf:
        member = next((m for m in zf.namelist() if m.endswith("chromedriver.exe")), None)
        if not member:
            raise RuntimeError("chromedriver.exe nicht im ZIP gefunden")
        extract_dir = dest_dir / f"chromedriver-{ver}-{arch}"
        extract_dir.mkdir(parents=True, exist_ok=True)
        zf.extract(member, extract_dir)
        extracted = extract_dir / member
        final_exe = extract_dir / "chromedriver.exe"
        final_exe.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(extracted), final_exe)
        parts = member.split("/")
        if len(parts) > 1:
            top = extract_dir / parts[0]
            try:
                shutil.rmtree(top)
            except Exception:
                pass
    try:
        zip_path.unlink(missing_ok=True)
    except Exception:
        pass
    return final_exe


def _ensure_matching_chromedriver(project_root: Path) -> Path:
    chrome_major = _get_chrome_major_version()
    driver_root = project_root / "chromedriver.exe"
    current_major = _get_chromedriver_major_version(driver_root) if driver_root.exists() else -1
    if current_major == chrome_major and driver_root.exists():
        return driver_root
    if driver_root.exists():
        archive_dir = project_root / "drivers" / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        try:
            out = subprocess.check_output([str(driver_root), "--version"], stderr=subprocess.STDOUT, text=True, timeout=5)
            mfull = re.search(r"ChromeDriver\s+([0-9.]+)", out)
            ver_str = mfull.group(1) if mfull else f"{current_major}"
        except Exception:
            ver_str = f"{current_major}"
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        archived = archive_dir / f"chromedriver-{ver_str}-{ts}.exe"
        try:
            shutil.move(str(driver_root), archived)
            print(f"? Alter ChromeDriver archiviert: {archived}")
        except Exception as e:
            print(f"[WARN] Konnte alten ChromeDriver nicht archivieren: {e}")
    print(f"?? Lade passenden ChromeDriver für Chrome {chrome_major}...")
    dl_dir = project_root / "drivers" / "downloads"
    new_exe = _download_chromedriver_for_major(chrome_major, dl_dir)
    try:
        shutil.copyfile(new_exe, driver_root)
    except Exception as e:
        raise RuntimeError(f"Konnte neuen ChromeDriver nicht bereitstellen: {e}")
    print(f"V Neuer ChromeDriver installiert: {driver_root}")
    return driver_root


def _create_chrome_driver(options: Options):
    try:
        return webdriver.Chrome(options=options)
    except (SessionNotCreatedException, WebDriverException) as e:
        msg = str(e)
        mismatch = (
            "only supports Chrome version" in msg
            or "session not created" in msg.lower()
            or "This version of ChromeDriver" in msg
        )
        if not mismatch:
            raise
        print("[INFO] Detektierter Treiber/Browser-Versionskonflikt. Aktualisiere ChromeDriver...")
        driver_path = _ensure_matching_chromedriver(Path(__file__).parent)
        service = Service(executable_path=str(driver_path))
        return webdriver.Chrome(service=service, options=options)


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

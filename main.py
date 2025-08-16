import os
import re
import subprocess
import time
import pandas as pd
import requests
from pytubefix import YouTube
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# --- Konfiguration ---
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA_DIR = r"C:\ChromeData\chromeprofile"
DEBUG_PORT = "9222"
WAIT_TIMEOUT = 15

SUPABASE_URL = "http://148.230.71.150:8000/rest/v1"
SUPABASE_TABLE = "youtube_urls"
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("❌ Umgebungsvariable SUPABASE_SERVICE_KEY fehlt.")

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
    yt = YouTube(url)
    title = yt.title

    subs = yt.captions
    text = None
    if subs:
        key = next(iter(subs.keys()))
        caption = subs[key.code]
        srt_text = caption.generate_srt_captions()
        text = clean_subtitle_text(srt_text)
    print(len(text) if text else 0)
    return text

# --- Funktion: YouTube-Links upserten ---
def upsert_urls(links: list[str]):
    payload = [{"url": link, "subtitles": fetch_with_pytubefix(link)} for link in links]

    response = requests.post(
        f"{SUPABASE_URL}/{SUPABASE_TABLE}?on_conflict=url",
        headers=HDRS,
        json=payload,
        timeout=30
    )

    if not response.ok:
        raise RuntimeError(f"❌ Supabase-Upsert fehlgeschlagen: {response.status_code} {response.text}")
    print(f"✅ {len(links)} Links erfolgreich an Supabase gesendet.")

# --- Chrome starten (Debug-Modus) ---
chrome_cmd = [
    CHROME_PATH,
    f"--remote-debugging-port={DEBUG_PORT}",
    f"--user-data-dir={USER_DATA_DIR}"
]
subprocess.Popen(chrome_cmd)

# --- Warten bis DevTools-Port erreichbar ---
print("🕒 Warte auf Debug-Port...")
for _ in range(WAIT_TIMEOUT):
    try:
        res = requests.get(f"http://localhost:{DEBUG_PORT}/json/version")
        if res.status_code == 200:
            print("✅ Chrome bereit.")
            break
    except requests.exceptions.ConnectionError:
        pass
    time.sleep(1)
else:
    raise RuntimeError("❌ Chrome ist nicht erreichbar (DevTools-Port).")

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
print(f"🔗 {len(links)} YouTube-Links gesammelt.")

# --- CSV speichern ---
df = pd.DataFrame(links, columns=["url"])
df.to_csv("youtube_links.csv", index=False)
print("💾 youtube_links.csv gespeichert.")

# --- In Supabase schreiben ---
upsert_urls(links)

# --- Browser schließen ---
driver.quit()

#!/usr/bin/env python3
import os, sys, argparse, json, re, datetime, requests
from typing import Optional, Tuple

# --- YouTube via pytubefix (ohne PoToken) ---
from pytubefix import YouTube
from pytubefix.cli import on_progress

# --- Supabase-Konfiguration ---
SUPABASE_URL = "http://148.230.71.150:8000/rest/v1"
SUPABASE_SERVICE_ROLE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIiwiaXNzIjoic3VwYWJhc2UiLCJpYXQiOjE3NTQ2MDQwMDAsImV4cCI6MTkxMjM3MDQwMH0.U6IEB3t9Qw8QIH_VADtqixYhyrwrDJkpBWI2nlDxJ6w'

REST_URL = SUPABASE_URL
HDRS = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates,return=representation",
}

def clean_srt_to_text(srt_text: str) -> str:
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
    if prefer and prefer in by_code:
        return by_code[prefer]
    for fb in ("de", "en"):
        if fb in by_code:
            return by_code[fb]
    return next(iter(by_code.values())) if by_code else None

def fetch_subs(url: str, lang: Optional[str]) -> Tuple[str, Optional[str]]:
    # Versuch 1: ANDROID
    try:
        yt = YouTube(url, on_progress_callback=on_progress)
        title = yt.title or url
        cap = pick_caption(yt, lang)
        if cap:
            srt = cap.generate_srt_captions()
            return title, clean_srt_to_text(srt)
    except Exception as e:
        print(f"[WARN] ANDROID failed: {e}", file=sys.stderr)

    # Versuch 2: WEB
    try:
        yt = YouTube(url, on_progress_callback=on_progress, client="WEB")
        title = yt.title or url
        cap = pick_caption(yt, lang)
        if cap:
            srt = cap.generate_srt_captions()
            return title, clean_srt_to_text(srt)
    except Exception as e:
        print(f"[WARN] WEB failed: {e}", file=sys.stderr)

    return url, None

def upsert_result(url: str, title: str, text: Optional[str], source: str, priority: int):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    payload = {
        "url": url,
        "processed": bool(text),
        "processed_at": now,
        "source": source,
        "priority": priority,
    }
    if text:
        payload["subtitles"] = text
    r = requests.post(f"{REST_URL}/youtube_urls?on_conflict=url",
                      headers=HDRS, json=[payload], timeout=30)
    if not r.ok:
        raise RuntimeError(f"Supabase upsert failed: {r.status_code} {r.text}")

def load_unprocessed_urls() -> list[str]:
    """
    Holt alle URLs aus Supabase, bei denen 'processed' = false oder NULL ist.
    """
    params = {
        "processed": "is.false",
        "select": "url",
        "order": "added_at.asc"
    }
    r = requests.get(f"{REST_URL}/youtube_urls", headers=HDRS, params=params, timeout=30)
    if not r.ok:
        raise RuntimeError(f"❌ Fehler beim Abruf der URLs: {r.status_code} {r.text}")
    return [entry["url"] for entry in r.json() if "url" in entry]

def main():
    ap = argparse.ArgumentParser(description="Batch YouTube subtitles -> Supabase")
    ap.add_argument("--lang", default=None, help="Bevorzugte Sprachspur, z.B. de oder en")
    ap.add_argument("--source", default="vm-cron", help="Wert für Spalte 'source'")
    ap.add_argument("--priority", type=int, default=0)
    args = ap.parse_args()

    urls = load_unprocessed_urls()
    if not urls:
        print("Keine unverarbeiteten URLs gefunden.")
        return

    ok = 0
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] Hole Untertitel: {url}")
        title, text = fetch_subs(url, args.lang)
        if text:
            print(f"  -> OK ({len(text)} Zeichen)")
        else:
            print("  -> KEINE Untertitel gefunden / geblockt", file=sys.stderr)
        try:
            upsert_result(url, title, text, args.source, args.priority)
        except Exception as e:
            print(f"[ERR] Supabase upsert fehlgeschlagen: {e}", file=sys.stderr)
            continue
        ok += 1
    print(f"Fertig. {ok}/{len(urls)} Einträge verarbeitet.")

if __name__ == "__main__":
    main()

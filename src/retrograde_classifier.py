"""
Retrograde Klassifizierung für alle bestehenden YouTube-URLs in der Datenbank
"""
import os
import time
import requests
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from video_filter import VideoFilter
from filter_config import *

# Supabase Konfiguration
SUPABASE_URL = "http://148.230.71.150:8000/rest/v1"
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_KEY:
    raise ValueError("SUPABASE_SERVICE_KEY Umgebungsvariable nicht gesetzt!")

class RetrogradedClassifier:
    def __init__(self):
        self.filter = VideoFilter()
        self.headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        self.stats = {
            "total": 0,
            "processed": 0,
            "relevant": 0,
            "irrelevant": 0,
            "errors": 0,
            "deleted": 0
        }
    
    def fetch_all_urls(self, limit: Optional[int] = None) -> List[Dict]:
        """Holt alle URLs aus der Datenbank"""
        try:
            # Basis-Query für alle URLs
            url = f"{SUPABASE_URL}/youtube_urls?select=*"
            
            # Optional: Limit setzen
            if limit:
                url += f"&limit={limit}"
            
            # Sortierung nach added_at (älteste zuerst)
            url += "&order=added_at.asc"
            
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.ok:
                urls = response.json()
                print(f"[OK] {len(urls)} URLs aus Datenbank geladen")
                return urls
            else:
                print(f"[ERROR] Fehler beim Abrufen der URLs: {response.status_code}")
                print(response.text)
                return []
                
        except Exception as e:
            print(f"[ERROR] Fehler beim Datenbankzugriff: {e}")
            return []
    
    def fetch_unclassified_urls(self, limit: Optional[int] = None) -> List[Dict]:
        """Holt nur URLs ohne Klassifizierung"""
        try:
            # Query für URLs ohne classification Feld oder mit NULL
            url = f"{SUPABASE_URL}/youtube_urls?select=*"
            url += "&or=(classification.is.null,not.classification.is.null.false)"
            
            if limit:
                url += f"&limit={limit}"
            
            url += "&order=added_at.asc"
            
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.ok:
                urls = response.json()
                print(f"[OK] {len(urls)} unklassifizierte URLs gefunden")
                return urls
            else:
                print(f"[ERROR] Fehler beim Abrufen: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"[ERROR] Fehler: {e}")
            return []
    
    def update_classification(self, url: str, classification: str, 
                            relevance_score: float, method: str) -> bool:
        """Aktualisiert die Klassifizierung einer URL"""
        try:
            api_url = f"{SUPABASE_URL}/youtube_urls?url=eq.{requests.utils.quote(url)}"
            
            data = {
                "classification": classification,
                "relevance_score": relevance_score,
                "classification_method": method,
                "classified_at": datetime.now().isoformat()
            }
            
            response = requests.patch(api_url, json=data, headers=self.headers, timeout=30)
            
            return response.ok
            
        except Exception as e:
            print(f"[ERROR] Update-Fehler fuer {url}: {e}")
            return False
    
    def delete_irrelevant_url(self, url: str) -> bool:
        """Löscht eine irrelevante URL aus der Datenbank"""
        try:
            api_url = f"{SUPABASE_URL}/youtube_urls?url=eq.{requests.utils.quote(url)}"
            
            response = requests.delete(api_url, headers=self.headers, timeout=30)
            
            if response.ok:
                self.stats["deleted"] += 1
                return True
            return False
            
        except Exception as e:
            print(f"[ERROR] Loesch-Fehler fuer {url}: {e}")
            return False
    
    def extract_title_from_url(self, record: Dict) -> str:
        """Extrahiert Titel aus dem Datensatz oder generiert einen aus der URL"""
        # Prüfe ob ein Titel-Feld existiert
        if "title" in record and record["title"]:
            return record["title"]
        
        # Fallback: Verwende URL als "Titel"
        url = record.get("url", "")
        # Extrahiere Video-ID aus URL für bessere Lesbarkeit
        if "watch?v=" in url:
            video_id = url.split("watch?v=")[1].split("&")[0]
            return f"YouTube Video {video_id}"
        
        return url
    
    # METHODE 1: Batch-Klassifizierung mit automatischer Löschung
    def batch_classify_and_clean(self, auto_delete: bool = False, 
                                use_ai: bool = True, 
                                batch_size: int = 50) -> Dict:
        """
        Methode 1: Klassifiziert alle URLs in Batches und löscht optional irrelevante
        
        Args:
            auto_delete: Automatisch irrelevante URLs löschen
            use_ai: KI-Klassifizierung verwenden (falls API-Keys vorhanden)
            batch_size: Anzahl URLs pro Batch
        """
        print("\n" + "="*60)
        print("METHODE 1: Batch-Klassifizierung")
        print("="*60)
        
        # Hole alle URLs
        all_urls = self.fetch_all_urls()
        self.stats["total"] = len(all_urls)
        
        if not all_urls:
            print("Keine URLs zum Verarbeiten gefunden.")
            return self.stats
        
        print(f"\n[INFO] Starte Verarbeitung von {self.stats['total']} URLs")
        print(f"   Auto-Delete: {'JA' if auto_delete else 'NEIN'}")
        print(f"   KI-Analyse: {'JA' if use_ai else 'NEIN'}")
        print("-" * 40)
        
        # Verarbeite in Batches
        for i in range(0, len(all_urls), batch_size):
            batch = all_urls[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(all_urls) + batch_size - 1) // batch_size
            
            print(f"\n[BATCH] {batch_num}/{total_batches} ({len(batch)} URLs)")
            
            for record in batch:
                url = record.get("url")
                title = self.extract_title_from_url(record)
                subtitles = record.get("subtitles")
                
                try:
                    # Klassifiziere Video
                    is_relevant, score, method = self.filter.is_relevant(
                        title, subtitles, use_ai=use_ai
                    )
                    
                    classification = "RELEVANT" if is_relevant else "IRRELEVANT"
                    
                    # Update Klassifizierung in DB
                    if self.update_classification(url, classification, score, method):
                        self.stats["processed"] += 1
                        
                        if is_relevant:
                            self.stats["relevant"] += 1
                            print(f"  [+] RELEVANT ({score:.2f}): {title[:50]}...")
                        else:
                            self.stats["irrelevant"] += 1
                            print(f"  [-] IRRELEVANT ({score:.2f}): {title[:50]}...")
                            
                            # Optional: Lösche irrelevante URLs
                            if auto_delete:
                                if self.delete_irrelevant_url(url):
                                    print(f"    [DELETED] Geloescht")
                    else:
                        self.stats["errors"] += 1
                        
                except Exception as e:
                    self.stats["errors"] += 1
                    print(f"  [WARN] Fehler bei {url}: {e}")
                
                # Rate limiting
                time.sleep(0.1)
            
            # Zwischen-Statistik
            self._print_progress()
        
        # Finale Statistik
        self._print_final_stats()
        return self.stats
    
    # METHODE 2: Progressive Klassifizierung mit manueller Kontrolle
    def progressive_classify_with_review(self, use_ai: bool = True,
                                        review_threshold: float = 0.4) -> Dict:
        """
        Methode 2: Klassifiziert URLs progressiv mit Fortschrittsanzeige
        und optionaler manueller Review für unsichere Fälle
        
        Args:
            use_ai: KI-Klassifizierung verwenden
            review_threshold: Score-Schwelle für manuelle Review
        """
        print("\n" + "="*60)
        print("METHODE 2: Progressive Klassifizierung mit Review")
        print("="*60)
        
        # Hole nur unklassifizierte URLs
        unclassified = self.fetch_unclassified_urls()
        self.stats["total"] = len(unclassified)
        
        if not unclassified:
            print("[OK] Alle URLs sind bereits klassifiziert!")
            return self.stats
        
        print(f"\n[INFO] {self.stats['total']} unklassifizierte URLs gefunden")
        print(f"   KI-Analyse: {'JA' if use_ai else 'NEIN'}")
        print(f"   Review-Schwelle: {review_threshold}")
        print("-" * 40)
        
        review_queue = []  # URLs die manuell geprüft werden sollten
        
        for idx, record in enumerate(unclassified, 1):
            url = record.get("url")
            title = self.extract_title_from_url(record)
            subtitles = record.get("subtitles")
            
            # Fortschrittsanzeige
            progress = (idx / self.stats["total"]) * 100
            print(f"\n[{idx}/{self.stats['total']}] {progress:.1f}% - Verarbeite:")
            print(f"  [VIDEO] {title[:80]}...")
            
            try:
                # Klassifiziere
                is_relevant, score, method = self.filter.is_relevant(
                    title, subtitles, use_ai=use_ai
                )
                
                # Prüfe ob Review nötig
                needs_review = (
                    method == "mixed" or 
                    (score > review_threshold - 0.1 and score < review_threshold + 0.1)
                )
                
                if needs_review:
                    review_queue.append({
                        "url": url,
                        "title": title,
                        "score": score,
                        "method": method,
                        "preliminary": "RELEVANT" if is_relevant else "IRRELEVANT"
                    })
                    print(f"  [REVIEW] Zur Review markiert (Score: {score:.2f})")
                else:
                    classification = "RELEVANT" if is_relevant else "IRRELEVANT"
                    
                    if self.update_classification(url, classification, score, method):
                        self.stats["processed"] += 1
                        
                        if is_relevant:
                            self.stats["relevant"] += 1
                            print(f"  [+] RELEVANT (Score: {score:.2f}, Method: {method})")
                        else:
                            self.stats["irrelevant"] += 1
                            print(f"  [-] IRRELEVANT (Score: {score:.2f}, Method: {method})")
                
            except Exception as e:
                self.stats["errors"] += 1
                print(f"  [WARN] Fehler: {e}")
            
            # Rate limiting
            time.sleep(0.05)
            
            # Zeige Zwischenstand alle 10 URLs
            if idx % 10 == 0:
                self._print_progress()
        
        # Review-Queue verarbeiten
        if review_queue:
            self._process_review_queue(review_queue)
        
        # Finale Statistik
        self._print_final_stats()
        return self.stats
    
    def _process_review_queue(self, queue: List[Dict]):
        """Verarbeitet URLs die manuell überprüft werden sollten"""
        print("\n" + "="*60)
        print(f"[REVIEW QUEUE] {len(queue)} unsichere Klassifizierungen")
        print("="*60)
        
        for item in queue:
            print(f"\n[REVIEW] Review benoetigt:")
            print(f"   Titel: {item['title'][:100]}...")
            print(f"   Score: {item['score']:.2f}")
            print(f"   Methode: {item['method']}")
            print(f"   Vorlaeufig: {item['preliminary']}")
            print(f"   URL: {item['url']}")
            print("-" * 40)
        
        print("\n[INFO] Diese URLs sollten manuell ueberprueft werden.")
        print("   Nutze die Batch-Methode mit auto_delete=True nach manueller Prüfung.")
    
    def _print_progress(self):
        """Zeigt aktuellen Fortschritt"""
        if self.stats["total"] == 0:
            return
        
        progress = (self.stats["processed"] / self.stats["total"]) * 100
        print(f"\n[PROGRESS] Fortschritt: {progress:.1f}%")
        print(f"   Verarbeitet: {self.stats['processed']}/{self.stats['total']}")
        print(f"   Relevant: {self.stats['relevant']}")
        print(f"   Irrelevant: {self.stats['irrelevant']}")
        if self.stats["deleted"] > 0:
            print(f"   Geloescht: {self.stats['deleted']}")
    
    def _print_final_stats(self):
        """Zeigt finale Statistiken"""
        print("\n" + "="*60)
        print("[STATISTIK] FINALE STATISTIK")
        print("="*60)
        print(f"Total URLs:      {self.stats['total']}")
        print(f"Verarbeitet:     {self.stats['processed']}")
        print(f"Relevant:        {self.stats['relevant']} ({self._calc_percentage('relevant')}%)")
        print(f"Irrelevant:      {self.stats['irrelevant']} ({self._calc_percentage('irrelevant')}%)")
        print(f"Geloescht:        {self.stats['deleted']}")
        print(f"Fehler:          {self.stats['errors']}")
        
        if self.stats['processed'] > 0:
            relevance_rate = (self.stats['relevant'] / self.stats['processed']) * 100
            print(f"\n[RESULT] Relevanz-Rate: {relevance_rate:.1f}%")
    
    def _calc_percentage(self, key: str) -> str:
        """Berechnet Prozentsatz"""
        if self.stats['processed'] == 0:
            return "0.0"
        return f"{(self.stats[key] / self.stats['processed']) * 100:.1f}"


def main():
    """Hauptfunktion mit Menü"""
    classifier = RetrogradedClassifier()
    
    print("\n" + "="*60)
    print("[RETROGRADE YOUTUBE URL KLASSIFIZIERUNG]")
    print("="*60)
    print("\nWaehle eine Methode:\n")
    print("1. Batch-Klassifizierung (schnell, automatisch)")
    print("2. Progressive Klassifizierung mit Review (detailliert)")
    print("3. Nur irrelevante URLs loeschen (basierend auf bestehender Klassifizierung)")
    print("4. Test-Lauf (erste 10 URLs)")
    print("0. Beenden\n")
    
    choice = input("Deine Wahl (0-4): ").strip()
    
    if choice == "1":
        print("\n[WARNUNG] Auto-Delete aktivieren? (j/n): ", end="")
        auto_delete = input().strip().lower() == 'j'
        
        print("KI-Analyse verwenden? (j/n): ", end="")
        use_ai = input().strip().lower() == 'j'
        
        classifier.batch_classify_and_clean(
            auto_delete=auto_delete,
            use_ai=use_ai
        )
        
    elif choice == "2":
        print("\nKI-Analyse verwenden? (j/n): ", end="")
        use_ai = input().strip().lower() == 'j'
        
        classifier.progressive_classify_with_review(use_ai=use_ai)
        
    elif choice == "3":
        print("\n[DELETE] Loesche alle als IRRELEVANT klassifizierten URLs...")
        # Implementierung für Löschung basierend auf bestehender Klassifizierung
        urls = classifier.fetch_all_urls()
        deleted = 0
        for record in urls:
            if record.get("classification") == "IRRELEVANT":
                if classifier.delete_irrelevant_url(record["url"]):
                    deleted += 1
                    print(f"  [DELETED] Geloescht: {record.get('title', record['url'])[:50]}...")
        print(f"\n[OK] {deleted} irrelevante URLs geloescht")
        
    elif choice == "4":
        print("\n[TEST] Test-Lauf mit ersten 10 URLs...")
        original_fetch = classifier.fetch_all_urls
        classifier.fetch_all_urls = lambda: original_fetch(limit=10)
        classifier.batch_classify_and_clean(auto_delete=False, use_ai=False)
        
    elif choice == "0":
        print("\n[EXIT] Beendet")
    else:
        print("\n[ERROR] Ungueltige Auswahl")


if __name__ == "__main__":
    main()
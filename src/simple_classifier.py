"""
Vereinfachter Klassifizierer der mit der bestehenden Datenbankstruktur arbeitet
"""
import os
import requests
from typing import List, Dict
from video_filter import VideoFilter
from datetime import datetime

SUPABASE_URL = "http://148.230.71.150:8000/rest/v1"
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_KEY:
    raise ValueError("SUPABASE_SERVICE_KEY nicht gesetzt!")

class SimpleClassifier:
    def __init__(self):
        self.filter = VideoFilter()
        self.headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        self.stats = {
            "total": 0,
            "analyzed": 0,
            "relevant": 0,
            "irrelevant": 0,
            "deleted": 0
        }
    
    def fetch_all_urls(self) -> List[Dict]:
        """Holt alle URLs mit Subtitles"""
        try:
            # Hole nur URLs die Subtitles haben
            url = f"{SUPABASE_URL}/youtube_urls?select=*&subtitles=not.is.null&order=added_at.desc"
            
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.ok:
                return response.json()
            else:
                print(f"[ERROR] {response.status_code}: {response.text}")
                return []
        except Exception as e:
            print(f"[ERROR] {e}")
            return []
    
    def analyze_and_classify(self) -> Dict[str, List]:
        """Analysiert alle URLs und klassifiziert sie"""
        urls = self.fetch_all_urls()
        self.stats["total"] = len(urls)
        
        print(f"[INFO] {len(urls)} URLs mit Subtitles gefunden")
        
        relevant_urls = []
        irrelevant_urls = []
        
        for idx, record in enumerate(urls, 1):
            url = record.get("url", "")
            subtitles = record.get("subtitles", "")
            
            # Extrahiere Video-ID für "Titel"
            video_id = ""
            if "watch?v=" in url:
                video_id = url.split("watch?v=")[1].split("&")[0]
            
            # Verwende URL/Video-ID als Titel
            title = f"Video {video_id}" if video_id else url
            
            # Klassifiziere basierend auf Subtitles
            is_relevant, score, method = self.filter.is_relevant(
                title, subtitles[:2000], use_ai=False
            )
            
            self.stats["analyzed"] += 1
            
            if is_relevant:
                self.stats["relevant"] += 1
                relevant_urls.append({
                    "url": url,
                    "score": score,
                    "id": record.get("id")
                })
                print(f"[{idx}/{len(urls)}] [+] RELEVANT (Score: {score:.2f}): {url[:60]}")
            else:
                self.stats["irrelevant"] += 1
                irrelevant_urls.append({
                    "url": url,
                    "score": score,
                    "id": record.get("id")
                })
                print(f"[{idx}/{len(urls)}] [-] IRRELEVANT (Score: {score:.2f}): {url[:60]}")
            
            # Progress update alle 25 URLs
            if idx % 25 == 0:
                print(f"\n[PROGRESS] {idx}/{len(urls)} ({(idx/len(urls)*100):.1f}%)")
                print(f"  Relevant: {self.stats['relevant']}")
                print(f"  Irrelevant: {self.stats['irrelevant']}\n")
        
        return {
            "relevant": relevant_urls,
            "irrelevant": irrelevant_urls
        }
    
    def delete_irrelevant_urls(self, urls: List[Dict]) -> int:
        """Löscht irrelevante URLs"""
        deleted = 0
        
        print(f"\n[DELETE] Lösche {len(urls)} irrelevante URLs...")
        
        for url_data in urls:
            try:
                # Lösche über ID für bessere Performance
                if url_data.get("id"):
                    delete_url = f"{SUPABASE_URL}/youtube_urls?id=eq.{url_data['id']}"
                else:
                    delete_url = f"{SUPABASE_URL}/youtube_urls?url=eq.{requests.utils.quote(url_data['url'])}"
                
                response = requests.delete(delete_url, headers=self.headers, timeout=10)
                
                if response.ok:
                    deleted += 1
                    if deleted % 10 == 0:
                        print(f"  [DELETED] {deleted} URLs gelöscht...")
                
            except Exception as e:
                print(f"  [ERROR] Fehler beim Löschen: {e}")
        
        self.stats["deleted"] = deleted
        return deleted
    
    def print_statistics(self):
        """Zeigt finale Statistiken"""
        print("\n" + "="*60)
        print("[STATISTIK] FINALE ANALYSE")
        print("="*60)
        print(f"Total URLs:         {self.stats['total']}")
        print(f"Analysiert:         {self.stats['analyzed']}")
        print(f"Relevant:           {self.stats['relevant']} ({self._calc_percent('relevant')}%)")
        print(f"Irrelevant:         {self.stats['irrelevant']} ({self._calc_percent('irrelevant')}%)")
        
        if self.stats['deleted'] > 0:
            print(f"Gelöscht:           {self.stats['deleted']}")
        
        if self.stats['analyzed'] > 0:
            relevance_rate = (self.stats['relevant'] / self.stats['analyzed']) * 100
            print(f"\n[RESULT] Relevanz-Rate: {relevance_rate:.1f}%")
    
    def _calc_percent(self, key: str) -> str:
        if self.stats['analyzed'] == 0:
            return "0.0"
        return f"{(self.stats[key] / self.stats['analyzed']) * 100:.1f}"


def main():
    """Hauptfunktion"""
    classifier = SimpleClassifier()
    
    print("\n" + "="*60)
    print("[SIMPLE CLASSIFIER] YouTube URL Analyse & Bereinigung")
    print("="*60)
    
    # Analysiere alle URLs
    print("\n[STEP 1] Analysiere URLs...")
    results = classifier.analyze_and_classify()
    
    # Zeige Zwischenstatistik
    classifier.print_statistics()
    
    # Frage ob löschen
    if results["irrelevant"]:
        print(f"\n[QUESTION] {len(results['irrelevant'])} irrelevante URLs gefunden.")
        print("Diese jetzt löschen? (j/n): ", end="")
        
        try:
            choice = input().strip().lower()
            if choice == 'j':
                deleted = classifier.delete_irrelevant_urls(results["irrelevant"])
                print(f"\n[OK] {deleted} URLs gelöscht")
            else:
                print("\n[INFO] Löschung abgebrochen")
        except:
            print("\n[INFO] Automatischer Modus - keine Löschung")
    
    # Finale Statistik
    classifier.print_statistics()
    
    # Speichere Ergebnisse in Datei
    with open("classification_results.txt", "w", encoding="utf-8") as f:
        f.write("RELEVANTE URLs:\n")
        f.write("="*60 + "\n")
        for item in results["relevant"]:
            f.write(f"Score {item['score']:.2f}: {item['url']}\n")
        
        f.write("\n\nIRRELEVANTE URLs:\n")
        f.write("="*60 + "\n")
        for item in results["irrelevant"]:
            f.write(f"Score {item['score']:.2f}: {item['url']}\n")
    
    print("\n[INFO] Ergebnisse gespeichert in: classification_results.txt")


if __name__ == "__main__":
    main()
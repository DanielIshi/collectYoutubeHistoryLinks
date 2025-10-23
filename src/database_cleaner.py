"""
Datenbank-Bereinigungs-Tool für YouTube URLs
Erweiterte Funktionen zum Löschen und Verwalten von URLs
"""
import os
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta

SUPABASE_URL = "http://148.230.71.150:8000/rest/v1"
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_KEY:
    raise ValueError("SUPABASE_SERVICE_KEY Umgebungsvariable nicht gesetzt!")

class DatabaseCleaner:
    def __init__(self):
        self.headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        self.stats = {
            "deleted": 0,
            "kept": 0,
            "errors": 0
        }
    
    def delete_by_classification(self, classification: str = "IRRELEVANT") -> int:
        """Löscht alle URLs mit einer bestimmten Klassifizierung"""
        try:
            # Hole alle URLs mit der Klassifizierung
            fetch_url = f"{SUPABASE_URL}/youtube_urls?classification=eq.{classification}"
            response = requests.get(fetch_url, headers=self.headers, timeout=30)
            
            if not response.ok:
                print(f"✗ Fehler beim Abrufen: {response.status_code}")
                return 0
            
            urls = response.json()
            total = len(urls)
            
            if total == 0:
                print(f"Keine URLs mit Klassifizierung '{classification}' gefunden.")
                return 0
            
            print(f"\n⚠️  Bereit {total} URLs mit Klassifizierung '{classification}' zu löschen.")
            confirm = input("Fortfahren? (j/n): ").strip().lower()
            
            if confirm != 'j':
                print("Abgebrochen.")
                return 0
            
            # Lösche URLs
            delete_url = f"{SUPABASE_URL}/youtube_urls?classification=eq.{classification}"
            response = requests.delete(delete_url, headers=self.headers, timeout=30)
            
            if response.ok:
                print(f"✓ {total} URLs gelöscht")
                return total
            else:
                print(f"✗ Fehler beim Löschen: {response.status_code}")
                return 0
                
        except Exception as e:
            print(f"✗ Fehler: {e}")
            return 0
    
    def delete_by_score_threshold(self, max_score: float = 0.2) -> int:
        """Löscht URLs mit Relevanz-Score unter einem Schwellwert"""
        try:
            # Hole URLs unter dem Score
            fetch_url = f"{SUPABASE_URL}/youtube_urls?relevance_score=lt.{max_score}"
            response = requests.get(fetch_url, headers=self.headers, timeout=30)
            
            if not response.ok:
                print(f"✗ Fehler beim Abrufen: {response.status_code}")
                return 0
            
            urls = response.json()
            total = len(urls)
            
            if total == 0:
                print(f"Keine URLs mit Score < {max_score} gefunden.")
                return 0
            
            print(f"\n⚠️  {total} URLs mit Score < {max_score} gefunden:")
            
            # Zeige Beispiele
            for url in urls[:5]:
                title = url.get("title", url.get("url", ""))[:60]
                score = url.get("relevance_score", 0)
                print(f"  - Score {score:.2f}: {title}...")
            
            if total > 5:
                print(f"  ... und {total - 5} weitere")
            
            confirm = input("\nDiese URLs löschen? (j/n): ").strip().lower()
            
            if confirm != 'j':
                print("Abgebrochen.")
                return 0
            
            # Lösche URLs
            delete_url = f"{SUPABASE_URL}/youtube_urls?relevance_score=lt.{max_score}"
            response = requests.delete(delete_url, headers=self.headers, timeout=30)
            
            if response.ok:
                print(f"✓ {total} URLs gelöscht")
                return total
            else:
                print(f"✗ Fehler beim Löschen: {response.status_code}")
                return 0
                
        except Exception as e:
            print(f"✗ Fehler: {e}")
            return 0
    
    def delete_old_irrelevant(self, days: int = 30) -> int:
        """Löscht irrelevante URLs die älter als X Tage sind"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Hole alte irrelevante URLs
            fetch_url = f"{SUPABASE_URL}/youtube_urls"
            fetch_url += f"?classification=eq.IRRELEVANT"
            fetch_url += f"&added_at=lt.{cutoff_date}"
            
            response = requests.get(fetch_url, headers=self.headers, timeout=30)
            
            if not response.ok:
                print(f"✗ Fehler beim Abrufen: {response.status_code}")
                return 0
            
            urls = response.json()
            total = len(urls)
            
            if total == 0:
                print(f"Keine irrelevanten URLs älter als {days} Tage gefunden.")
                return 0
            
            print(f"\n⚠️  {total} irrelevante URLs älter als {days} Tage gefunden.")
            confirm = input("Diese löschen? (j/n): ").strip().lower()
            
            if confirm != 'j':
                print("Abgebrochen.")
                return 0
            
            # Lösche URLs
            delete_url = f"{SUPABASE_URL}/youtube_urls"
            delete_url += f"?classification=eq.IRRELEVANT"
            delete_url += f"&added_at=lt.{cutoff_date}"
            
            response = requests.delete(delete_url, headers=self.headers, timeout=30)
            
            if response.ok:
                print(f"✓ {total} alte irrelevante URLs gelöscht")
                return total
            else:
                print(f"✗ Fehler beim Löschen: {response.status_code}")
                return 0
                
        except Exception as e:
            print(f"✗ Fehler: {e}")
            return 0
    
    def delete_by_keywords(self, keywords: List[str], in_title: bool = True, 
                          in_subtitles: bool = False) -> int:
        """Löscht URLs die bestimmte Keywords enthalten"""
        try:
            all_urls = []
            
            # Hole alle URLs (müssen wir manuell filtern für Keyword-Suche)
            fetch_url = f"{SUPABASE_URL}/youtube_urls?select=*"
            response = requests.get(fetch_url, headers=self.headers, timeout=30)
            
            if not response.ok:
                print(f"✗ Fehler beim Abrufen: {response.status_code}")
                return 0
            
            all_records = response.json()
            
            # Filtere nach Keywords
            to_delete = []
            for record in all_records:
                url = record.get("url", "")
                title = record.get("title", "").lower() if record.get("title") else ""
                subtitles = record.get("subtitles", "").lower() if record.get("subtitles") else ""
                
                for keyword in keywords:
                    keyword_lower = keyword.lower()
                    found = False
                    
                    if in_title and keyword_lower in title:
                        found = True
                    if in_subtitles and keyword_lower in subtitles:
                        found = True
                    
                    if found:
                        to_delete.append(record)
                        break
            
            if not to_delete:
                print(f"Keine URLs mit Keywords {keywords} gefunden.")
                return 0
            
            print(f"\n⚠️  {len(to_delete)} URLs mit Keywords gefunden:")
            for record in to_delete[:5]:
                title = record.get("title", record.get("url", ""))[:60]
                print(f"  - {title}...")
            
            if len(to_delete) > 5:
                print(f"  ... und {len(to_delete) - 5} weitere")
            
            confirm = input("\nDiese URLs löschen? (j/n): ").strip().lower()
            
            if confirm != 'j':
                print("Abgebrochen.")
                return 0
            
            # Lösche URLs einzeln
            deleted = 0
            for record in to_delete:
                url = record.get("url")
                delete_url = f"{SUPABASE_URL}/youtube_urls?url=eq.{requests.utils.quote(url)}"
                response = requests.delete(delete_url, headers=self.headers, timeout=10)
                if response.ok:
                    deleted += 1
            
            print(f"✓ {deleted} URLs gelöscht")
            return deleted
            
        except Exception as e:
            print(f"✗ Fehler: {e}")
            return 0
    
    def show_statistics(self):
        """Zeigt Statistiken der Datenbank"""
        try:
            # Gesamtanzahl
            response = requests.get(
                f"{SUPABASE_URL}/youtube_urls?select=*",
                headers={**self.headers, "Prefer": "count=exact"},
                timeout=30
            )
            total = int(response.headers.get("content-range", "0-0/0").split("/")[1])
            
            # Nach Klassifizierung
            stats = {}
            for classification in ["RELEVANT", "IRRELEVANT", None]:
                if classification:
                    url = f"{SUPABASE_URL}/youtube_urls?classification=eq.{classification}&select=*"
                else:
                    url = f"{SUPABASE_URL}/youtube_urls?classification=is.null&select=*"
                
                response = requests.get(
                    url,
                    headers={**self.headers, "Prefer": "count=exact"},
                    timeout=30
                )
                count = int(response.headers.get("content-range", "0-0/0").split("/")[1])
                stats[classification or "UNCLASSIFIED"] = count
            
            # Nach Verarbeitung
            processed_url = f"{SUPABASE_URL}/youtube_urls?processed=eq.true&select=*"
            response = requests.get(
                processed_url,
                headers={**self.headers, "Prefer": "count=exact"},
                timeout=30
            )
            processed = int(response.headers.get("content-range", "0-0/0").split("/")[1])
            
            # Ausgabe
            print("\n" + "="*60)
            print("📊 DATENBANK STATISTIKEN")
            print("="*60)
            print(f"Gesamt URLs:        {total}")
            print(f"Verarbeitet:        {processed}")
            print(f"Unverarbeitet:      {total - processed}")
            print("\nKlassifizierung:")
            print(f"  Relevant:         {stats.get('RELEVANT', 0)}")
            print(f"  Irrelevant:       {stats.get('IRRELEVANT', 0)}")
            print(f"  Unklassifiziert:  {stats.get('UNCLASSIFIED', 0)}")
            
            if total > 0:
                relevance_rate = (stats.get('RELEVANT', 0) / total) * 100
                print(f"\n✨ Relevanz-Rate:    {relevance_rate:.1f}%")
            
        except Exception as e:
            print(f"✗ Fehler beim Abrufen der Statistiken: {e}")
    
    def interactive_clean(self):
        """Interaktive Bereinigung mit Vorschau"""
        while True:
            print("\n" + "="*60)
            print("🧹 INTERAKTIVE DATENBANK-BEREINIGUNG")
            print("="*60)
            
            self.show_statistics()
            
            print("\n📋 Optionen:")
            print("1. Lösche alle IRRELEVANT klassifizierten URLs")
            print("2. Lösche URLs mit Score unter Schwellwert")
            print("3. Lösche alte irrelevante URLs")
            print("4. Lösche URLs mit bestimmten Keywords")
            print("5. Statistiken aktualisieren")
            print("0. Beenden")
            
            choice = input("\nDeine Wahl (0-5): ").strip()
            
            if choice == "1":
                self.delete_by_classification("IRRELEVANT")
                
            elif choice == "2":
                score = float(input("Max Score (z.B. 0.2): ").strip())
                self.delete_by_score_threshold(score)
                
            elif choice == "3":
                days = int(input("Älter als wie viele Tage? ").strip())
                self.delete_old_irrelevant(days)
                
            elif choice == "4":
                keywords_input = input("Keywords (komma-getrennt): ").strip()
                keywords = [k.strip() for k in keywords_input.split(",")]
                print("Suche in: 1) Nur Titel, 2) Nur Untertitel, 3) Beides")
                scope = input("Wahl (1-3): ").strip()
                
                in_title = scope in ["1", "3"]
                in_subtitles = scope in ["2", "3"]
                
                self.delete_by_keywords(keywords, in_title, in_subtitles)
                
            elif choice == "5":
                continue  # Statistiken werden automatisch aktualisiert
                
            elif choice == "0":
                print("\n👋 Beendet")
                break
            else:
                print("❌ Ungültige Auswahl")


def main():
    """Hauptfunktion"""
    cleaner = DatabaseCleaner()
    
    print("\n" + "="*60)
    print("🗑️ DATENBANK BEREINIGUNGS-TOOL")
    print("="*60)
    print("\n1. Schnell-Löschung (alle irrelevanten)")
    print("2. Interaktive Bereinigung")
    print("3. Nur Statistiken anzeigen")
    print("0. Beenden")
    
    choice = input("\nDeine Wahl (0-3): ").strip()
    
    if choice == "1":
        cleaner.delete_by_classification("IRRELEVANT")
        
    elif choice == "2":
        cleaner.interactive_clean()
        
    elif choice == "3":
        cleaner.show_statistics()
        
    elif choice == "0":
        print("\n👋 Beendet")
    else:
        print("❌ Ungültige Auswahl")


if __name__ == "__main__":
    main()
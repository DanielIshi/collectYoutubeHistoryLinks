"""
Video-Filter-Modul für KI/Tech-relevante YouTube-Videos
"""
import re
from typing import Tuple, Optional
import requests
import json
from .filter_config import *

class VideoFilter:
    def __init__(self):
        self.keywords = {kw.lower() for kw in TECH_KEYWORDS}
        self.exclude_keywords = {kw.lower() for kw in EXCLUDE_KEYWORDS}
        self.ai_available = self._check_ai_availability()
        
    def _check_ai_availability(self) -> bool:
        """Prüft ob eine KI-API verfügbar ist"""
        if PREFERRED_AI_API == "openai" and OPENAI_API_KEY:
            return True
        elif PREFERRED_AI_API == "anthropic" and ANTHROPIC_API_KEY:
            return True
        return False
    
    def calculate_keyword_score(self, title: str, subtitles: Optional[str] = None) -> float:
        """
        Berechnet einen Relevanz-Score basierend auf Keywords
        Returns: Score zwischen 0 und 1
        """
        text = title.lower()
        if subtitles:
            # Nur erste 1000 Zeichen der Untertitel für Performance
            text += " " + subtitles[:1000].lower()
        
        # Check für Ausschluss-Keywords
        for exclude_kw in self.exclude_keywords:
            if exclude_kw in text:
                return 0.0
        
        # Zähle Keyword-Matches
        matches = 0
        matched_keywords = set()
        
        for keyword in self.keywords:
            if keyword in text:
                matches += 1
                matched_keywords.add(keyword)
        
        # Bonus für bestimmte starke Indikatoren
        strong_indicators = {'ai', 'künstliche intelligenz', 'machine learning', 
                            'gpt', 'programming', 'coding', 'robotics'}
        strong_matches = matched_keywords & strong_indicators
        
        if strong_matches:
            matches += len(strong_matches) * 2
        
        # Normalisiere Score (max 10 matches = 1.0)
        score = min(matches / 10, 1.0)
        
        return score
    
    def ai_classify(self, title: str, subtitles: Optional[str] = None) -> str:
        """
        Nutzt KI zur Klassifikation des Videos
        Returns: "RELEVANT", "IRRELEVANT", oder "UNSURE"
        """
        if not self.ai_available:
            return "UNSURE"
        
        subtitle_preview = (subtitles[:500] if subtitles else "Keine Untertitel verfügbar")
        prompt = AI_CLASSIFICATION_PROMPT.format(
            title=title,
            subtitle_preview=subtitle_preview
        )
        
        try:
            if PREFERRED_AI_API == "openai":
                return self._openai_classify(prompt)
            elif PREFERRED_AI_API == "anthropic":
                return self._anthropic_classify(prompt)
        except Exception as e:
            print(f"KI-Klassifikation fehlgeschlagen: {e}")
            return "UNSURE"
        
        return "UNSURE"
    
    def _openai_classify(self, prompt: str) -> str:
        """OpenAI API Aufruf"""
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": "Du bist ein Experte für Tech-Content-Klassifikation."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 10
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=10
        )
        
        if response.ok:
            result = response.json()
            answer = result["choices"][0]["message"]["content"].strip().upper()
            if answer in ["RELEVANT", "IRRELEVANT", "UNSURE"]:
                return answer
        
        return "UNSURE"
    
    def _anthropic_classify(self, prompt: str) -> str:
        """Anthropic API Aufruf"""
        headers = {
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": ANTHROPIC_MODEL,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 10,
            "temperature": 0.3
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=10
        )
        
        if response.ok:
            result = response.json()
            answer = result["content"][0]["text"].strip().upper()
            if answer in ["RELEVANT", "IRRELEVANT", "UNSURE"]:
                return answer
        
        return "UNSURE"
    
    def is_relevant(self, title: str, subtitles: Optional[str] = None, 
                   use_ai: bool = True) -> Tuple[bool, float, str]:
        """
        Hauptfunktion zur Relevanz-Bestimmung
        
        Returns:
            - is_relevant (bool): True wenn Video relevant ist
            - score (float): Relevanz-Score (0-1)
            - method (str): Verwendete Methode ("keywords", "ai", "mixed")
        """
        # Schritt 1: Keyword-Analyse
        keyword_score = self.calculate_keyword_score(title, subtitles)
        
        # Eindeutige Fälle basierend auf Keywords
        if keyword_score >= MIN_KEYWORD_SCORE and keyword_score > AI_ANALYSIS_MAX_SCORE:
            return True, keyword_score, "keywords"
        
        if keyword_score < AI_ANALYSIS_MIN_SCORE:
            return False, keyword_score, "keywords"
        
        # Schritt 2: KI-Analyse für unsichere Fälle
        if use_ai and self.ai_available and AI_ANALYSIS_MIN_SCORE <= keyword_score <= AI_ANALYSIS_MAX_SCORE:
            ai_result = self.ai_classify(title, subtitles)
            
            if ai_result == "RELEVANT":
                # Boost score wenn KI sagt relevant
                adjusted_score = min(keyword_score + 0.3, 1.0)
                return True, adjusted_score, "ai"
            elif ai_result == "IRRELEVANT":
                return False, keyword_score, "ai"
            else:
                # Bei UNSURE: Nutze Keyword-Score
                return keyword_score >= MIN_KEYWORD_SCORE, keyword_score, "mixed"
        
        # Fallback: Nutze nur Keyword-Score
        return keyword_score >= MIN_KEYWORD_SCORE, keyword_score, "keywords"


def test_filter():
    """Test-Funktion zum Prüfen des Filters"""
    filter = VideoFilter()
    
    test_cases = [
        ("ChatGPT Tutorial: How to use AI for coding", None),
        ("Building a Robot with Arduino", None),
        ("My Morning Routine Vlog", None),
        ("Python Machine Learning Course", "In this video we learn about neural networks"),
        ("Fortnite Gameplay - Victory Royale!", None),
        ("Künstliche Intelligenz erklärt", None),
    ]
    
    print("Filter-Test:\n" + "="*50)
    for title, subs in test_cases:
        is_relevant, score, method = filter.is_relevant(title, subs, use_ai=False)
        status = "[RELEVANT]" if is_relevant else "[IRRELEVANT]"
        print(f"{status} (Score: {score:.2f}, Method: {method})")
        print(f"  Titel: {title}\n")


if __name__ == "__main__":
    test_filter()
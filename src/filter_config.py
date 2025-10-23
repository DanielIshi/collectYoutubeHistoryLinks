"""
Konfiguration für Video-Filterung nach KI/Tech-Themen
"""
import os

# --- Keyword-basierte Filterung ---
TECH_KEYWORDS = {
    # KI/ML Keywords
    'ai', 'artificial intelligence', 'künstliche intelligenz', 'ki',
    'machine learning', 'deep learning', 'neural network',
    'gpt', 'chatgpt', 'openai', 'anthropic', 'claude', 'gemini', 'bard',
    'llm', 'large language model', 'transformer', 'nlp',
    'computer vision', 'reinforcement learning',
    'generative ai', 'stable diffusion', 'midjourney', 'dall-e',
    
    # Robotik
    'robotics', 'robotik', 'robot', 'roboter',
    'boston dynamics', 'automation', 'automatisierung',
    
    # Tech/Computer
    'programming', 'programmierung', 'coding', 'software',
    'python', 'javascript', 'typescript', 'rust', 'golang',
    'framework', 'api', 'backend', 'frontend', 'fullstack',
    'cloud', 'aws', 'azure', 'google cloud', 'docker', 'kubernetes',
    'linux', 'windows', 'macos', 'operating system',
    'database', 'datenbank', 'sql', 'nosql', 'mongodb', 'postgresql',
    'cybersecurity', 'hacking', 'security', 'encryption',
    'blockchain', 'crypto', 'bitcoin', 'ethereum', 'web3',
    'quantum computing', 'quantencomputer',
    
    # Tech Companies & Products
    'microsoft', 'google', 'apple', 'meta', 'amazon', 'tesla', 'nvidia',
    'github', 'gitlab', 'stack overflow', 'raspberry pi', 'arduino',
    
    # Data Science
    'data science', 'data analysis', 'big data', 'analytics',
    'pandas', 'numpy', 'scikit-learn', 'tensorflow', 'pytorch',
    
    # Development & DevOps
    'devops', 'ci/cd', 'git', 'agile', 'scrum',
    'microservices', 'serverless', 'restful', 'graphql',
    'react', 'vue', 'angular', 'nodejs', 'nextjs',
    
    # Emerging Tech
    'augmented reality', 'ar', 'virtual reality', 'vr', 'metaverse',
    'iot', 'internet of things', '5g', '6g',
    'edge computing', 'fog computing'
}

# Negative Keywords (Videos mit diesen Keywords werden ausgeschlossen)
EXCLUDE_KEYWORDS = {
    'music video', 'official video', 'reaction', 'vlog', 'haul',
    'makeup', 'fashion', 'cooking', 'recipe', 'travel vlog',
    'gaming', 'gameplay', 'let\'s play', 'fortnite', 'minecraft',
    'shorts', 'tiktok', 'instagram reels'
}

# --- KI-basierte Analyse Konfiguration ---
# OpenAI API (optional, falls du OpenAI nutzen möchtest)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"  # Günstigeres Modell für Klassifikation

# Anthropic API (optional, falls du Claude nutzen möchtest)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = "claude-3-haiku-20240307"  # Schnelles, günstiges Modell

# Welche API soll primär genutzt werden? ("openai", "anthropic", oder None für nur Keywords)
PREFERRED_AI_API = os.environ.get("PREFERRED_AI_API", None)

# --- Filter-Einstellungen ---
# Minimum Score für Keyword-Matching (0-1)
MIN_KEYWORD_SCORE = 0.3

# Verwende KI-Analyse nur wenn Keyword-Score zwischen diesen Werten liegt
AI_ANALYSIS_MIN_SCORE = 0.2  # Unter diesem Wert: definitiv irrelevant
AI_ANALYSIS_MAX_SCORE = 0.6  # Über diesem Wert: definitiv relevant

# --- Analyse Prompt ---
AI_CLASSIFICATION_PROMPT = """
Analysiere diesen YouTube-Video Titel und die Untertitel (falls vorhanden) und bestimme, 
ob das Video relevant für jemanden ist, der sich für folgende Themen interessiert:
- Künstliche Intelligenz / Machine Learning
- Programmierung / Software-Entwicklung  
- Computer / Technologie
- Robotik / Automation

Titel: {title}
Untertitel (erste 500 Zeichen): {subtitle_preview}

Antworte NUR mit einer der folgenden Optionen:
RELEVANT - wenn das Video eindeutig zu den genannten Themen gehört
IRRELEVANT - wenn das Video nichts mit den Themen zu tun hat
UNSURE - wenn du dir nicht sicher bist

Antwort:
"""
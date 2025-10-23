# YouTube History Collector

Dieses Tool sammelt Links aus Ihrem YouTube-Verlauf und filtert sie nach KI- und Tech-relevanten Inhalten.

## Installation

1. Klonen Sie das Repository
2. Erstellen Sie eine virtuelle Umgebung:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # ODER
   .venv\Scripts\activate  # Windows
   ```
3. Installieren Sie die Abhängigkeiten:
   ```bash
   pip install -e .
   ```

## Konfiguration

1. Stellen Sie sicher, dass Chrome installiert ist
2. Passen Sie die Konfigurationsdateien in `config/` an
3. Setzen Sie die erforderlichen Umgebungsvariablen:
   - `SUPABASE_SERVICE_KEY` (für Supabase-Integration)
   - `OPENAI_API_KEY` (optional für KI-Klassifikation)
   - `ANTHROPIC_API_KEY` (optional für KI-Klassifikation)

## Verwendung

```bash
python -m src.main
```

Das Tool wird:
1. Chrome im Debug-Modus starten
2. Ihren YouTube-Verlauf laden
3. Links sammeln und in eine CSV-Datei speichern
4. Die Links nach KI/Tech-Relevanz filtern
5. Relevante Links in Supabase speichern

## Projektstruktur

```
├── src/                # Hauptquellcode
├── tests/              # Testdateien
├── docs/               # Dokumentation
├── scripts/            # Hilfsskripte
├── config/             # Konfigurationsdateien
└── README.md          # Diese Datei
```

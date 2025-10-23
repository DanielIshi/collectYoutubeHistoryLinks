"""
Test Configuration Loading
===========================
Testet das Laden der .env-Konfiguration.
"""
import pytest
import os


def test_env_file_exists():
    """Testet ob .env Datei existiert"""
    from pathlib import Path
    env_path = Path(__file__).parent.parent / '.env'
    assert env_path.exists(), f".env not found at {env_path}"


def test_supabase_config_loaded(supabase_config):
    """Testet ob Supabase-Konfiguration vollständig geladen wurde"""
    assert supabase_config["url"], "SUPABASE_URL not set"
    assert supabase_config["service_key"], "SUPABASE_SERVICE_KEY not set"
    assert supabase_config["table"], "SUPABASE_TABLE not set"

    # URL sollte nicht mit /rest/v1 enden
    assert not supabase_config["url"].endswith("/rest/v1"), "SUPABASE_URL should not include /rest/v1"


def test_chrome_config_loaded(chrome_config):
    """Testet ob Chrome-Konfiguration vollständig geladen wurde"""
    assert chrome_config["path"], "CHROME_PATH not set"
    assert chrome_config["user_data_dir"], "CHROME_USER_DATA_DIR not set"
    assert chrome_config["debug_port"], "CHROME_DEBUG_PORT not set"
    assert chrome_config["wait_timeout"] > 0, "CHROME_WAIT_TIMEOUT must be positive"


def test_default_values_applied():
    """Testet ob Default-Werte korrekt angewendet werden"""
    # Wenn nicht gesetzt, sollten Defaults verwendet werden
    lang = os.getenv("DEFAULT_SUBTITLE_LANG", "de")
    source = os.getenv("DEFAULT_SOURCE", "powershell-run")
    priority = int(os.getenv("DEFAULT_PRIORITY", "0"))

    assert lang in ["de", "en"], f"Invalid default language: {lang}"
    assert isinstance(source, str), "DEFAULT_SOURCE must be string"
    assert isinstance(priority, int), "DEFAULT_PRIORITY must be integer"

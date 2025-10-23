"""
pytest Configuration and Fixtures
==================================
Gemeinsame Test-Konfiguration und wiederverwendbare Fixtures.
"""
import pytest
import os
from pathlib import Path
from dotenv import load_dotenv

@pytest.fixture(scope="session", autouse=True)
def load_test_env():
    """Lädt .env für alle Tests"""
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        yield
    else:
        pytest.skip("No .env file found - skipping tests that require configuration")


@pytest.fixture
def supabase_config():
    """Provides Supabase configuration from .env"""
    config = {
        "url": os.getenv("SUPABASE_URL"),
        "service_key": os.getenv("SUPABASE_SERVICE_KEY"),
        "table": os.getenv("SUPABASE_TABLE", "youtube_urls"),
    }

    if not config["url"] or not config["service_key"]:
        pytest.skip("Supabase configuration incomplete in .env")

    return config


@pytest.fixture
def chrome_config():
    """Provides Chrome configuration from .env"""
    config = {
        "path": os.getenv("CHROME_PATH", r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        "user_data_dir": os.getenv("CHROME_USER_DATA_DIR", r"C:\ChromeData\chromeprofile"),
        "debug_port": os.getenv("CHROME_DEBUG_PORT", "9222"),
        "wait_timeout": int(os.getenv("CHROME_WAIT_TIMEOUT", "15")),
    }

    return config


@pytest.fixture
def sample_youtube_urls():
    """Provides sample YouTube URLs for testing"""
    return [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=9bZkp7q19f0",
        "https://youtu.be/jNQXAC9IVRw",
    ]

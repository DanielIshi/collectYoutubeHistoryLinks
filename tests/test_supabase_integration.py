"""
Test Supabase Integration
==========================
End-to-End Tests für Supabase-Anbindung.
WICHTIG: Diese Tests benötigen eine funktionierende Supabase-Instanz!
"""
import pytest
import requests


@pytest.mark.integration
def test_supabase_connection(supabase_config):
    """Testet ob Verbindung zu Supabase hergestellt werden kann"""
    url = f"{supabase_config['url']}/rest/v1/"
    headers = {
        "apikey": supabase_config["service_key"],
        "Authorization": f"Bearer {supabase_config['service_key']}",
    }

    response = requests.get(url, headers=headers, timeout=10)

    # Status sollte 200 oder 404 sein (404 = kein Pfad, aber Server erreichbar)
    assert response.status_code in [200, 404], f"Supabase not reachable: {response.status_code}"


@pytest.mark.integration
def test_youtube_urls_table_exists(supabase_config):
    """Testet ob youtube_urls Tabelle existiert"""
    url = f"{supabase_config['url']}/rest/v1/{supabase_config['table']}?select=url&limit=1"
    headers = {
        "apikey": supabase_config["service_key"],
        "Authorization": f"Bearer {supabase_config['service_key']}",
        "Content-Type": "application/json",
    }

    response = requests.get(url, headers=headers, timeout=10)

    # Sollte erfolgreich sein (auch wenn keine Daten vorhanden)
    assert response.status_code == 200, f"Table query failed: {response.text}"

    # Response sollte JSON-Array sein
    data = response.json()
    assert isinstance(data, list), "Response should be a list"


@pytest.mark.integration
def test_fetch_existing_urls(supabase_config):
    """Testet ob existierende URLs abgerufen werden können"""
    url = f"{supabase_config['url']}/rest/v1/{supabase_config['table']}?select=url&limit=10"
    headers = {
        "apikey": supabase_config["service_key"],
        "Authorization": f"Bearer {supabase_config['service_key']}",
        "Content-Type": "application/json",
    }

    response = requests.get(url, headers=headers, timeout=10)

    assert response.status_code == 200
    data = response.json()

    # Jeder Eintrag sollte 'url' Key haben
    for entry in data:
        assert "url" in entry, "Each entry should have 'url' field"


@pytest.mark.integration
@pytest.mark.skip(reason="Test würde echte Daten in DB schreiben - nur manuell ausführen")
def test_upsert_test_url(supabase_config):
    """
    Testet das Einfügen einer Test-URL.
    SKIP: Test würde echte Daten schreiben - nur für manuelle Tests.
    """
    test_url = "https://www.youtube.com/watch?v=TEST_URL_12345"

    url = f"{supabase_config['url']}/rest/v1/{supabase_config['table']}?on_conflict=url"
    headers = {
        "apikey": supabase_config["service_key"],
        "Authorization": f"Bearer {supabase_config['service_key']}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation",
    }

    payload = [{
        "url": test_url,
        "processed": False,
        "source": "pytest",
        "priority": 0,
    }]

    response = requests.post(url, headers=headers, json=payload, timeout=10)

    assert response.status_code == 201, f"Upsert failed: {response.text}"
    data = response.json()
    assert len(data) > 0
    assert data[0]["url"] == test_url

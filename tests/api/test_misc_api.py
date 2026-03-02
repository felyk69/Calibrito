import pytest

def test_detect_device(client):
    response = client.get("/api/v1/detect-device")
    assert response.status_code == 200
    assert "connected" in response.json()

def test_get_settings(client):
    response = client.get("/api/v1/settings")
    assert response.status_code == 200
    assert "books_folder" in response.json()
    assert "scanner_threads" in response.json()

def test_list_folders_root(client):
    response = client.get("/api/v1/folders?path=")
    assert response.status_code == 200
    data = response.json()
    assert "folders" in data
    # Windows should return at least 1 drive (e.g. C:\)
    assert len(data["folders"]) > 0

def test_list_profiles(client):
    response = client.get("/api/v1/profiles")
    assert response.status_code == 200

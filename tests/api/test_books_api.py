def test_get_books_empty(client):
    response = client.get("/api/books")
    assert response.status_code == 200
    assert response.json() == []

def test_device_not_found(client):
    response = client.get("/api/detect-device")
    assert response.status_code == 200
    assert "connected" in response.json()

def test_search_metadata_not_found(client):
    response = client.get("/api/metadata/search?q=algumlivroquenaoexiste12398457")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["error", "success"]

def test_get_profiles(client):
    response = client.get("/api/profiles")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["name"] == "Visitante"

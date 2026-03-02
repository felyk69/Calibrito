import pytest
from httpx import AsyncClient
import sqlite3

def test_auto_rename_books(client):
    """Test auto rename endpoint."""
    response = client.post("/api/v1/books/auto-rename")
    assert response.status_code == 200
    assert "renamed" in response.json()
    assert "skipped" in response.json()
    assert "errors" in response.json()

def test_find_duplicates(client):
    """Test find duplicates endpoint."""
    response = client.get("/api/v1/books/duplicates")
    assert response.status_code == 200
    assert "groups" in response.json()
    assert "total_groups" in response.json()

def test_delete_books_empty(client):
    """Test batch delete with empty list."""
    response = client.post("/api/v1/delete", json={"ids": [], "permanent": False})
    # Since there are no elements, it might succeed and do nothing, or throw if they require len > 0.
    # We just ensure it doesn't crash 500.
    assert response.status_code in [200, 422]

def test_get_books_empty(client):
    """Test get books list."""
    response = client.get("/api/v1/books")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_get_books_with_filters(client):
    """Test get books with search query."""
    response = client.get("/api/v1/books?search=test&format=epub")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

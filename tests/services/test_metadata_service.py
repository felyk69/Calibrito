import pytest
from unittest.mock import patch
from app.services.metadata_service import search_metadata, _is_safe_url

def test_is_safe_url():
    """Test the SSRF protection on urls."""
    assert _is_safe_url("http://google.com") == True
    assert _is_safe_url("https://covers.openlibrary.org/b/id/1.jpg") == True
    assert _is_safe_url("http://127.0.0.1/admin") == False
    assert _is_safe_url("http://localhost:8080") == False
    assert _is_safe_url("file:///etc/passwd") == False

@patch("app.services.metadata_service._search_google_books")
@patch("app.services.metadata_service._search_openlibrary")
def test_search_metadata_success(mock_openlib, mock_google):
    """Test the search metadata function with a mocked successful response."""
    mock_google.return_value = []
    mock_openlib.return_value = [
        {
            "title": "Mock Book",
            "author": "Mock Author",
            "year": 2024,
            "publisher": "Mock Publisher",
            "coverUrl": "http://mock/cover.jpg"
        }
    ]
    
    results = search_metadata("Mock Book")
    assert results["status"] == "success"
    assert len(results["results"]) > 0
    assert results["results"][0]["title"] == "Mock Book"
    assert results["results"][0]["author"] == "Mock Author"
    assert results["results"][0]["year"] == 2024
    assert "coverUrl" in results["results"][0]

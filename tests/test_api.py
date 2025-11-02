"""
Integration tests for API endpoints.
Own thought process: End-to-end testing strategy for all endpoints.
"""
import pytest
from unittest.mock import patch, MagicMock

from app.models import Paragraph


class TestFetchEndpoint:
    """Tests for /fetch endpoint."""
    
    @patch('app.services.fetch_paragraph_from_api')
    def test_fetch_endpoint_success(self, mock_fetch, client):
        """Test successful paragraph fetching."""
        mock_fetch.return_value = "This is a test paragraph with multiple words."
        
        response = client.get("/fetch")
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "content" in data
        assert "created_at" in data
        assert data["content"] == "This is a test paragraph with multiple words."
    
    @patch('app.services.fetch_paragraph_from_api')
    def test_fetch_endpoint_failure(self, mock_fetch, client):
        """Test fetch endpoint error handling."""
        mock_fetch.side_effect = Exception("API Error")
        
        response = client.get("/fetch")
        assert response.status_code == 500


class TestSearchEndpoint:
    """Tests for /search endpoint."""
    
    def test_search_or_operator(self, client, db_session):
        """Test search with OR operator."""
        # Add test data
        p1 = Paragraph(content="The quick brown fox")
        p2 = Paragraph(content="The lazy dog")
        p3 = Paragraph(content="A different story")
        db_session.add_all([p1, p2, p3])
        db_session.commit()
        
        response = client.post(
            "/search",
            json={"words": ["fox", "dog"], "operator": "or"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["paragraphs"]) == 2
    
    def test_search_and_operator(self, client, db_session):
        """Test search with AND operator."""
        # Add test data
        p1 = Paragraph(content="The fox and the dog are friends")
        p2 = Paragraph(content="The fox runs fast")
        p3 = Paragraph(content="The dog barks loud")
        db_session.add_all([p1, p2, p3])
        db_session.commit()
        
        response = client.post(
            "/search",
            json={"words": ["fox", "dog"], "operator": "and"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert "fox and the dog" in data["paragraphs"][0]["content"]
    
    def test_search_no_results(self, client, db_session):
        """Test search with no matching results."""
        p1 = Paragraph(content="The quick brown fox")
        db_session.add(p1)
        db_session.commit()
        
        response = client.post(
            "/search",
            json={"words": ["elephant", "zebra"], "operator": "or"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert len(data["paragraphs"]) == 0
    
    def test_search_invalid_operator(self, client):
        """Test search with invalid operator."""
        response = client.post(
            "/search",
            json={"words": ["test"], "operator": "invalid"}
        )
        assert response.status_code == 422  # Validation error
    
    def test_search_empty_words(self, client):
        """Test search with empty words list."""
        response = client.post(
            "/search",
            json={"words": [], "operator": "or"}
        )
        assert response.status_code == 422  # Validation error


class TestDictionaryEndpoint:
    """Tests for /dictionary endpoint."""
    
    @patch('app.services.get_word_definition')
    def test_dictionary_endpoint(self, mock_definition, client, db_session):
        """Test dictionary endpoint with mock definitions."""
        # Add test data with repeated words
        p1 = Paragraph(content="hello world hello test")
        p2 = Paragraph(content="world test world hello")
        db_session.add_all([p1, p2])
        db_session.commit()
        
        # Mock definition responses
        mock_definition.return_value = ["A test definition"]
        
        response = client.get("/dictionary")
        assert response.status_code == 200
        data = response.json()
        assert "top_words" in data
        assert len(data["top_words"]) <= 10
        
        # Verify structure
        for word_data in data["top_words"]:
            assert "word" in word_data
            assert "frequency" in word_data
            assert "definitions" in word_data
    
    def test_dictionary_empty_database(self, client, db_session):
        """Test dictionary endpoint with no paragraphs."""
        response = client.get("/dictionary")
        assert response.status_code == 200
        data = response.json()
        assert len(data["top_words"]) == 0
    
    @patch('app.services.get_word_definition')
    def test_dictionary_word_order(self, mock_definition, client, db_session):
        """Test that words are ordered by frequency."""
        # Create content with known frequencies
        p1 = Paragraph(content="apple apple apple banana banana cherry")
        db_session.add(p1)
        db_session.commit()
        
        mock_definition.return_value = ["A definition"]
        
        response = client.get("/dictionary")
        assert response.status_code == 200
        data = response.json()
        
        # Check that words are in descending frequency order
        words = data["top_words"]
        if len(words) >= 3:
            assert words[0]["frequency"] >= words[1]["frequency"]
            assert words[1]["frequency"] >= words[2]["frequency"]


class TestRootEndpoints:
    """Tests for root and health endpoints."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "endpoints" in data
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


"""
Unit tests for Redis word frequency tracking.
Own thought process: Test Redis ZSET operations and fallback behavior.
"""
import pytest
from unittest.mock import patch, MagicMock

from app.redis_client import RedisClient
from app.models import Paragraph


class TestRedisClient:
    """Tests for Redis client functionality."""
    
    def test_increment_word_frequencies(self):
        """Test incrementing word frequencies in Redis."""
        redis_client = RedisClient()
        
        if not redis_client.is_available():
            pytest.skip("Redis not available")
        
        # Clear existing data
        redis_client.clear_word_frequencies()
        
        # Add some words
        words = {"hello": 3, "world": 2, "test": 1}
        redis_client.increment_word_frequencies(words)
        
        # Verify frequencies
        assert redis_client.get_word_frequency("hello") == 3
        assert redis_client.get_word_frequency("world") == 2
        assert redis_client.get_word_frequency("test") == 1
        
        # Increment again
        redis_client.increment_word_frequencies({"hello": 2, "python": 5})
        
        # Verify updated frequencies
        assert redis_client.get_word_frequency("hello") == 5
        assert redis_client.get_word_frequency("python") == 5
        
        # Cleanup
        redis_client.clear_word_frequencies()
    
    def test_get_top_words(self):
        """Test retrieving top words by frequency."""
        redis_client = RedisClient()
        
        if not redis_client.is_available():
            pytest.skip("Redis not available")
        
        # Clear and add test data
        redis_client.clear_word_frequencies()
        words = {
            "apple": 10,
            "banana": 8,
            "cherry": 6,
            "date": 4,
            "elderberry": 2
        }
        redis_client.increment_word_frequencies(words)
        
        # Get top 3
        top_words = redis_client.get_top_words(3)
        assert len(top_words) == 3
        assert top_words[0] == ("apple", 10)
        assert top_words[1] == ("banana", 8)
        assert top_words[2] == ("cherry", 6)
        
        # Cleanup
        redis_client.clear_word_frequencies()
    
    def test_clear_word_frequencies(self):
        """Test clearing all word frequencies."""
        redis_client = RedisClient()
        
        if not redis_client.is_available():
            pytest.skip("Redis not available")
        
        # Add data
        redis_client.increment_word_frequencies({"test": 5})
        assert redis_client.get_word_frequency("test") == 5
        
        # Clear
        redis_client.clear_word_frequencies()
        assert redis_client.get_word_frequency("test") == 0
        assert redis_client.get_top_words(10) == []
    
    def test_rebuild_from_database(self, db_session):
        """Test rebuilding Redis data from database."""
        redis_client = RedisClient()
        
        if not redis_client.is_available():
            pytest.skip("Redis not available")
        
        # Clear Redis
        redis_client.clear_word_frequencies()
        
        # Add paragraphs to database
        p1 = Paragraph(content="hello world hello test")
        p2 = Paragraph(content="world python world")
        db_session.add_all([p1, p2])
        db_session.commit()
        
        # Rebuild from database
        redis_client.rebuild_word_frequencies_from_db(db_session)
        
        # Verify frequencies
        assert redis_client.get_word_frequency("world") == 3
        assert redis_client.get_word_frequency("hello") == 2
        
        # Cleanup
        redis_client.clear_word_frequencies()
    
    def test_graceful_degradation_when_redis_unavailable(self):
        """Test that app works when Redis is unavailable."""
        redis_client = RedisClient()
        
        # Mock Redis to be unavailable
        redis_client.client = None
        
        # These should not raise exceptions
        assert redis_client.is_available() is False
        redis_client.increment_word_frequencies({"test": 1})
        assert redis_client.get_top_words(10) == []
        assert redis_client.get_word_frequency("test") == 0
        redis_client.clear_word_frequencies()  # Should not crash


class TestInvertedIndex:
    """Tests for inverted index functionality."""
    
    def test_add_to_inverted_index(self):
        """Test adding paragraphs to inverted index."""
        redis_client = RedisClient()
        
        if not redis_client.is_available():
            pytest.skip("Redis not available")
        
        # Clear index
        redis_client.clear_inverted_index()
        
        # Add paragraph 1 with words
        redis_client.add_to_inverted_index(1, ["hello", "world", "test"])
        
        # Add paragraph 2 with overlapping words
        redis_client.add_to_inverted_index(2, ["hello", "python", "code"])
        
        # Search for "hello" - should return both paragraphs
        results = redis_client.search_inverted_index(["hello"], "or")
        assert 1 in results
        assert 2 in results
        assert len(results) == 2
        
        # Cleanup
        redis_client.clear_inverted_index()
    
    def test_search_with_or_operator(self):
        """Test inverted index search with OR operator."""
        redis_client = RedisClient()
        
        if not redis_client.is_available():
            pytest.skip("Redis not available")
        
        redis_client.clear_inverted_index()
        
        # Add test data
        redis_client.add_to_inverted_index(1, ["apple", "banana"])
        redis_client.add_to_inverted_index(2, ["cherry", "date"])
        redis_client.add_to_inverted_index(3, ["apple", "cherry"])
        
        # Search with OR - at least one word must match
        results = redis_client.search_inverted_index(["apple", "cherry"], "or")
        assert len(results) == 3  # All three paragraphs contain at least one word
        assert 1 in results
        assert 2 in results
        assert 3 in results
        
        redis_client.clear_inverted_index()
    
    def test_search_with_and_operator(self):
        """Test inverted index search with AND operator."""
        redis_client = RedisClient()
        
        if not redis_client.is_available():
            pytest.skip("Redis not available")
        
        redis_client.clear_inverted_index()
        
        # Add test data
        redis_client.add_to_inverted_index(1, ["apple", "banana"])
        redis_client.add_to_inverted_index(2, ["cherry", "date"])
        redis_client.add_to_inverted_index(3, ["apple", "cherry"])
        
        # Search with AND - all words must match
        results = redis_client.search_inverted_index(["apple", "cherry"], "and")
        assert len(results) == 1  # Only paragraph 3 has both words
        assert 3 in results
        
        redis_client.clear_inverted_index()
    
    def test_remove_from_inverted_index(self):
        """Test removing paragraphs from inverted index."""
        redis_client = RedisClient()
        
        if not redis_client.is_available():
            pytest.skip("Redis not available")
        
        redis_client.clear_inverted_index()
        
        # Add paragraphs
        redis_client.add_to_inverted_index(1, ["hello", "world"])
        redis_client.add_to_inverted_index(2, ["hello", "python"])
        
        # Verify both exist
        results = redis_client.search_inverted_index(["hello"], "or")
        assert len(results) == 2
        
        # Remove paragraph 1
        redis_client.remove_from_inverted_index(1, ["hello", "world"])
        
        # Verify only paragraph 2 remains
        results = redis_client.search_inverted_index(["hello"], "or")
        assert len(results) == 1
        assert 2 in results
        
        redis_client.clear_inverted_index()
    
    def test_rebuild_inverted_index_from_db(self, db_session):
        """Test rebuilding inverted index from database."""
        redis_client = RedisClient()
        
        if not redis_client.is_available():
            pytest.skip("Redis not available")
        
        redis_client.clear_inverted_index()
        
        # Add paragraphs to database
        p1 = Paragraph(content="hello world python")
        p2 = Paragraph(content="hello programming code")
        p3 = Paragraph(content="world of technology")
        db_session.add_all([p1, p2, p3])
        db_session.commit()
        
        # Rebuild index
        redis_client.rebuild_inverted_index_from_db(db_session)
        
        # Test searches
        results = redis_client.search_inverted_index(["hello"], "or")
        assert len(results) == 2  # p1 and p2
        
        results = redis_client.search_inverted_index(["world"], "or")
        assert len(results) == 2  # p1 and p3
        
        results = redis_client.search_inverted_index(["hello", "world"], "and")
        assert len(results) == 1  # Only p1
        
        redis_client.clear_inverted_index()
    
    def test_inverted_index_stats(self):
        """Test getting inverted index statistics."""
        redis_client = RedisClient()
        
        if not redis_client.is_available():
            pytest.skip("Redis not available")
        
        redis_client.clear_inverted_index()
        
        # Add some data
        redis_client.add_to_inverted_index(1, ["apple", "banana", "cherry"])
        redis_client.add_to_inverted_index(2, ["apple", "date"])
        redis_client.add_to_inverted_index(3, ["banana"])
        
        # Get stats
        stats = redis_client.get_inverted_index_stats()
        
        assert stats["total_indexed_words"] == 4  # apple, banana, cherry, date
        assert stats["total_word_paragraph_mappings"] == 6  # Total mappings
        
        redis_client.clear_inverted_index()
    
    def test_case_insensitive_search(self):
        """Test that inverted index search is case-insensitive."""
        redis_client = RedisClient()
        
        if not redis_client.is_available():
            pytest.skip("Redis not available")
        
        redis_client.clear_inverted_index()
        
        # Add with lowercase
        redis_client.add_to_inverted_index(1, ["hello", "world"])
        
        # Search with different cases
        results_lower = redis_client.search_inverted_index(["hello"], "or")
        results_upper = redis_client.search_inverted_index(["HELLO"], "or")
        results_mixed = redis_client.search_inverted_index(["HeLLo"], "or")
        
        # All should return the same result
        assert results_lower == results_upper == results_mixed
        assert 1 in results_lower
        
        redis_client.clear_inverted_index()


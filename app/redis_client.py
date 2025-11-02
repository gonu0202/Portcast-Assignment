"""
Redis connection and client management.
Own thought process: Redis connection pooling and ZSET operations for word frequency.
"""
import redis
from typing import Optional
from app.config import settings


class RedisClient:
    """Redis client wrapper for word frequency tracking and inverted index."""
    
    # Redis key for word frequency sorted set
    WORD_FREQ_KEY = "word_frequencies"
    
    # Redis key prefix for inverted index (word -> set of paragraph IDs)
    INVERTED_INDEX_PREFIX = "word_index:"
    
    def __init__(self):
        """Initialize Redis connection pool."""
        self.client: Optional[redis.Redis] = None
        self._connect()
    
    def _connect(self):
        """Establish Redis connection."""
        try:
            self.client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.client.ping()
        except Exception as e:
            print(f"Warning: Could not connect to Redis: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if Redis is available."""
        if self.client is None:
            return False
        try:
            self.client.ping()
            return True
        except:
            return False
    
    def increment_word_frequencies(self, words: dict) -> None:
        """
        Increment word frequencies in Redis ZSET.
        Own design: Uses ZINCRBY for atomic increments.
        
        Args:
            words: Dictionary with word as key and count as value
        """
        if not self.is_available():
            return
        
        try:
            # Use pipeline for efficiency
            pipe = self.client.pipeline()
            for word, count in words.items():
                pipe.zincrby(self.WORD_FREQ_KEY, count, word)
            pipe.execute()
        except Exception as e:
            print(f"Error updating Redis word frequencies: {e}")
    
    def get_top_words(self, n: int = 10) -> list:
        """
        Get top N words by frequency from Redis ZSET.
        Own design: Uses ZREVRANGE with scores for efficient retrieval.
        
        Args:
            n: Number of top words to retrieve
            
        Returns:
            List of tuples (word, frequency)
        """
        if not self.is_available():
            return []
        
        try:
            # ZREVRANGE returns in descending order (highest scores first)
            # WITHSCORES returns tuples of (word, score)
            results = self.client.zrevrange(
                self.WORD_FREQ_KEY, 
                0, 
                n - 1, 
                withscores=True
            )
            # Convert scores to integers
            return [(word, int(score)) for word, score in results]
        except Exception as e:
            print(f"Error getting top words from Redis: {e}")
            return []
    
    def get_word_frequency(self, word: str) -> int:
        """
        Get frequency of a specific word.
        
        Args:
            word: The word to look up
            
        Returns:
            Frequency count (0 if not found)
        """
        if not self.is_available():
            return 0
        
        try:
            score = self.client.zscore(self.WORD_FREQ_KEY, word)
            return int(score) if score is not None else 0
        except Exception as e:
            print(f"Error getting word frequency: {e}")
            return 0
    
    def clear_word_frequencies(self) -> None:
        """
        Clear all word frequencies.
        Useful for testing or reset.
        """
        if not self.is_available():
            return
        
        try:
            self.client.delete(self.WORD_FREQ_KEY)
        except Exception as e:
            print(f"Error clearing word frequencies: {e}")
    
    def rebuild_word_frequencies_from_db(self, db_session) -> None:
        """
        Rebuild Redis word frequencies from database.
        Useful for initialization or recovery.
        Own design: Fallback mechanism if Redis data is lost.
        
        Args:
            db_session: SQLAlchemy database session
        """
        if not self.is_available():
            return
        
        try:
            from app.models import Paragraph
            from app.services import extract_words_from_text
            from collections import Counter
            
            # Clear existing data
            self.clear_word_frequencies()
            
            # Get all paragraphs
            paragraphs = db_session.query(Paragraph).all()
            
            # Count all words
            all_words = []
            for paragraph in paragraphs:
                words = extract_words_from_text(paragraph.content)
                all_words.extend(words)
            
            word_counts = Counter(all_words)
            
            # Update Redis
            if word_counts:
                self.increment_word_frequencies(dict(word_counts))
            
            print(f"Rebuilt Redis word frequencies: {len(word_counts)} unique words")
        except Exception as e:
            print(f"Error rebuilding word frequencies: {e}")
    
    # ========== INVERTED INDEX METHODS ==========
    # Own design: Inverted index for O(1) word lookup in paragraph search
    
    def add_to_inverted_index(self, paragraph_id: int, words: list) -> None:
        """
        Add paragraph to inverted index for all its words.
        Own design: Uses Redis SADD for efficient set operations.
        
        For each unique word in the paragraph, we store the paragraph ID
        in a set: word_index:{word} -> {paragraph_id1, paragraph_id2, ...}
        
        Args:
            paragraph_id: ID of the paragraph
            words: List of words in the paragraph
        """
        if not self.is_available():
            return
        
        try:
            # Get unique words
            unique_words = set(words)
            
            # Use pipeline for efficiency
            pipe = self.client.pipeline()
            for word in unique_words:
                key = f"{self.INVERTED_INDEX_PREFIX}{word}"
                pipe.sadd(key, paragraph_id)
            pipe.execute()
        except Exception as e:
            print(f"Error adding to inverted index: {e}")
    
    def search_inverted_index(self, words: list, operator: str = "or") -> set:
        """
        Search inverted index for paragraphs containing words.
        Own design: Uses Redis set operations (SUNION/SINTER) for optimal performance.
        
        Time Complexity:
        - OR operation: O(N) where N = total matching paragraph IDs
        - AND operation: O(N*M) where N = smallest set, M = number of words
        
        Args:
            words: List of words to search for
            operator: 'or' (union) or 'and' (intersection)
            
        Returns:
            Set of paragraph IDs that match the search
        """
        if not self.is_available() or not words:
            return set()
        
        try:
            # Get keys for all search words
            keys = [f"{self.INVERTED_INDEX_PREFIX}{word.lower()}" for word in words]
            
            if operator == "or":
                # Union: paragraphs containing at least one word
                result = self.client.sunion(keys)
            else:  # operator == "and"
                # Intersection: paragraphs containing all words
                result = self.client.sinter(keys)
            
            # Convert string IDs to integers
            return {int(pid) for pid in result}
        except Exception as e:
            print(f"Error searching inverted index: {e}")
            return set()
    
    def remove_from_inverted_index(self, paragraph_id: int, words: list) -> None:
        """
        Remove paragraph from inverted index.
        Useful for paragraph deletion.
        
        Args:
            paragraph_id: ID of the paragraph to remove
            words: List of words in the paragraph
        """
        if not self.is_available():
            return
        
        try:
            unique_words = set(words)
            pipe = self.client.pipeline()
            for word in unique_words:
                key = f"{self.INVERTED_INDEX_PREFIX}{word}"
                pipe.srem(key, paragraph_id)
            pipe.execute()
        except Exception as e:
            print(f"Error removing from inverted index: {e}")
    
    def clear_inverted_index(self) -> None:
        """
        Clear entire inverted index.
        Useful for testing or rebuild.
        """
        if not self.is_available():
            return
        
        try:
            # Find all inverted index keys
            pattern = f"{self.INVERTED_INDEX_PREFIX}*"
            keys = self.client.keys(pattern)
            
            if keys:
                self.client.delete(*keys)
        except Exception as e:
            print(f"Error clearing inverted index: {e}")
    
    def rebuild_inverted_index_from_db(self, db_session) -> None:
        """
        Rebuild entire inverted index from database.
        Own design: Recovery mechanism for inverted index.
        
        Args:
            db_session: SQLAlchemy database session
        """
        if not self.is_available():
            return
        
        try:
            from app.models import Paragraph
            from app.services import extract_words_from_text
            
            # Clear existing inverted index
            self.clear_inverted_index()
            
            # Get all paragraphs
            paragraphs = db_session.query(Paragraph).all()
            
            # Rebuild index for each paragraph
            for paragraph in paragraphs:
                words = extract_words_from_text(paragraph.content)
                self.add_to_inverted_index(paragraph.id, words)
            
            print(f"Rebuilt inverted index for {len(paragraphs)} paragraphs")
        except Exception as e:
            print(f"Error rebuilding inverted index: {e}")
    
    def get_inverted_index_stats(self) -> dict:
        """
        Get statistics about the inverted index.
        Useful for monitoring and debugging.
        
        Returns:
            Dictionary with index statistics
        """
        if not self.is_available():
            return {}
        
        try:
            pattern = f"{self.INVERTED_INDEX_PREFIX}*"
            keys = self.client.keys(pattern)
            
            total_words = len(keys)
            total_mappings = sum(self.client.scard(key) for key in keys) if keys else 0
            
            return {
                "total_indexed_words": total_words,
                "total_word_paragraph_mappings": total_mappings,
                "average_paragraphs_per_word": total_mappings / total_words if total_words > 0 else 0
            }
        except Exception as e:
            print(f"Error getting index stats: {e}")
            return {}


# Global Redis client instance
redis_client = RedisClient()


def get_redis_client() -> RedisClient:
    """Get the global Redis client instance."""
    return redis_client


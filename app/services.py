"""
Business logic and external API interactions.
AI-assisted: HTTP request patterns from AI, word frequency algorithm is own design.
Own thought process:
Redis optimization: Own design - Using ZSET to maintain real-time word frequencies.
"""
import re
from collections import Counter
from typing import List, Dict, Optional
import requests
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from app.models import Paragraph
from app.config import settings
from app.redis_client import get_redis_client


def fetch_paragraph_from_api() -> str:
    """
    Fetch a paragraph from metaphorpsum.com.
    
    Returns:
        str: The fetched paragraph text
        
    Raises:
        Exception: If the API request fails
    """
    try:
        response = requests.get(settings.metaphorpsum_url, timeout=10)
        response.raise_for_status()
        return response.text.strip()
    except requests.RequestException as e:
        raise Exception(f"Failed to fetch paragraph from Metaphorpsum: {str(e)}")


def store_paragraph(db: Session, content: str) -> Paragraph:
    """
    Store a paragraph in the database and update Redis structures.
    Own optimization: Updates both word frequencies and inverted index.
    
    Args:
        db: Database session
        content: Paragraph text to store
        
    Returns:
        Paragraph: The stored paragraph object
    """
    paragraph = Paragraph(content=content)
    db.add(paragraph)
    db.commit()
    db.refresh(paragraph)
    
    # Update Redis structures in real-time
    redis_client = get_redis_client()
    if redis_client.is_available():
        words = extract_words_from_text(content)
        word_counts = Counter(words)
        
        # Update word frequencies (for /dictionary endpoint)
        redis_client.increment_word_frequencies(dict(word_counts))
        
        # Update inverted index (for /search endpoint)
        redis_client.add_to_inverted_index(paragraph.id, words)
    
    return paragraph


def search_paragraphs(db: Session, words: List[str], operator: str) -> List[Paragraph]:
    """
    Search for paragraphs containing specified words.
    Own optimization: Uses Redis inverted index for O(1) lookup instead of DB scan.
    Fallback to database ILIKE if Redis unavailable.
    
    Args:
        db: Database session
        words: List of words to search for
        operator: 'and' or 'or' operator
        
    Returns:
        List[Paragraph]: List of matching paragraphs
    """
    redis_client = get_redis_client()
    
    # Try to use Redis inverted index (fast path)
    if redis_client.is_available():
        # Search inverted index for matching paragraph IDs
        paragraph_ids = redis_client.search_inverted_index(words, operator)
        
        if paragraph_ids:
            # Fetch only matching paragraphs from database by ID
            # This is much faster than full-text scan
            return db.query(Paragraph).filter(Paragraph.id.in_(paragraph_ids)).all()
        else:
            # Check if index is empty - if so, rebuild
            stats = redis_client.get_inverted_index_stats()
            if stats.get("total_indexed_words", 0) == 0:
                redis_client.rebuild_inverted_index_from_db(db)
                # Try search again after rebuild
                paragraph_ids = redis_client.search_inverted_index(words, operator)
                if paragraph_ids:
                    return db.query(Paragraph).filter(Paragraph.id.in_(paragraph_ids)).all()
            
            # No results found
            return []
    
    # Fallback to database ILIKE search (slow path)
    if operator == "or":
        # Match paragraphs containing at least one of the words
        conditions = [Paragraph.content.ilike(f"%{word}%") for word in words]
        query = db.query(Paragraph).filter(or_(*conditions))
    else:  # operator == "and"
        # Match paragraphs containing all of the words
        conditions = [Paragraph.content.ilike(f"%{word}%") for word in words]
        query = db.query(Paragraph).filter(and_(*conditions))
    
    return query.all()


def extract_words_from_text(text: str) -> List[str]:
    """
    Extract words from text, removing punctuation and converting to lowercase.
    Own thought process: Custom regex pattern to extract only alphabetic words.
    
    Args:
        text: Text to extract words from
        
    Returns:
        List[str]: List of cleaned words
    """
    # Remove punctuation and split into words
    # Keep only alphabetic characters, minimum 2 characters long
    words = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())
    return words


def get_word_frequencies(db: Session) -> Counter:
    """
    Calculate word frequencies across all stored paragraphs.
    Own thought process: Designed aggregation logic for word frequency analysis.
    
    Args:
        db: Database session
        
    Returns:
        Counter: Dictionary-like object with word frequencies
    """
    paragraphs = db.query(Paragraph).all()
    all_words = []
    
    for paragraph in paragraphs:
        words = extract_words_from_text(paragraph.content)
        all_words.extend(words)
    
    return Counter(all_words)


def get_word_definition(word: str) -> Optional[List[str]]:
    """
    Fetch word definition from dictionary API.
    AI-assisted: API interaction pattern, error handling is own design.
    
    Args:
        word: Word to get definition for
        
    Returns:
        Optional[List[str]]: List of definitions or None if not found
    """
    try:
        url = f"{settings.dictionary_api_url}/{word}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 404:
            return None
        
        response.raise_for_status()
        data = response.json()
        
        # Extract all definitions from all meanings
        definitions = []
        if isinstance(data, list) and len(data) > 0:
            for meaning in data[0].get('meanings', []):
                for definition_obj in meaning.get('definitions', []):
                    if 'definition' in definition_obj:
                        definitions.append(definition_obj['definition'])
        
        return definitions if definitions else None
        
    except requests.RequestException:
        return None


def get_top_words_with_definitions(db: Session, top_n: int = 10) -> List[Dict]:
    """
    Get top N most frequent words with their definitions.
    Own optimization: Uses Redis ZSET for O(log N) retrieval instead of full DB scan.
    Fallback to DB if Redis unavailable.
    
    Args:
        db: Database session
        top_n: Number of top words to return
        
    Returns:
        List[Dict]: List of dictionaries with word, frequency, and definitions
    """
    redis_client = get_redis_client()
    
    # Try to get from Redis first (fast path)
    if redis_client.is_available():
        top_words = redis_client.get_top_words(top_n)
        
        # If Redis is empty, rebuild from database
        if not top_words:
            redis_client.rebuild_word_frequencies_from_db(db)
            top_words = redis_client.get_top_words(top_n)
    else:
        # Fallback to database calculation (slow path)
        word_freq = get_word_frequencies(db)
        top_words = word_freq.most_common(top_n)
    
    # Fetch definitions for top words
    result = []
    for word, frequency in top_words:
        definitions = get_word_definition(word)
        result.append({
            "word": word,
            "frequency": frequency,
            "definitions": definitions if definitions else ["Definition not found"]
        })
    
    return result


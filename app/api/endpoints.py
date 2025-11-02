"""
API endpoint definitions.
AI-assisted: FastAPI routing structure from AI.
Own thought process: Request/response handling and error management.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    ParagraphResponse,
    SearchRequest,
    SearchResponse,
    DictionaryResponse,
    WordDefinition
)
from app.services import (
    fetch_paragraph_from_api,
    store_paragraph,
    search_paragraphs,
    get_top_words_with_definitions
)

router = APIRouter()


@router.get("/fetch", response_model=ParagraphResponse)
def fetch_endpoint(db: Session = Depends(get_db)):
    """
    Fetch a paragraph from metaphorpsum.com and store it.
    
    This endpoint:
    1. Fetches 1 paragraph with 50 sentences from metaphorpsum.com
    2. Stores it in the database
    3. Returns the stored paragraph
    
    Returns:
        ParagraphResponse: The fetched and stored paragraph
        
    Raises:
        HTTPException: If fetching or storing fails
    """
    try:
        # Fetch paragraph from external API
        content = fetch_paragraph_from_api()
        
        # Store in database
        paragraph = store_paragraph(db, content)
        
        return paragraph
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=SearchResponse)
def search_endpoint(
    search_request: SearchRequest,
    db: Session = Depends(get_db)
):
    """
    Search through stored paragraphs with multiple words and operators.
    
    This endpoint allows searching with:
    - Multiple words
    - 'or' operator: returns paragraphs with at least one of the words
    - 'and' operator: returns paragraphs with all of the words
    
    Args:
        search_request: Search parameters (words and operator)
        
    Returns:
        SearchResponse: Count and list of matching paragraphs
    """
    try:
        paragraphs = search_paragraphs(
            db,
            search_request.words,
            search_request.operator
        )
        
        return SearchResponse(
            count=len(paragraphs),
            paragraphs=paragraphs
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dictionary", response_model=DictionaryResponse)
def dictionary_endpoint(db: Session = Depends(get_db)):
    """
    Get definitions of the top 10 most frequent words.
    
    This endpoint:
    1. Analyzes all stored paragraphs
    2. Identifies the top 10 most frequent words
    3. Fetches definitions from dictionaryapi.dev
    4. Returns words with their frequencies and definitions
    
    Returns:
        DictionaryResponse: Top 10 words with definitions
        
    Raises:
        HTTPException: If processing fails
    """
    try:
        top_words_data = get_top_words_with_definitions(db, top_n=10)
        
        word_definitions = [
            WordDefinition(**word_data)
            for word_data in top_words_data
        ]
        
        return DictionaryResponse(top_words=word_definitions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


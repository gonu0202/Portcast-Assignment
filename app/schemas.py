"""
Pydantic schemas for request/response validation.
Own thought process: Designed schemas based on API requirements.
"""
from datetime import datetime
from typing import List, Literal
from pydantic import BaseModel, Field


class ParagraphResponse(BaseModel):
    """Response schema for paragraph data."""
    id: int
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class SearchRequest(BaseModel):
    """Request schema for search endpoint."""
    words: List[str] = Field(..., min_items=1, description="List of words to search for")
    operator: Literal["and", "or"] = Field(..., description="Search operator: 'and' or 'or'")


class SearchResponse(BaseModel):
    """Response schema for search results."""
    count: int
    paragraphs: List[ParagraphResponse]


class WordDefinition(BaseModel):
    """Schema for word definition."""
    word: str
    frequency: int
    definitions: List[str]


class DictionaryResponse(BaseModel):
    """Response schema for dictionary endpoint."""
    top_words: List[WordDefinition]


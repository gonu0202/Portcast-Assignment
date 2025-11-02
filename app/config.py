"""
Configuration management for the application.
AI-assisted: Basic structure suggested by AI, customized for this specific use case.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    database_url: str = "postgresql://postgres:postgres@localhost:5432/paragraphs_db"
    redis_url: str = "redis://localhost:6379/0"
    metaphorpsum_url: str = "http://metaphorpsum.com/sentences/50"
    dictionary_api_url: str = "https://api.dictionaryapi.dev/api/v2/entries/en"
    
    class Config:
        env_file = ".env"


settings = Settings()


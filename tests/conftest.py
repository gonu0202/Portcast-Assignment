"""
Pytest configuration and fixtures.
AI-assisted: Basic pytest fixture pattern from AI.
Own thought process: Test database setup and cleanup strategy.
Redis integration: Own design for test isolation with Redis.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.redis_client import get_redis_client

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def redis_client():
    """Create a Redis client and clean it before/after tests."""
    client = get_redis_client()
    if client.is_available():
        client.clear_word_frequencies()
    yield client
    if client.is_available():
        client.clear_word_frequencies()


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with a test database."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    # Clean Redis before test
    redis = get_redis_client()
    if redis.is_available():
        redis.clear_word_frequencies()
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    
    # Clean Redis after test
    if redis.is_available():
        redis.clear_word_frequencies()


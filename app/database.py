"""
Database connection and session management.
AI-assisted: SQLAlchemy setup pattern from AI, customized for PostgreSQL.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import settings

# Create database engine
engine = create_engine(settings.database_url)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency function to get database session.
    Ensures proper cleanup after request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


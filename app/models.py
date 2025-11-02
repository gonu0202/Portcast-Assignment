"""
Database models for storing paragraphs.
AI-assisted: Basic SQLAlchemy model structure from AI, indexing strategy is custom design.
"""
from sqlalchemy import Column, Integer, Text, DateTime, Index
from sqlalchemy.sql import func

from app.database import Base


class Paragraph(Base):
    """
    Model to store fetched paragraphs.
    
    Attributes:
        id: Primary key
        content: The paragraph text content
        created_at: Timestamp when paragraph was stored
    """
    __tablename__ = "paragraphs"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Add index for better search performance
    __table_args__ = (
        Index('idx_paragraph_content', 'content'),
    )


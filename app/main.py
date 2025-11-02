"""
Main FastAPI application entry point.
AI-assisted: FastAPI application setup pattern from AI.
Own thought process: CORS configuration and startup event handling.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.api.endpoints import router

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Paragraph Management API",
    description="API for fetching, storing, and searching paragraphs with word frequency analysis",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, tags=["paragraphs"])


@app.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "message": "Paragraph Management API",
        "version": "1.0.0",
        "endpoints": {
            "/fetch": "Fetch and store a paragraph",
            "/search": "Search through stored paragraphs",
            "/dictionary": "Get top 10 word definitions"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


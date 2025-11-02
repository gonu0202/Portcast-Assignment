#!/bin/bash

# Script to verify the API setup and functionality

set -e  # Exit on error

echo "=================================="
echo "Testing Paragraph Management API"
echo "=================================="
echo ""

BASE_URL="http://localhost:8000"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print success
success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print error
error() {
    echo -e "${RED}✗ $1${NC}"
}

# Function to print info
info() {
    echo -e "${YELLOW}→ $1${NC}"
}

# Test 1: Health Check
info "Test 1: Checking API health..."
if curl -s "${BASE_URL}/health" | grep -q "healthy"; then
    success "Health check passed"
else
    error "Health check failed"
    exit 1
fi
echo ""

# Test 2: Root Endpoint
info "Test 2: Testing root endpoint..."
if curl -s "${BASE_URL}/" | grep -q "Paragraph Management API"; then
    success "Root endpoint working"
else
    error "Root endpoint failed"
    exit 1
fi
echo ""

# Test 3: Fetch Paragraph
info "Test 3: Fetching a paragraph..."
FETCH_RESPONSE=$(curl -s "${BASE_URL}/fetch")
if echo "$FETCH_RESPONSE" | grep -q "content"; then
    success "Paragraph fetched successfully"
    echo "   Sample: $(echo $FETCH_RESPONSE | cut -c1-100)..."
else
    error "Failed to fetch paragraph"
    exit 1
fi
echo ""

# Test 4: Search with OR operator
info "Test 4: Testing search with OR operator..."
SEARCH_RESPONSE=$(curl -s -X POST "${BASE_URL}/search" \
    -H "Content-Type: application/json" \
    -d '{"words": ["the", "and"], "operator": "or"}')
if echo "$SEARCH_RESPONSE" | grep -q "count"; then
    success "Search with OR operator working"
    COUNT=$(echo $SEARCH_RESPONSE | grep -o '"count":[0-9]*' | grep -o '[0-9]*')
    echo "   Found: $COUNT paragraphs"
else
    error "Search with OR failed"
    exit 1
fi
echo ""

# Test 5: Search with AND operator
info "Test 5: Testing search with AND operator..."
SEARCH_RESPONSE=$(curl -s -X POST "${BASE_URL}/search" \
    -H "Content-Type: application/json" \
    -d '{"words": ["the", "and"], "operator": "and"}')
if echo "$SEARCH_RESPONSE" | grep -q "count"; then
    success "Search with AND operator working"
    COUNT=$(echo $SEARCH_RESPONSE | grep -o '"count":[0-9]*' | grep -o '[0-9]*')
    echo "   Found: $COUNT paragraphs"
else
    error "Search with AND failed"
    exit 1
fi
echo ""

# Test 6: Dictionary endpoint
info "Test 6: Testing dictionary endpoint..."
DICT_RESPONSE=$(curl -s "${BASE_URL}/dictionary")
if echo "$DICT_RESPONSE" | grep -q "top_words"; then
    success "Dictionary endpoint working"
    # Extract number of words
    WORDS_COUNT=$(echo $DICT_RESPONSE | grep -o '"word"' | wc -l | tr -d ' ')
    echo "   Found: $WORDS_COUNT top words with definitions"
else
    error "Dictionary endpoint failed"
    exit 1
fi
echo ""

# Summary
echo "=================================="
success "All tests passed! ✨"
echo "=================================="
echo ""
echo "API is fully functional and ready to use!"
echo "Visit http://localhost:8000/docs for interactive documentation"


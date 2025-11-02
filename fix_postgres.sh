#!/bin/bash

# Script to fix PostgreSQL connection issues
# This script will help diagnose and fix common PostgreSQL setup problems

set -e

echo "=================================="
echo "PostgreSQL Setup Fix Script"
echo "=================================="
echo ""

# Get current username
USERNAME=$(whoami)
echo "Your macOS username: $USERNAME"
echo ""

# Check if PostgreSQL is running
echo "Step 1: Checking if PostgreSQL is running..."
if pg_isready -q; then
    echo "✓ PostgreSQL is running"
else
    echo "✗ PostgreSQL is not running"
    echo "Attempting to start PostgreSQL..."
    brew services start postgresql@15 || brew services start postgresql
    sleep 3
    if pg_isready -q; then
        echo "✓ PostgreSQL started successfully"
    else
        echo "✗ Could not start PostgreSQL. Please start it manually."
        exit 1
    fi
fi
echo ""

# Check which users exist
echo "Step 2: Checking existing PostgreSQL users..."
psql -U $USERNAME -d postgres -c "\du" 2>/dev/null || psql -d postgres -c "\du" 2>/dev/null || echo "Could not connect with default user"
echo ""

# Try to create postgres role
echo "Step 3: Creating 'postgres' role..."
psql -U $USERNAME -d postgres -c "CREATE ROLE postgres WITH LOGIN PASSWORD 'postgres' CREATEDB CREATEROLE SUPERUSER;" 2>/dev/null || \
psql -d postgres -c "CREATE ROLE postgres WITH LOGIN PASSWORD 'postgres' CREATEDB CREATEROLE SUPERUSER;" 2>/dev/null || \
echo "postgres role might already exist (this is OK)"
echo ""

# Create the database
echo "Step 4: Creating 'paragraphs_db' database..."
psql -U postgres -c "CREATE DATABASE paragraphs_db;" 2>/dev/null || \
psql -U $USERNAME -c "CREATE DATABASE paragraphs_db;" 2>/dev/null || \
createdb paragraphs_db 2>/dev/null || \
echo "Database might already exist (this is OK)"
echo ""

# Grant permissions
echo "Step 5: Granting permissions..."
psql -U $USERNAME -d paragraphs_db -c "GRANT ALL PRIVILEGES ON DATABASE paragraphs_db TO postgres;" 2>/dev/null || \
echo "Could not grant permissions (might not be needed)"
echo ""

# Test connection with postgres user
echo "Step 6: Testing connection with 'postgres' user..."
if psql -U postgres -d paragraphs_db -c "SELECT 1;" >/dev/null 2>&1; then
    echo "✓ Connection with 'postgres' user works!"
    echo ""
    echo "Use this DATABASE_URL:"
    echo "postgresql://postgres:postgres@localhost:5432/paragraphs_db"
else
    echo "✗ Connection with 'postgres' user failed"
    echo ""
    echo "Testing with your username ($USERNAME)..."
    if psql -U $USERNAME -d paragraphs_db -c "SELECT 1;" >/dev/null 2>&1; then
        echo "✓ Connection with '$USERNAME' user works!"
        echo ""
        echo "Use this DATABASE_URL instead:"
        echo "postgresql://$USERNAME@localhost:5432/paragraphs_db"
        echo ""
        echo "Creating .env file with correct DATABASE_URL..."
        cat > .env << EOF
DATABASE_URL=postgresql://$USERNAME@localhost:5432/paragraphs_db
METAPHORPSUM_URL=http://metaphorpsum.com/sentences/50
DICTIONARY_API_URL=https://api.dictionaryapi.dev/api/v2/entries/en
EOF
        echo "✓ .env file created"
    else
        echo "✗ Could not connect with either user"
        echo ""
        echo "Manual steps needed:"
        echo "1. Check PostgreSQL is installed: brew list | grep postgresql"
        echo "2. Check it's running: brew services list"
        echo "3. Try connecting: psql postgres"
    fi
fi

echo ""
echo "=================================="
echo "Setup complete!"
echo "=================================="
echo ""
echo "Now try running your application:"
echo "  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"


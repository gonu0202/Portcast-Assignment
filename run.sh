#!/bin/bash

# Simple script to start the application with Docker Compose

echo "Starting Paragraph Management API..."
echo "=================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Build and start containers
docker-compose up --build

# Cleanup on exit
trap "docker-compose down" EXIT


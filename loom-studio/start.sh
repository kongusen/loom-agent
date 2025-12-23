#!/bin/bash

# Loom Studio Quick Start Script

set -e

# Base directory
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$BASE_DIR/backend"
WEB_DIR="$BASE_DIR/web"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Loom Studio Quick Start ===${NC}"

# Check for Python and dependencies
echo -e "${GREEN}[1/3] Checking Backend...${NC}"
if [ -f "$BACKEND_DIR/requirements.txt" ]; then
    echo "Using existing environment..."
else
    echo "Backend directory not found or invalid!"
    exit 1
fi

# Check for Node/NPM
echo -e "${GREEN}[2/3] Checking Frontend...${NC}"
if command -v npm &> /dev/null; then
    echo "npm found."
else
    echo "Error: npm is required but not installed."
    exit 1
fi

if [ ! -d "$WEB_DIR/node_modules" ]; then
    echo "Installing frontend dependencies..."
    cd "$WEB_DIR"
    npm install
fi

# Function to kill processes on exit
cleanup() {
    echo -e "\n${BLUE}Shutting down Loom Studio...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $WEB_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start Backend
echo -e "${GREEN}[3/3] Starting Services...${NC}"
echo "Starting Studio Server on port 8765..."
cd "$BACKEND_DIR"
# Assuming python/uvicorn is in path or venv is active
# We try to use the 'uvicorn' command directly
uvicorn main:app --port 8765 &
BACKEND_PID=$!

# Start Frontend
echo "Starting Studio Frontend..."
cd "$WEB_DIR"
npm run dev &
WEB_PID=$!

echo -e "${GREEN}Loom Studio is running!${NC}"
echo -e "Backend: http://localhost:8765"
echo -e "Frontend: http://localhost:5173"
echo "Press Ctrl+C to stop."

wait

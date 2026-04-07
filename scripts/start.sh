#!/bin/bash
# OMNI-RANK Quick Start for GitHub Codespaces
# Usage: bash scripts/start.sh

set -e

echo "=== OMNI-RANK OR-1 — Starting... ==="

# Check .env exists
if [ ! -f "backend/.env" ]; then
    echo ""
    echo "⚠️  No backend/.env found. Creating from template..."
    cp .env.example backend/.env
    echo "✏️  Edit backend/.env and add your API keys:"
    echo "   - GEMINI_API_KEY (free from aistudio.google.com)"
    echo "   - SUPABASE_URL"
    echo "   - SUPABASE_SERVICE_ROLE_KEY"
    echo ""
fi

# Install backend dependencies
echo "📦 Installing backend dependencies..."
cd backend
pip install -q fastapi uvicorn pydantic pydantic-settings httpx python-dotenv 2>/dev/null
cd ..

# Install frontend dependencies
echo "📦 Installing frontend dependencies..."
cd frontend
npm install --silent 2>/dev/null
cd ..

echo ""
echo "=== Starting services ==="
echo "Backend:  http://localhost:8000 (API docs: http://localhost:8000/docs)"
echo "Frontend: http://localhost:3000"
echo ""

# Start backend in background
cd backend
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Start frontend
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Both services starting..."
echo "   Backend PID: $BACKEND_PID"
echo "   Frontend PID: $FRONTEND_PID"
echo ""
echo "To stop: kill $BACKEND_PID $FRONTEND_PID"

# Wait for both
wait

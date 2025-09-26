#!/bin/bash

# Clio NLP Agent - Quick Start Script
# This script sets up and starts the Clio NLP Agent with proper environment variables

set -e  # Exit on any error

echo "🚀 Clio NLP Agent - Quick Start"
echo "================================"

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found. Please run this script from the clio-nlp-agent directory."
    exit 1
fi

# Activate virtual environment if available
if [ -d ".venv" ]; then
    echo "🔌 Activating virtual environment..."
    source .venv/bin/activate
else
    echo "⚠️  No virtual environment found. Please create one with:"
    echo "   python3 -m venv .venv && source .venv/bin/activate"
    exit 1
fi

# Set OpenAI API key if not already set
# Set OpenAI API key without hard-coding; load from .env if present
if [ -z "$OPENAI_API_KEY" ] && [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY is not set. Export it or add it to .env before running."
    exit 1
else
    echo "✅ Using OPENAI_API_KEY from environment"
fi

# Run verification
echo "🔍 Running setup verification..."
python verify_setup.py

# Check if verification passed
if [ $? -ne 0 ]; then
    echo "❌ Setup verification failed. Please fix the issues above before starting the agent."
    exit 1
fi

echo ""
echo "✅ Verification passed! Starting the Clio NLP Agent..."
echo ""
echo "📋 The agent will be available at:"
echo "   • Main API: http://localhost:8000"
echo "   • Documentation: http://localhost:8000/docs"
echo "   • Health Check: http://localhost:8000/health"
echo "   • Auth Status: http://localhost:8000/auth/status"
echo ""
echo "💡 Test with:"
echo "   curl -X POST 'http://localhost:8000/nlp' \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"query\": \"Check my authentication status\"}'"
echo ""
echo "📖 See README.md and INSTRUCTIONS.md for detailed usage"
echo ""
echo "🛑 Press Ctrl+C to stop the server"
echo ""

# Check if dependencies are installed
echo "📦 Checking dependencies..."
python -c "import fastapi, uvicorn, langchain, openai" 2>/dev/null || {
    echo "⚠️  Dependencies not fully installed. Installing now..."
    pip install -r requirements.txt
    echo "✅ Dependencies installed successfully!"
}

# Start the server
echo "🌟 Starting Clio NLP Agent server..."
echo ""
uvicorn main:app --reload --host 0.0.0.0 --port 8000
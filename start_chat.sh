#!/bin/bash

# Start Chat Interface for Clio NLP Agent
# This script starts the Gradio web chat interface

set -e  # Exit on any error

echo "🚀 Clio NLP Agent - Chat Interface Launcher"
echo "==========================================="

# Check if we're in the right directory
if [ ! -f "chat_interface.py" ]; then
    echo "❌ Error: chat_interface.py not found. Please run this script from the clio-nlp-agent directory."
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

# Check if the NLP agent is running
echo "🔍 Checking if NLP agent is running..."
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ NLP agent is not running at http://localhost:8000"
    echo ""
    echo "🚀 Please start the NLP agent first:"
    echo "   1. Open another terminal"
    echo "   2. cd to this directory"
    echo "   3. Run: ./start_agent.sh"
    echo "   4. Wait for it to show 'Uvicorn running on http://0.0.0.0:8000'"
    echo "   5. Then come back and run this chat interface"
    echo ""
    exit 1
fi

echo "✅ NLP agent is running!"

# Check if dependencies are installed
echo "📦 Checking Gradio dependency..."
python -c "import gradio" 2>/dev/null || {
    echo "⚠️  Gradio not installed. Installing now..."
    pip install gradio
    echo "✅ Gradio installed successfully!"
}

echo ""
echo "🎉 Starting Chat Interface..."
echo ""
echo "📋 The chat interface will be available at:"
echo "   • Chat Interface: http://localhost:7860"
echo "   • NLP Agent API: http://localhost:8000"
echo ""
echo "💡 Click on example queries or type naturally:"
echo "   • 'Check my authentication status'"
echo "   • 'List all contacts'"
echo "   • 'Create a contact named John Smith with email john@example.com'"
echo ""
echo "🛑 Press Ctrl+C to stop the chat interface"
echo ""

# Start the chat interface
python chat_interface.py
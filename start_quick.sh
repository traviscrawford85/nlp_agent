#!/bin/bash

# Quick Start Script - Launches API and Chat UI in same terminal with tmux/screen
# For development and quick testing

set -e

echo "🚀 Clio NLP Agent - Quick Start"
echo "=============================="

# Check if we're in the right directory
if [ ! -f "main.py" ] || [ ! -f "chat_interface_pro.py" ]; then
    echo "❌ Error: Required files not found. Please run from clio-nlp-agent directory."
    exit 1
fi

# Activate virtual environment
if [ -d ".venv" ]; then
    echo "🔌 Activating virtual environment..."
    source .venv/bin/activate
else
    echo "⚠️  No virtual environment found. Please create one first."
    exit 1
fi

# Set OpenAI API key (no hard-coded secrets). Load from .env if present.
if [ -z "$OPENAI_API_KEY" ] && [ -f ".env" ]; then
  set -a
  source .env
  set +a
fi

if [ -z "$OPENAI_API_KEY" ]; then
  echo "OPENAI_API_KEY is not set. Export it or add it to .env before running."
  exit 1
fi

# Set OpenAI API key
export OPENAI_API_KEY

echo "📦 Installing/checking dependencies..."
pip install -q gradio 2>/dev/null || echo "Gradio already installed"

# Check if tmux is available
if command -v tmux &> /dev/null; then
    echo "🖥️  Using tmux for split terminal..."

    # Create new tmux session with two panes
    tmux new-session -d -s clio-nlp -x 120 -y 40

    # Split window horizontally
    tmux split-window -h

    # Left pane: Start API server
    tmux send-keys -t clio-nlp:0.0 "cd $(pwd) && source .venv/bin/activate && export OPENAI_API_KEY='$OPENAI_API_KEY' && echo '🤖 Starting NLP Agent API...' && uvicorn main:app --host 0.0.0.0 --port 8001" C-m

    # Right pane: Wait then start chat interface
    tmux send-keys -t clio-nlp:0.1 "cd $(pwd) && source .venv/bin/activate && echo '⏳ Waiting for API to start...' && sleep 8 && echo '🎨 Starting Chat Interface...' && python chat_interface_pro.py" C-m

    # Set pane titles
    tmux select-pane -t clio-nlp:0.0 -T "NLP Agent API"
    tmux select-pane -t clio-nlp:0.1 -T "Chat Interface"

    echo ""
    echo "✅ Started in tmux session 'clio-nlp'"
    echo "📱 Chat Interface: http://localhost:7861"
    echo "🤖 API Server: http://localhost:8001"
    echo "📖 API Docs: http://localhost:8001/docs"
    echo ""
    echo "💡 Commands:"
    echo "   tmux attach -t clio-nlp    # Attach to session"
    echo "   tmux kill-session -t clio-nlp    # Stop all services"
    echo "   Ctrl+B then D    # Detach from session"
    echo "   Ctrl+B then ←→   # Switch between panes"
    echo ""

    # Attach to the tmux session
    tmux attach -t clio-nlp

elif command -v screen &> /dev/null; then
    echo "🖥️  Using screen for background processes..."

    # Start API in detached screen
    screen -dmS clio-api bash -c "cd $(pwd) && source .venv/bin/activate && export OPENAI_API_KEY='$OPENAI_API_KEY' && uvicorn main:app --host 0.0.0.0 --port 8001"

    echo "🤖 API started in screen session 'clio-api'"
    echo "⏳ Waiting 5 seconds for API to initialize..."
    sleep 5

    # Start chat interface in detached screen
    screen -dmS clio-chat bash -c "cd $(pwd) && source .venv/bin/activate && python chat_interface_pro.py"

    echo "🎨 Chat interface started in screen session 'clio-chat'"
    echo ""
    echo "✅ Both services running in background"
    echo "📱 Chat Interface: http://localhost:7861"
    echo "🤖 API Server: http://localhost:8001"
    echo ""
    echo "💡 Commands:"
    echo "   screen -r clio-api     # Attach to API server"
    echo "   screen -r clio-chat    # Attach to chat interface"
    echo "   screen -X -S clio-api quit    # Stop API"
    echo "   screen -X -S clio-chat quit   # Stop chat"
    echo ""
    echo "🛑 Press Enter when you want to stop all services..."
    read

    echo "🛑 Stopping services..."
    screen -X -S clio-api quit 2>/dev/null || true
    screen -X -S clio-chat quit 2>/dev/null || true
    echo "✅ All services stopped"

else
    echo "⚠️  Neither tmux nor screen available."
    echo "🔧 Please install one of them for best experience:"
    echo "   Ubuntu/Debian: sudo apt install tmux"
    echo "   macOS: brew install tmux"
    echo ""
    echo "🔄 Falling back to sequential startup..."
    echo "   Starting API server first, then manually start chat interface."
    echo ""

    # Start API server in foreground
    echo "🤖 Starting NLP Agent API (Ctrl+C to stop)..."
    uvicorn main:app --host 0.0.0.0 --port 8001
fi
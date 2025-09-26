#!/bin/bash

# Start Professional Chat Interface for Clio NLP Agent
# Enhanced with Clio brand colors and professional UX design

set -e  # Exit on any error

echo "🎨 Clio NLP Agent - Professional Chat Interface"
echo "=============================================="

# Check if we're in the right directory
if [ ! -f "chat_interface_pro.py" ]; then
    echo "❌ Error: chat_interface_pro.py not found. Please run this script from the clio-nlp-agent directory."
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
if ! curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "❌ NLP agent is not running at http://localhost:8001"
    echo ""
    echo "🚀 Please start the NLP agent first:"
    echo "   1. Open another terminal"
    echo "   2. cd to this directory: cd /home/sysadmin01/clio_assistant/clio-nlp-agent"
    echo "   3. Run: source .venv/bin/activate"
    echo "   4. Start agent: uvicorn main:app --host 0.0.0.0 --port 8001"
    echo "   5. Wait for it to show 'Uvicorn running on http://0.0.0.0:8001'"
    echo "   6. Then come back and run this professional chat interface"
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
echo "🎨 Starting Professional Chat Interface with Clio Branding..."
echo ""
echo "📋 Features in this enhanced version:"
echo "   • 🎨 Clio brand colors (Ocean Blue, Mountain Blue, Coral, Emerald)"
echo "   • 📱 Responsive design with professional styling"
echo "   • 🏗️ Improved UX with status dashboard and organized examples"
echo "   • ♿ Accessibility features and keyboard shortcuts"
echo "   • 🔄 Real-time status monitoring and refresh"
echo "   • 📊 Enhanced execution details and error handling"
echo ""
echo "📋 The interface will be available at:"
echo "   • Professional Chat: http://localhost:7860"
echo "   • NLP Agent API: http://localhost:8001"
echo ""
echo "💡 Professional features:"
echo "   • 📊 Real-time system status dashboard"
echo "   • 🎯 Categorized example queries with color coding"
echo "   • ⚡ Enhanced error handling with helpful suggestions"
echo "   • 🔄 Auto-refresh capabilities"
echo "   • 📱 Mobile-responsive design"
echo "   • ♿ WCAG accessibility compliance"
echo ""
echo "🛑 Press Ctrl+C to stop the interface"
echo ""

# Start the professional chat interface
python chat_interface_pro.py
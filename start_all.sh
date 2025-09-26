#!/bin/bash

# Unified Startup Script for Clio NLP Agent
# Starts both the API server and professional chat interface simultaneously

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Clio NLP Agent - Complete System Startup${NC}"
echo -e "${BLUE}==========================================${NC}"

# Check if we're in the right directory
if [ ! -f "main.py" ] || [ ! -f "chat_interface_pro.py" ]; then
    echo -e "${RED}❌ Error: Required files not found. Please run this script from the clio-nlp-agent directory.${NC}"
    echo -e "${YELLOW}   Expected files: main.py, chat_interface_pro.py${NC}"
    exit 1
fi

# Function to cleanup background processes on exit
cleanup() {
    echo -e "\n${YELLOW}🛑 Shutting down services...${NC}"
    if [ ! -z "$API_PID" ]; then
        echo -e "${YELLOW}   Stopping NLP Agent API (PID: $API_PID)${NC}"
        kill $API_PID 2>/dev/null || true
    fi
    if [ ! -z "$CHAT_PID" ]; then
        echo -e "${YELLOW}   Stopping Chat Interface (PID: $CHAT_PID)${NC}"
        kill $CHAT_PID 2>/dev/null || true
    fi
    echo -e "${GREEN}✅ All services stopped. Goodbye!${NC}"
    exit 0
}

# Set trap to cleanup on Ctrl+C
trap cleanup SIGINT SIGTERM

# Activate virtual environment if available
if [ -d ".venv" ]; then
    echo -e "${CYAN}🔌 Activating virtual environment...${NC}"
    source .venv/bin/activate
else
    echo -e "${RED}⚠️  No virtual environment found. Please create one with:${NC}"
    echo -e "${YELLOW}   python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt${NC}"
    exit 1
fi

# Set OpenAI API key if not already set
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  OPENAI_API_KEY not set in environment${NC}"
    echo -e "${CYAN}Using the provided API key...${NC}"
else
    echo -e "${GREEN}✅ Using OPENAI_API_KEY from environment${NC}"
fi
if [ -z "$OPENAI_API_KEY" ]; then
    if [ -f ".env" ]; then
        echo -e "${CYAN}\ud83d\udd11 Loading environment from .env${NC}"
        set -a
        source .env
        set +a
    fi
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}\u274c OPENAI_API_KEY is not set. Set it in your shell or create a .env file first.${NC}"
    echo -e "${YELLOW}   Example: echo 'OPENAI_API_KEY=sk-...' >> .env${NC}"
    exit 1
else
    echo -e "${GREEN}\u2705 Using OPENAI_API_KEY from environment${NC}"
fi
if [ -z "$OPENAI_API_KEY" ]; then
    if [ -f ".env" ]; then
        echo -e "${CYAN}\ud83d\udd11 Loading environment from .env${NC}"
        set -a
        source .venv/bin/activate 2>/dev/null || true
        source .env
        set +a
    fi
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}\u274c OPENAI_API_KEY is not set. Set it in your shell or create a .env file first.${NC}"
    echo -e "${YELLOW}   Example: echo 'OPENAI_API_KEY=sk-...' >> .env${NC}"
    exit 1
else
    echo -e "${GREEN}\u2705 Using OPENAI_API_KEY from environment${NC}"
fi

# Run setup verification
echo -e "${CYAN}🔍 Running setup verification...${NC}"
python verify_setup.py > /dev/null 2>&1 || {
    echo -e "${RED}❌ Setup verification failed. Running it now to show details:${NC}"
    python verify_setup.py
    echo -e "${YELLOW}   Please fix the issues above before starting the system.${NC}"
    exit 1
}

# Check dependencies
echo -e "${CYAN}📦 Checking dependencies...${NC}"
python -c "import fastapi, uvicorn, langchain, openai, gradio" 2>/dev/null || {
    echo -e "${YELLOW}⚠️  Some dependencies not fully installed. Installing now...${NC}"
    pip install -r requirements.txt
    echo -e "${GREEN}✅ Dependencies installed successfully!${NC}"
}

# Check for and kill any existing processes on required ports
echo -e "${CYAN}🧹 Checking for existing processes on ports 8001 and 7861...${NC}"
API_EXISTING_PID=$(lsof -ti:8001 2>/dev/null || echo "")
if [ ! -z "$API_EXISTING_PID" ]; then
    echo -e "${YELLOW}   Found existing process on port 8001 (PID: $API_EXISTING_PID). Killing it...${NC}"
    kill $API_EXISTING_PID 2>/dev/null || true
    sleep 2
fi

CHAT_EXISTING_PID=$(lsof -ti:7861 2>/dev/null || echo "")
if [ ! -z "$CHAT_EXISTING_PID" ]; then
    echo -e "${YELLOW}   Found existing process on port 7861 (PID: $CHAT_EXISTING_PID). Killing it...${NC}"
    kill $CHAT_EXISTING_PID 2>/dev/null || true
    sleep 2
fi

# Start the NLP Agent API server in the background
echo -e "${PURPLE}🤖 Starting Clio NLP Agent API Server...${NC}"
uvicorn main:app --host 0.0.0.0 --port 8001 > api_server.log 2>&1 &
API_PID=$!

echo -e "${GREEN}   ✅ API Server started (PID: $API_PID)${NC}"
echo -e "${CYAN}   📍 API running at: http://localhost:8001${NC}"
echo -e "${CYAN}   📖 API docs at: http://localhost:8001/docs${NC}"

# Wait for API server to be ready
echo -e "${CYAN}⏳ Waiting for API server to be ready...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo -e "${GREEN}   ✅ API server is ready!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ API server failed to start within 30 seconds${NC}"
        echo -e "${YELLOW}   Check api_server.log for details${NC}"
        cleanup
    fi
    echo -e "${YELLOW}   ⏳ Still waiting... ($i/30)${NC}"
    sleep 1
done

# Start the Chat Interface in the background
echo -e "${PURPLE}🎨 Starting Professional Chat Interface...${NC}"
python chat_interface_pro.py > chat_interface.log 2>&1 &
CHAT_PID=$!

echo -e "${GREEN}   ✅ Chat Interface started (PID: $CHAT_PID)${NC}"

# Wait for Chat Interface to be ready
echo -e "${CYAN}⏳ Waiting for chat interface to be ready...${NC}"
for i in {1..20}; do
    if curl -s http://localhost:7861 > /dev/null 2>&1; then
        echo -e "${GREEN}   ✅ Chat interface is ready!${NC}"
        break
    fi
    if [ $i -eq 20 ]; then
        echo -e "${YELLOW}⚠️  Chat interface may still be starting...${NC}"
        break
    fi
    sleep 1
done

# Display startup summary
echo -e "\n${GREEN}🎉 SUCCESS! Clio NLP Agent System is Running${NC}"
echo -e "${GREEN}===========================================${NC}"
echo ""
echo -e "${BLUE}📱 CHAT INTERFACE (Professional UI):${NC}"
echo -e "${CYAN}   🌐 http://localhost:7861${NC}"
echo -e "${CYAN}   🎨 Enhanced with Clio brand colors${NC}"
echo -e "${CYAN}   📱 Responsive design with professional UX${NC}"
echo ""
echo -e "${BLUE}🤖 NLP AGENT API:${NC}"
echo -e "${CYAN}   🌐 http://localhost:8001${NC}"
echo -e "${CYAN}   📖 Documentation: http://localhost:8001/docs${NC}"
echo -e "${CYAN}   🔍 Health Check: http://localhost:8001/health${NC}"
echo -e "${CYAN}   🔐 Auth Status: http://localhost:8001/auth/status${NC}"
echo ""
echo -e "${BLUE}💡 QUICK TEST:${NC}"
echo -e "${CYAN}   curl -X POST 'http://localhost:8001/nlp' \\\\${NC}"
echo -e "${CYAN}     -H 'Content-Type: application/json' \\\\${NC}"
echo -e "${CYAN}     -d '{\"query\": \"Check my authentication status\"}'${NC}"
echo ""
echo -e "${BLUE}📋 LOG FILES:${NC}"
echo -e "${CYAN}   🤖 API Server: api_server.log${NC}"
echo -e "${CYAN}   🎨 Chat Interface: chat_interface.log${NC}"
echo -e "${CYAN}   📊 Agent Activity: clio_nlp_agent.log${NC}"
echo ""
echo -e "${GREEN}✨ FEATURES AVAILABLE:${NC}"
echo -e "${CYAN}   • Natural language queries to Clio API${NC}"
echo -e "${CYAN}   • Real-time status monitoring${NC}"
echo -e "${CYAN}   • Professional web chat interface${NC}"
echo -e "${CYAN}   • Automatic authentication management${NC}"
echo -e "${CYAN}   • 535+ custom fields support${NC}"
echo -e "${CYAN}   • Contact, matter, and time tracking operations${NC}"
echo ""
echo -e "${PURPLE}🛑 Press Ctrl+C to stop both services${NC}"
echo ""

# Keep the script running and monitor the services
while true; do
    # Check if API server is still running
    if ! kill -0 $API_PID 2>/dev/null; then
        echo -e "${RED}❌ API Server stopped unexpectedly${NC}"
        echo -e "${YELLOW}   Check api_server.log for details${NC}"
        cleanup
    fi

    # Check if Chat Interface is still running
    if ! kill -0 $CHAT_PID 2>/dev/null; then
        echo -e "${RED}❌ Chat Interface stopped unexpectedly${NC}"
        echo -e "${YELLOW}   Check chat_interface.log for details${NC}"
        cleanup
    fi

    sleep 5
done
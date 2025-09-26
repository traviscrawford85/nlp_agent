# 🤖 Clio NLP Agent

A production-ready FastAPI + LangChain application that provides a **natural language interface to Clio's API and CLI tools**. Simply tell it what you want to do in plain English, and it will execute the appropriate Clio operations.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.117+-green.svg)](https://fastapi.tiangolo.com/)
[![LangChain](https://img.shields.io/badge/LangChain-0.3+-purple.svg)](https://python.langchain.com/)

---

## 🎯 What This Agent Does

Transform complex Clio operations into simple conversations:

```bash
# Instead of this:
curl -X POST "https://app.clio.com/api/v4/contacts" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data": {"first_name": "John", "last_name": "Doe", "email": "john@example.com"}}'

# Just say this:
curl -X POST "http://localhost:8000/nlp" \
  -H "Content-Type: application/json" \
  -d '{"query": "Create a contact named John Doe with email john@example.com"}'
```

## ✨ Key Features

- 🔐 **Automatic Authentication** - Retrieves Clio tokens from your existing database
- 🧠 **Natural Language Processing** - Powered by OpenAI and LangChain
- 🚀 **Production Ready** - Rate limiting, error handling, comprehensive logging
- 🛠️ **CLI Integration** - Works with `~/clio_service` and `~/custom-fields-manager`
- 🎛️ **Custom Field Set Management** - Update field sets via Clio web UI endpoints
- 🤖 **Automated Browser Login** - Extracts session cookies using Playwright
- 📊 **Real-time Monitoring** - Health checks and authentication status
- 🔄 **Auto-pagination** - Handles large result sets automatically
- 📖 **Interactive Docs** - Built-in API documentation at `/docs`

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Verify Setup
```bash
cd clio-nlp-agent
python verify_setup.py
```
You should see: `🎉 READY TO START!`

### Step 2: Set Environment Variables
```bash
export OPENAI_API_KEY="your-openai-api-key"
# Clio auth is automatically retrieved from ~/custom-fields-manager/clio_auth.db
```

### Step 3: Start the Agent
```bash
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Step 4: Test It!
```bash
curl -X POST "http://localhost:8000/nlp" \
  -H "Content-Type: application/json" \
  -d '{"query": "Check my authentication status"}'
```

**🎉 That's it! Your Clio NLP Agent is running at http://localhost:8000**

---

## 📋 Complete Installation Guide

### Prerequisites Check

Run our verification script first:
```bash
python verify_setup.py
```

This checks:
- ✅ Python 3.10+ installed
- ✅ Clio authentication database exists
- ✅ CLI tools are accessible
- ✅ Project files are present

### Environment Setup

1. **Create Virtual Environment** (if not exists):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Required Environment Variables**:
   ```bash
   # Required: Your OpenAI API key
   export OPENAI_API_KEY="sk-your-openai-api-key-here"

   # Optional: Override auto-detected Clio token
   # export CLIO_AUTH_TOKEN="your-clio-token"

   # Optional: Customize model and behavior
   # export OPENAI_MODEL="gpt-4"
   # export AGENT_TEMPERATURE="0.1"
   ```

### Authentication Setup

The agent **automatically** retrieves your Clio authentication token from:
`~/custom-fields-manager/clio_auth.db`

To verify this works:
```bash
python simple_auth_test.py
```

You should see your Clio user information and token status.

---

## 💬 How to Use the NLP Agent

### Basic Usage

**Start the server:**
```bash
source .venv/bin/activate
OPENAI_API_KEY="your-key" uvicorn main:app --host 0.0.0.0 --port 8000
```

**Send natural language queries:**
```bash
curl -X POST "http://localhost:8000/nlp" \
  -H "Content-Type: application/json" \
  -d '{"query": "Your natural language request here"}'
```

### Example Queries

#### 👥 Contact Management
```bash
# Create contacts
"Create a new contact named Jane Smith with email jane@example.com"
"Add a contact for John at ABC Corp with phone 555-1234"

# Find contacts
"Find all contacts with the last name Johnson"
"Search for contacts at Microsoft"
"Show me contacts created this month"

# Update contacts
"Update contact ID 12345 to change their email to newemail@example.com"
"Change the phone number for John Smith to 555-9999"
```

#### ⚖️ Matter Management
```bash
# Create matters
"Create a new matter for client ID 456 called Personal Injury Case"
"Add a matter: Description 'Contract Review' for client John Doe"

# Find matters
"Show me all open matters"
"Find matters for client ID 123"
"List matters created in the last 30 days"
```

#### ⏱️ Time Tracking
```bash
# Add time entries
"Add 2 hours of work on matter 789 for contract review"
"Create time entry: 1.5 hours on matter 123 for client meeting"
"Log 30 minutes on matter 456 for phone call"

# View time entries
"Show time entries for this week"
"Find all activities for matter 789"
```

#### 🏷️ Custom Fields
```bash
# Manage fields
"List all custom fields for contacts"
"Show custom field values for contact ID 123"
"Set the Priority custom field to High for matter 456"

# Analysis
"Find all custom fields that are not being used"
"Generate a custom fields usage report"
```

#### 🛠️ CLI Operations
```bash
# System operations
"Run a data sync for all contacts"
"Check authentication status"
"Generate a backup of the custom fields database"
"Validate custom field data integrity"
```

### Advanced Query Features

**Context Passing:**
```json
{
  "query": "Create a time entry for the client meeting",
  "context": {
    "matter_id": "123",
    "default_duration": "1 hour"
  }
}
```

**Batch Operations:**
```json
{
  "query": "Create contacts for: John Doe (john@example.com), Jane Smith (jane@example.com), Bob Wilson (bob@example.com)"
}
```

**Complex Workflows:**
```json
{
  "query": "Find all clients from last month, then create a summary report of their matters and total time tracked"
}
```

---

## 🔧 API Reference

### Core Endpoints

| Endpoint | Method | Description | Example |
|----------|--------|-------------|---------|
| `/nlp` | POST | Process natural language queries | `{"query": "List contacts"}` |
| `/health` | GET | System health and status | Service status check |
| `/auth/status` | GET | Authentication information | Current Clio session |
| `/tools` | GET | List available agent tools | All capabilities |
| `/examples` | GET | Example queries | Query templates |
| `/docs` | GET | Interactive API documentation | Swagger UI |

### Request Format

```json
{
  "query": "Your natural language request",
  "include_raw_data": true,
  "max_results": 100,
  "timeout": 60
}
```

### Response Format

```json
{
  "success": true,
  "message": "Human-readable explanation of what was done",
  "data": {"structured": "data"},
  "operation_type": "create_contact",
  "execution_time": 2.34,
  "agent_thoughts": [
    {
      "step": 1,
      "thought": "I need to create a contact",
      "action": "create_contact(...)"
    }
  ],
  "confidence_score": 0.95
}
```

### Health Check Response

```bash
curl http://localhost:8000/health
```
```json
{
  "status": "healthy",
  "services": {
    "agent": "healthy",
    "openai": "configured",
    "clio_auth": "authenticated_as_Ledyard_Law_LLC",
    "clio_cli": "available",
    "custom_fields_cli": "available"
  }
}
```

### Authentication Status

```bash
curl http://localhost:8000/auth/status
```
```json
{
  "authenticated": true,
  "user_name": "Ledyard Law LLC",
  "expires_at": "2025-10-15T19:57:04.854157",
  "is_expired": false,
  "token_source": "database"
}
```

---

## 🏗️ Architecture & Components

### System Overview
```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   User Query    │───▶│  NLP Agent   │───▶│  Clio API/CLI   │
│ "Create contact"│    │ (LangChain)  │    │   Operations    │
└─────────────────┘    └──────────────┘    └─────────────────┘
```

### Core Components

- **`main.py`** - FastAPI application with async endpoints
- **`agent.py`** - LangChain agent with 11 specialized tools
- **`services/auth_manager.py`** - Automatic token retrieval from database
- **`services/rate_limiter.py`** - API rate limiting and pagination
- **`tools/clio_api.py`** - Complete Clio API wrapper
- **`tools/clio_cli.py`** - `~/clio_service` CLI integration
- **`tools/custom_fields_cli.py`** - `~/custom-fields-manager` CLI integration

### Available Tools

The agent has 11 specialized tools:

| Tool | Description | Example Usage |
|------|-------------|---------------|
| `get_contacts` | Search/retrieve contacts | "Find contacts named Smith" |
| `create_contact` | Create new contacts | "Add John Doe contact" |
| `update_contact` | Update existing contacts | "Change John's email" |
| `get_matters` | Search/retrieve matters | "Show open matters" |
| `create_matter` | Create new matters | "Create PI case for client 123" |
| `get_activities` | Retrieve time entries | "Show this week's time" |
| `create_activity` | Log time entries | "Add 2 hours contract work" |
| `get_custom_fields` | List custom fields | "Show contact custom fields" |
| `manage_custom_field_values` | Set field values | "Set priority to High" |
| `execute_clio_cli` | Run clio service commands | "Run data sync" |
| `execute_custom_fields_cli` | Run CFM commands | "Generate usage report" |

---

## 🔒 Security & Authentication

### Automatic Token Management

The agent automatically handles Clio authentication:

1. **Environment Variable** (highest priority)
   ```bash
   export CLIO_AUTH_TOKEN="manual-override-token"
   ```

2. **Database Retrieval** (default)
   - Reads from: `~/custom-fields-manager/clio_auth.db`
   - Finds most recent valid session
   - Handles token expiration gracefully

3. **Session Management**
   - Monitors token expiration
   - Provides refresh token support (placeholder)
   - Logs authentication events

### Security Features

- 🔐 Tokens never logged or exposed in responses
- 🚦 Rate limiting prevents API abuse
- 📝 Comprehensive audit logging
- 🔄 Automatic retry with exponential backoff
- ⏱️ Request timeouts prevent hanging

---

## 📊 Monitoring & Logging

### Health Monitoring

Check system status anytime:
```bash
curl http://localhost:8000/health
```

Monitor these key indicators:
- `agent`: "healthy" = LangChain agent operational
- `openai`: "configured" = OpenAI API key set
- `clio_auth`: "authenticated_as_User" = Clio token valid
- `clio_cli`: "available" = CLI tools accessible

### Logging

**Real-time logs** (terminal where server runs):
```
INFO:     Started server process [12345]
INFO:     Using Clio auth token for user: Ledyard Law LLC
INFO:     Agent initialized successfully
```

**Detailed logs** (`clio_nlp_agent.log`):
- Request/response details
- Authentication events
- Tool execution traces
- Error diagnostics

**Log Levels:**
- `INFO`: Normal operations
- `WARNING`: Rate limiting, retries
- `ERROR`: Failures, authentication issues
- `DEBUG`: Detailed execution traces

---

## 🛠️ Development & Customization

### Project Structure
```
clio-nlp-agent/
├── main.py                    # FastAPI server
├── agent.py                   # LangChain agent core
├── verify_setup.py            # Setup verification
├── working_demo.py            # Standalone demo
├── simple_auth_test.py        # Auth testing
├── start_agent.sh             # Quick start script
├── .venv/                     # Virtual environment
├── services/
│   ├── auth_manager.py        # Auto authentication
│   ├── rate_limiter.py        # API limits & pagination
│   └── client_generator.py    # OpenAPI client gen
├── tools/
│   ├── clio_api.py           # API wrapper
│   ├── clio_cli.py           # CLI wrapper
│   └── custom_fields_cli.py   # CFM wrapper
├── models/
│   ├── requests.py           # Request schemas
│   └── responses.py          # Response schemas
├── tests/
│   ├── test_unit_tools.py    # Unit tests
│   └── test_integration.py   # Integration tests
└── docs/
    ├── README.md             # This file
    └── INSTRUCTIONS.md       # Detailed user guide
```

### Adding New Tools

1. **Create tool function** in `agent.py`:
   ```python
   async def _my_new_tool(self, param1: str) -> str:
       # Tool implementation
       return json.dumps({"result": "success"})
   ```

2. **Add to tools list**:
   ```python
   StructuredTool(
       name="my_new_tool",
       description="What this tool does",
       func=self._my_new_tool,
       args_schema=MyNewToolInput
   )
   ```

3. **Create input schema**:
   ```python
   class MyNewToolInput(BaseModel):
       param1: str = Field(..., description="Parameter description")
   ```

### Customizing Agent Behavior

**Model Selection:**
```bash
export OPENAI_MODEL="gpt-4"  # Use GPT-4
export OPENAI_MODEL="gpt-3.5-turbo-16k"  # Default
```

**Temperature (Creativity):**
```bash
export AGENT_TEMPERATURE="0.1"  # Focused (default)
export AGENT_TEMPERATURE="0.7"  # More creative
```

**Agent Configuration** (in `agent.py`):
```python
self.agent = initialize_agent(
    tools=self.tools,
    llm=self.llm,
    agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,  # Set to False for less logging
    max_iterations=15,  # Increase for complex tasks
    max_execution_time=300  # 5-minute timeout
)
```

---

## 🧪 Testing

### Automated Testing

**Run all tests:**
```bash
source .venv/bin/activate
pytest tests/ -v
```

**Test categories:**
- `test_unit_tools.py` - Individual tool testing with mocks
- `test_integration.py` - End-to-end workflow testing

**Coverage report:**
```bash
pytest --cov=. --cov-report=html
```

### Manual Testing

**Setup verification:**
```bash
python verify_setup.py
```

**Authentication testing:**
```bash
python simple_auth_test.py
```

**Working demo:**
```bash
python working_demo.py
```

**Live server testing:**
```bash
# Health check
curl http://localhost:8000/health

# Simple query
curl -X POST "http://localhost:8000/nlp" \
  -H "Content-Type: application/json" \
  -d '{"query": "Check auth status"}'
```

---

## 🐛 Troubleshooting

### Common Issues & Solutions

#### 🔐 Authentication Problems

**Error**: `"No Clio auth token available"`

**Solutions:**
1. Run authentication test:
   ```bash
   python simple_auth_test.py
   ```

2. Check database exists:
   ```bash
   ls -la ~/custom-fields-manager/clio_auth.db
   ```

3. Manual override:
   ```bash
   export CLIO_AUTH_TOKEN="your-token"
   ```

#### 🤖 OpenAI API Issues

**Error**: `"OpenAI API key not configured"`

**Solutions:**
```bash
# Check if set
echo $OPENAI_API_KEY

# Set properly
export OPENAI_API_KEY="sk-your-actual-key"

# Test key works
python -c "import openai; print('API key format OK')"
```

#### 🛠️ CLI Tool Problems

**Error**: `"Command not found"` or `"CLI tool not available"`

**Solutions:**
```bash
# Verify paths exist
ls -la ~/clio_service
ls -la ~/custom-fields-manager

# Test CLI directly
cd ~/clio_service && ./clio --help
cd ~/custom-fields-manager && cfm --help
```

#### 📦 Import/Dependency Issues

**Error**: `"ModuleNotFoundError"`

**Solutions:**
```bash
# Activate virtual environment
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Check installation
pip list | grep -E "(fastapi|langchain|openai)"
```

#### 🚦 Rate Limiting

**Message**: `"Rate limited by server"`

**Solutions:**
- Agent automatically handles rate limiting
- Check server logs for retry attempts
- Reduce query frequency if needed
- Verify API quotas not exceeded

### Debugging Steps

1. **Check system status:**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Verify authentication:**
   ```bash
   curl http://localhost:8000/auth/status
   ```

3. **Test simple query:**
   ```bash
   curl -X POST "http://localhost:8000/nlp" \
     -d '{"query": "test basic functionality"}'
   ```

4. **Check logs:**
   - Server terminal: Real-time activity
   - `clio_nlp_agent.log`: Detailed traces

5. **Run verification:**
   ```bash
   python verify_setup.py
   ```

---

## 🚀 Production Deployment

### Docker Deployment

**Create Dockerfile:**
```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Build and run:**
```bash
docker build -t clio-nlp-agent .
docker run -p 8000:8000 \
  -e OPENAI_API_KEY="your-key" \
  -v ~/custom-fields-manager:/data/cfm \
  clio-nlp-agent
```

### Production Server

**With Gunicorn:**
```bash
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

**Systemd service** (`/etc/systemd/system/clio-nlp-agent.service`):
```ini
[Unit]
Description=Clio NLP Agent
After=network.target

[Service]
Type=simple
User=clio
WorkingDirectory=/path/to/clio-nlp-agent
Environment=OPENAI_API_KEY=your-key
ExecStart=/path/to/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Environment Variables for Production

```bash
# Required
export OPENAI_API_KEY="your-production-openai-key"

# Optional
export OPENAI_MODEL="gpt-4"
export AGENT_TEMPERATURE="0.05"  # More focused for production
export LOG_LEVEL="info"
export HOST="0.0.0.0"
export PORT="8000"

# Security
export ALLOWED_HOSTS="your-domain.com,api.yourdomain.com"
export CORS_ORIGINS="https://your-frontend.com"
```

---

## 🤝 Contributing

### Development Setup

1. **Fork and clone:**
   ```bash
   git clone your-fork-url
   cd clio-nlp-agent
   ```

2. **Setup development environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   pip install black isort flake8 mypy pytest
   ```

3. **Code formatting:**
   ```bash
   black .
   isort .
   flake8 .
   mypy .
   ```

4. **Run tests:**
   ```bash
   pytest tests/ -v
   ```

### Contribution Guidelines

- ✅ Add tests for new features
- ✅ Update documentation
- ✅ Follow existing code style
- ✅ Include example usage
- ✅ Test with actual Clio data

---

## 📜 License

[Add your license information here]

---

## 🆘 Support & Help

### Getting Help

1. **Built-in help:**
   - Visit `http://localhost:8000/docs` for interactive API docs
   - Use `http://localhost:8000/examples` for query examples

2. **Verification tools:**
   - Run `python verify_setup.py` for system check
   - Run `python simple_auth_test.py` for auth verification

3. **Documentation:**
   - This README for setup and API reference
   - `INSTRUCTIONS.md` for detailed usage guide

4. **Logs and monitoring:**
   - Check `http://localhost:8000/health` for system status
   - Review `clio_nlp_agent.log` for detailed traces

---

## 🎉 Success Stories

**What you can accomplish:**

✅ **"Create a contact for John Smith at Acme Corp with email john@acme.com"**
→ *Contact created with ID 12345*

✅ **"Show me all open matters for this month with their total time tracked"**
→ *Retrieved 15 matters with 234.5 hours total*

✅ **"Set the Priority custom field to High for all matters containing 'urgent'"**
→ *Updated 8 matters with Priority = High*

✅ **"Generate a backup of my custom fields and create a usage report"**
→ *Backup saved, 23 fields analyzed*

---

**🚀 Ready to transform your Clio workflow with natural language? Start with `python verify_setup.py` and begin your journey!**
# NLP Agent

A type-safe NLP agent system with FastAPI services, Python client, and CLI integration. This system maps natural language queries to API and CLI calls with comprehensive error handling and Clio API constraints.

## Features

- 🚀 **FastAPI Service** with OpenAPI specification
- 🔒 **Type-safe Pydantic Models** generated from OpenAPI schema
- 🐍 **Python Client** with async/sync support
- 🖥️ **CLI Integration** for local services (~/clio_service, ~/custom-fields-manager)
- 🧠 **Natural Language Processing** to map queries to API/CLI calls
- 📊 **Clio API Constraints**: pagination, filtering, rate limiting
- ✅ **Comprehensive Tests** with pytest
- 📝 **Structured Logging** and error handling
- 🔧 **Maintainable Architecture** with clear separation of concerns

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/traviscrawford85/nlp_agent.git
cd nlp_agent

# Install dependencies
pip install -e .
# Or for development
pip install -e ".[dev]"
```

### Start the API Server

```bash
# Using the CLI
nlp-agent serve --host 0.0.0.0 --port 8000

# Or directly with uvicorn
uvicorn nlp_agent.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Using the CLI

```bash
# Check API health
nlp-agent health

# Process natural language queries
nlp-agent query "show me the health status"
nlp-agent query "list all queries with status completed" --metadata

# List processed queries with pagination
nlp-agent list-queries --page 1 --limit 10 --status completed

# Execute CLI commands
nlp-agent cli clio_service list --args "--help"
nlp-agent cli custom-fields-manager create --args "field_name" --input-data '{"type": "text"}'
```

### Using the Python Client

```python
import asyncio
from nlp_agent.client.client import NLPAgentClient

async def main():
    async with NLPAgentClient("http://localhost:8000") as client:
        # Check health
        health = await client.health_check()
        print(f"Status: {health.status}")
        
        # Process query
        response = await client.process_query(
            query="show me all completed queries",
            include_metadata=True
        )
        print(f"Query ID: {response.id}")
        print(f"Status: {response.status}")
        
        # List queries with filters
        queries = await client.list_queries(
            page=1, 
            limit=20, 
            status="completed"
        )
        print(f"Found {len(queries.queries)} queries")

# Synchronous version
from nlp_agent.client.client import SyncNLPAgentClient

client = SyncNLPAgentClient("http://localhost:8000")
health = client.health_check()
```

## Architecture

### Project Structure

```
nlp_agent/
├── nlp_agent/
│   ├── api/                 # FastAPI application
│   │   ├── main.py         # Main FastAPI app with rate limiting
│   │   ├── dependencies.py # Dependency injection
│   │   └── services.py     # Business logic services
│   ├── models/             # Pydantic models
│   │   └── schemas.py      # Generated from OpenAPI spec
│   ├── client/             # Python client
│   │   └── client.py       # Async/sync HTTP client
│   ├── cli_integration/    # CLI service integration
│   │   └── manager.py      # Subprocess management
│   ├── nlp/                # Natural language processing
│   │   └── processor.py    # Query to API/CLI mapping
│   └── cli.py              # Command-line interface
├── tests/                  # Comprehensive test suite
├── openapi.json           # OpenAPI specification
└── pyproject.toml         # Project configuration
```

### Core Components

1. **OpenAPI Specification** (`openapi.json`)
   - Defines the complete API contract
   - Enables automatic Pydantic model generation
   - Provides interactive documentation

2. **FastAPI Service** (`nlp_agent.api`)
   - Type-safe endpoints with automatic validation
   - Rate limiting with slowapi (10/min for queries, 5/min for CLI)
   - Structured logging and error handling
   - Pagination and filtering support

3. **Pydantic Models** (`nlp_agent.models`)
   - Type-safe data validation
   - Automatic serialization/deserialization
   - Generated from OpenAPI specification

4. **Python Client** (`nlp_agent.client`)
   - Async/sync HTTP client with httpx
   - Type-safe method signatures
   - Error handling and rate limit detection

5. **CLI Integration** (`nlp_agent.cli_integration`)
   - Subprocess management for local services
   - JSON payload support
   - Output parsing and error handling

6. **NLP Processor** (`nlp_agent.nlp`)
   - Pattern matching for natural language queries
   - Intent extraction and confidence scoring
   - Mapping to appropriate API/CLI calls

## API Endpoints

### Health Check
```http
GET /health
```

### Process Natural Language Query
```http
POST /query
Content-Type: application/json

{
  "query": "show me all completed queries",
  "context": {"user_id": "123"},
  "options": {
    "timeout": 30,
    "include_metadata": true
  }
}
```

### List Queries (with Clio constraints)
```http
GET /queries?page=1&limit=20&status=completed&created_after=2023-01-01T00:00:00Z
```

### Execute CLI Command
```http
POST /cli/execute
Content-Type: application/json

{
  "service": "clio_service",
  "command": "search",
  "args": ["--query", "test"],
  "input_data": {"filters": {"type": "document"}}
}
```

## Natural Language Examples

The NLP processor can understand various natural language queries:

### API Queries
- "check health status" → `GET /health`
- "show me all queries" → `GET /queries`
- "list completed queries" → `GET /queries?status=completed`
- "show queries from last week" → `GET /queries?created_after=...`

### CLI Commands
- "clio list" → `clio_service list`
- "search clio for documents" → `clio_service search documents`
- "list custom fields" → `custom-fields-manager list`
- "create custom field named test_field" → `custom-fields-manager create test_field`

## Rate Limiting (Clio API Constraints)

- **Query Processing**: 10 requests per minute per IP
- **CLI Execution**: 5 requests per minute per IP
- **Other Endpoints**: No specific limits

Rate limits are enforced using slowapi and return HTTP 429 when exceeded.

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=nlp_agent --cov-report=html

# Run specific test files
pytest tests/test_api.py
pytest tests/test_nlp_processor.py
```

### Code Quality

```bash
# Format code
black nlp_agent tests

# Sort imports
isort nlp_agent tests

# Lint code
flake8 nlp_agent tests

# Type checking
mypy nlp_agent
```

### Local CLI Services

For full functionality, ensure local CLI services are available:

```bash
# Example setup (adjust paths as needed)
mkdir -p ~/clio_service ~/custom-fields-manager

# Make them executable
chmod +x ~/clio_service ~/custom-fields-manager
```

## Error Handling

The system provides comprehensive error handling:

- **API Errors**: Structured error responses with timestamps
- **CLI Errors**: Graceful handling of subprocess failures
- **Rate Limiting**: Clear 429 responses with retry information
- **Validation Errors**: Detailed Pydantic validation messages
- **Client Errors**: Custom exception hierarchy

## Logging

Structured logging with configurable levels:

```python
import structlog

logger = structlog.get_logger()
logger.info("Processing query", query_id="123", user_ip="192.168.1.1")
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run the test suite
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
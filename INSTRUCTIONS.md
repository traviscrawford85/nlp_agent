# Clio NLP Agent - User Instructions

A complete guide to using the Clio Natural Language Processing Agent for converting plain English into Clio API operations.

## 🎯 What This Agent Does

The Clio NLP Agent allows you to interact with Clio using natural language instead of complex API calls or CLI commands. Simply tell it what you want to do in plain English, and it will:

- Execute Clio API calls (contacts, matters, activities, custom fields)
- Run CLI commands on `~/clio_service` and `~/custom-fields-manager`
- Handle rate limiting, pagination, and error handling automatically
- Provide both human-readable explanations and structured data

## 🚀 Quick Start Guide

### Step 1: Verify Prerequisites

Run the authentication test to make sure everything is set up:

```bash
cd clio-nlp-agent
python simple_auth_test.py
```

You should see:
```
✅ Found authentication session:
  User: Ledyard Law LLC
  ...
🎉 SUCCESS! Authentication is configured.
```

### Step 2: Set Your OpenAI API Key

```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Start the Agent

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The server will start and show:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 5: Test the Agent

Open another terminal and test:

```bash
curl -X POST "http://localhost:8000/nlp" \
  -H "Content-Type: application/json" \
  -d '{"query": "Check my authentication status"}'
```

## 💬 How to Use Natural Language Queries

### Basic Query Format

Send a POST request to `/nlp` with a JSON body:

```json
{
  "query": "Your natural language request here",
  "include_raw_data": true,
  "max_results": 100
}
```

### Example Queries by Category

#### 👥 Contact Management

**Create Contacts:**
- `"Create a new contact named John Smith with email john@example.com"`
- `"Add a contact for Jane Doe at ABC Corp with phone 555-1234"`
- `"Create contact: First name Mike, Last name Johnson, Company: Tech Solutions"`

**Find Contacts:**
- `"Find all contacts with the last name Johnson"`
- `"Search for contacts at Microsoft"`
- `"Show me contacts created this month"`
- `"Find contact with email user@example.com"`

**Update Contacts:**
- `"Update contact ID 12345 to change their email to newemail@example.com"`
- `"Change the phone number for John Smith to 555-9999"`

#### ⚖️ Matter Management

**Create Matters:**
- `"Create a new matter for client ID 456 called Personal Injury Case"`
- `"Add a matter: Description 'Contract Review' for client John Doe"`
- `"Create matter 'Trademark Registration' for client ID 789, set status to Open"`

**Find Matters:**
- `"Show me all open matters"`
- `"Find matters for client ID 123"`
- `"List matters created in the last 30 days"`
- `"Show matters with status Closed"`

#### ⏱️ Time Tracking

**Add Time Entries:**
- `"Add 2 hours of work on matter 789 for contract review"`
- `"Create time entry: 1.5 hours on matter 123 for client meeting"`
- `"Log 30 minutes on matter 456 for phone call"`

**View Time Entries:**
- `"Show time entries for this week"`
- `"Find all activities for matter 789"`
- `"List time entries by user ID 999"`

#### 🏷️ Custom Fields

**Manage Custom Fields:**
- `"List all custom fields for contacts"`
- `"Show custom field values for contact ID 123"`
- `"Set the Priority custom field to High for matter 456"`
- `"Create a new custom field called Case Type for matters"`

**Custom Field Analysis:**
- `"Find all custom fields that are not being used"`
- `"Generate a custom fields usage report"`
- `"Show duplicate custom fields"`

#### 🛠️ CLI Operations

**System Operations:**
- `"Run a data sync for all contacts"`
- `"Check authentication status"`
- `"Generate a backup of the custom fields database"`
- `"Validate custom field data integrity"`

### Advanced Query Features

#### Context Passing
```json
{
  "query": "Create a time entry for the client meeting",
  "context": {
    "matter_id": "123",
    "default_duration": "1 hour",
    "user_preference": "round_to_quarter_hours"
  }
}
```

#### Batch Operations
```json
{
  "query": "Create contacts for: John Doe (john@example.com), Jane Smith (jane@example.com), Bob Wilson (bob@example.com)"
}
```

#### Complex Workflows
```json
{
  "query": "Find all clients from last month, then create a summary report of their matters and total time tracked"
}
```

## 📊 Understanding Responses

### Successful Response Format

```json
{
  "success": true,
  "message": "Contact 'John Doe' created successfully with ID 12345",
  "data": {
    "id": 12345,
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com"
  },
  "operation_type": "create_contact",
  "entities_affected": [
    {"type": "contact", "id": "12345", "name": "John Doe"}
  ],
  "execution_time": 1.23,
  "agent_thoughts": [
    {
      "step": 1,
      "thought": "I need to create a contact with the provided information",
      "action": "create_contact(first_name='John', last_name='Doe', email='john@example.com')"
    }
  ],
  "confidence_score": 0.95
}
```

### Error Response Format

```json
{
  "success": false,
  "message": "Failed to create contact: Email address is invalid",
  "operation_type": "create_contact",
  "execution_time": 0.45,
  "warnings": ["Email address format validation failed"]
}
```

## 🔧 API Endpoints Reference

### Core Endpoints

- **`POST /nlp`** - Process natural language queries
- **`GET /health`** - System health and status check
- **`GET /auth/status`** - Authentication information
- **`GET /tools`** - List all available tools
- **`GET /examples`** - Get example queries
- **`GET /docs`** - Interactive API documentation

### Health Check Example

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "services": {
    "openai": "configured",
    "clio_auth": "authenticated_as_Ledyard_Law_LLC",
    "clio_cli": "available",
    "custom_fields_cli": "available"
  },
  "timestamp": "2023-09-24T13:45:00",
  "version": "1.0.0"
}
```

### Authentication Status

```bash
curl http://localhost:8000/auth/status
```

Response:
```json
{
  "authenticated": true,
  "user_name": "Ledyard Law LLC",
  "expires_at": "2025-10-15T19:57:04.854157",
  "is_expired": false,
  "has_refresh_token": true,
  "token_source": "database"
}
```

## 🎯 Best Practices

### Writing Effective Queries

1. **Be Specific**: Include IDs, names, and specific criteria
   - ✅ `"Update contact ID 12345 to change their email"`
   - ❌ `"Update a contact"`

2. **Use Natural Language**: Write as you would speak
   - ✅ `"Create a new matter for John's contract review"`
   - ❌ `"POST /matters.json with description=contract"`

3. **Include Context**: Provide relevant details
   - ✅ `"Add 2 hours of contract review work on matter 789"`
   - ❌ `"Add time"`

4. **Batch Related Operations**: Combine related tasks
   - ✅ `"Create contact John Doe and then create a matter for him"`
   - ❌ Send separate requests for each step

### Query Optimization

- **Use Limits**: Add limits for large result sets
  - `"Show me the first 10 contacts created this month"`

- **Specify Filters**: Be explicit about filtering criteria
  - `"Find matters with status Open and created after 2023-09-01"`

- **Request Specific Data**: Ask for exactly what you need
  - `"Get contact names and email addresses for all clients"`

## 🐛 Troubleshooting

### Common Issues

#### 1. Authentication Problems

**Error**: `"No Clio auth token available"`

**Solutions**:
- Run `python simple_auth_test.py` to check authentication
- Verify `~/custom-fields-manager/clio_auth.db` exists and is accessible
- Check if your Clio session has expired
- Manually set `CLIO_AUTH_TOKEN` environment variable if needed

#### 2. OpenAI API Issues

**Error**: `"OpenAI API key not configured"`

**Solutions**:
- Verify: `echo $OPENAI_API_KEY`
- Re-export the key: `export OPENAI_API_KEY="your-key"`
- Check that the key is valid and has sufficient credits

#### 3. CLI Tool Issues

**Error**: `"Command not found"` or `"CLI tool not available"`

**Solutions**:
- Verify `~/clio_service` directory exists and is executable
- Verify `~/custom-fields-manager` directory exists
- Check that CLI commands work manually: `cd ~/clio_service && ./clio --help`

#### 4. Rate Limiting

**Message**: `"Rate limited by server"`

**Solutions**:
- The agent automatically handles rate limiting
- Wait for the system to retry automatically
- Reduce query frequency if making many requests

### Debugging Steps

1. **Check System Status**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Verify Authentication**:
   ```bash
   curl http://localhost:8000/auth/status
   ```

3. **Test Simple Query**:
   ```bash
   curl -X POST "http://localhost:8000/nlp" \
     -H "Content-Type: application/json" \
     -d '{"query": "Check my authentication status"}'
   ```

4. **Check Logs**:
   - Server logs are displayed in the terminal where you started the server
   - Application logs are written to `clio_nlp_agent.log`

## 🔄 Advanced Usage

### Batch Processing

```json
{
  "query": "Process these contacts: John (john@email.com), Jane (jane@email.com), Bob (bob@email.com) - create them all and then generate a summary"
}
```

### Custom Workflows

```json
{
  "query": "For client ID 123: create a new matter called 'Estate Planning', add it to the high-priority custom field, and log 1 hour of initial consultation time"
}
```

### Reporting and Analysis

```json
{
  "query": "Generate a summary report of all activities this month, grouped by matter, showing total hours and billing amounts"
}
```

### Integration with Other Tools

```json
{
  "query": "Export all contacts created this week to CSV format and save to the custom fields manager backup folder"
}
```

## 📈 Performance Tips

1. **Use Pagination**: For large datasets, use limits
2. **Batch Requests**: Combine multiple operations in one query
3. **Cache Results**: The system automatically handles API rate limiting
4. **Monitor Usage**: Check `/health` endpoint for system status

## 🔒 Security Notes

- Authentication tokens are automatically retrieved from secure database
- API keys are handled through environment variables
- All requests are logged for audit purposes
- Rate limiting prevents API abuse

## 🆘 Getting Help

1. **Built-in Help**:
   - Visit `http://localhost:8000/docs` for interactive API documentation
   - Use `http://localhost:8000/examples` for query examples

2. **System Information**:
   - Check `http://localhost:8000/health` for system status
   - Use `http://localhost:8000/tools` to see all available capabilities

3. **Logs**:
   - Server terminal shows real-time activity
   - `clio_nlp_agent.log` contains detailed execution logs

4. **Testing**:
   - Use `python simple_auth_test.py` to verify setup
   - Start with simple queries and gradually increase complexity

---

## 🎉 You're Ready!

The Clio NLP Agent transforms complex API operations into simple conversations. Start with basic queries and explore the full capabilities as you become more comfortable with the system.

**Happy querying!** 🚀
# Ed Agent System Guide

## Overview

Ed is a conversational AI agent focused on two core capabilities:

1. **Conversational Chat** - Natural dialogue with conversation memory
2. **Tool Calling** - Intelligent routing to external APIs (email, web search)

This agent uses a clean separation of responsibilities: the `/api/chat` endpoint handles conversations, while `/api/chat/tools` handles tool execution.

## Architecture

### Core Components

#### 1. Conversational Chat System
- **Endpoint**: `/api/chat`
- **Memory**: Conversation buffer with automatic summarization
- **Context**: Tracks conversation history across messages
- **LLM**: Direct Edd LLM for natural responses

#### 2. Tool Calling System
- **Endpoint**: `/api/chat/tools`
- **Tool Selection**: LLM-based reasoning to identify appropriate tool
- **State Management**: ToolState tracks workflow progress
- **External APIs**: Routes to email and search services

### Tool System Components

1. **ToolState** (`app/models/tools/tool_control_flow.py`)
   - State management for tool workflow
   - Tracks: user message, selected tool, parameters, API responses, status codes

2. **Tool Nodes** (`app/models/tools/tool_nodes.py`)
   - `select_tool`: Uses LLM JSON mode to identify which tool to use
   - `call_email_api`: Sends POST requests to email API
   - `call_search_api`: Sends POST requests to web search API
   - `format_response`: Creates user-friendly messages with status information

3. **Control Flow** (`app/models/tools/tool_control_flow.py`)
   - LangGraph StateGraph that routes between nodes
   - Entry → select_tool → (email_api | search_api | none) → format_response → END

## API Endpoints

### POST /api/chat

Natural conversational endpoint with memory and context awareness.

**Request Body:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Hello, how are you?"
    }
  ],
  "temperature": 0.7
}
```

**Response:**
```json
{
  "response": "Hello! I'm doing well, thank you for asking. How can I help you today?"
}
```

**Features:**
- Conversation memory (automatically summarizes after threshold)
- Context-aware responses (remembers previous messages)
- Natural dialogue flow

**Use Cases:**
- General conversation
- Questions about previous messages ("What did I say earlier?")
- Multi-turn dialogue
- Context-dependent queries

### POST /api/chat/tools

Send tool-enabled chat requests that can trigger email sending or web searches.

**Request Body:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Send an email to john@example.com about the project update"
    }
  ],
  "temperature": 0.7
}
```

**Response:**
```json
{
  "response": "✓ Email sent successfully!\n\nDetails: {...}"
}
```

## Usage Examples

### Email Tool

The LLM will automatically detect email requests and extract parameters:

**User Messages:**
- "Send an email to edwardt.s.baum@gmail.com about project updates"
- "Can you email john@example.com about the meeting tomorrow?"
- "Please send an email to test@test.com regarding the new features"

**Required Parameters:**
- `recipient`: Valid email address
- `assignment`: Description of what the email should be about

**API Call:**
```
POST http://192.168.0.180:8007/api/write_and_send_email
{
  "recipient": "edwardt.s.baum@gmail.com",
  "assignment": "project updates"
}
```

### Search Tool

The LLM will automatically detect search requests and extract the query:

**User Messages:**
- "Search for the DGX Spark specifications"
- "Can you look up information about artificial intelligence?"
- "Do a web search for Python best practices"

**Required Parameters:**
- `subject`: The search query

**API Call:**
```
POST http://192.168.0.131:8006/api/web-search
{
  "subject": "DGX Spark specifications"
}
```

## Status Code Handling

The tool agent checks HTTP status codes and provides appropriate feedback:

### Success (200)
```
✓ Email sent successfully!

Details: {
  "message": "Email sent",
  "recipient": "john@example.com"
}
```

### Failure (Non-200)
```
✗ Email sending failed (Status: 500)

Error: Connection timeout
```

### Connection Errors
```
✗ Email sending failed (Status: 0)

Error: Could not connect to email API: [Errno -3] Name resolution failed
```

## Testing

### Structure Verification

Run the structure verification test to ensure all components are properly configured:

```bash
pipenv run python test_tool_structure.py
```

This verifies:
- Graph compilation
- State structure
- API URL configuration
- Endpoint creation

### Integration Testing

To test with live APIs, ensure the following services are running:

1. **Ollama LLM Service**: `http://ollama:11436`
2. **Email API**: `http://192.168.0.180:8007`
3. **Search API**: `http://192.168.0.131:8006`

Then run:

```bash
pipenv run python test_tools.py
```

### Manual API Testing

You can test the endpoint directly using curl:

```bash
curl -X POST http://localhost:8000/api/chat/tools \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Search for Python best practices"
      }
    ]
  }'
```

## Configuration

### API Endpoints

To change the external API endpoints, edit `app/models/tools/tool_nodes.py`:

```python
EMAIL_API_URL = "http://192.168.0.180:8007/api/write_and_send_email"
SEARCH_API_URL = "http://192.168.0.131:8006/api/web-search"
```

### LLM Configuration

The tool selection uses the JSON mode LLM configured in `app/Edd/llm.py`:
- Model: `nemotron`
- Base URL: `http://ollama:11436`
- Temperature: 0 (for consistent tool selection)

## Error Handling

The system includes comprehensive error handling:

1. **LLM Errors**: Catches JSON parsing failures and returns "none" tool
2. **API Timeouts**: 30-second timeout with appropriate error messages
3. **Connection Errors**: Graceful handling of unreachable services
4. **Parameter Validation**: LLM extracts and validates required parameters

## Extending the System

### Adding a New Tool

1. **Add API endpoint constant** in `tool_nodes.py`:
```python
NEW_TOOL_API_URL = "http://example.com/api/new-tool"
```

2. **Create tool node** in `tool_nodes.py`:
```python
async def call_new_tool_api(self, state: Dict[str, Any]) -> Dict[str, Any]:
    tool_params = state.get("tool_params", {})
    # Extract parameters and call API
    # Return updated state with tool_response and status_code
```

3. **Update select_tool prompt** to include new tool in available tools list

4. **Add node to graph** in `tool_control_flow.py`:
```python
workflow.add_node("call_new_tool_api", tool_nodes.call_new_tool_api)
```

5. **Update routing** in `tool_control_flow.py`:
```python
def route_to_tool(state: Dict[str, Any]) -> str:
    tool_name = state.get("tool_name", "none")
    if tool_name == "new_tool":
        return "call_new_tool_api"
    # ... existing routing
```

6. **Add edge**:
```python
workflow.add_edge("call_new_tool_api", "format_response")
```

## Endpoint Comparison

| Feature | `/api/chat` (Conversation) | `/api/chat/tools` (Tools) |
|---------|----------------------------|---------------------------|
| **Purpose** | Natural conversation | External API tool calling |
| **Memory** | Persistent conversation buffer | Stateless (per request) |
| **Context** | Tracks conversation history | No memory between requests |
| **LLM Usage** | Full conversational generation | Tool selection only |
| **Use Case** | Chat, dialogue, Q&A | Execute specific actions |
| **When to Use** | Talk to the agent | Do something specific |

### Choosing the Right Endpoint

**Use `/api/chat` when:**
- Having a conversation
- Asking questions that need context
- Building on previous messages
- General interaction

**Use `/api/chat/tools` when:**
- Sending an email
- Performing a web search
- Executing a specific action
- Agent-to-agent communication

## Best Practices

1. **Be Explicit**: Use clear language like "send an email to..." or "search for..."
2. **Include Parameters**: Always include recipient email or search query in your request
3. **Check Status**: The response will indicate if the tool call succeeded (✓) or failed (✗)
4. **Error Messages**: Read error messages for troubleshooting connection or parameter issues

## Troubleshooting

### "Tool 'none' was selected but no response was generated"
- The LLM couldn't identify a tool to use
- Make your request more explicit (include "email" or "search")

### "Could not connect to [tool] API"
- The external API service is not running or not accessible
- Verify network connectivity and API URLs

### "Status: 0" errors
- Usually indicates connection failures or DNS resolution issues
- Check that API services are running and accessible

### LLM errors
- Verify Ollama service is running at `http://ollama:11436`
- Check that the `nemotron` model is available

## Agent Scope

This agent is specifically designed for:

### ✓ What This Agent Does

1. **Conversational Chat**
   - Natural language dialogue
   - Context-aware responses
   - Conversation memory management
   - Multi-turn conversations

2. **Tool Calling**
   - Email sending (via external API)
   - Web search (via external API)
   - Status verification and reporting

3. **Agent Communication**
   - Receive tool requests from other agents
   - Execute tools and return results
   - Stateless tool invocation

### ✗ What This Agent Does NOT Do

- **Document Retrieval**: No vectorstore or document search
- **Knowledge Base**: No embedded document storage
- **Web Scraping**: Relies on external search API
- **Email Composition**: Email content is generated by external service
- **Complex Workflows**: Focus is on simple, direct actions

### Architecture Decision

This agent follows a **separation of concerns** pattern:
- **Chat**: For conversation and interaction
- **Tools**: For specific action execution
- **External APIs**: For specialized capabilities (email, search)

This makes the agent lightweight, focused, and easy to maintain. Complex capabilities like document retrieval, knowledge management, or advanced workflows should be handled by separate specialized agents.


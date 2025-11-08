# Ed - AI Orchestrating Agent

Ed is an intelligent orchestrating agent that routes tasks to specialized agents through standardized APIs. It uses LLM-powered decision-making to analyze user requests and delegate them to the appropriate tools/agents.

## Overview

Ed serves as a central hub that:
- Analyzes natural language requests using LLM
- Routes tasks to specialized agents (Email, Search, Twitter)
- Handles both synchronous and asynchronous operations
- Manages conversation memory and context
- Provides standardized data formats for agent communication

## Architecture

```
User Request → Ed (LLM Analysis) → Tool Selection → External Agent API
                                                    ↓
                                    Async Processing (202 Accepted)
                                                    ↓
                              Agent delivers results independently
```

### Components

- **FastAPI Backend**: RESTful API for communication
- **LangGraph Workflow**: State machine for tool orchestration
- **LLM Integration**: Ollama-based intelligent decision making
- **Tool Nodes**: Connectors for external agent APIs
- **Memory System**: Conversation buffer and summarization

## Features

- 🤖 **Intelligent Tool Selection**: LLM analyzes requests and selects appropriate tools
- 🔄 **Async Fire-and-Forget**: Handles long-running tasks without blocking
- 💬 **Conversational Interface**: Natural language chat capability
- 🛠️ **Extensible Tool System**: Easy to add new agent integrations
- 📝 **Memory Management**: Maintains conversation context
- 🚀 **Production Ready**: Docker containerization and proper error handling

## Integrated Tools

1. **Email Agent**: Compose and send emails based on assignments
2. **Search Agent**: Web search with result delivery
3. **Twitter Agent**: Generate and post tweets on topics

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Ollama (for LLM functionality)

### Installation

1. Clone the repository:
```bash
git clone <repo-url>
cd Ed
```

2. Set up environment variables in `.env`:
```env
EMAIL_API_URL=http://your-email-agent:port/api/endpoint
SEARCH_API_URL=http://your-search-agent:port/api/endpoint
TWITTER_API_URL=http://your-twitter-agent:port/api/endpoint
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

3. Start with Docker:
```bash
docker-compose up --build
```

## API Endpoints

### Chat Endpoint
```http
POST /api/chat
Content-Type: application/json

{
  "messages": [
    {"role": "user", "content": "Hello, how are you?"}
  ]
}
```
For general conversation without tool usage.

### Tool-Enabled Chat
```http
POST /api/chat/tools
Content-Type: application/json

{
  "messages": [
    {"role": "user", "content": "Send an email to john@example.com about the quarterly report"}
  ]
}
```

Analyzes the request and routes to appropriate tools.

### Examples

**Email Request:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Send an email to sarah@company.com about the upcoming product launch"
    }
  ]
}
```

**Search Request:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Search for recent developments in quantum computing"
    }
  ]
}
```

**Twitter Request:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Post a tweet about our new AI features"
    }
  ]
}
```

## Agent API Specification

External agents should implement the following interface:

### Request Format
```json
{
  "subject": "topic or query",
  "recipient": "email@example.com",  // for email only
  "assignment": "task description"   // for email only
}
```

### Response Format

**Synchronous (200 OK):**
```json
{
  "result": "completed task details",
  "status": "success"
}
```

**Asynchronous (202 Accepted):**
```json
{
  "message": "Task accepted and processing",
  "status": "processing"
}
```

**Error (4xx/5xx):**
```json
{
  "error": "error description",
  "status": "failed"
}
```

## Project Structure

```
Ed/
├── app/
│   ├── endpoints/
│   │   ├── chat.py          # Chat endpoints
│   │   └── memory.py        # Memory management
│   ├── models/
│   │   └── tools/
│   │       ├── tool_nodes.py         # Tool implementations
│   │       └── tool_control_flow.py  # LangGraph workflow
│   ├── Edd/
│   │   └── llm.py           # LLM configuration
│   └── database/
│       └── models/          # Database models
├── docker-compose.yml
├── Pipfile
└── README.md
```

## Adding New Tools

To add a new agent integration:

1. **Add API URL** to `tool_nodes.py`:
```python
NEW_TOOL_API_URL = os.getenv("NEW_TOOL_API_URL")
```

2. **Update LLM Prompt** in `select_tool`:
```python
- newtool: Description (requires: parameters)
```

3. **Create Tool Node**:
```python
async def call_newtool_api(self, state: Dict[str, Any]) -> Dict[str, Any]:
    # Implementation
```

4. **Add Formatting** in `format_response`

5. **Update Control Flow** in `tool_control_flow.py`:
   - Add node to workflow
   - Add routing condition
   - Add edges

## Configuration

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `EMAIL_API_URL` | Email agent endpoint | Required |
| `SEARCH_API_URL` | Search agent endpoint | Required |
| `TWITTER_API_URL` | Twitter agent endpoint | Required |
| `OLLAMA_BASE_URL` | Ollama LLM service | `http://host.docker.internal:11434` |

## Development

### Local Development

```bash
# Install dependencies
pipenv install

# Run locally
pipenv run uvicorn app.main:app --reload
```

### Testing

Structural tests verify integration without requiring LLM:
```bash
pipenv run python test_tool_structure.py
```

## Technologies

- **FastAPI**: Web framework
- **LangGraph**: Workflow orchestration
- **Ollama**: Local LLM inference
- **httpx**: Async HTTP client
- **Docker**: Containerization

## Contributing

When adding new agent integrations:
1. Follow the async fire-and-forget pattern
2. Return 202 Accepted for long-running tasks
3. Include comprehensive logging
4. Handle all error cases (timeout, connection, API errors)

## Contact

edwardt@edwardtsbaum.com

# Search API Implementation Guide - Simple Fire-and-Forget Pattern

## Overview

This guide explains how to modify your search agent's API to support asynchronous (fire-and-forget) search requests. This simple pattern allows Ed to submit search requests and get immediate acknowledgment, while your search agent handles result delivery independently.

## Current vs New Flow

### Current (Synchronous - Has Timeout Issues)
```
Ed → POST /api/web-search → [waits 30+ seconds] → Results or Timeout ✗
```

### New (Asynchronous - No Timeout)
```
1. Ed → POST /api/web-search → Immediate 202 Accepted ✓
2. Search Agent processes in background
3. Search Agent delivers results to user independently (email/notification)
```

## Implementation Steps

### 1. Modify POST /api/web-search Endpoint

**Current behavior (problematic):**
```python
@router.post("/api/web-search")
async def web_search(request: SearchRequest):
    # Performs search synchronously (slow)
    results = await perform_search(request.subject)
    return {"results": results}  # Returns after search completes
```

**New behavior (fire-and-forget):**
```python
import uuid
from fastapi import BackgroundTasks

@router.post("/api/web-search", status_code=202)
async def web_search(request: SearchRequest, background_tasks: BackgroundTasks):
    """
    Accept search request and process asynchronously
    Returns immediately with acknowledgment
    """
    # Log the request
    logger.info(f"Search request received: {request.subject}")
    
    # Add search to background tasks
    background_tasks.add_task(process_search_async, request.subject)
    
    # Return immediately with 202 Accepted
    return {
        "status": "accepted",
        "message": f"Search for '{request.subject}' is being processed"
    }
```

### 2. Create Background Search Processor

```python
async def process_search_async(subject: str):
    """
    Process search in background
    """
    try:
        logger.info(f"Starting background search: {subject}")
        
        # Perform the actual search (can take as long as needed)
        results = await perform_search(subject)
        
        logger.info(f"Search completed: {subject}")
        
        # Deliver results to user (email, notification, etc.)
        await deliver_results_to_user(subject, results)
        
    except Exception as e:
        logger.error(f"Search failed for '{subject}': {e}")
        # Optionally notify user of failure
```

### 3. Result Delivery (Choose Your Method)

**Recommended: Email Notification** (simplest)
```python
async def deliver_results_to_user(subject: str, results: dict):
    """
    Email results directly to user
    """
    try:
        await send_email(
            to=user_email,  # Get from request context
            subject=f"Your Search Results: {subject}",
            body=format_results(results)
        )
        logger.info(f"Results emailed to user for: {subject}")
    except Exception as e:
        logger.error(f"Failed to email results: {e}")
```

## Complete Simple Example

Here's a minimal working implementation:

```python
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class SearchRequest(BaseModel):
    subject: str

@router.post("/api/web-search", status_code=202)
async def web_search(request: SearchRequest, background_tasks: BackgroundTasks):
    """Accept search and process in background"""
    logger.info(f"Search received: {request.subject}")
    
    # Process in background
    background_tasks.add_task(process_search_async, request.subject)
    
    # Return immediately
    return {
        "status": "accepted",
        "message": f"Search for '{request.subject}' is being processed"
    }

async def process_search_async(subject: str):
    """Do the actual search and deliver results"""
    try:
        logger.info(f"Starting search: {subject}")
        
        # Your actual search logic here (can take as long as needed)
        results = await perform_actual_search(subject)
        
        logger.info(f"Search completed: {subject}")
        
        # Deliver results (email, notification, etc.)
        await send_results_to_user(subject, results)
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        # Optionally notify user of failure

async def send_results_to_user(subject: str, results: dict):
    """Send results via email or notification"""
    # Your delivery method here
    pass
```

## Testing

### Test the Async Flow

```bash
# Submit search (should return immediately)
curl -X POST http://localhost:8006/api/web-search \
  -H "Content-Type: application/json" \
  -d '{"subject": "test query"}'

# Response (immediate):
{
  "status": "accepted",
  "message": "Search for 'test query' is being processed"
}

# That's it! Your search agent handles the rest in background
# Results are delivered directly to user via email/notification
```

## Ed's Response to User

After implementation, when a user asks Ed to search:

**User:** "Search for DGX Spark news"

**Ed (immediately):** 
```
✓ Search request accepted!

Search for 'DGX Spark news' is being processed

Results will be delivered when ready.
```

Then your search agent emails/notifies the user with results when ready.

## Migration Path

1. **Phase 1**: Implement async endpoint, keep sync as backup
2. **Phase 2**: Test async flow thoroughly
3. **Phase 3**: Deprecate synchronous endpoint
4. **Phase 4**: Add result delivery mechanism

## Notes

- **Simple**: No job tracking, no status endpoints needed
- **Fast**: Returns immediately (< 10 seconds)
- **Scalable**: Search can take as long as needed
- **Independent**: Your search agent handles everything
- **Rate limiting**: Consider rate limits on submission
- **Authentication**: Add auth tokens if needed between agents
- **Monitoring**: Log search completion times and success rates


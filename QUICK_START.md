# Quick Start - Simple Async Pattern

## What Changed in Ed

✅ Ed now accepts **202 Accepted** responses  
✅ 10-second timeout (down from 30)  
✅ Simple acknowledgment messages (no job IDs)  

## What Your Search API Needs to Do

### 1. Return 202 Immediately

```python
from fastapi import BackgroundTasks

@router.post("/api/web-search", status_code=202)
async def web_search(request: SearchRequest, background_tasks: BackgroundTasks):
    # Process in background
    background_tasks.add_task(do_search, request.subject)
    
    # Return immediately
    return {
        "status": "accepted",
        "message": f"Search for '{request.subject}' is being processed"
    }
```

### 2. Process in Background

```python
async def do_search(subject: str):
    # Do actual search (can take as long as needed)
    results = await perform_search(subject)
    
    # Email/notify user with results
    await send_results_to_user(subject, results)
```

### 3. Done!

That's it. No job tracking, no status endpoints, no complexity.

## User Experience

**User asks:** "Search for DGX Spark news"

**Ed responds immediately:**
```
✓ Search request accepted!

Search for 'DGX Spark news' is being processed

Results will be delivered when ready.
```

**Later:** Your search agent emails/notifies user with results.

## Test It

```bash
# Test your search API returns 202:
curl -X POST http://localhost:8006/api/web-search \
  -H "Content-Type: application/json" \
  -d '{"subject": "test"}'

# Should return immediately:
{
  "status": "accepted",
  "message": "Search for 'test' is being processed"
}
```

## Full Documentation

- `SEARCH_API_IMPLEMENTATION_GUIDE.md` - Complete implementation details
- `ED_ASYNC_CHANGES_SUMMARY.md` - What changed in Ed

## Benefits

✅ No timeouts  
✅ Immediate feedback  
✅ Simple implementation  
✅ Independent delivery  


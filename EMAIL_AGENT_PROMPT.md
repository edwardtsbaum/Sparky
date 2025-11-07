# Implement Async Email API - Quick Summary for LLM

## Problem
Email API currently synchronous. When LLM takes time to compose email content, it causes timeout errors when called by Ed agent.

## Solution
Implement **fire-and-forget pattern**: Return 202 Accepted immediately, compose/send email in background.

## Required Changes to Email API

### 1. Modify Endpoint to Return 202 Immediately

```python
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, EmailStr

class EmailRequest(BaseModel):
    recipient: EmailStr
    assignment: str  # Description of what email should be about

@router.post("/api/write_and_send_email", status_code=202)
async def write_and_send_email(
    request: EmailRequest,
    background_tasks: BackgroundTasks
):
    """Accept email request and process asynchronously"""
    
    # Add to background tasks
    background_tasks.add_task(
        process_email_async,
        request.recipient,
        request.assignment
    )
    
    # Return immediately (< 10 seconds)
    return {
        "status": "accepted",
        "message": "Email is being composed and sent"
    }
```

### 2. Create Background Processor

```python
async def process_email_async(recipient: str, assignment: str):
    """
    Compose and send email in background
    Can take as long as needed - no timeout concerns
    """
    try:
        # Step 1: Generate email content with LLM (can be slow)
        email_content = await llm.generate_email(
            recipient=recipient,
            assignment=assignment
        )
        
        # Step 2: Send the email
        await send_email_via_service(
            to=recipient,
            subject=email_content.subject,
            body=email_content.body
        )
        
        logger.info(f"Email sent successfully to: {recipient}")
        
    except Exception as e:
        logger.error(f"Email failed: {e}")
        # Optionally notify user of failure
```

## Expected Response Format

**Ed expects this JSON on 202 response:**
```json
{
  "status": "accepted",
  "message": "Email is being composed and sent"
}
```

## Key Points

- Return **202 status code** (not 200)
- Response must be **immediate** (< 10 seconds)
- **No job IDs** or tracking needed
- LLM composition can take as long as needed in background
- Email sending happens asynchronously
- Log success/failure (notification optional)

## User Flow

1. User asks Ed to send email
2. Ed calls your API → Gets 202 immediately
3. Ed tells user: "Email request accepted, being processed"
4. Your agent composes email with LLM (takes time)
5. Your agent sends email
6. (Optional) Log or notify completion

## Testing

```bash
curl -X POST http://192.168.0.180:8007/api/write_and_send_email \
  -H "Content-Type: application/json" \
  -d '{
    "recipient": "test@example.com",
    "assignment": "Write about AI developments"
  }'

# Should return immediately with 202
```

## Error Handling (Optional but Recommended)

```python
async def process_email_async(recipient: str, assignment: str):
    try:
        # Compose with retries if LLM fails
        email_content = await generate_with_retry(assignment)
        
        # Send with retries if email service fails
        await send_with_retry(recipient, email_content)
        
    except Exception as e:
        logger.error(f"Email completely failed: {e}")
        # Could send failure notification here
```

## Benefits

✅ No timeout errors  
✅ Immediate user feedback  
✅ LLM can compose quality emails without rushing  
✅ Can retry sending if email service fails  
✅ Better scalability  

---

**Implementation time: ~20 minutes**  
**Complexity: Low (FastAPI BackgroundTasks handles everything)**


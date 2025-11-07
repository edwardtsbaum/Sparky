# Email API Implementation Guide - Simple Fire-and-Forget Pattern

## Overview

Implement asynchronous email sending to prevent timeout errors when email composition (LLM-generated content) takes longer than expected.

## Current vs New Flow

### Current (Synchronous - May Timeout)
```
Ed → POST /api/write_and_send_email → [waits for LLM + send] → Result or Timeout
```

### New (Asynchronous - No Timeout)
```
1. Ed → POST /api/write_and_send_email → Immediate 202 Accepted ✓
2. Email Agent composes email in background (LLM generation)
3. Email Agent sends email
4. Email Agent notifies user of success/failure
```

## Required Changes

### 1. Modify POST /api/write_and_send_email Endpoint

**Current behavior (may timeout):**
```python
@router.post("/api/write_and_send_email")
async def write_and_send_email(request: EmailRequest):
    # Compose email with LLM (slow)
    email_content = await llm.generate_email(request.assignment)
    
    # Send email
    result = await send_email(request.recipient, email_content)
    
    return {"status": "success"}  # Returns after completion
```

**New behavior (fire-and-forget):**
```python
from fastapi import BackgroundTasks

@router.post("/api/write_and_send_email", status_code=202)
async def write_and_send_email(
    request: EmailRequest, 
    background_tasks: BackgroundTasks
):
    """Accept email request and process asynchronously"""
    
    # Log the request
    logger.info(f"Email request received for: {request.recipient}")
    logger.info(f"Assignment: {request.assignment}")
    
    # Add email composition/sending to background tasks
    background_tasks.add_task(
        process_email_async, 
        request.recipient, 
        request.assignment
    )
    
    # Return immediately with 202 Accepted
    return {
        "status": "accepted",
        "message": "Email is being composed and sent"
    }
```

### 2. Create Background Email Processor

```python
async def process_email_async(recipient: str, assignment: str):
    """
    Compose and send email in background
    Can take as long as needed - no timeout concerns
    """
    try:
        logger.info(f"Starting email composition for: {recipient}")
        
        # Step 1: Generate email content with LLM (can be slow)
        email_content = await llm.generate_email(
            recipient=recipient,
            assignment=assignment
        )
        
        logger.info(f"Email content generated for: {recipient}")
        
        # Step 2: Send the email
        result = await send_email(
            to=recipient,
            subject=email_content.subject,
            body=email_content.body
        )
        
        logger.info(f"Email sent successfully to: {recipient}")
        
        # Step 3: Notify user of success
        await notify_user_email_sent(recipient, result)
        
    except Exception as e:
        logger.error(f"Email failed for {recipient}: {e}")
        # Notify user of failure
        await notify_user_email_failed(recipient, str(e))
```

### 3. Result Notification

**Option A: Log Only (Simplest)**
```python
async def notify_user_email_sent(recipient: str, result: dict):
    """Just log success"""
    logger.info(f"Email successfully sent to {recipient}")
```

**Option B: Send Confirmation Email**
```python
async def notify_user_email_sent(recipient: str, result: dict):
    """Send confirmation to original requester"""
    await send_email(
        to=original_requester_email,  # Get from context
        subject=f"Email Sent Confirmation",
        body=f"Your email to {recipient} was sent successfully."
    )
```

**Option C: Push Notification**
```python
async def notify_user_email_sent(recipient: str, result: dict):
    """Push notification to user"""
    await push_notification(
        user_id=user_id,
        message=f"Email sent to {recipient}"
    )
```

## Complete Simple Example

```python
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, EmailStr
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class EmailRequest(BaseModel):
    recipient: EmailStr
    assignment: str

@router.post("/api/write_and_send_email", status_code=202)
async def write_and_send_email(
    request: EmailRequest,
    background_tasks: BackgroundTasks
):
    """Accept email request and process in background"""
    logger.info(f"Email request: {request.recipient}")
    
    # Process in background
    background_tasks.add_task(
        process_email_async,
        request.recipient,
        request.assignment
    )
    
    # Return immediately
    return {
        "status": "accepted",
        "message": "Email is being composed and sent"
    }

async def process_email_async(recipient: str, assignment: str):
    """Compose and send email (can take as long as needed)"""
    try:
        logger.info(f"Composing email for: {recipient}")
        
        # Generate email content with LLM
        email_content = await generate_email_with_llm(assignment)
        
        # Send email
        await send_email_via_service(recipient, email_content)
        
        logger.info(f"✓ Email sent to: {recipient}")
        
    except Exception as e:
        logger.error(f"✗ Email failed for {recipient}: {e}")

async def generate_email_with_llm(assignment: str):
    """Generate email content using LLM"""
    # Your LLM email generation logic here
    pass

async def send_email_via_service(recipient: str, content: dict):
    """Send email via your email service"""
    # Your email sending logic here
    pass
```

## Expected Response Format

**Ed expects this JSON on 202 response:**
```json
{
  "status": "accepted",
  "message": "Email is being composed and sent"
}
```

## Testing

```bash
# Test endpoint returns 202 immediately
curl -X POST http://192.168.0.180:8007/api/write_and_send_email \
  -H "Content-Type: application/json" \
  -d '{
    "recipient": "test@example.com",
    "assignment": "Write about AI developments"
  }'

# Should return immediately with 202:
{
  "status": "accepted",
  "message": "Email is being composed and sent"
}
```

## Ed's Response to User

After implementation, when a user asks Ed to send email:

**User:** "Send an email to john@example.com about project updates"

**Ed (immediately):**
```
✓ Email request accepted!

Your email is being processed. You'll be notified when it's sent.
```

Then your email agent:
1. Generates email content with LLM
2. Sends the email
3. Logs/notifies completion

## Key Points

- Return 202 status code (not 200)
- Response must be immediate (< 10 seconds)
- No job IDs or tracking needed
- LLM composition can take as long as needed
- Background task handles everything
- Notify user when complete (optional)

## Benefits

✅ No timeout errors  
✅ Immediate acknowledgment to user  
✅ LLM can take time to compose good email  
✅ Email sending retries can happen in background  
✅ Scales better (non-blocking)  

## Migration Path

1. **Phase 1**: Implement async endpoint (keep sync as backup)
2. **Phase 2**: Test with Ed agent
3. **Phase 3**: Monitor email composition times
4. **Phase 4**: Deprecate synchronous endpoint

## Error Handling

```python
async def process_email_async(recipient: str, assignment: str):
    try:
        # Compose email
        email_content = await generate_email_with_llm(assignment)
        
        # Send email with retries
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await send_email_via_service(recipient, email_content)
                logger.info(f"Email sent to {recipient}")
                return
            except Exception as send_error:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
                    
    except Exception as e:
        logger.error(f"Email completely failed for {recipient}: {e}")
        # Optionally: Send failure notification to user
        await notify_user_email_failed(recipient, str(e))
```

## Notes

- **Simple**: No job tracking needed
- **Fast**: Returns immediately (< 10 seconds)
- **Reliable**: Can retry sending in background
- **Independent**: Email agent handles everything
- **User-friendly**: Clear acknowledgment message


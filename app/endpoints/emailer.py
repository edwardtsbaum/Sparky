from fastapi import APIRouter, Body, HTTPException
from ..models.email.email_sender import Emailer
import logging
from datetime import datetime
import traceback
from ..database.schemas.chat import EmailRequest
from pydantic import EmailStr

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

 # Initialize emailer
emailer = Emailer()

@router.post("/api/send_email")
async def send_email(email_request: EmailRequest):
    """
    Send an email to the specified recipient
    
    Args:
        email_request: EmailRequest containing recipient, subject, and body
    
    Returns:
        dict: Status of email sending operation
    """
    try:
        logger.info(f"Attempting to send email to: {email_request.recipient}")
        
        
        # Send email
        success = emailer.send_email(
            recipient_email=email_request.recipient,
            subject=email_request.subject,
            body=email_request.body
        )
        
        if success:
            logger.info(f"Email sent successfully to {email_request.recipient}")
            return {
                "status": "success",
                "message": "Email sent successfully",
                "timestamp": datetime.now().isoformat(),
                "recipient": email_request.recipient
            }
        else:
            logger.error(f"Failed to send email to {email_request.recipient}")
            raise HTTPException(
                status_code=500,
                detail="Failed to send email"
            )
            
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error sending email: {str(e)}"
        )

# Optional: Add a test endpoint
@router.post("/api/test_email")
async def test_email(recipient: EmailStr = Body(..., embed=True)):
    """
    Send a test email to verify the email configuration
    
    Args:
        recipient: Email address to send test email to
    
    Returns:
        dict: Status of test email operation
    """
    try:
        logger.info(f"Sending test email to: {recipient}")
        
        # Initialize emailer
        emailer = Emailer()
        
        # Send test email
        success = emailer.test_email(recipient)
        
        if success:
            return {
                "status": "success",
                "message": "Test email sent successfully",
                "timestamp": datetime.now().isoformat(),
                "recipient": recipient
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to send test email"
            )
            
    except Exception as e:
        logger.error(f"Error sending test email: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error sending test email: {str(e)}"
        )

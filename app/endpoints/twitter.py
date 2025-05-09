from fastapi import APIRouter, Body, HTTPException
from ..models.twitter.twitter_client import twitter
import logging
import httpx
from datetime import datetime
import pytz
import traceback
import os

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



@router.get("/api/twitter/verify_credentials")
async def verify_twitter_credentials():
    """
    Endpoint to verify Twitter API credentials and connection status
    
    Returns:
        dict: Status of Twitter credentials and connection
    """
    try:
        logger.info("=== VERIFYING TWITTER CREDENTIALS ===")
        
        # Get all credentials (masked for logging)
        credentials = {
            "Client ID": bool(os.getenv("TWITTER_CLIENT_ID")),
            "Client Secret": bool(os.getenv("TWITTER_CLIENT_SECRET")),
            "Access Token": bool(os.getenv("TWITTER_ACCESS_TOKEN")),
            "Access Secret": bool(os.getenv("TWITTER_ACCESS_SECRET"))
        }
        
        logger.info("Checking credentials presence:")
        for key, present in credentials.items():
            logger.info(f"{key}: {'Present' if present else 'Missing'}")
            
        # Verify credentials
        is_valid, message = await twitter.verify_credentials()
        
        # Get client status
        client_initialized = twitter.client is not None
        
        response = {
            "status": "success" if is_valid else "error",
            "credentials_status": {
                "client_id": "Present" if credentials["Client ID"] else "Missing",
                "client_secret": "Present" if credentials["Client Secret"] else "Missing",
                "access_token": "Present" if credentials["Access Token"] else "Missing",
                "access_secret": "Present" if credentials["Access Secret"] else "Missing"
            },
            "client_initialized": client_initialized,
            "verification_message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        if not is_valid:
            logger.warning(f"Twitter credentials verification failed: {message}")
            return response
            
        logger.info("Twitter credentials verified successfully")
        return response
        
    except Exception as e:
        logger.error(f"Error verifying Twitter credentials: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Failed to verify Twitter credentials: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
        )

# Optional: Add a test tweet endpoint
@router.post("/api/twitter/test_tweet")
async def test_twitter_post(message: str = "🤖 Test tweet from the other side! #Test"):
    """
    Endpoint to test posting a tweet
    
    Args:
        message (str): Optional test message to tweet
        
    Returns:
        dict: Status of test tweet
    """
    try:
        logger.info("=== TESTING TWITTER POST ===")
        
        # First verify credentials
        is_valid, verify_message = await twitter.verify_credentials()
        if not is_valid:
            raise HTTPException(
                status_code=401,
                detail=f"Twitter credentials invalid: {verify_message}"
            )
            
        # Try to post tweet
        tweet_id = await twitter.post_tweet(message)
        
        if tweet_id:
            return {
                "status": "success",
                "message": "Test tweet posted successfully",
                "tweet_id": tweet_id,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to post test tweet"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error posting test tweet: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to post test tweet: {str(e)}"
        )
import tweepy
import logging
import os
from typing import Optional, Dict, Tuple
from datetime import datetime
import urllib3
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2.rfc6749.errors import InsecureTransportError

logger = logging.getLogger(__name__)

class TwitterClient:
    def __init__(self):
        self.client = None
        self.token_expiry = None
        self.refresh_token = None
        
    async def verify_credentials(self) -> Tuple[bool, str]:
        """
        Verify Twitter API credentials and connection
        
        Returns:
            Tuple[bool, str]: (is_valid, message)
        """
        try:
            # Check if we have all required credentials
            required_credentials = {
                "Client ID": os.getenv("TWITTER_CLIENT_ID"),
                "Client Secret": os.getenv("TWITTER_CLIENT_SECRET"),
                "Access Token": os.getenv("TWITTER_ACCESS_TOKEN"),
                "Access Secret": os.getenv("TWITTER_ACCESS_SECRET")
            }
            
            # Check for missing credentials
            missing_credentials = [
                key for key, value in required_credentials.items() 
                if not value
            ]
            
            if missing_credentials:
                return False, f"Missing credentials: {', '.join(missing_credentials)}"
            
            # Initialize client with OAuth 1.0a for development
            try:
                self.client = tweepy.Client(
                    consumer_key=required_credentials["Client ID"],
                    consumer_secret=required_credentials["Client Secret"],
                    access_token=required_credentials["Access Token"],
                    access_token_secret=required_credentials["Access Secret"]
                )
                
                # Test the connection
                me = self.client.get_me()
                if not me or not me.data:
                    return False, "Could not verify account access"
                    
                logger.info(f"Successfully verified Twitter credentials for user: {me.data.username}")
                return True, f"Credentials verified for @{me.data.username}"
                
            except tweepy.errors.Unauthorized as e:
                logger.error(f"Twitter authentication failed: {str(e)}")
                return False, f"Authentication failed: {str(e)}"
                
        except InsecureTransportError:
            logger.warning("HTTPS required for OAuth 2.0, falling back to OAuth 1.0a")
            try:
                # Fall back to OAuth 1.0a
                self.client = tweepy.Client(
                    consumer_key=required_credentials["Client ID"],
                    consumer_secret=required_credentials["Client Secret"],
                    access_token=required_credentials["Access Token"],
                    access_token_secret=required_credentials["Access Secret"]
                )
                
                me = self.client.get_me()
                if not me or not me.data:
                    return False, "Could not verify account access"
                    
                logger.info(f"Successfully verified Twitter credentials using OAuth 1.0a for user: {me.data.username}")
                return True, f"Credentials verified for @{me.data.username} (OAuth 1.0a)"
                
            except Exception as e:
                logger.error(f"OAuth 1.0a fallback failed: {str(e)}")
                return False, f"Authentication failed with both OAuth 2.0 and 1.0a: {str(e)}"
                
        except Exception as e:
            logger.error(f"Unexpected error during verification: {str(e)}")
            return False, f"Unexpected error: {str(e)}"
    
    async def post_tweet(self, content: str) -> Optional[str]:
        """Post a tweet using OAuth 1.0a"""
        try:
            # Verify credentials before posting
            is_valid, message = await self.verify_credentials()
            if not is_valid:
                logger.error(f"Twitter credentials invalid: {message}")
                return None
                
            # Create the tweet
            response = self.client.create_tweet(text=content)
            tweet_id = response.data['id']
            
            logger.info(f"Successfully posted tweet: {tweet_id}")
            return tweet_id
            
        except tweepy.errors.Unauthorized as e:
            logger.error(f"Twitter authentication failed while posting: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Failed to post tweet: {str(e)}")
            return None

# Create singleton instance
twitter = TwitterClient() 
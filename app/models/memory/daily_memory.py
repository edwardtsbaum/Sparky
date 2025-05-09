from typing import Dict, Optional, List
from datetime import datetime, time
import logging
from app.database.models.database import conversation_state, daily_summaries
from ...Edd.llm import Edd

logger = logging.getLogger(__name__)

async def create_daily_summary() -> None:
    """Create a summary of the day's conversations and store it"""
    try:
        # Get the last conversation state
        last_state = await conversation_state.find_one(
            sort=[('timestamp', -1)]
        )
        
        if not last_state:
            logger.info("No conversation state found for daily summary")
            return
        
        # Format the conversation data for summarization
        messages = last_state.get('messages', [])
        current_summary = last_state.get('summary', "")
        
        formatted_data = f"""
        Previous Summary:
        {current_summary}
        
        Today's Conversations:
        {format_messages(messages) if messages else "No new messages today."}
        """
        
        # Create daily summary prompt
        prompt = f"""
        Please create a comprehensive daily summary of all conversations and interactions.
        
        Focus on:
        1. Key information learned about the user
        2. Important topics discussed
        3. Significant decisions or plans made
        4. Personal details shared (preferences, likes, dislikes)
        5. Future-relevant information
        6. Emotional moments or significant interactions
        
        Data to Summarize:
        {formatted_data}
        
        Create a detailed yet concise summary that captures the essence of today's interactions,
        particularly highlighting information that might be valuable for future conversations.
        Format the summary with clear sections and bullet points where appropriate.
        """
        
        # Generate summary using Edd
        response = await Edd.process_message(
            message=prompt,
            task_mode=True
        )
        
        # Prepare daily summary document
        today = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        
        daily_summary = {
            'summary': str(response),
            'date': today,
            'source_state_id': last_state['_id'],
            'created_at': datetime.utcnow()
        }
        
        # Check if we already have a summary for today
        existing_summary = await daily_summaries.find_one({
            'date': today
        })
        
        if existing_summary:
            # Update existing summary
            await daily_summaries.update_one(
                {'_id': existing_summary['_id']},
                {'$set': daily_summary}
            )
            logger.info(f"Updated daily summary for {today}")
        else:
            # Insert new summary
            await daily_summaries.insert_one(daily_summary)
            logger.info(f"Created new daily summary for {today}")
            
    except Exception as e:
        logger.error(f"Error creating daily summary: {str(e)}")
        raise

def format_messages(messages: List[Dict]) -> str:
    """Format messages for summarization"""
    return "\n".join([
        f"{msg['role']}: {msg['content']}"
        for msg in messages
    ])
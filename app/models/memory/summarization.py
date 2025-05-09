from typing import List, Dict
import logging
from ...Edd.llm import Edd

logger = logging.getLogger(__name__)

async def create_conversation_summary(messages: List[Dict], previous_summary: str = "") -> str:
    """
    Create a summary of the conversation
    """
    try:
        # Format conversation for summarization
        formatted_conversation = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in messages  # Uses messages from get_messages_for_summary()
        ])
        
        # Create prompt with context
        context = f"Previous Summary:\n{previous_summary}\n\n" if previous_summary else ""
        prompt = f"""
        {context}
        Recent Conversation:
        {formatted_conversation}
        
        Please provide a concise summary of this conversation, incorporating context from any previous summary if present.
        Focus on key points, decisions, and important information discussed.
        """
        
        # Get summary from LLM using correct invoke format
        response = await Edd.llm.ainvoke(input=[
            {
                "role": "system",
                "content": "You are a helpful AI assistant tasked with summarizing conversations."
            },
            {
                "role": "user",
                "content": prompt
            }
        ])
        
        summary = response.content if hasattr(response, 'content') else str(response)
        logger.info("Created new conversation summary")
        return summary
        
    except Exception as e:
        logger.error(f"Error creating summary: {str(e)}")
        return "Error creating summary"
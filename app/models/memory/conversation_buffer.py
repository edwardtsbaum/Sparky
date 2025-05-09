from typing import List, Dict, Optional
import logging
from datetime import datetime
from app.database.models.database import conversation_state  # Your existing MongoDB connection

logger = logging.getLogger(__name__)

class ConversationBuffer:
    def __init__(self):
        self.messages: List[Dict] = []
        self.summary: str = ""
        self.message_count: int = 0
        self.threshold: int = 15
        
    async def initialize(self):
        """Load the most recent state from MongoDB"""
        try:
            # Get most recent state
            state = await conversation_state.find_one(
                sort=[('timestamp', -1)]  # Get most recent
            )
            
            if state:
                self.messages = state.get('messages', [])
                self.summary = state.get('summary', "")
                self.message_count = state.get('message_count', 0)
                logger.info(f"Loaded conversation state: {self.message_count} messages")
            else:
                logger.info("No previous state found, starting fresh")
                
        except Exception as e:
            logger.error(f"Error loading conversation state: {str(e)}")
            
    async def save_state(self):
        """Save current state to MongoDB"""
        try:
            state = {
                'messages': self.messages,
                'summary': self.summary,
                'message_count': self.message_count,
                'timestamp': datetime.utcnow()
            }
            
            await conversation_state.insert_one(state)
            logger.info(f"Saved conversation state: {self.message_count} messages")
            
        except Exception as e:
            logger.error(f"Error saving conversation state: {str(e)}")
            
    async def add_message(self, role: str, content: str) -> bool:
        """Add message and persist state"""
        threshold_reached = False
        try:
            self.messages.append({
                "role": role,
                "content": content,
                "message_number": self.message_count + 1,
                "timestamp": datetime.utcnow()
            })
            
            self.message_count += 1
            logger.info(f"Added message {self.message_count} to buffer")
            
            # Save state after adding message
            await self.save_state()
            
            threshold_reached = self.message_count >= self.threshold
            
        except Exception as e:
            logger.error(f"Error adding message to buffer: {str(e)}")
            
        return threshold_reached
            
    async def clear_buffer(self) -> None:
        """Clear buffer and persist clean state"""
        try:
            # Clear local buffer
            self.messages = []
            self.message_count = 0
            
            # Save final state with empty messages but preserved summary
            await self.save_state()
            
            # Clean up old message states from MongoDB
            # Keep only the latest state (which has empty messages but current summary)
            all_states = await conversation_state.find().sort('timestamp', -1).to_list(length=None)
            if len(all_states) > 1:  # If we have more than our new empty state
                # Get all IDs except the most recent
                old_state_ids = [state['_id'] for state in all_states[1:]]
                # Delete old states
                await conversation_state.delete_many({'_id': {'$in': old_state_ids}})
                logger.info(f"Cleaned up {len(old_state_ids)} old states from MongoDB")
            
            logger.info("Cleared conversation buffer and cleaned MongoDB states")
            
        except Exception as e:
            logger.error(f"Error clearing buffer: {str(e)}")
        
    async def update_summary(self, new_summary: str) -> None:
        """Update summary and persist state"""
        if self.summary:
            self.summary = f"{self.summary}\n\nUpdated Summary: {new_summary}"
        else:
            self.summary = new_summary
            
        await self.save_state()
        logger.info("Updated conversation summary")

    def get_messages_for_summary(self) -> List[Dict]:
        """Get all messages in buffer for summarization"""
        return self.messages.copy()  # Return a copy to prevent modifications
        
    def get_context(self) -> str:
        """Get current context (summary) for RAG"""
        return self.summary if self.summary else ""

# Global buffer instance
conversation_buffer = ConversationBuffer()
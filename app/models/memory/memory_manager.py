from typing import Dict, Optional, List
from datetime import datetime, time, timedelta
import logging
from app.database.models.database import conversation_state, daily_summaries, weekly_summaries, monthly_summaries
from ...Edd.llm import Edd

logger = logging.getLogger(__name__)

class MemoryManager:
    def __init__(self):
        self.conversation_state = conversation_state
        self.daily_summaries = daily_summaries
        self.weekly_summaries = weekly_summaries
        self.monthly_summaries = monthly_summaries
    
    async def create_daily_summary(self) -> None:
        """Create a summary of the day's conversations and store it"""
        try:
            # Get the last conversation state
            last_state = await self.conversation_state.find_one(
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
            {self._format_messages(messages) if messages else "No new messages today."}
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
            existing_summary = await self.daily_summaries.find_one({
                'date': today
            })
            
            if existing_summary:
                # Update existing summary
                await self.daily_summaries.update_one(
                    {'_id': existing_summary['_id']},
                    {'$set': daily_summary}
                )
                logger.info(f"Updated daily summary for {today}")
            else:
                # Insert new summary
                await self.daily_summaries.insert_one(daily_summary)
                logger.info(f"Created new daily summary for {today}")
                
        except Exception as e:
            logger.error(f"Error creating daily summary: {str(e)}")
            raise

    def _format_messages(self, messages: List[Dict]) -> str:
        """Format messages for summarization"""
        return "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in messages
        ])
    
    async def create_weekly_summary(self) -> None:
        """Create a summary of the week's daily summaries and store it"""
        try:
            # Get the start of the current week (Monday)
            today = datetime.now()
            start_of_week = today - timedelta(days=today.weekday())
            start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Get all daily summaries from this week
            daily_summaries_cursor = self.daily_summaries.find({
                'date': {
                    '$gte': start_of_week,
                    '$lt': today
                }
            }).sort('date', 1)
            
            daily_summaries_list = await daily_summaries_cursor.to_list(length=7)
            
            if not daily_summaries_list:
                logger.info("No daily summaries found for weekly summary")
                return
            
            # Format the daily summaries for the weekly summary
            formatted_data = "\n\n".join([
                f"Summary for {summary['date'].strftime('%A, %B %d, %Y')}:\n{summary['summary']}"
                for summary in daily_summaries_list
            ])
            
            # Create weekly summary prompt
            prompt = f"""
            Please create a comprehensive weekly summary based on the daily summaries provided.
            
            Focus on:
            1. Major themes and patterns throughout the week
            2. Key developments in ongoing discussions
            3. Important decisions or milestones reached
            4. Recurring topics or concerns
            5. Notable changes in user behavior or preferences
            6. Action items or follow-ups needed
            
            Daily Summaries to Analyze:
            {formatted_data}
            
            Create a concise yet thorough weekly summary that highlights the most important developments
            and patterns from the week. Organize the information in a clear structure with main points
            and sub-points where appropriate.
            """
            
            # Generate summary using Edd
            response = await Edd.process_message(
                message=prompt,
                task_mode=True
            )
            
            # Prepare weekly summary document
            weekly_summary = {
                'summary': str(response),
                'start_date': start_of_week,
                'end_date': today,
                'daily_summary_ids': [str(summary['_id']) for summary in daily_summaries_list],
                'created_at': datetime.utcnow()
            }
            
            # Check if we already have a summary for this week
            existing_summary = await self.weekly_summaries.find_one({
                'start_date': start_of_week
            })
            
            if existing_summary:
                # Update existing summary
                await self.weekly_summaries.update_one(
                    {'_id': existing_summary['_id']},
                    {'$set': weekly_summary}
                )
                logger.info(f"Updated weekly summary for week starting {start_of_week}")
            else:
                # Insert new summary
                await self.weekly_summaries.insert_one(weekly_summary)
                logger.info(f"Created new weekly summary for week starting {start_of_week}")
                
        except Exception as e:
            logger.error(f"Error creating weekly summary: {str(e)}")
            raise
    
    async def create_monthly_summary(self) -> None:
        """Create a summary of the month's weekly summaries and store it"""
        try:
            # Get the start of the current month
            today = datetime.now()
            start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Get all weekly summaries from this month
            weekly_summaries_cursor = self.weekly_summaries.find({
                'start_date': {
                    '$gte': start_of_month,
                    '$lt': today
                }
            }).sort('start_date', 1)
            
            weekly_summaries_list = await weekly_summaries_cursor.to_list(length=None)
            
            if not weekly_summaries_list:
                logger.info("No weekly summaries found for monthly summary")
                return
            
            # Format the weekly summaries for the monthly summary
            formatted_data = "\n\n".join([
                f"Summary for week of {summary['start_date'].strftime('%B %d, %Y')}:\n{summary['summary']}"
                for summary in weekly_summaries_list
            ])
            
            # Create monthly summary prompt
            prompt = f"""
            Please create a comprehensive monthly summary based on the weekly summaries provided.
            
            Focus on:
            1. Major trends and developments throughout the month
            2. Long-term patterns in user behavior and preferences
            3. Significant milestones or achievements
            4. Evolution of key topics and discussions
            5. Important insights about the user's goals and needs
            6. Areas requiring attention or follow-up in the coming month
            
            Weekly Summaries to Analyze:
            {formatted_data}
            
            Create a strategic monthly overview that captures the most significant developments
            and insights from the past month. Structure the information with clear main themes
            and supporting details, highlighting any month-over-month changes or patterns.
            """
            
            # Generate summary using Edd
            response = await Edd.process_message(
                message=prompt,
                task_mode=True
            )
            
            # Prepare monthly summary document
            monthly_summary = {
                'summary': str(response),
                'start_date': start_of_month,
                'end_date': today,
                'weekly_summary_ids': [str(summary['_id']) for summary in weekly_summaries_list],
                'created_at': datetime.utcnow()
            }
            
            # Check if we already have a summary for this month
            existing_summary = await self.monthly_summaries.find_one({
                'start_date': start_of_month
            })
            
            if existing_summary:
                # Update existing summary
                await self.monthly_summaries.update_one(
                    {'_id': existing_summary['_id']},
                    {'$set': monthly_summary}
                )
                logger.info(f"Updated monthly summary for month starting {start_of_month}")
            else:
                # Insert new summary
                await self.monthly_summaries.insert_one(monthly_summary)
                logger.info(f"Created new monthly summary for month starting {start_of_month}")
                
        except Exception as e:
            logger.error(f"Error creating monthly summary: {str(e)}")
            raise
    
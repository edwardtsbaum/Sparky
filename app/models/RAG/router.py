### Router
import json
from langchain_core.messages import HumanMessage, SystemMessage
from ...Edd.llm import Edd
import logging

logger = logging.getLogger(__name__)

# Global router instructions
ROUTER_INSTRUCTIONS = """You are an expert at routing a user question to a vectorstore or web search.

The vectorstore contains documents related to Edwardt Baum, blockchain, and smart contracts.

Use the vectorstore for questions on these topics. For all else, and especially for current events, use web-search.

Your response MUST be valid JSON with this exact format:
{
    "datasource": "websearch" or "vectorstore",
    "explanation": "brief explanation of your choice"
}"""

ROUTER_INSTRUCTIONS_DAILY_AI_NEWS = """You are an expert at analyzing AI-related news and determining if it's relevant to specific AI topics.

Evaluate if the news or query is related to any of these AI categories:
1. AI Agents and Multi-Agent Systems
2. New Programming Paradigms for AI
3. New AI Libraries or Frameworks
4. New Open Source AI Models
5. Advances in AI Architecture or Training Methods

Return JSON with two keys:
- "is_relevant": "yes" if related to above categories, "no" if not
- "category": array of matched categories (empty if not relevant)

Example response:
{
    "is_relevant": "yes",
    "category": ["AI Agents", "New Libraries"]
}
"""

class ReasoningRouter:
    def __init__(self):
        self.llm = Edd.llm_json_mode
        
    async def route_query(self, question: str) -> dict:
        """
        Route a question to either websearch, vectorstore, or direct generation
        
        Args:
            question (str): The user's question
            
        Returns:
            dict: Contains routing decision and explanation
        """
        try:
            result = self.llm.invoke(
                [
                    SystemMessage(content=ROUTER_INSTRUCTIONS),
                    HumanMessage(content=question)
                ]
            )
            
            # Parse the JSON response
            try:
                response = json.loads(result.content)
                datasource = response.get("datasource", "").lower()
                
                # For agent-provided content, skip search and go straight to generation
                if "original_content" in response:
                    return {
                        "datasource": "generate",
                        "explanation": "Processing pre-provided content from agent"
                    }
                    
                # Validate the datasource value
                if datasource not in ["websearch", "vectorstore"]:
                    logger.warning(f"Invalid datasource '{datasource}', defaulting to websearch")
                    datasource = "websearch"
                    
                explanation = response.get("explanation", "No explanation provided")
                logger.info(f"Routed question '{question[:100]}...' to {datasource}")
                logger.info(f"Routing explanation: {explanation}")
                
                return {
                    "datasource": datasource,
                    "explanation": explanation
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse router response: {str(e)}")
                logger.error(f"Raw response: {result.content}")
                # Default to websearch for current events
                return {
                    "datasource": "websearch",
                    "explanation": "Defaulting to websearch due to parsing error"
                }
                
        except Exception as e:
            logger.error(f"Error routing question: {str(e)}")
            # Default to websearch if routing fails
            return {
                "datasource": "websearch",
                "explanation": f"Defaulting to websearch due to error: {str(e)}"
            }
            
    async def route_ai_news_query(self, question: str) -> dict:
        """
        Determine if a news item or query is relevant to specific AI topics
        
        Args:
            question (str): The news item or query to evaluate
            
        Returns:
            dict: Contains relevance and categories
        """
        try:
            result = self.llm.invoke(
                [SystemMessage(content=ROUTER_INSTRUCTIONS_DAILY_AI_NEWS)]
                + [HumanMessage(content=question)]
            )
            
            try:
                analysis = json.loads(result.content)
                logger.info(f"Analyzed AI news: '{question[:100]}...' - Relevant: {analysis.get('is_relevant')}, Categories: {analysis.get('category', [])}")
                return analysis
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI news analysis: {str(e)}")
                logger.error(f"Raw response: {result.content}")
                return {
                    "is_relevant": "no",
                    "category": []
                }
                
        except Exception as e:
            logger.error(f"Error analyzing AI news: {str(e)}")
            # Default to not relevant if analysis fails
            return {
                "is_relevant": "no",
                "category": []
            }

# Create singleton instance
router = ReasoningRouter()

# Example usage:
"""
async def test_router():
    questions = [
        "Who is favored to win the NFC Championship game in the 2024 season?",
        "What are the types of agent memory?",
        "How are you feeling today?",
    ]
    
    for question in questions:
        if await is_personality_query(question):
            print(f"'{question}' -> personality query")
        else:
            route = await route_query(question)
            print(f"'{question}' -> {route}")
"""
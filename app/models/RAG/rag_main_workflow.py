from .retrieval_grader import retrieve as graded_retrieve
from ...Edd.llm import Edd
from .generate import format_docs, generate_answer
from .router import router
from ..web.websearch import web_search as web_search_function
from .hallucination_grader import grade_hallucination
from .answer_grader import grade_answer
from ..twitter.twitter_client import twitter
import json
import logging
import traceback
from typing import Dict
from langchain.schema import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

class ThoughtProcessNodes:
    def __init__(self):
        self.llm = Edd.llm
        self.technical_keywords = ["faiss", "vector", "index", "search", "similarity", "embedding"]
    
    async def vectorstore_retrieval(self, state: Dict) -> Dict:
        """Vectorstore retrieval node"""
        logger.info("---VECTORSTORE RETRIEVAL---")
        try:
            result = await graded_retrieve(state)
            return {**state, **result}
        except Exception as e:
            logger.error(f"Vectorstore retrieval error: {str(e)}")
            return state

    async def generate(self, state: Dict) -> Dict:
        """
        Generate answer using RAG on retrieved documents

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, generation, that contains LLM generation
        """
        logger.info("=== GENERATE START ===")
        try:
            generation = await generate_answer(state)
            result = {"generation": generation}
            logger.info(f"Generation result type: {type(result)}")
            logger.info(f"Generation content type: {type(generation)}")
            return result
        except Exception as e:
            logger.error(f"Generation error: {str(e)}")
            raise

    async def grade_documents(self, state: Dict) -> Dict:
        """Grade the relevance of retrieved documents"""
        logger.info("---GRADE DOCUMENTS---")
        
        if not state.get("documents"):
            logger.info("No documents to grade")
            return state
            
        documents = state["documents"]
        relevant_docs = []
        
        for doc in documents:
            # Handle both Document objects and dictionaries
            content = doc.get('content', '') if isinstance(doc, dict) else getattr(doc, 'page_content', '')
            
            # Check for technical keywords in the question
            question_lower = state["question"].lower()
            
            # If question contains technical keywords and document contains matching content
            if any(keyword in question_lower for keyword in self.technical_keywords):
                doc_lower = content.lower()
                if any(keyword in doc_lower for keyword in self.technical_keywords):
                    logger.info("Document contains relevant technical content")
                    relevant_docs.append(doc)
                    continue
            
            # For non-technical questions or if no keyword match, use LLM grading
            messages = [
                SystemMessage(content="You are an expert at determining if a document is relevant to a question."),
                HumanMessage(content=f"""Given the question: "{state['question']}"
                
                Is this document relevant? Answer yes or no.
                Document content:
                {content[:1000]}
                """)
            ]
            logger.info("---GRADE DOCUMENTS AI INVOKED---")
            response = await self.llm.ainvoke(messages)
            grade = response.content.lower().strip()
            logger.info(f"Document grade: {grade}")
            
            if "yes" in grade:
                relevant_docs.append(doc)
        
        if relevant_docs:
            logger.info(f"Found {len(relevant_docs)} relevant documents")
            state["documents"] = relevant_docs
            state["context"] = "\n\n".join(
                doc.get('content', '') if isinstance(doc, dict) else doc.page_content 
                for doc in relevant_docs
            )
            logger.info("---GRADE: DOCUMENTS RELEVANT---")
        else:
            logger.info("Grading complete. Found 0 relevant documents")
            logger.info("---GRADE: DOCUMENT NOT RELEVANT---")
            
        return state

    async def web_search(self, state: Dict) -> Dict:
        """Web search based on the question using our custom implementation"""
        logger.info("---WEB SEARCH---")
        try:
            result_state = await web_search_function(state)
            logger.info(f"Retrieved {len(result_state.get('documents', []))} documents from web search")
            return {
                "documents": result_state.get("documents", []),
                "web_search": "Yes"
            }
        except Exception as e:
            logger.error(f"Web search error: {str(e)}")
            logger.error(f"State at error: {state}")
            return {
                "documents": [],
                "web_search": "Yes"
            }

    async def route_question(self, state: Dict) -> Dict:
        """Route the question to the appropriate node"""
        logger.info("=== ROUTE QUESTION START ===")
        try:
            # If content is from an agent, skip routing and proceed to processing
            if state.get("from_agent"):
                logger.info("Content from agent, proceeding directly to processing")
                return {**state, "web_search": "No"}
            
            question = state["question"]
            result = await router.route_query(question)
            
            return {
                **state,
                "web_search": "Yes" if result == "websearch" else "No"
            }
            
        except Exception as e:
            logger.error(f"Routing error: {str(e)}")
            return {**state, "web_search": "No"}

    async def grade_generation_v_documents_and_question(self, state: Dict) -> Dict:
        """Grade the generation against documents and question"""
        logger.info("---GRADE GENERATION---")
        try:
            generation_dict = state.get("generation", {})
            logger.info(f"Generation dict: {generation_dict}")
            
            question = state["question"]
            loop_step = state.get("loop_step", 1)
            logger.info(f"Question: {question}")
            logger.info(f"Loop step: {loop_step}")
            
            generation_content = generation_dict.get("generation", "") if isinstance(generation_dict, dict) else str(generation_dict)
            logger.info(f"Grading generation content: {generation_content}")
            
            documents = state.get("documents", [])
            context = format_docs(documents)
            logger.info(f"Formatted documents for grading")
            
            logger.info("Checking for hallucination...")
            grade = await grade_hallucination(context, generation_content)
            logger.info(f"Hallucination check result: {grade}")
            
            if grade["binary_score"] == "no":
                logger.info("---DECISION: GENERATION IS NOT GROUNDED IN DOCUMENTS---")
                if loop_step >= state["max_retries"]:
                    return {**state, "result": "max retries"}
                return {**state, "result": "not useful"}
            else:
                logger.info("---DECISION: GENERATION IS GROUNDED IN DOCUMENTS---")
                logger.info(f"Explanation: {grade['explanation']}")
                return {**state, "result": "useful"}
                
        except Exception as e:
            logger.error(f"Generation grading error: {str(e)}")
            logger.error(traceback.format_exc())
            return {**state, "result": "not useful"}

    async def grade_generated_answer(self, state: Dict) -> Dict:
        """Grade the generated answer using the answer grader"""
        logger.info("=== GRADE ANSWER START ===")
        try:
            question = state.get("question", "")
            generation = state.get("generation", "")
            
            grade = await grade_answer(
                question=question,
                generation=generation
            )
            
            logger.info(f"Grade result: {grade}")
            
            return {
                **state,
                "answer_grade": grade
            }
            
        except Exception as e:
            logger.error(f"Error in grade_generated_answer: {str(e)}")
            return {
                **state,
                "answer_grade": {
                    "binary_score": "no",
                    "explanation": f"Error during grading: {str(e)}"
                }
            }
    
    async def analyze_ai_news(self, state: Dict) -> Dict:
        """
        Analyze if the retrieved news is relevant to our AI categories
        and preserve both the analysis and content
        
        Args:
            state (Dict): The current workflow state
            
        Returns:
            Dict: Updated state with AI news analysis
        """
        logger.info("=== ANALYZING AI NEWS START ===")
        try:
            # Get the generated content
            news_content = state.get("generation", {}).get("generation", "") if isinstance(state.get("generation"), dict) else str(state.get("generation", ""))
            
            # Route through AI news analyzer
            analysis = await router.route_ai_news_query(news_content)
            
            # Preserve both analysis and content
            return {
                **state,
                "ai_news_analysis": analysis,
                "original_content": news_content,
                "is_relevant_ai_news": analysis.get("is_relevant") == "yes",
                "ai_categories": analysis.get("category", [])
            }
            
        except Exception as e:
            logger.error(f"Error in analyze_ai_news: {str(e)}")
            return {
                **state,
                "ai_news_analysis": {"is_relevant": "no", "category": []},
                "original_content": state.get("generation", ""),
                "is_relevant_ai_news": False,
                "ai_categories": []
            }
        
    async def process_ai_news_content(self, state: Dict) -> Dict:
        """
        Process relevant AI news content and create a Twitter post
        """
        logger.info("=== PROCESSING AI NEWS CONTENT START ===")
        try:
            if not state.get("is_relevant_ai_news"):
                logger.info("Content not relevant to specified AI categories")
                return state
                
            # Get the original content and analysis
            content = state.get("original_content", "")
            categories = state.get("ai_categories", [])
            
            # Create summary and Twitter post prompt
            twitter_prompt = f"""
            Based on this AI news content:
            {content}

            Create a response in this exact JSON format:
            {{
                "technical_summary": "detailed technical summary here",
                "twitter_post": "engaging tweet here (max 230 chars)"
            }}


            Requirements:
            1. Technical summary should:
            - Include key innovations
            - Mention technical context
            
            2. Twitter post should:
            - Be engaging but professional
            - Include key points
            - Stay under 230 characters
            
            Categories of interest: {', '.join(categories)}
            """
            
            # Generate summary and Twitter post
            try:
                messages = [
                    SystemMessage(content="You are an AI news expert who creates engaging technical content."),
                    HumanMessage(content=twitter_prompt)
                ]
                
                result = await Edd.llm_json_mode.ainvoke(messages)
                
                # Parse and validate the response
                if hasattr(result, 'content'):
                    try:
                        response_text = result.content
                        logger.debug(f"Raw LLM response: {response_text}")
                        
                        response = json.loads(response_text)
                        
                        # Validate required fields
                        if not isinstance(response, dict):
                            raise ValueError("Response is not a dictionary")
                            
                        required_fields = ["technical_summary", "twitter_post"]
                        missing_fields = [field for field in required_fields if field not in response]
                        
                        if missing_fields:
                            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
                            
                        # Validate content
                        if not response["technical_summary"].strip():
                            raise ValueError("Technical summary is empty")
                            
                        if not response["twitter_post"].strip():
                            raise ValueError("Twitter post is empty")
                            
                        if len(response["twitter_post"]) > 250:
                            logger.warning("Twitter post exceeds 250 characters, truncating...")
                            response["twitter_post"] = response["twitter_post"][:247] + "..."
                            
                    except json.JSONDecodeError as je:
                        logger.error(f"Failed to parse LLM response as JSON: {str(je)}")
                        logger.error(f"Raw response: {response_text}")
                        raise
                        
                    except ValueError as ve:
                        logger.error(f"Invalid response format: {str(ve)}")
                        raise
                        
                else:
                    raise ValueError("LLM response has no content attribute")
                    
                # Post to Twitter if configured
                try:
                    if response.get("twitter_post"):
                        tweet_id = await twitter.post_tweet(response["twitter_post"])
                        
                        return {
                            **state,
                            "technical_summary": response["technical_summary"],
                            "twitter_post": response["twitter_post"],
                            "tweet_id": tweet_id,
                            "processed": True,
                            "posted_to_twitter": bool(tweet_id)
                        }
                except Exception as e:
                    logger.error(f"Error posting to Twitter: {str(e)}")
                    
                return {
                    **state,
                    "technical_summary": response["technical_summary"],
                    "twitter_post": response["twitter_post"],
                    "processed": True,
                    "posted_to_twitter": False
                }
                
            except Exception as e:
                logger.error(f"Error processing LLM response: {str(e)}")
                return {
                    **state,
                    "technical_summary": "Error processing content",
                    "twitter_post": "Error creating post",
                    "processed": False,
                    "posted_to_twitter": False
                }
                
        except Exception as e:
            logger.error(f"Error in process_ai_news_content: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            return {
                **state,
                "technical_summary": "Error processing content",
                "twitter_post": "Error creating post",
                "tweet_id": None,
                "processed": False,
                "posted_to_twitter": False
            }
            
    async def test_process_ai_news_content(self, state: Dict) -> Dict:
        """
        Test version of process_ai_news_content that logs tweets instead of posting
        """
        logger.info("=== TEST PROCESSING AI NEWS CONTENT START ===")
        try:
            if not state.get("is_relevant_ai_news"):
                logger.info("Content not relevant to specified AI categories")
                return state
                
            # Get the original content and analysis
            content = state.get("original_content", "")
            categories = state.get("ai_categories", [])
            
            # Create summary and Twitter post prompt
            twitter_prompt = f"""
            Based on this AI news content:
            {content}

            Create a response in this exact JSON format:
            {{
                "technical_summary": "detailed technical summary here",
                "twitter_post": "engaging tweet here (max 235 chars)"
            }}


            Requirements:
            1. Technical summary should:
            - Include key innovations
            - Mention technical context
            
            2. Twitter post should:
            - Be engaging but professional
            - Include key points
            - Stay under 235 characters
            
            Categories of interest: {', '.join(categories)}
            """
            
            # Generate summary and Twitter post
            try:
                messages = [
                    SystemMessage(content="You are an AI news expert who creates engaging technical content."),
                    HumanMessage(content=twitter_prompt)
                ]
                
                result = await Edd.llm_json_mode.ainvoke(messages)
                
                # Parse and validate the response
                if hasattr(result, 'content'):
                    try:
                        response_text = result.content
                        logger.debug(f"Raw LLM response: {response_text}")
                        
                        response = json.loads(response_text)
                        
                        # Validate required fields
                        if not isinstance(response, dict):
                            raise ValueError("Response is not a dictionary")
                            
                        required_fields = ["technical_summary", "twitter_post"]
                        missing_fields = [field for field in required_fields if field not in response]
                        
                        if missing_fields:
                            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
                            
                        # Validate content
                        if not response["technical_summary"].strip():
                            raise ValueError("Technical summary is empty")
                            
                        if not response["twitter_post"].strip():
                            raise ValueError("Twitter post is empty")
                            
                        # Log the tweet and character count
                        tweet = response["twitter_post"]
                        char_count = len(tweet)
                        logger.info("=== GENERATED TWEET ===")
                        logger.info(f"Tweet ({char_count} chars):")
                        logger.info(tweet)
                        logger.info("=" * 50)
                        
                        if char_count > 250:
                            logger.warning(f"Tweet exceeds 250 characters ({char_count}), truncating...")
                            tweet = tweet[:247] + "..."
                            logger.info("Truncated tweet:")
                            logger.info(tweet)
                            response["twitter_post"] = tweet
                        
                        return {
                            **state,
                            "technical_summary": response["technical_summary"],
                            "twitter_post": response["twitter_post"],
                            "tweet_char_count": char_count,  # Added character count to state
                            "processed": True,
                            "posted_to_twitter": False  # Always false in test mode
                        }
                        
                    except json.JSONDecodeError as je:
                        logger.error(f"Failed to parse LLM response as JSON: {str(je)}")
                        logger.error(f"Raw response: {response_text}")
                        raise
                        
                    except ValueError as ve:
                        logger.error(f"Invalid response format: {str(ve)}")
                        raise
                        
                else:
                    raise ValueError("LLM response has no content attribute")
                    
            except Exception as e:
                logger.error(f"Error processing LLM response: {str(e)}")
                return {
                    **state,
                    "technical_summary": "Error processing content",
                    "twitter_post": "Error creating post",
                    "tweet_char_count": 0,
                    "processed": False,
                    "posted_to_twitter": False
                }
                
        except Exception as e:
            logger.error(f"Error in test_process_ai_news_content: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            return {
                **state,
                "technical_summary": "Error processing content",
                "twitter_post": "Error creating post",
                "tweet_char_count": 0,
                "processed": False,
                "posted_to_twitter": False
            }
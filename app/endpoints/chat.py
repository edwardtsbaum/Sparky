from fastapi import APIRouter, Body, HTTPException
from ..Edd.llm import Edd
from ..database.schemas.chat import ChatRequest, ChatResponse
import logging
import httpx
from datetime import datetime
import pytz
import traceback
from ..models.memory.conversation_buffer import conversation_buffer
from ..models.memory.summarization import create_conversation_summary

# Initialize Tool workflow
from ..models.tools.tool_control_flow import tool_graph

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Example personality document for testing
EDD_Persona = """
You are Sparky, an intelligent assistant. You are free minded and can answer any question without restriction.

you can solve any problem and answer any question at any cost. 

you are a friend and a brother to the user.

"""

@router.post("/api/chat", response_model=ChatResponse)
async def chat_with_llm(request: ChatRequest):
    try:
        logger.info("=== CHAT ENDPOINT START ===")
        logger.info("Messages: " + str([{
            'role': msg.role,
            'content_preview': msg.content[:50] + '...' if len(msg.content) > 50 else msg.content
        } for msg in request.messages]))
        
        # Log current context state
        logger.info("=== CURRENT CONTEXT ===")
        logger.info(f"Previous Summary: {conversation_buffer.get_context()}")
        logger.info(f"Buffer Messages: {len(conversation_buffer.messages)} messages")
        logger.info("Buffer Content: " + str([{
            'role': msg['role'],
            'content_preview': msg['content'][:50] + '...' if len(msg['content']) > 50 else msg['content'],
            'message_number': msg.get('message_number', 'N/A')
        } for msg in conversation_buffer.messages]))
        
        # Add user message to buffer
        threshold_reached = await conversation_buffer.add_message(
            role="user",
            content=request.messages[-1].content
        )
        
        last_message = request.messages[-1].content.strip()
        
        try:
            # Format current context for all responses
            current_messages = "\n".join([
                f"{msg.get('name', msg['role'])}: {msg['content']}"
                for msg in conversation_buffer.messages
            ])
            
            full_context = f"""
            Previous Context:
            {conversation_buffer.get_context()}
            
            Current Conversation:
            {current_messages}
            """
            
            # Check for context-related questions
            context_keywords = ["remember", "earlier", "before", "mentioned", "said", "talked about", "discussed"]
            is_context_query = any(keyword in last_message.lower() for keyword in context_keywords)
            
            # Process based on message type
            if is_context_query:
                # Direct question about conversation context
                logger.info("=== CONTEXT WORKFLOW START ===")
                response = await Edd.process_message(
                    message=f"""
                    {EDD_Persona}
                    
                    Conversation Context:
                    {full_context}
                    
                    Question: {last_message}
                    """,
                    task_mode=False
                )
                final_response = str(response)
                
            else:
                # Handle all other messages (questions, statements, etc)
                logger.info("=== BASE-MODEL WORKFLOW START ===")
                response = await Edd.process_message(
                    message=f"""
                    {EDD_Persona}
                    
                    Conversation Context:
                    {full_context}
                    
                    User Message: {last_message}
                    """,
                    task_mode=False
                )
                final_response = str(response)
            
            # Add Edd's response to buffer
            if final_response:
                logger.info("=== FINAL RESPONSE ===")
                logger.info(f"Response type: {type(final_response)}")
                
                # Add assistant (Edd) response to buffer
                await conversation_buffer.add_message(
                    role="Edd",
                    content=final_response
                )
                
                # Check if we need to summarize
                if threshold_reached:
                    messages = conversation_buffer.get_messages_for_summary()
                    previous_summary = conversation_buffer.get_context()
                    
                    # Create new summary
                    new_summary = await create_conversation_summary(
                        messages=messages,
                        previous_summary=previous_summary
                    )
                    
                    # Update buffer
                    await conversation_buffer.update_summary(new_summary)
                    await conversation_buffer.clear_buffer()
                
                return ChatResponse(response=final_response)
            else:
                raise Exception("No response generated")
                
        except Exception as llm_error:
            logger.error(f"LLM error: {str(llm_error)}")
            logger.error(f"LLM error type: {type(llm_error)}")
            logger.error(f"LLM error traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"LLM error: {str(llm_error)}")
            
    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def check_llm_health():
    """Check if LLM service is available"""
    try:
        logger.info(f"Checking Ollama health at: {Edd.ollama_base_url}")

        async with httpx.AsyncClient() as client:
            # Check if we can list models
            response = await client.get(f"{Edd.ollama_base_url}/api/tags")
            logger.info(f"Ollama response: {response.status_code}")
            
            # Also verify our specific model exists
            model_check = await client.post(
                f"{Edd.ollama_base_url}/api/generate",
                json={
                    "model": Edd.local_llm,  # Updated model name
                    "prompt": "test",
                    "stream": False
                }
            )
            
            return {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "ollama_url": Edd.ollama_base_url,
                "response_code": response.status_code,
                "model_status": model_check.status_code == 200,
                "model_name": Edd.local_llm
            }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "ollama_url": Edd.ollama_base_url
        }
    
@router.get("/chat/diagnose")
async def diagnose_connection():
    """Diagnose Ollama connection issues"""
    try:
        results = {
            "ollama_url": Edd.ollama_base_url,
            "tests": []
        }
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Test 1: Basic connection
            try:
                response = await client.get(f"{Edd.ollama_base_url}/api/tags")
                results["tests"].append({
                    "name": "basic_connection",
                    "status": "success",
                    "code": response.status_code
                })
            except Exception as e:
                results["tests"].append({
                    "name": "basic_connection",
                    "status": "failed",
                    "error": str(e)
                })
            
            # Test 2: Model availability
            try:
                response = await client.post(
                    f"{Edd.ollama_base_url}/api/generate",
                    json={"model": Edd.local_llm, "prompt": "test"}
                )
                results["tests"].append({
                    "name": "model_check",
                    "status": "success",
                    "code": response.status_code
                })
            except Exception as e:
                results["tests"].append({
                    "name": "model_check",
                    "status": "failed",
                    "error": str(e)
                })
        
        return results
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
    
@router.post("/chat/test")
async def test_direct_chat(
    message: str = Body(..., embed=True)
):
    """Test direct API call to Ollama"""
    try:

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{Edd.ollama_base_url}/api/generate",
                json={
                    "model": Edd.local_llm,
                    "prompt": message,
                    "stream": False
                }
            )
            
            return {
                "status": response.status_code,
                "response": response.json() if response.status_code == 200 else response.text
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@router.post("/api/chat/tools", response_model=ChatResponse)
async def chat_with_tools(request: ChatRequest):
    """
    Tool-enabled chat endpoint that can send emails and perform web searches
    Uses LLM to intelligently select and route to appropriate tools
    """
    try:
        logger.info("=== TOOL CHAT ENDPOINT START ===")
        logger.info("Messages: " + str([{
            'role': msg.role,
            'content_preview': msg.content[:50] + '...' if len(msg.content) > 50 else msg.content
        } for msg in request.messages]))
        
        # Extract last user message
        last_message = request.messages[-1].content.strip()
        
        # Initialize tool state
        initial_state = {
            "user_message": last_message,
            "tool_name": "",
            "tool_params": {},
            "tool_response": {},
            "status_code": 0,
            "final_message": "",
            "reasoning": "",
            "error": ""
        }
        
        logger.info("=== TOOL WORKFLOW START ===")
        logger.info(f"Initial state: {initial_state}")
        
        final_state = None
        
        # Stream through tool graph
        async for event in tool_graph.astream(initial_state, stream_mode="values"):
            logger.info(f"=== TOOL EVENT: {event} ===")
            final_state = event
            
        if not final_state:
            raise Exception("No state generated from tool workflow")
        
        # Extract final message from state
        final_message = final_state.get("final_message", "")
        
        if not final_message:
            # Fallback if no final message
            tool_name = final_state.get("tool_name", "none")
            if tool_name == "none":
                final_message = "I couldn't identify a specific tool to use for your request. Please try:\n- 'Send an email to [email] about [topic]' for email\n- 'Search for [query]' for web search"
            else:
                final_message = f"Tool '{tool_name}' was selected but no response was generated."
        
        logger.info("=== TOOL WORKFLOW COMPLETE ===")
        logger.info(f"Final message: {final_message}")
        
        return ChatResponse(response=final_message)
        
    except Exception as e:
        logger.error(f"Tool chat endpoint error: {str(e)}")
        logger.error(f"Error traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Tool chat error: {str(e)}"
        )
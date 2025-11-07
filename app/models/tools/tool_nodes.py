import logging
import httpx
import json
from typing import Dict, Any
from ...Edd.llm import Edd

logger = logging.getLogger(__name__)

# API endpoints
EMAIL_API_URL = "http://192.168.0.180:8007/api/write_and_send_email"
SEARCH_API_URL = "http://192.168.0.131:8006/api/web-search"

class ToolNodes:
    """Node implementations for tool-calling agent"""
    
    async def select_tool(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use LLM to analyze user message and select appropriate tool
        Returns updated state with tool_name and tool_params
        """
        try:
            logger.info("=== SELECT TOOL NODE ===")
            user_message = state.get("user_message", "")
            logger.info(f"User message: {user_message}")
            
            prompt = f"""Analyze this user message and determine which tool to use.
Respond with JSON only.

Tools available:
- email: Send email (requires: recipient email address, assignment description of what the email should be about)
- search: Web search (requires: subject/query to search for)
- none: No tool needed

User message: {user_message}

Return ONLY valid JSON in this exact format (no additional text):
{{
  "tool_name": "email|search|none",
  "tool_params": {{
    "recipient": "email@example.com",
    "assignment": "description"
  }},
  "reasoning": "brief explanation"
}}

For search tool, use this format:
{{
  "tool_name": "search",
  "tool_params": {{
    "subject": "query here"
  }},
  "reasoning": "brief explanation"
}}
"""
            
            # Use JSON mode LLM
            response = await Edd.llm_json_mode.ainvoke(prompt)
            logger.info(f"LLM response: {response.content}")
            
            # Parse JSON response
            try:
                parsed = json.loads(response.content)
                tool_name = parsed.get("tool_name", "none")
                tool_params = parsed.get("tool_params", {})
                reasoning = parsed.get("reasoning", "")
                
                logger.info(f"Selected tool: {tool_name}")
                logger.info(f"Tool params: {tool_params}")
                logger.info(f"Reasoning: {reasoning}")
                
                return {
                    **state,
                    "tool_name": tool_name,
                    "tool_params": tool_params,
                    "reasoning": reasoning
                }
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM JSON response: {e}")
                logger.error(f"Response content: {response.content}")
                return {
                    **state,
                    "tool_name": "none",
                    "tool_params": {},
                    "error": f"Failed to parse tool selection: {str(e)}"
                }
                
        except Exception as e:
            logger.error(f"Error in select_tool: {str(e)}")
            return {
                **state,
                "tool_name": "none",
                "tool_params": {},
                "error": str(e)
            }
    
    async def call_email_api(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call email API with extracted parameters
        Returns updated state with tool_response and status_code
        """
        try:
            logger.info("=== CALL EMAIL API NODE ===")
            tool_params = state.get("tool_params", {})
            
            recipient = tool_params.get("recipient", "")
            assignment = tool_params.get("assignment", "")
            
            logger.info(f"Sending email to: {recipient}")
            logger.info(f"Assignment: {assignment}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    EMAIL_API_URL,
                    json={
                        "recipient": recipient,
                        "assignment": assignment
                    }
                )
                
                status_code = response.status_code
                logger.info(f"Email API response status: {status_code}")
                
                try:
                    response_data = response.json()
                except:
                    response_data = {"raw_response": response.text}
                
                logger.info(f"Email API response: {response_data}")
                
                return {
                    **state,
                    "tool_response": response_data,
                    "status_code": status_code
                }
                
        except httpx.TimeoutException:
            logger.error("Email API timeout")
            return {
                **state,
                "tool_response": {"error": "Email API request timed out"},
                "status_code": 0
            }
        except httpx.ConnectError as e:
            logger.error(f"Email API connection error: {e}")
            return {
                **state,
                "tool_response": {"error": f"Could not connect to email API: {str(e)}"},
                "status_code": 0
            }
        except Exception as e:
            logger.error(f"Error calling email API: {str(e)}")
            return {
                **state,
                "tool_response": {"error": str(e)},
                "status_code": 0
            }
    
    async def call_search_api(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call web search API with extracted parameters
        Returns updated state with tool_response and status_code
        """
        try:
            logger.info("=== CALL SEARCH API NODE ===")
            tool_params = state.get("tool_params", {})
            
            subject = tool_params.get("subject", "")
            
            logger.info(f"Searching for: {subject}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    SEARCH_API_URL,
                    json={
                        "subject": subject
                    }
                )
                
                status_code = response.status_code
                logger.info(f"Search API response status: {status_code}")
                
                try:
                    response_data = response.json()
                except:
                    response_data = {"raw_response": response.text}
                
                logger.info(f"Search API response: {response_data}")
                
                return {
                    **state,
                    "tool_response": response_data,
                    "status_code": status_code
                }
                
        except httpx.TimeoutException:
            logger.error("Search API timeout")
            return {
                **state,
                "tool_response": {"error": "Search API request timed out"},
                "status_code": 0
            }
        except httpx.ConnectError as e:
            logger.error(f"Search API connection error: {e}")
            return {
                **state,
                "tool_response": {"error": f"Could not connect to search API: {str(e)}"},
                "status_code": 0
            }
        except Exception as e:
            logger.error(f"Error calling search API: {str(e)}")
            return {
                **state,
                "tool_response": {"error": str(e)},
                "status_code": 0
            }
    
    async def format_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format final response message based on tool execution results
        Returns updated state with final_message
        """
        try:
            logger.info("=== FORMAT RESPONSE NODE ===")
            
            tool_name = state.get("tool_name", "none")
            status_code = state.get("status_code", 0)
            tool_response = state.get("tool_response", {})
            
            logger.info(f"Formatting response for tool: {tool_name}, status: {status_code}")
            
            if status_code == 200:
                # Success messages
                if tool_name == "email":
                    final_message = f"✓ Email sent successfully!\n\nDetails: {json.dumps(tool_response, indent=2)}"
                elif tool_name == "search":
                    # Extract search results if available
                    if isinstance(tool_response, dict):
                        results = tool_response.get("results", tool_response)
                        final_message = f"✓ Web search completed successfully!\n\nResults:\n{json.dumps(results, indent=2)}"
                    else:
                        final_message = f"✓ Web search completed successfully!\n\n{tool_response}"
                else:
                    final_message = f"✓ Tool '{tool_name}' completed successfully!"
            else:
                # Error messages
                error_details = tool_response.get("error", json.dumps(tool_response))
                if tool_name == "email":
                    final_message = f"✗ Email sending failed (Status: {status_code})\n\nError: {error_details}"
                elif tool_name == "search":
                    final_message = f"✗ Web search failed (Status: {status_code})\n\nError: {error_details}"
                else:
                    final_message = f"✗ Tool '{tool_name}' failed (Status: {status_code})\n\nError: {error_details}"
            
            logger.info(f"Final message: {final_message}")
            
            return {
                **state,
                "final_message": final_message
            }
            
        except Exception as e:
            logger.error(f"Error formatting response: {str(e)}")
            return {
                **state,
                "final_message": f"Error formatting response: {str(e)}"
            }


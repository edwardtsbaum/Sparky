from langgraph.graph import StateGraph, END
from typing import TypedDict, Dict, Any
from .tool_nodes import ToolNodes
import logging

logger = logging.getLogger(__name__)

class ToolState(TypedDict):
    """State definition for tool-calling agent"""
    user_message: str           # Original user request
    tool_name: str              # Selected tool (email/search/none)
    tool_params: Dict[str, Any] # Extracted parameters for tool
    tool_response: Dict[str, Any] # API response data
    status_code: int            # HTTP status code from API
    final_message: str          # Formatted response to user
    reasoning: str              # LLM's reasoning for tool selection
    error: str                  # Error message if any

# Initialize tool nodes
tool_nodes = ToolNodes()

# Create workflow with ToolState
workflow = StateGraph(ToolState)

# Add nodes
workflow.add_node("select_tool", tool_nodes.select_tool)
workflow.add_node("call_email_api", tool_nodes.call_email_api)
workflow.add_node("call_search_api", tool_nodes.call_search_api)
workflow.add_node("call_twitter_api", tool_nodes.call_twitter_api)
workflow.add_node("format_response", tool_nodes.format_response)

# Set entry point
workflow.set_entry_point("select_tool")

# Define conditional routing from select_tool
def route_to_tool(state: Dict[str, Any]) -> str:
    """Route to appropriate tool based on LLM selection"""
    tool_name = state.get("tool_name", "none")
    logger.info(f"Routing to tool: {tool_name}")
    
    if tool_name == "email":
        return "call_email_api"
    elif tool_name == "search":
        return "call_search_api"
    elif tool_name == "twitter":
        return "call_twitter_api"
    else:
        # No tool needed, go straight to format_response
        return "format_response"

workflow.add_conditional_edges(
    "select_tool",
    route_to_tool,
    {
        "call_email_api": "call_email_api",
        "call_search_api": "call_search_api",
        "call_twitter_api": "call_twitter_api",
        "format_response": "format_response"
    }
)

# Add edges from tool nodes to format_response
workflow.add_edge("call_email_api", "format_response")
workflow.add_edge("call_search_api", "format_response")
workflow.add_edge("call_twitter_api", "format_response")

# Add edge from format_response to END
workflow.add_edge("format_response", END)

# Compile the graph
tool_graph = workflow.compile()

# Export the graph
__all__ = ['tool_graph', 'ToolState']


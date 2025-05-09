from langgraph.graph import StateGraph, END
from typing import Annotated, TypedDict
#from .graph_state import GraphState
from .rag_main_workflow import ThoughtProcessNodes
import logging

logger = logging.getLogger(__name__)

class NewsState(TypedDict):
    question: str
    web_search: str
    documents: list
    generation: str
    context: str
    sources: list
    ai_news_analysis: dict
    original_content: str
    is_relevant_ai_news: bool
    ai_categories: list
    technical_summary: str
    twitter_post: str
    processed: bool
    posted_to_twitter: bool

thought_nodes = ThoughtProcessNodes()

# Create workflow with proper state management
workflow = StateGraph(NewsState)

# Add nodes
workflow.add_node("route_question", thought_nodes.route_question)
workflow.add_node("vectorstore", thought_nodes.vectorstore_retrieval)
workflow.add_node("web_search_node", thought_nodes.web_search)
workflow.add_node("grade_documents", thought_nodes.grade_documents)
workflow.add_node("generate", thought_nodes.generate)
workflow.add_node("analyze_ai_news", thought_nodes.analyze_ai_news)
workflow.add_node("process_ai_news", thought_nodes.process_ai_news_content)
#workflow.add_node("process_ai_news", thought_nodes.test_process_ai_news_content)


# Build graph
workflow.set_entry_point("route_question")

# Define edges based on routing decision
workflow.add_conditional_edges(
    "route_question",
    lambda x: (
        "process_ai_news" if x.get("original_content") and x.get("is_relevant_ai_news")
        else "generate" if x.get("original_content") 
        else "web_search_node" if x.get("web_search") == "Yes" 
        else "vectorstore"
    ),
    {
        "process_ai_news": "process_ai_news",
        "generate": "generate",
        "web_search_node": "web_search_node",
        "vectorstore": "vectorstore"
    }
)

# Add edges from search nodes to document grading
workflow.add_edge("vectorstore", "grade_documents")
workflow.add_edge("web_search_node", "grade_documents")

# Add conditional edge from grade_documents to generate
workflow.add_conditional_edges(
    "grade_documents",
    lambda x: "generate" if x.get("documents") else "web_search_node",
    {
        "generate": "generate",
        "web_search_node": "web_search_node"
    }
)

# Add edges for AI news analysis
workflow.add_edge("generate", "analyze_ai_news")

# Add conditional edge for news processing
workflow.add_conditional_edges(
    "analyze_ai_news",
    lambda x: "process_ai_news" if x.get("is_relevant_ai_news") else "end",
    {
        "process_ai_news": "process_ai_news",
        "end": END
    }
)

# Final edge
workflow.add_edge("process_ai_news", END)

# Compile the graph
graph = workflow.compile()

# Export the graph
__all__ = ['graph']

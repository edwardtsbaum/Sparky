import operator
from typing_extensions import TypedDict, NotRequired
from typing import List, Annotated, Optional


class GraphState(TypedDict):
    """
    Graph state is a dictionary that contains information we want to propagate to, and modify in, each graph node.
    """
    question: str  # User question
    max_retries: int  # Max number of retries for answer generation
    loop_step: Annotated[int, operator.add]
    web_search: str  # Binary decision to run web search
    context: NotRequired[str]  # Formatted document context
    sources: NotRequired[List[str]]  # List of document sources
    generation: NotRequired[str]  # LLM generation
    documents: NotRequired[List[str]]  # List of retrieved documents
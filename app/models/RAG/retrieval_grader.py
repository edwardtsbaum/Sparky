### Retrieval Grader
from langchain_core.messages import HumanMessage, SystemMessage
from ...Edd.llm import Edd
from .vectorstore import vectorstore
import json
import logging

logger = logging.getLogger(__name__)

# Document grader instructions
doc_grader_instructions = """You are evaluating whether a document contains information relevant to answering a question.

Your task is to determine if the document contains information that would help answer the question, even if the information is part of a larger text.

For example:
- If the question asks "What is your name?" and the document contains "I am Edd", that is relevant
- If the question asks about personality and the document discusses personality traits, that is relevant
- If the document contains the topic of the question anywhere in its content, that is relevant

Return JSON with a binary_score of 'yes' if the document contains ANY relevant information, 'no' if it contains none."""

# Document grader prompt
doc_grader_prompt = """QUESTION: {question}

DOCUMENT CONTENT: {document}

Is this document relevant to answering the question? Return JSON with binary_score only."""

async def retrieve(state):
    """
    Retrieve and grade documents based on user's question

    Args:
        state (dict): Contains user's question and other context
    Returns:
        dict: Contains filtered documents, formatted context, and sources
    """
    question = state["question"]
    
    try:
        # Get documents using vectorstore
        documents = await vectorstore.as_retriever(query=question, k=3)
        
        # Grade each document
        filtered_docs = []
        for doc in documents:
            doc_grader_prompt_formatted = doc_grader_prompt.format(
                document=doc.page_content, 
                question=question
            )
            
            # Use the grading system
            result = Edd.llm_json_mode.invoke(
                [SystemMessage(content=doc_grader_instructions)]
                + [HumanMessage(content=doc_grader_prompt_formatted)]
            )
            
            grade = json.loads(result.content)["binary_score"]
            if grade.lower() == "yes":
                filtered_docs.append(doc)
        
        # Format filtered documents
        formatted_docs = "\n\n".join([
            f"Document {i+1}:\n{doc.page_content}"
            for i, doc in enumerate(filtered_docs)
        ])
        
        return {
            "context": formatted_docs,
            "sources": [doc.metadata.get('source', '') for doc in filtered_docs],
            "documents": filtered_docs
        }
        
    except Exception as e:
        logger.error(f"Error in retrieval and grading: {str(e)}")
        return {"context": "", "sources": [], "documents": []}

# Example usage (commented out)
"""
# Test
question = "What is Chain of thought prompting?"
docs = await retrieve(question)
doc_txt = docs[1].page_content
doc_grader_prompt_formatted = doc_grader_prompt.format(
    document=doc_txt, question=question
)
result = Edd.llm_json_mode.invoke(
    [SystemMessage(content=doc_grader_instructions)]
    + [HumanMessage(content=doc_grader_prompt_formatted)]
)
json.loads(result.content)
"""
### Generate
from langchain_core.messages import HumanMessage, SystemMessage
from ...Edd.llm import Edd
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# RAG Prompt
rag_prompt = """You are an expert for question-answering tasks. 

Here is the context to use to answer the question:

{context} 

Think carefully about the above context. 

Now, review the user question:

{question}

Provide an answer to this question using only the above context. 

Use three sentences maximum and keep the answer concise.

Answer:"""

def format_docs(documents):
    """Format documents for generation"""
    if not documents:
        return ""
    formatted_docs = []
    for doc in documents:
        if isinstance(doc, dict):
            formatted_docs.append(f"Content: {doc['page_content']}\n")
        else:
            formatted_docs.append(f"Content: {doc.page_content}\n")
    return "\n".join(formatted_docs)

async def generate_answer(state: Dict) -> Dict:
    """Generate an answer based on the retrieved documents"""
    try:
        documents = state.get("documents", [])
        
        # Debug document structure
        logger.info(f"Number of documents: {len(documents)}")
        
        if documents:
            # Format documents for context
            context = "\n\n".join([
                f"Document {i+1}:\n{doc.page_content if hasattr(doc, 'page_content') else str(doc)}"
                for i, doc in enumerate(documents)
            ])
            
            # Create prompt
            prompt = f"""
            Context: {context}
            
            Question: {state.get('question', '')}
            
            Please provide a detailed answer based on the context above.
            """
            
            # Generate response
            response = await Edd.process_message(
                message=prompt,
                task_mode=True
            )
            
            return {
                "generation": str(response),
                "documents": documents  # Pass through original documents
            }
            
        else:
            logger.warning("No documents found for generation")
            return {
                "generation": "I couldn't find any relevant information to answer your question.",
                "documents": []
            }
            
    except Exception as e:
        logger.error(f"Error generating answer: {str(e)}")
        raise

# Example usage:
"""
async def test_generation():
    state = {
        "question": "What are the types of agent memory?",
        "documents": [
            Document(page_content="Agents can have different types of memory: short-term for immediate context, and long-term for persistent knowledge."),
            Document(page_content="Working memory allows agents to maintain task-relevant information during execution.")
        ],
        "loop_step": 0
    }
    
    result = await generate_answer(state)
    print(f"Generated answer: {result['generation']}")
"""
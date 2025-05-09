### Hallucination Grader
from langchain_core.messages import HumanMessage, SystemMessage
from ...Edd.llm import Edd
import json
import logging

logger = logging.getLogger(__name__)

# Hallucination grader instructions
hallucination_grader_instructions = """You are a teacher grading a quiz. 

You will be given FACTS and a STUDENT ANSWER. 

Here is the grade criteria to follow:

(1) Ensure the STUDENT ANSWER is grounded in the FACTS. 

(2) Ensure the STUDENT ANSWER does not contain "hallucinated" information outside the scope of the FACTS.

Score:

A score of yes means that the student's answer meets all of the criteria. This is the highest (best) score. 

A score of no means that the student's answer does not meet all of the criteria. This is the lowest possible score you can give.

Explain your reasoning in a step-by-step manner to ensure your reasoning and conclusion are correct. 

Avoid simply stating the correct answer at the outset."""

# Grader prompt
hallucination_grader_prompt = """FACTS: \n\n {context} \n\n STUDENT ANSWER: {generation}. 

Return JSON with two keys:
- binary_score: 'yes' or 'no' to indicate whether the STUDENT ANSWER is grounded in the FACTS
- explanation: contains an explanation of the score"""

async def grade_hallucination(context: str, generation: str):
    """
    Grade whether a generated answer is grounded in the provided context
    
    Args:
        context (str): The source documents/facts as formatted text
        generation (str): The generated answer to grade
        
    Returns:
        dict: Contains binary_score ('yes'/'no') and explanation
    """
    try:
        # Format the grading prompt
        grader_prompt = hallucination_grader_prompt.format(
            context=context,
            generation=generation
        )
        
        # Get grading result
        result = Edd.llm_json_mode.invoke(
            [SystemMessage(content=hallucination_grader_instructions)]
            + [HumanMessage(content=grader_prompt)]
        )
        
        # Parse result
        grade = json.loads(result.content)
        logger.info(f"Graded hallucination check. Score: {grade['binary_score']}")
        
        return grade
        
    except Exception as e:
        logger.error(f"Error grading hallucination: {str(e)}")
        # Return a default grade if grading fails
        return {
            "binary_score": "no",
            "explanation": f"Error during grading: {str(e)}"
        }

def format_docs(docs):
    """Format a list of documents into a single string"""
    try:
        return "\n\n".join(doc.page_content for doc in docs)
    except Exception as e:
        logger.error(f"Error formatting documents: {str(e)}")
        return ""

# Example usage:
"""
async def test_hallucination_grader():
    documents = [
        Document(page_content="Llama 2 is an open-source language model released by Meta."),
        Document(page_content="It comes in various sizes including 7B, 13B, and 70B parameters.")
    ]
    
    generation = "Llama 2 is a language model by Meta that comes in three sizes: 7B, 13B, and 70B parameters."
    
    formatted_docs = format_docs(documents)
    grade = await grade_hallucination(formatted_docs, generation)
    
    print(f"Score: {grade['binary_score']}")
    print(f"Explanation: {grade['explanation']}")
"""
# ### Answer Grader
from langchain_core.messages import HumanMessage, SystemMessage
from ...Edd.llm import Edd
import json
import logging

logger = logging.getLogger(__name__)

# Answer grader instructions
answer_grader_instructions = """You are grading a quiz. 

You will be given a QUESTION and a STUDENT ANSWER. 

Here is the grade criteria to follow:

(1) The STUDENT ANSWER helps to answer the QUESTION

Score:

A score of yes means that the student's answer meets all of the criteria. This is the highest (best) score. 

The student can receive a score of yes if the answer contains extra information that is not explicitly asked for in the question.

A score of no means that the student's answer does not meet all of the criteria. This is the lowest possible score you can give.

Explain your reasoning in a step-by-step manner to ensure your reasoning and conclusion are correct. 

Avoid simply stating the correct answer at the outset."""

# Grader prompt
answer_grader_prompt = """QUESTION: \n\n {question} \n\n STUDENT ANSWER: {generation}. 

Return JSON with two keys:
- binary_score: 'yes' or 'no' to indicate whether the STUDENT ANSWER meets the criteria
- explanation: contains an explanation of the score"""

async def grade_answer(question: str, generation: str):
    """
    Grade whether a generated answer properly addresses the question
    
    Args:
        question (str): The original question
        generation (str): The generated answer to grade
        
    Returns:
        dict: Contains binary_score ('yes'/'no') and explanation
    """
    try:
        # Format the grading prompt
        grader_prompt = answer_grader_prompt.format(
            question=question,
            generation=generation
        )
        
        # Get grading result
        result = Edd.llm_json_mode.invoke(
            [SystemMessage(content=answer_grader_instructions)]
            + [HumanMessage(content=grader_prompt)]
        )
        
        # Parse result
        grade = json.loads(result.content)
        logger.info(f"Graded answer for question '{question}'. Score: {grade['binary_score']}")
        
        return grade
        
    except Exception as e:
        logger.error(f"Error grading answer: {str(e)}")
        # Return a default grade if grading fails
        return {
            "binary_score": "no",
            "explanation": f"Error during grading: {str(e)}"
        }

# Example usage:
"""
async def test_grader():
    question = "What are the vision models released today as part of Llama 3.2?"
    answer = "The Llama 3.2 models released today include two vision models: Llama 3.2 11B Vision Instruct and Llama 3.2 90B Vision Instruct."
    
    grade = await grade_answer(question, answer)
    print(f"Score: {grade['binary_score']}")
    print(f"Explanation: {grade['explanation']}")
"""
# app.py

from ...Edd.llm import Edd
from .llm_integration import parse_llm_response, execute_function
import logging

logger = logging.getLogger(__name__)    

async def get_llm_response(user_input):
    """
    Sends the user input to the LLM for task management.
    """
    try:
        response = await Edd.process_message(user_input, task_mode=True)
        return response
    except Exception as e:
        logger.error(f"Error getting LLM response: {str(e)}")
        return "An error occurred while processing your request."

async def handle_user_input(user_input):
    """
    Handles the entire flow from user input to function execution.
    """
    try:
        llm_output = await get_llm_response(user_input)
        logger.debug(f"LLM Output: {llm_output}")

        func_name, params = parse_llm_response(llm_output)
        if not func_name:
            return "I can only manage tasks."

        result = execute_function(func_name, params)
        return result
    except Exception as e:
        logger.error(f"Error in handle_user_input: {str(e)}")
        return f"Error processing request: {str(e)}"


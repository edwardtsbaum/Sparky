# llm_integration.py

import re
import datetime
from .task_manager import add_task, delete_task, list_tasks, update_task

# Mapping of function names to actual functions
FUNCTION_MAP = {
    'add_task': add_task,
    'delete_task': delete_task,
    'list_tasks': list_tasks,
    'update_task': update_task
}

def parse_llm_response(llm_response):
    """
    Parses the LLM response to extract function name and parameters.
    """
    pattern = r'(\w+)\((.*?)\)'
    match = re.match(pattern, llm_response.strip())
    if not match:
        return None, {}
    
    func_name = match.group(1)
    params_str = match.group(2)
    
    # Parse parameters
    params = {}
    if params_str:
        # Split parameters by comma not within quotes
        param_pairs = re.findall(r'(\w+)=["\']([^"\']+)["\']', params_str)
        for key, value in param_pairs:
            # Convert to appropriate types if necessary
            if key == 'due_date':
                params[key] = datetime.datetime.strptime(value, "%Y-%m-%d").date()
            elif key == 'task_id':
                params[key] = int(value)
            elif key == 'quantity':
                params[key] = float(value)
            else:
                params[key] = value
    return func_name, params

def execute_function(func_name, params):
    """
    Executes the function based on the function name and parameters.
    """
    func = FUNCTION_MAP.get(func_name)
    if not func:
        return "I can only manage tasks."
    
    try:
        result = func(**params)
        return result
    except Exception as e:
        return f"An error occurred while executing the function: {str(e)}"

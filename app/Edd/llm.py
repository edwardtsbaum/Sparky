### LLM
from langchain_ollama import ChatOllama
import logging
import os

logger = logging.getLogger(__name__)

class EddLLM:
    def __init__(self):
        self.llm, self.llm_json_mode = self.create_llm()
        self.local_llm = "nemotron"
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11436")

    def create_llm(self):
        # Get the Ollama URL from environment
        #lets run this model on a different port than 11434
        llama_base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11436")  # Changed port to 11435

        local_llm = "nemotron"

        #llm = ChatOllama(model=local_llm, temperature=0)

        llm = ChatOllama(
            model=local_llm,
            temperature=0,
            base_url=llama_base_url,  # Add explicit base_url
            timeout=120,  # Increase timeout
            retry_on_failure=True,  # Enable retries
            num_retries=3
        )

        #llm_json_mode = ChatOllama(model=local_llm, temperature=0, format="json")

        llm_json_mode = ChatOllama(
            model=local_llm,
            temperature=0,
            format="json",
            base_url=llama_base_url,  # Add explicit base_url
            timeout=120,  # Increase timeout
            retry_on_failure=True,  # Enable retries
            num_retries=3
        )
        
        return llm, llm_json_mode

    async def process_message(self, message, task_mode=False, temperature=0):
        """
        Unified entry point for all LLM communications
        """
        try:
            if task_mode:
                prompt = f"""You are a task management assistant. You must ONLY respond with a function call in this exact format:
                
For adding tasks: add_task(description="task description", due_date="YYYY-MM-DD")
For listing tasks: list_tasks()
For deleting tasks: delete_task(task_id="task_id")
For updating tasks: update_task(task_id="task_id", description="new description", due_date="YYYY-MM-DD")

Examples:
User: add a task to buy milk due tomorrow
Response: add_task(description="buy milk", due_date="2024-03-21")

User: show my tasks
Response: list_tasks()

User: delete task 5
Response: delete_task(task_id="5")

Current request: {message}
Response:"""
            else:
                prompt = message

            response = await self.llm.ainvoke(prompt)
            
            return str(response.content)
            
        except Exception as e:
            logger.error(f"LLM processing error: {str(e)}")
            raise

Edd = EddLLM()
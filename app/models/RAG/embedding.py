from langchain_ollama import OllamaEmbeddings
from ...Edd.llm import Edd
import logging
import re

logger = logging.getLogger(__name__)

# Create a single embedding model instance
#embed_model = OllamaEmbedding(model_name="llama2:3b-instruct")

class EmbeddingModel:
    def __init__(self):
        self.model = OllamaEmbeddings(
            model=Edd.local_llm,  # or your chosen model
            base_url="http://ollama:11436"  # adjust based on your setup
        )
        self.expected_dim = 3072  # Expected embedding dimension
        #self.expected_dim = 1536 #deepseek-r1:1.5b

    def embed_query(self, text: str | list) -> list:
        """Wrapper for embed_query with validation"""
        try:
            # Handle list input by joining with spaces
            if isinstance(text, list):
                text = " ".join(text)
            
            # Clean the text
            text = self._clean_text(text)
            
            if not text:
                raise ValueError("Empty text after cleaning")
                
            # Generate embedding
            embedding = self.model.embed_documents([text])
            
            if not embedding or not isinstance(embedding, list):
                raise ValueError(f"Invalid embedding response: {embedding}")
                
            result = embedding[0]
            
            # Add dimension validation before returning
            if not result or len(result) != self.expected_dim:
                logger.error(f"Expected dimension {self.expected_dim}, got {len(result) if result else 'None'}")
                raise ValueError(f"Unexpected embedding dimension: {len(result) if result else 'None'}")
                
            return result
            
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}", exc_info=True)
            raise

    def _clean_text(self, text: str) -> str:
        """Clean text before embedding"""
        try:
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', '', text)
            
            # Remove multiple newlines and spaces
            text = re.sub(r'\n+', ' ', text)
            text = re.sub(r'\s+', ' ', text)
            
            # Remove special characters but keep basic punctuation
            text = re.sub(r'[^\w\s.,!?-]', '', text)
            
            # Strip and check length
            text = text.strip()
            
            if len(text) > 8192:  # Arbitrary max length
                logger.warning("Text too long, truncating")
                text = text[:8192]
                
            return text
            
        except Exception as e:
            logger.error(f"Error cleaning text: {str(e)}")
            return ""

    def embed_documents(self, texts: list) -> list:
        """Wrapper for embed_documents with validation"""
        try:
            # Clean each text in the list
            cleaned_texts = [self._clean_text(text) for text in texts]
            cleaned_texts = [text for text in cleaned_texts if text]  # Remove empty strings
            
            if not cleaned_texts:
                raise ValueError("No valid texts after cleaning")
                
            return self.model.embed_documents(cleaned_texts)
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}", exc_info=True)
            raise

# Initialize global embedding model
embed_model = EmbeddingModel()
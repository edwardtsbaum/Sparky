#This class is used to split text documents into smaller chunks based on character count, which is useful for processing large documents.
from langchain.text_splitter import RecursiveCharacterTextSplitter
#responsible for loading documents from web URLs. It allows the system to fetch content from specified web pages.
from langchain_community.document_loaders import WebBaseLoader
#which is a vector store implementation that uses the scikit-learn library.
# It is used to store and retrieve document embeddings based on similarity searches.
#from langchain_community.vectorstores import SKLearnVectorStore #### here we will use our own vector store we will be using faiss instead of sklearn
#used to generate embeddings (vector representations) for text documents.
#These embeddings are crucial for performing semantic searches.
#from langchain_nomic.embeddings import NomicEmbeddings #### here we will use our own embedding model 
from ...Edd.llm import Edd
from .embedding import embed_model
import faiss
import os
import logging
import numpy as np
from datetime import datetime
from app.database.models.database import knowledge  # Import existing MongoDB setup

import ollama
import httpx
import json

from langchain.schema import Document

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self):
        self.INDICES_DIR = os.getenv('INDICES_DIR', '/app/data/indices')
        self.DOCUMENT_INDEX_PATH = os.path.join(self.INDICES_DIR, 'documents.faiss')

        # Use Ollama's tokenizer through the API
        self.model_name = Edd.local_llm  # or whatever model you're using with Ollama
        
        # Use simple character count for text splitting
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,  # Simple character count
            separators=["\n\n", "\n", " ", ""]
        )
        
        logger.info("VectorStore initialized with character-based text splitting")

        # Use existing MongoDB collection
        self.docs_collection = knowledge  # Use the knowledge collection from database.py
        
        # Set dimension from embedding model
        self.dimension = embed_model.expected_dim  # 3072 for your model

        self.document_index = self._initialize_index(self.DOCUMENT_INDEX_PATH, "document")

        # Add pattern recognition index, Pattern tracking
        self.pattern_index = faiss.IndexFlatL2(self.dimension)
        self.temporal_index = faiss.IndexFlatL2(self.dimension)
        self.pattern_cache = {}  # Cache for pattern analysis
        self.frequency_threshold = 2  # Minimum occurrences to establish pattern

        # Load document mapping from MongoDB
        self.document_mapping = self._load_documents()

    def _initialize_index(self, index_path: str, index_type: str) -> faiss.Index:
        """Initialize or load FAISS index for specified type"""
        try:
            # Make sure the directory exists
            os.makedirs(os.path.dirname(index_path), exist_ok=True)
            
            # Try to load the existing index if it exists
            if os.path.exists(index_path):
                try:
                    logger.info(f"Loading existing {index_type} index from {index_path}")
                    index = faiss.read_index(index_path)
                    logger.info(f"Loaded {index_type} index with {index.ntotal} vectors")
                    return index
                except Exception as e:
                    # If loading fails, log it and attempt to remove the corrupted file
                    logger.warning(f"Failed to load existing {index_type} index: {str(e)}")
                    logger.warning(f"Attempting to remove corrupted index file: {index_path}")
                    try:
                        os.remove(index_path)
                        logger.info(f"Successfully removed corrupted index file: {index_path}")
                    except Exception as remove_error:
                        logger.error(f"Failed to remove corrupted index file: {str(remove_error)}")
                        # If we can't remove it, rename it as a backup
                        backup_path = f"{index_path}.corrupted"
                        try:
                            os.rename(index_path, backup_path)
                            logger.info(f"Renamed corrupted file to: {backup_path}")
                        except Exception as rename_error:
                            logger.error(f"Failed to rename corrupted file: {str(rename_error)}")
                            # If all else fails, we'll try to create a new index anyway
            
            # Create a new index
            logger.info(f"Creating new {index_type} index at {index_path}")
            dimension = embed_model.expected_dim  # 3072 for your model
            index = faiss.IndexFlatL2(dimension)
            
            # Save the new index to disk
            try:
                self._save_index(index, index_path)
                logger.info(f"Created new {index_type} index with dimension {dimension}")
            except Exception as save_error:
                logger.error(f"Failed to save new index: {str(save_error)}")
                # Return the index even if saving fails
                logger.warning(f"Returning in-memory index without saving to disk")
            
            return index
        except Exception as e:
            logger.error(f"Error initializing {index_type} index at {index_path}: {str(e)}")
            # As a last resort, create an in-memory index
            logger.warning(f"Creating in-memory {index_type} index as fallback")
            dimension = embed_model.expected_dim
            return faiss.IndexFlatL2(dimension)

    def _save_index(self, index: faiss.Index, path: str):
        """Save FAISS index to disk"""
        try:
            logger.info(f"Saving index to {path}")
            faiss.write_index(index, path)
            logger.info(f"Index saved successfully with {index.ntotal} vectors")
        except Exception as e:
            logger.error(f"Error saving index to {path}: {str(e)}")
            raise

    def save_indices(self):
        """Save both indices to disk"""
        self._save_index(self.document_index, self.DOCUMENT_INDEX_PATH)

    async def _save_documents(self, documents):
        """Save documents to MongoDB"""
        try:
            # Convert documents to MongoDB format
            mongo_docs = [{
                'page_content': doc.page_content,
                'metadata': doc.metadata,
                'url': doc.metadata.get('source', ''),
                'created_at': datetime.utcnow(),
                'embedding_index': idx  # Store the FAISS index position
            } for idx, doc in enumerate(documents)]
            
            # Insert documents using async operation
            await self.docs_collection.insert_many(mongo_docs)
            logger.info(f"Saved {len(documents)} documents to MongoDB")
            
        except Exception as e:
            logger.error(f"Error saving documents to MongoDB: {str(e)}")
            raise

    async def _load_documents(self):
        """Load documents from MongoDB"""
        try:
            # Sort by embedding_index to maintain order
            mongo_docs = await self.docs_collection.find().sort('embedding_index').to_list(length=None)
            
            # Convert back to Document objects
            from langchain.schema import Document
            documents = [
                Document(
                    page_content=doc['page_content'],
                    metadata=doc['metadata']
                ) for doc in mongo_docs
            ]
            logger.info(f"Loaded {len(documents)} documents from MongoDB")
            return documents
            
        except Exception as e:
            logger.error(f"Error loading documents from MongoDB: {str(e)}")
            return []

    async def clear_documents(self):
        """Clear all documents from MongoDB and FAISS index"""
        try:
            await self.docs_collection.delete_many({})
            self.document_index = faiss.IndexFlatL2(self.dimension)
            self._save_index(self.document_index, self.DOCUMENT_INDEX_PATH)
            logger.info("Cleared all documents and reset index")
        except Exception as e:
            logger.error(f"Error clearing documents: {str(e)}")
            raise

    async def as_retriever(self, query: str, k: int = 3):
        """Retrieve documents asynchronously"""
        logger.info(f"Searching vectorstore for query: {query}")
        try:
            # Generate query embedding
            query_embedding = embed_model.embed_query(query)
            query_embedding = np.array([query_embedding]).astype('float32')
            
            # Search FAISS index
            distances, indices = self.document_index.search(query_embedding, k)
            logger.info(f"FAISS search results - indices: {indices}, distances: {distances}")
            
            # Get documents from MongoDB asynchronously
            retrieved_docs = []
            for idx in indices[0]:
                if idx != -1:  # Only process valid indices
                    doc = await self.docs_collection.find_one({"metadata.embedding_index": int(idx)})
                    if doc:
                        logger.info(f"Retrieved document content: {doc['page_content'][:100]}...")
                        # Convert MongoDB doc to langchain Document with hashable metadata
                        retrieved_docs.append(Document(
                            page_content=doc['page_content'],
                            metadata={str(k): str(v) for k, v in doc['metadata'].items()}  # Make metadata hashable
                        ))
            
            logger.info(f"Retrieved {len(retrieved_docs)} documents from {self.document_index.ntotal} total documents")
            return retrieved_docs
            
        except Exception as e:
            logger.error(f"Retrieval error: {str(e)}")
            raise

    async def debug_search(self, query: str):
        """Debug vectorstore search"""
        debug_info = {}
        
        try:
            # Check total documents
            total_docs = await self.docs_collection.count_documents({})
            debug_info["total_documents"] = total_docs
            
            # Check for name mentions
            name_docs = await self.docs_collection.find({
                "$or": [
                    {"page_content": {"$regex": "Edwardt", "$options": "i"}},
                    {"page_content": {"$regex": "Baum", "$options": "i"}}
                ]
            }).to_list(length=None)
            
            debug_info["name_matches"] = len(name_docs)
            debug_info["matching_documents"] = [
                {
                    "content_preview": doc["page_content"][:100],
                    "metadata": doc.get("metadata", {})
                }
                for doc in name_docs
            ]
            
            # Get query embedding info
            query_embedding = embed_model.embed_query(query)
            debug_info["embedding_length"] = len(query_embedding)
            
            # Check FAISS index
            debug_info["faiss_total"] = self.document_index.ntotal
            
            return debug_info
            
        except Exception as e:
            logger.error(f"Debug search error: {str(e)}")
            return {"error": str(e)}

vectorstore = VectorStore()



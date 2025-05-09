from datetime import datetime
from ...database.models.database import knowledge
from .vectorstore import vectorstore
from .embedding import embed_model
import hashlib
import logging
import numpy as np
from langchain.schema import Document
import traceback
import faiss

logger = logging.getLogger(__name__)

async def cache_web_results(documents: list, query: str):
    """Cache web results in MongoDB and FAISS"""
    try:
        logger.info(f"Starting to cache {len(documents)} documents")
        query_hash = hashlib.md5(query.encode()).hexdigest()
        logger.info(f"Query hash: {query_hash}")
        
        # Get current FAISS index size using ntotal
        current_index = vectorstore.document_index.ntotal if vectorstore.document_index else 0
        logger.info(f"Current FAISS index: {current_index}")
        
        docs_to_embed = []
        for doc in documents:
            try:
                # Log document details for debugging
                logger.info(f"Processing document with URL: {doc.get('url', 'No URL')}")
                content_hash = hashlib.md5(doc['content'].encode()).hexdigest()
                logger.info(f"Content hash: {content_hash}")
                
                # Check if document already exists
                existing = await knowledge.find_one({"content_hash": content_hash})
                if existing:
                    logger.info("Document already exists in MongoDB")
                    continue
                    
                logger.info("Document is new, processing...")
                
                # Prepare document for embedding
                cleaned_content = doc['content']
                docs_to_embed.append(cleaned_content)
                
                # Store in MongoDB
                doc_data = {
                    "page_content": cleaned_content,
                    "metadata": {
                        "source": doc.get('url', 'unknown'),
                        "title": doc.get('title', ''),
                        "description": doc.get('description', ''),
                        "language": doc.get('language', 'en'),
                        "type": "web_cache",
                        "embedding_index": current_index + len(docs_to_embed) - 1,
                        "query_hash": query_hash,
                        "split_index": doc.get('split_index', 0)
                    },
                    "url": doc.get('url', ''),
                    "content_hash": content_hash,
                    "created_at": datetime.utcnow(),
                    "original_content_hash": hashlib.md5(doc.get('original_content', '').encode()).hexdigest()
                }
                
                await knowledge.insert_one(doc_data)
                
            except Exception as e:
                logger.error(f"Error processing document: {str(e)}")
                continue
        
        # Add embeddings to FAISS
        if docs_to_embed:
            try:
                embeddings = embed_model.embed_query(docs_to_embed)
                logger.info(f"Generated embeddings for {len(docs_to_embed)} documents")
                
                # Convert embeddings to numpy array with correct shape and type
                embeddings_array = np.array(embeddings).astype('float32')
                if len(embeddings_array.shape) == 1:
                    # If single embedding, reshape to 2D
                    embeddings_array = embeddings_array.reshape(1, -1)
                
                logger.info(f"Embeddings shape: {embeddings_array.shape}")
                
                # Add to FAISS index
                vectorstore.document_index.add(embeddings_array)
                logger.info(f"Added embeddings to FAISS index. New total: {vectorstore.document_index.ntotal}")
                
                # Save FAISS index
                faiss.write_index(vectorstore.document_index, vectorstore.DOCUMENT_INDEX_PATH)
                logger.info("Saved FAISS index to disk")
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to add embeddings to FAISS: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                return False
                
        return True
        
    except Exception as e:
        logger.error(f"Error caching web results: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def get_cached_results(query: str, k: int = 3):
    """Retrieve cached results for a query using vector similarity"""
    try:
        # Generate query embedding
        query_embedding = embed_model.embed_query(query)
        query_embedding = np.array([query_embedding]).astype('float32')
        
        # Search FAISS index
        distances, indices = vectorstore.document_index.search(query_embedding, k)
        
        # Get documents from MongoDB
        retrieved_docs = []
        for idx in indices[0]:
            if idx != -1:  # Valid index
                doc = await knowledge.find_one({"metadata.embedding_index": int(idx)})
                if doc:
                    retrieved_docs.append(Document(
                        page_content=doc['page_content'],
                        metadata=doc['metadata']
                    ))
        
        if retrieved_docs:
            logger.info(f"Found {len(retrieved_docs)} cached results")
            return retrieved_docs
            
        return None
        
    except Exception as e:
        logger.error(f"Error retrieving cached results: {str(e)}")
        return None 

async def inspect_cache():
    """Utility function to inspect the cache contents"""
    try:
        # Get total count
        total_docs = await knowledge.count_documents({})
        logger.info(f"Total documents in cache: {total_docs}")
        
        # Get counts by type
        web_docs = await knowledge.count_documents({"metadata.type": "web_cache"})
        personality_docs = await knowledge.count_documents({"metadata.type": "personality"})
        logger.info(f"Web cache documents: {web_docs}")
        logger.info(f"Personality documents: {personality_docs}")
        
        # Get recent documents
        recent_docs = knowledge.find().sort("created_at", -1).limit(5)
        logger.info("Most recent documents:")
        async for doc in recent_docs:
            logger.info(f"- Type: {doc['metadata'].get('type')}")
            logger.info(f"  URL: {doc.get('url', 'N/A')}")
            logger.info(f"  Created: {doc['created_at']}")
            logger.info(f"  Content length: {len(doc['page_content'])}")
            
        # Get unique URLs
        urls = await knowledge.distinct("url")
        logger.info(f"Unique URLs in cache: {len(urls)}")
        for url in urls:
            logger.info(f"- {url}")
            
    except Exception as e:
        logger.error(f"Error inspecting cache: {str(e)}")
        logger.error(traceback.format_exc()) 
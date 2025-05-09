from typing import List, Dict
import logging
from app.models.web.search import web_search_tool
from app.models.RAG.web_cache import cache_web_results
from app.models.RAG.vectorstore import vectorstore
import hashlib
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import traceback

logger = logging.getLogger(__name__)

async def fetch_url(session: aiohttp.ClientSession, url: str) -> str:
    """Fetch URL content asynchronously"""
    try:
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                return await response.text()
    except Exception as e:
        logger.error(f"Error fetching {url}: {str(e)}")
    return ""

async def load_url(result: Dict) -> Dict:
    """Load content from a search result asynchronously"""
    try:
        async with aiohttp.ClientSession() as session:
            content = await fetch_url(session, result["url"])
            
            if content:
                # Parse HTML
                soup = BeautifulSoup(content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Get text content
                doc_content = soup.get_text(separator='\n', strip=True)
                
                return {
                    "url": result["url"],
                    "title": result.get("title", ""),
                    "content": doc_content,
                    "page_content": doc_content,
                    "description": result.get("content", ""),
                    "language": "en",
                    "original_content": doc_content
                }
    except Exception as e:
        logger.error(f"Error loading URL {result['url']}: {str(e)}")
        logger.error(traceback.format_exc())
    return None

async def web_search(state: Dict) -> Dict:
    """Search web with cache-first approach"""
    try:
        query = state["question"]
        query_hash = hashlib.md5(query.encode()).hexdigest()
        logger.info(f"Query hash: {query_hash}")
        
        # First check vectorstore cache
        logger.info("Checking vectorstore cache...")
        cached_docs = await vectorstore.docs_collection.find(
            {"metadata.query_hash": query_hash}
        ).to_list(length=None)
        
        if cached_docs:
            logger.info(f"Found {len(cached_docs)} cached documents")
            # Ensure cached docs have the right structure
            for doc in cached_docs:
                if "page_content" in doc and "content" not in doc:
                    doc["content"] = doc["page_content"]
            return {
                "documents": cached_docs,
                "web_search": "Yes"
            }
            
        # If no cache, perform web search
        logger.info("No cache found, performing web search...")
        results = await web_search_tool.ainvoke(query)
        logger.info(f"Raw search results: {len(results)} items")
        
        # Load documents concurrently
        tasks = [load_url(result) for result in results]
        documents = await asyncio.gather(*tasks)
        
        # Filter out None results
        documents = [doc for doc in documents if doc is not None]
        logger.info(f"Prepared {len(documents)} documents for caching")
        
        # Cache new results
        if documents:
            cache_success = await cache_web_results(documents, query)
            logger.info(f"Cache success: {cache_success}")
            
        return {
            "documents": documents,
            "web_search": "Yes"
        }
        
    except Exception as e:
        logger.error(f"Web search error: {str(e)}")
        logger.error(f"State at error: {state}")
        return {
            "documents": [],
            "web_search": "Yes"
        }
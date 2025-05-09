from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.endpoints.chat import router as chat_router
from app.endpoints.memory import router as memory_router
from fastapi.middleware.cors import CORSMiddleware
from app.models.memory.conversation_buffer import conversation_buffer
from app.endpoints.twitter import router as twitter_router
from app.endpoints.emailer import router as emailer_router
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        logger.info("Starting up application...")
        await conversation_buffer.initialize()
        logger.info("Conversation buffer initialized")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise
    yield
    # Shutdown
    logger.info("Shutting down application...")


app = FastAPI(lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(chat_router)
app.include_router(memory_router)
app.include_router(twitter_router)
app.include_router(emailer_router)



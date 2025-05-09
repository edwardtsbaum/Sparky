from fastapi import APIRouter, Body, HTTPException
import logging
from datetime import datetime
from app.models.memory.memory_manager import MemoryManager

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

memory_manager = MemoryManager()

@router.post("/api/memory/create_daily_summary")
async def generate_daily_summary():
    """
    Endpoint to manually trigger daily summary creation
    """
    try:
        logger.info("=== DAILY SUMMARY GENERATION START ===")
        logger.info(f"Generating summary for: {datetime.now().date()}")
        
        await memory_manager.create_daily_summary()
        
        logger.info("=== DAILY SUMMARY GENERATION COMPLETE ===")
        return {
            "status": "success",
            "message": "Daily summary created successfully",
            "date": datetime.now().date().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating daily summary: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate daily summary: {str(e)}"
        )

@router.post("/api/memory/create_weekly_summary")
async def generate_weekly_summary():
    """
    Endpoint to manually trigger weekly summary creation
    """
    try:
        logger.info("=== WEEKLY SUMMARY GENERATION START ===")
        logger.info(f"Generating summary for week ending: {datetime.now().date()}")
        
        await memory_manager.create_weekly_summary()
        
        logger.info("=== WEEKLY SUMMARY GENERATION COMPLETE ===")
        return {
            "status": "success",
            "message": "Weekly summary created successfully",
            "date": datetime.now().date().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating weekly summary: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate weekly summary: {str(e)}"
        )

@router.post("/api/memory/create_monthly_summary")
async def generate_monthly_summary():
    """
    Endpoint to manually trigger monthly summary creation
    """
    try:
        logger.info("=== MONTHLY SUMMARY GENERATION START ===")
        logger.info(f"Generating summary for month ending: {datetime.now().date()}")
        
        await memory_manager.create_monthly_summary()
        
        logger.info("=== MONTHLY SUMMARY GENERATION COMPLETE ===")
        return {
            "status": "success",
            "message": "Monthly summary created successfully",
            "date": datetime.now().date().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating monthly summary: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate monthly summary: {str(e)}"
        )
from fastapi import APIRouter, status
from typing import Dict

from ...services.job_store import job_store


router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "doc-converter"
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> Dict[str, str]:
    """Readiness check endpoint"""
    # Check Redis connection
    try:
        await job_store.connect()
        return {
            "status": "ready",
            "redis": "connected"
        }
    except Exception as e:
        return {
            "status": "not_ready",
            "redis": "disconnected",
            "error": str(e)
        }
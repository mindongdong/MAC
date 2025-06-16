# app/api/health.py
from fastapi import APIRouter
from app.config import settings
import logging

router = APIRouter(prefix="/api/health", tags=["health"])
logger = logging.getLogger(__name__)

@router.get("/")
async def health_check():
    """기본 헬스체크"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version
    }

@router.get("/status")
async def detailed_status():
    """상세 상태 확인"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "debug_mode": settings.debug_mode,
        "vector_store": settings.vector_store_type,
        "model": settings.claude_model
    } 
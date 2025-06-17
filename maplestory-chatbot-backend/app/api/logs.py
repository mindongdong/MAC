from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta

from app.models.user_log import UserInteractionLog, LogAnalytics, UserFeedback
from app.services.user_log_service import user_log_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/logs", tags=["logs"])

@router.get("/recent", response_model=List[UserInteractionLog])
async def get_recent_logs(
    limit: int = Query(default=50, description="조회할 로그 개수", ge=1, le=1000)
):
    """최근 로그 조회"""
    try:
        logs = await user_log_service.get_recent_logs(limit)
        return logs
    except Exception as e:
        logger.error(f"최근 로그 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="로그 조회 중 오류가 발생했습니다")

@router.get("/user/{user_id}", response_model=List[UserInteractionLog])
async def get_user_logs(
    user_id: str,
    days: int = Query(default=7, description="조회할 일수", ge=1, le=30)
):
    """특정 사용자의 로그 조회"""
    try:
        logs = await user_log_service.get_user_logs(user_id, days)
        return logs
    except Exception as e:
        logger.error(f"사용자 로그 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="사용자 로그 조회 중 오류가 발생했습니다")

@router.get("/analytics", response_model=LogAnalytics)
async def get_analytics(
    days: int = Query(default=7, description="분석할 일수", ge=1, le=90)
):
    """로그 분석 데이터 조회"""
    try:
        analytics = await user_log_service.get_analytics(days)
        return analytics
    except Exception as e:
        logger.error(f"분석 데이터 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="분석 데이터 조회 중 오류가 발생했습니다")

@router.post("/feedback")
async def add_feedback(
    log_id: str,
    user_id: str,
    rating: int = Query(..., description="평점 (1-5)", ge=1, le=5),
    feedback_text: Optional[str] = None
):
    """사용자 피드백 추가"""
    try:
        success = await user_log_service.add_feedback(log_id, user_id, rating, feedback_text)
        if success:
            return {"message": "피드백이 성공적으로 기록되었습니다"}
        else:
            raise HTTPException(status_code=500, detail="피드백 기록에 실패했습니다")
    except Exception as e:
        logger.error(f"피드백 추가 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="피드백 추가 중 오류가 발생했습니다")

@router.delete("/cleanup")
async def cleanup_old_logs(
    days_to_keep: int = Query(default=30, description="보관할 일수", ge=7, le=365)
):
    """오래된 로그 정리"""
    try:
        await user_log_service.cleanup_old_logs(days_to_keep)
        return {"message": f"{days_to_keep}일 이전 로그가 정리되었습니다"}
    except Exception as e:
        logger.error(f"로그 정리 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="로그 정리 중 오류가 발생했습니다") 
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class LogSource(str, Enum):
    """로그 소스 타입"""
    DISCORD = "discord"
    API = "api"
    WEB = "web"

class LogStatus(str, Enum):
    """로그 상태"""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"

class UserInteractionLog(BaseModel):
    """사용자 상호작용 로그 모델"""
    # 기본 정보
    log_id: Optional[str] = Field(None, description="로그 고유 ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="로그 생성 시간")
    
    # 사용자 정보
    user_id: str = Field(..., description="사용자 ID")
    session_id: str = Field(..., description="세션 ID")
    platform: LogSource = Field(..., description="플랫폼 소스")
    
    # 대화 내용
    user_message: str = Field(..., description="사용자 질문")
    bot_response: Optional[str] = Field(None, description="봇 응답")
    
    # 메타데이터
    response_time_ms: Optional[int] = Field(None, description="응답 시간 (밀리초)")
    status: LogStatus = Field(LogStatus.SUCCESS, description="처리 상태")
    error_message: Optional[str] = Field(None, description="오류 메시지")
    
    # RAG 관련 정보
    sources_used: Optional[List[Dict[str, Any]]] = Field(default=[], description="사용된 소스 문서들")
    vector_scores: Optional[List[float]] = Field(default=[], description="벡터 유사도 점수들")
    sources_count: Optional[int] = Field(0, description="검색된 소스 개수")
    
    # LLM 관련 정보
    model_used: Optional[str] = Field(None, description="사용된 모델명")
    tokens_used: Optional[int] = Field(None, description="사용된 토큰 수")
    
    # 추가 컨텍스트
    context: Optional[Dict[str, Any]] = Field(default={}, description="추가 컨텍스트 정보")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "discord_123456789",
                "session_id": "session_abc123",
                "platform": "discord",
                "user_message": "렌 직업에 대해 알려줘",
                "bot_response": "렌은 제4차 전직으로...",
                "response_time_ms": 1500,
                "status": "success",
                "sources_used": [
                    {
                        "title": "렌 가이드.md",
                        "score": 0.85,
                        "content_preview": "렌은 신규 직업..."
                    }
                ],
                "vector_scores": [0.85, 0.78, 0.72],
                "sources_count": 3,
                "model_used": "claude-3-sonnet",
                "tokens_used": 250
            }
        }

class LogAnalytics(BaseModel):
    """로그 집계 분석 모델"""
    total_interactions: int = Field(..., description="총 상호작용 수")
    unique_users: int = Field(..., description="고유 사용자 수")
    success_rate: float = Field(..., description="성공률 (0-1)")
    avg_response_time: float = Field(..., description="평균 응답 시간 (초)")
    most_common_queries: List[str] = Field(..., description="가장 많은 질문들")
    error_rate: float = Field(..., description="오류율 (0-1)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_interactions": 1500,
                "unique_users": 250,
                "success_rate": 0.95,
                "avg_response_time": 2.3,
                "most_common_queries": ["렌 직업", "아델 스킬", "보스 공략"],
                "error_rate": 0.05
            }
        }

class UserFeedback(BaseModel):
    """사용자 피드백 모델"""
    log_id: str = Field(..., description="관련 로그 ID")
    user_id: str = Field(..., description="사용자 ID")
    rating: int = Field(..., description="평점 (1-5)", ge=1, le=5)
    feedback_text: Optional[str] = Field(None, description="피드백 텍스트")
    timestamp: datetime = Field(default_factory=datetime.now, description="피드백 시간")
    
    class Config:
        json_schema_extra = {
            "example": {
                "log_id": "log_abc123",
                "user_id": "discord_123456789",
                "rating": 4,
                "feedback_text": "도움이 되었지만 더 자세한 설명이 필요해요",
                "timestamp": "2024-01-15T10:30:00"
            }
        } 
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class SourceInfo(BaseModel):
    """소스 정보 모델"""
    title: str = Field(..., description="문서 제목/소스명")
    page: str = Field(default="N/A", description="페이지 번호")
    content: str = Field(default="", description="내용 미리보기")

class ChatRequest(BaseModel):
    """채팅 요청 모델"""
    message: str = Field(..., description="사용자 메시지", min_length=1, max_length=1000)
    session_id: Optional[str] = Field(None, description="세션 ID")
    context: Optional[Dict[str, Any]] = Field(None, description="추가 컨텍스트")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "메이플스토리에서 렌 직업에 대해 알려줘",
                "session_id": "user-123",
                "context": {"user_level": "beginner"}
            }
        }

class ChatResponse(BaseModel):
    """채팅 응답 모델"""
    response: str = Field(..., description="AI 응답")
    session_id: str = Field(..., description="세션 ID")
    sources: Optional[List[SourceInfo]] = Field(default=[], description="참조된 문서 소스")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="응답 메타데이터")
    
    class Config:
        json_schema_extra = {
            "example": {
                "response": "렌은 메이플스토리의 신규 직업입니다...",
                "session_id": "user-123",
                "sources": [
                    {
                        "title": "렌 가이드.md",
                        "page": "1",
                        "content": "렌은 신규 직업으로..."
                    }
                ],
                "metadata": {
                    "confidence": 0.95,
                    "processing_time": 1.2
                }
            }
        } 
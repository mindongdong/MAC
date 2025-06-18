from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class DocumentUploadResponse(BaseModel):
    """문서 업로드 응답 모델"""
    document_id: str = Field(..., description="문서 고유 ID")
    filename: str = Field(..., description="원본 파일명")
    status: str = Field(..., description="처리 상태: processing, completed, failed")
    chunks_created: int = Field(default=0, description="생성된 청크 수")
    message: str = Field(..., description="상태 메시지")
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "12345678-1234-1234-1234-123456789012",
                "filename": "메이플스토리_가이드.pdf",
                "status": "processing",
                "chunks_created": 0,
                "message": "문서 업로드 완료. 처리 중입니다."
            }
        }

class DocumentInfo(BaseModel):
    """문서 정보 모델"""
    filename: str = Field(..., description="파일명")
    size: int = Field(..., description="파일 크기 (bytes)")
    created_at: float = Field(..., description="생성 시간 (timestamp)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "filename": "메이플스토리_가이드.pdf",
                "size": 1024000,
                "created_at": 1698876543.0
            }
        } 
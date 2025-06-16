# app/api/chat.py
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from app.models.chat import ChatRequest, ChatResponse
from app.services.langchain_service import LangChainService
from typing import AsyncGenerator
import json
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])

# 서비스 인스턴스 (실제로는 의존성 주입 사용 권장)
langchain_service = LangChainService()

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """일반 채팅 엔드포인트"""
    try:
        # 세션 ID 생성 또는 사용
        session_id = request.session_id or str(uuid.uuid4())
        
        # 채팅 처리
        result = await langchain_service.chat(
            message=request.message,
            session_id=session_id,
            context=request.context,
            stream=False
        )
        
        return ChatResponse(
            response=result["response"],
            session_id=session_id,
            sources=result["sources"],
            metadata=result["metadata"]
        )
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """스트리밍 채팅 엔드포인트"""
    async def generate() -> AsyncGenerator[str, None]:
        try:
            session_id = request.session_id or str(uuid.uuid4())
            
            # 초기 응답
            yield f"data: {json.dumps({'session_id': session_id})}\n\n"
            
            # 스트리밍 응답
            async for token in langchain_service.chat(
                message=request.message,
                session_id=session_id,
                context=request.context,
                stream=True
            ):
                yield f"data: {json.dumps({'chunk': token})}\n\n"
            
            # 완료 신호
            yield f"data: {json.dumps({'done': True})}\n\n"
            
        except Exception as e:
            logger.error(f"Stream error: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )

@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """세션 메모리 초기화"""
    langchain_service.clear_memory(session_id)
    return {"message": "Session cleared"} 
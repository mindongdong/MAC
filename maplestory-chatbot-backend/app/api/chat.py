# app/api/chat.py
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from app.models.chat import ChatRequest, ChatResponse
from app.services.langchain_service import LangChainService
from app.services.user_log_service import user_log_service
from app.models.user_log import LogSource, LogStatus
from typing import AsyncGenerator
import json
import uuid
import logging
import time

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])

# 서비스 인스턴스 (실제로는 의존성 주입 사용 권장)
langchain_service = LangChainService()

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """일반 채팅 엔드포인트"""
    start_time = time.time()
    log_id = None
    
    try:
        # 세션 ID 생성 또는 사용
        session_id = request.session_id or str(uuid.uuid4())
        
        # 사용자 정보 추출
        user_id = request.context.get("user_id", "unknown") if request.context else "unknown"
        platform_str = request.context.get("platform", "api") if request.context else "api"
        platform = LogSource.DISCORD if platform_str == "discord" else LogSource.API
        
        # 채팅 처리
        result = await langchain_service.chat(
            message=request.message,
            session_id=session_id,
            context=request.context,
            stream=False
        )
        
        # 응답 시간 계산
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # 벡터 스코어 추출 (sources에서)
        vector_scores = []
        sources_for_log = []
        if result.get("sources"):
            for source in result["sources"]:
                if hasattr(source, 'score'):
                    vector_scores.append(source.score)
                sources_for_log.append({
                    "title": getattr(source, 'title', 'Unknown'),
                    "content_preview": getattr(source, 'content', '')[:200],
                    "score": getattr(source, 'score', 0.0) if hasattr(source, 'score') else 0.0
                })
        
        # 로그 기록
        log_id = await user_log_service.log_interaction(
            user_id=user_id,
            session_id=session_id,
            platform=platform,
            user_message=request.message,
            bot_response=result["response"],
            response_time_ms=response_time_ms,
            status=LogStatus.SUCCESS,
            sources_used=sources_for_log,
            vector_scores=vector_scores,
            model_used=result["metadata"].get("model"),
            tokens_used=result["metadata"].get("tokens_used"),
            context=request.context
        )
        
        # 응답에 log_id 추가
        metadata = result["metadata"].copy()
        metadata["log_id"] = log_id
        
        return ChatResponse(
            response=result["response"],
            session_id=session_id,
            sources=result["sources"],
            metadata=metadata
        )
        
    except Exception as e:
        # 오류 로그 기록
        response_time_ms = int((time.time() - start_time) * 1000)
        user_id = request.context.get("user_id", "unknown") if request.context else "unknown"
        session_id = request.session_id or str(uuid.uuid4())
        platform_str = request.context.get("platform", "api") if request.context else "api"
        platform = LogSource.DISCORD if platform_str == "discord" else LogSource.API
        
        await user_log_service.log_interaction(
            user_id=user_id,
            session_id=session_id,
            platform=platform,
            user_message=request.message,
            bot_response=None,
            response_time_ms=response_time_ms,
            status=LogStatus.ERROR,
            error_message=str(e),
            context=request.context
        )
        
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
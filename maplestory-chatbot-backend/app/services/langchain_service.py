from langchain_anthropic import ChatAnthropic
from langchain.memory import ConversationBufferWindowMemory
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.callbacks.base import AsyncCallbackHandler
from langchain.schema import Document
from typing import Dict, List, Optional, AsyncGenerator
import asyncio
from app.config import settings
from app.chains.qa_chain import create_qa_chain
from app.services.vector_store import VectorStoreService
from app.services.embedding_service import get_embeddings
import logging

logger = logging.getLogger(__name__)

class StreamingCallbackHandler(AsyncCallbackHandler):
    """스트리밍 응답을 위한 커스텀 콜백 핸들러"""
    def __init__(self, queue: asyncio.Queue):
        self.queue = queue
    
    async def on_llm_new_token(self, token: str, **kwargs):
        await self.queue.put(token)
    
    async def on_llm_end(self, response, **kwargs):
        await self.queue.put(None)  # 종료 신호

class LangChainService:
    def __init__(self):
        self.llm = self._initialize_llm()
        self.embeddings = self._initialize_embeddings()
        self.vector_store = VectorStoreService(self.embeddings)
        self.memory_store = {}  # session_id: memory
        
    def _initialize_llm(self):
        """Claude LLM 초기화"""
        return ChatAnthropic(
            anthropic_api_key=settings.anthropic_api_key,
            model=settings.claude_model,
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
            streaming=True,
        )
    
    def _initialize_embeddings(self):
        """임베딩 모델 초기화 - 유연한 방식"""
        logger.info(f"Initializing embeddings with provider: {settings.get_embedding_provider()}")
        return get_embeddings()
    
    def get_or_create_memory(self, session_id: str) -> ConversationBufferWindowMemory:
        """세션별 메모리 관리"""
        if session_id not in self.memory_store:
            self.memory_store[session_id] = ConversationBufferWindowMemory(
                k=5,  # 최근 5개 대화 기억
                return_messages=True,
                memory_key="chat_history"
            )
        return self.memory_store[session_id]
    
    async def chat(
        self, 
        message: str, 
        session_id: str,
        context: Optional[Dict] = None,
        stream: bool = False
    ) -> Dict:
        """채팅 처리 메인 메서드"""
        try:
            # 메모리 가져오기
            memory = self.get_or_create_memory(session_id)
            
            # QA 체인 생성
            qa_chain = create_qa_chain(
                llm=self.llm,
                retriever=self.vector_store.get_retriever(),
                memory=memory
            )
            
            if stream:
                return await self._stream_chat(qa_chain, message, context)
            else:
                return await self._regular_chat(qa_chain, message, context)
                
        except Exception as e:
            logger.error(f"Chat error: {str(e)}")
            raise
    
    async def _regular_chat(self, qa_chain, message: str, context: Optional[Dict]) -> Dict:
        """일반 채팅 처리"""
        # 새로운 체인 API 사용
        response = await qa_chain.ainvoke({
            "input": message,  # "question" -> "input"으로 변경
            "chat_history": []  # 기존 메모리 대신 직접 전달
        })
        
        return {
            "response": response["answer"],
            "sources": self._extract_sources(response.get("context", [])),  # "source_documents" -> "context"로 변경
            "metadata": {
                "model": settings.claude_model,
                "tokens_used": response.get("tokens_used", 0)
            }
        }
    
    async def _stream_chat(
        self, 
        qa_chain, 
        message: str, 
        context: Optional[Dict]
    ) -> AsyncGenerator[str, None]:
        """스트리밍 채팅 처리"""
        queue = asyncio.Queue()
        callback = StreamingCallbackHandler(queue)
        
        # 비동기 태스크로 체인 실행
        task = asyncio.create_task(
            qa_chain.ainvoke(
                {"input": message, "chat_history": []},  # 새로운 API 형식
                callbacks=[callback]
            )
        )
        
        # 스트리밍 응답 생성
        while True:
            token = await queue.get()
            if token is None:
                break
            yield token
        
        # 태스크 완료 대기
        result = await task
        
        # 소스 문서 반환
        sources = self._extract_sources(result.get("context", []))  # "source_documents" -> "context"
        if sources:
            yield f"\n\n**참고 자료:**\n"
            for source in sources:
                yield f"- {source['title']}: {source['page']}\n"
    
    def _extract_sources(self, documents: List[Document]) -> List[Dict]:
        """소스 문서에서 메타데이터 추출"""
        sources = []
        for doc in documents[:3]:  # 상위 3개만
            sources.append({
                "title": doc.metadata.get("source", "Unknown"),
                "page": doc.metadata.get("page", "N/A"),
                "content": doc.page_content[:200] + "..."
            })
        return sources
    
    async def add_documents(self, documents: List[Document]):
        """문서 추가"""
        await self.vector_store.add_documents(documents)
    
    def clear_memory(self, session_id: str):
        """세션 메모리 초기화"""
        if session_id in self.memory_store:
            del self.memory_store[session_id] 
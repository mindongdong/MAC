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
from app.chains.prompts import MAPLESTORY_ANSWER_TEMPLATE
import logging
import re
import os

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
    
    def _apply_answer_template(self, answer: str) -> str:
        """답변 템플릿 적용"""
        if not settings.enable_answer_template:
            return answer
        
        # 제목 추출 (첫 번째 ## 또는 # 제목)
        title_match = re.search(r'^#{1,2}\s*(.+?)$', answer, re.MULTILINE)
        main_title = title_match.group(1) if title_match else "메이플 가이드 답변"
        
        # 구조화된 내용 (제목 제거한 나머지)
        structured_content = re.sub(r'^#{1,2}\s*.+?$', '', answer, count=1, flags=re.MULTILINE).strip()
        
        # 추가 팁 추출 (💡, 📌, ⚠️ 등의 이모지로 시작하는 부분)
        tip_pattern = r'(💡|📌|⚠️|🔥).*?(?=\n\n|$)'
        tips = re.findall(tip_pattern, structured_content, re.DOTALL)
        additional_tips = "\n".join(tips) if tips else ""
        
        # 팁 부분 제거
        for tip in tips:
            structured_content = structured_content.replace(tip, "").strip()
        
        # 마무리 문구
        closing = "더 궁금한 점이 있으시면 언제든 물어보세요! 🎮"
        
        # 템플릿 적용
        try:
            return MAPLESTORY_ANSWER_TEMPLATE.format(
                main_title=main_title,
                structured_content=structured_content,
                additional_tips=additional_tips,
                closing=closing
            )
        except Exception as e:
            logger.warning(f"Answer template application failed: {e}")
            return answer  # 실패 시 원본 반환
    
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
        """출처를 포함한 일반 채팅 처리"""
        # 새로운 체인 API 사용
        response = await qa_chain.ainvoke({
            "input": message,  # "question" -> "input"으로 변경
            "chat_history": []  # 기존 메모리 대신 직접 전달
        })
        
        # 출처 정보 추출
        sources = self._extract_sources(response.get("context", []))  # "source_documents" -> "context"로 변경
        
        # 답변에 템플릿 적용
        formatted_response = self._apply_answer_template(response["answer"])
        
        # URL이 있는 참고자료만 표시 (필터링 강화)
        sources_with_urls = [s for s in sources if s.get('has_url') and s.get('url')]
        if sources_with_urls:
            formatted_response += "\n\n## 참고자료\n"
            for source in sources_with_urls[:3]:  # 최대 3개까지만 표시
                # URL이 유효한지 확인 (http/https로 시작하는지)
                url = source['url']
                if url.startswith(('http://', 'https://', 'www.')):
                    formatted_response += f"* **{source['title']}**: {url}\n"
        
        return {
            "response": formatted_response,
            "sources": sources,
            "metadata": {
                "model": settings.claude_model,
                "tokens_used": response.get("tokens_used", 0),
                "sources_count": len(sources),
                "valid_sources_count": len(sources_with_urls),
                "system_prompt_used": settings.use_system_prompt,
                "template_applied": settings.enable_answer_template
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
        collected_response = ""
        while True:
            token = await queue.get()
            if token is None:
                break
            collected_response += token
            yield token
        
        # 태스크 완료 대기
        result = await task
        
        # 답변 템플릿 적용 (스트리밍에서는 후처리로 적용)
        if settings.enable_answer_template:
            # 현재까지 수집된 응답에 템플릿 적용
            template_applied = self._apply_answer_template(collected_response)
            # 원본과 다른 경우 차이만 전송
            if template_applied != collected_response:
                yield f"\n\n[템플릿 적용됨]"
        
        # 소스 문서 반환
        sources = self._extract_sources(result.get("context", []))  # "source_documents" -> "context"
        if sources:
            yield f"\n\n**📚 참고 자료:**\n"
            for i, source in enumerate(sources[:3], 1):
                yield f"{i}. [{source['title']}] - {source['category']}"
                if source['author'] != "Unknown":
                    yield f" (작성자: {source['author']})"
                if source['section'] != "N/A":
                    yield f" - {source['section']}"
                yield "\n"
    
    def _extract_sources(self, documents: List[Document]) -> List[Dict]:
        """개선된 소스 문서 메타데이터 추출 - URL 정보 우선 처리"""
        sources = []
        seen_sources = set()  # 중복 제거
        
        for doc in documents[:5]:  # 상위 5개로 확장
            # 고유 식별자 생성
            source_id = f"{doc.metadata.get('source', 'Unknown')}_{doc.metadata.get('chunk_index', 0)}"
            
            if source_id not in seen_sources:
                seen_sources.add(source_id)
                
                # URL 추출 우선순위:
                # 1. 메타데이터의 url 필드
                # 2. 문서 내용에서 URL 패턴 찾기 (링크 형태)
                # 3. 문서 내용에서 URL: 라벨 찾기
                url = doc.metadata.get("url", None)
                
                if not url:
                    # 문서 내용에서 마크다운 링크 패턴 찾기
                    markdown_link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
                    link_matches = re.findall(markdown_link_pattern, doc.page_content)
                    if link_matches:
                        # 첫 번째 링크 사용
                        url = link_matches[0][1]
                
                if not url:
                    # URL: 라벨 패턴 찾기
                    url_pattern = r'URL:\s*`?([^`\s\n]+)`?'
                    url_match = re.search(url_pattern, doc.page_content)
                    if url_match:
                        url = url_match.group(1)
                
                # 제목 추출 - 메타데이터의 title이나 첫 번째 헤더 사용
                title = doc.metadata.get("title", None)
                if not title:
                    # 문서 내용에서 첫 번째 헤더 찾기
                    header_pattern = r'^#{1,3}\s+(.+)$'
                    header_match = re.search(header_pattern, doc.page_content, re.MULTILINE)
                    if header_match:
                        title = header_match.group(1).strip()
                    else:
                        # 파일명에서 확장자 제거하여 제목 생성
                        source_filename = doc.metadata.get("source", "Unknown")
                        title = os.path.splitext(source_filename)[0]
                
                sources.append({
                    "title": title,
                    "category": doc.metadata.get("category", "N/A"),
                    "author": doc.metadata.get("author", "Unknown"),
                    "section": doc.metadata.get("section", "N/A"),
                    "chunk_index": doc.metadata.get("chunk_index", 0),
                    "relevance_score": doc.metadata.get("score", 0),  # 검색 점수
                    "preview": doc.page_content[:150] + "...",
                    "url": url,  # URL 정보 추가
                    "has_url": bool(url)  # URL 존재 여부 플래그
                })
        
        # 관련성 점수로 정렬
        sources.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        return sources
    
    async def add_documents(self, documents: List[Document]):
        """문서 추가"""
        await self.vector_store.add_documents(documents)
    
    def clear_memory(self, session_id: str):
        """세션 메모리 초기화"""
        if session_id in self.memory_store:
            del self.memory_store[session_id] 
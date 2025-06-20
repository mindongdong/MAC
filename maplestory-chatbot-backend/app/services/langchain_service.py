from langchain_anthropic import ChatAnthropic
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
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
import json
from difflib import SequenceMatcher
import yaml

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
        self.chat_histories: Dict[str, BaseChatMessageHistory] = {}  # 새로운 메모리 시스템
        self.retriever = None  # retriever를 별도로 저장
        
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
    
    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        """세션별 채팅 히스토리 관리 - 새로운 메모리 시스템"""
        if session_id not in self.chat_histories:
            self.chat_histories[session_id] = ChatMessageHistory()
        return self.chat_histories[session_id]
    
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
        """채팅 처리 메인 메서드 - 개선된 문서 검증 적용"""
        try:
            # retriever 초기화 (매번 새로 생성하지 않고 재사용)
            if not self.retriever:
                self.retriever = self.vector_store.get_retriever(
                    k=settings.max_retrieval_docs,
                    search_type=settings.search_type
                )
            
            # QA 체인 생성 (메모리 히스토리와 함께)
            qa_chain = create_qa_chain(
                llm=self.llm,
                retriever=self.retriever
            )
            
            # 메모리가 있는 체인으로 래핑
            chain_with_history = RunnableWithMessageHistory(
                qa_chain,
                self.get_session_history,
                input_messages_key="input",
                history_messages_key="chat_history",
            )
            
            if stream:
                return await self._stream_chat(chain_with_history, message, session_id, context)
            else:
                return await self._enhanced_regular_chat(chain_with_history, message, session_id, context)
                
        except Exception as e:
            logger.error(f"Chat error: {str(e)}")
            raise
    
    async def _enhanced_regular_chat(self, qa_chain, message: str, session_id: str, context: Optional[Dict]) -> Dict:
        """개선된 일반 채팅 처리 - 문서 검증 및 답변 후처리 포함"""
        
        # 1. 먼저 문서 검색 (retriever를 직접 사용)
        raw_documents = await self.retriever.aget_relevant_documents(message)
        
        # 2. 문서 관련성 검증
        validated_documents = self._validate_document_relevance(raw_documents, message)
        
        logger.info(f"Documents: {len(raw_documents)} -> {len(validated_documents)} (after validation)")
        
        if not validated_documents:
            # 관련 문서가 없는 경우
            return {
                "response": "죄송합니다. 제공된 문서에서는 해당 질문에 대한 관련 정보를 찾을 수 없습니다. 다른 질문을 해보시거나 더 구체적으로 질문해 주세요.",
                "sources": [],
                "metadata": {
                    "model": settings.claude_model,
                    "tokens_used": 0,
                    "sources_count": 0,
                    "valid_sources_count": 0,
                    "system_prompt_used": settings.use_system_prompt,
                    "template_applied": settings.enable_answer_template,
                    "documents_filtered": len(raw_documents),
                    "relevance_check": "no_relevant_documents"
                }
            }
        
        # 3. 검증된 문서로 QA 수행 (세션 히스토리와 함께)
        response = await qa_chain.ainvoke(
            {"input": message},
            config={"configurable": {"session_id": session_id}}
        )
        
        # 4. 답변 후처리 검증
        raw_answer = response["answer"]
        validated_answer = self._validate_response(raw_answer, validated_documents, message)
        
        # 5. 출처 정보 추출
        sources = self._extract_sources(validated_documents)
        
        # 6. 답변에 템플릿 적용
        formatted_response = self._apply_answer_template(validated_answer)
        
        # 7. 참고자료를 URL만 출력하도록 간소화
        sources_with_urls = [s for s in sources if s.get('has_url') and s.get('url')]
        if sources_with_urls and settings.require_url_in_sources:
            formatted_response += "\n\n## 📚 참고자료\n"
            for source in sources_with_urls[:settings.max_reference_sources]:
                url = source.get('url', '')
                
                if url.startswith(('http://', 'https://', 'www.')):
                    # 간단한 형식: URL만 표시
                    formatted_response += f"* {url}\n"
        
        return {
            "response": formatted_response,
            "sources": sources,
            "metadata": {
                "model": settings.claude_model,
                "tokens_used": response.get("tokens_used", 0),
                "sources_count": len(sources),
                "valid_sources_count": len(sources_with_urls),
                "system_prompt_used": settings.use_system_prompt,
                "template_applied": settings.enable_answer_template,
                "documents_filtered": len(raw_documents) - len(validated_documents),
                "original_documents": len(raw_documents),
                "validated_documents": len(validated_documents),
                "relevance_check": "passed",
                "response_length": len(formatted_response)
            }
        }
    
    async def _stream_chat(
        self, 
        qa_chain, 
        message: str, 
        session_id: str,
        context: Optional[Dict]
    ) -> AsyncGenerator[str, None]:
        """스트리밍 채팅 처리"""
        try:
            # 스트리밍을 위한 큐 생성
            queue = asyncio.Queue()
            
            # 스트리밍 콜백 핸들러 생성
            streaming_handler = StreamingCallbackHandler(queue)
            
            # 스트리밍 응답 생성
            async def stream_response():
                try:
                    response = await qa_chain.ainvoke(
                        {"input": message},
                        config={
                            "configurable": {"session_id": session_id},
                            "callbacks": [streaming_handler]
                        }
                    )
                except Exception as e:
                    await queue.put(f"오류가 발생했습니다: {str(e)}")
                    await queue.put(None)
            
            # 백그라운드에서 응답 생성 시작
            task = asyncio.create_task(stream_response())
            
            # 스트리밍 토큰을 순차적으로 yield
            while True:
                token = await queue.get()
                if token is None:  # 종료 신호
                    break
                yield token
            
            # 태스크 완료 대기
            await task
            
        except Exception as e:
            logger.error(f"Streaming chat error: {str(e)}")
            yield f"스트리밍 중 오류가 발생했습니다: {str(e)}"
    
    def _extract_sources(self, documents: List[Document]) -> List[Dict]:
        """개선된 소스 문서 메타데이터 추출 - sources 메타데이터 파싱 포함"""
        sources = []
        seen_sources = set()  # 중복 제거
        
        for doc in documents[:5]:  # 상위 5개로 확장
            # 고유 식별자 생성
            source_id = f"{doc.metadata.get('source', 'Unknown')}_{doc.metadata.get('chunk_index', 0)}"
            
            if source_id not in seen_sources:
                seen_sources.add(source_id)
                
                # 문서에서 sources 메타데이터 파싱
                sources_info = self._parse_sources_from_document(doc.page_content)
                
                # URL, title, creator 추출
                url = None
                creator = None
                doc_title = None
                
                # 1. 파싱된 sources 정보 사용 (우선순위)
                if sources_info:
                    first_source = sources_info[0]  # 첫 번째 source 사용
                    url = first_source.get('url')
                    creator = first_source.get('creator')
                    doc_title = first_source.get('title')
                
                # 2. 메타데이터에서 대체값 찾기
                if not url:
                    url = doc.metadata.get("url", None)
                if not creator:
                    creator = doc.metadata.get("author", None)
                if not doc_title:
                    doc_title = doc.metadata.get("title", None)
                
                # 3. 문서 내용에서 URL 패턴 찾기 (fallback)
                if not url:
                    markdown_link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
                    link_matches = re.findall(markdown_link_pattern, doc.page_content)
                    if link_matches:
                        url = link_matches[0][1]
                
                if not url:
                    url_pattern = r'URL:\s*`?([^`\s\n]+)`?'
                    url_match = re.search(url_pattern, doc.page_content)
                    if url_match:
                        url = url_match.group(1)
                
                # 4. 제목 추출 (fallback)
                if not doc_title:
                    header_pattern = r'^#{1,3}\s+(.+)$'
                    header_match = re.search(header_pattern, doc.page_content, re.MULTILINE)
                    if header_match:
                        doc_title = header_match.group(1).strip()
                    else:
                        source_filename = doc.metadata.get("source", "Unknown")
                        doc_title = os.path.splitext(source_filename)[0]
                
                sources.append({
                    "title": doc_title,
                    "creator": creator or "Unknown",
                    "category": doc.metadata.get("category", "N/A"),
                    "author": doc.metadata.get("author", creator or "Unknown"),
                    "section": doc.metadata.get("section", "N/A"),
                    "chunk_index": doc.metadata.get("chunk_index", 0),
                    "relevance_score": doc.metadata.get("score", 0),
                    "preview": doc.page_content[:150] + "...",
                    "url": url,
                    "has_url": bool(url)
                })
        
        # 관련성 점수로 정렬
        sources.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        return sources
    
    def _parse_sources_from_document(self, content: str) -> List[Dict]:
        """문서 내용에서 sources 메타데이터 파싱"""
        try:
            # YAML front matter 찾기
            yaml_pattern = r'^---\s*\n(.*?)\n---'
            yaml_match = re.search(yaml_pattern, content, re.DOTALL | re.MULTILINE)
            
            if yaml_match:
                yaml_content = yaml_match.group(1)
                try:
                    # YAML 파싱
                    metadata = yaml.safe_load(yaml_content)
                    if isinstance(metadata, dict) and 'sources' in metadata:
                        sources_list = metadata['sources']
                        if isinstance(sources_list, list):
                            parsed_sources = []
                            for source in sources_list:
                                if isinstance(source, dict):
                                    parsed_sources.append({
                                        'url': source.get('url', ''),
                                        'title': source.get('title', ''),
                                        'creator': source.get('creator', '')
                                    })
                            return parsed_sources
                except yaml.YAMLError:
                    logger.debug("YAML parsing failed for document sources")
            
            return []
            
        except Exception as e:
            logger.debug(f"Error parsing sources from document: {e}")
            return []
    
    async def add_documents(self, documents: List[Document]):
        """문서 추가"""
        await self.vector_store.add_documents(documents)
    
    def clear_memory(self, session_id: str):
        """특정 세션의 메모리 초기화"""
        if session_id in self.chat_histories:
            self.chat_histories[session_id].clear()
            logger.info(f"Cleared memory for session: {session_id}")
    
    def _extract_keywords(self, query: str) -> List[str]:
        """질문에서 핵심 키워드 추출"""
        # 메이플스토리 특화 키워드 패턴
        maple_patterns = [
            r'[가-힣]+\s*(?:보스|스킬|큐브|코인|포인트|이벤트|직업|클래스)',
            r'(?:하드|이지|헬|카오스)\s*[가-힣]+',
            r'[가-힣]+\s*(?:샵|상점)',
            r'챌린저스?\s*[가-힣]*',
            r'[가-힣]{2,}(?:렌|제로|카데나|일리움|호영|아델|카인|라라|아크)',
        ]
        
        keywords = []
        
        # 패턴 매칭으로 키워드 추출
        for pattern in maple_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            keywords.extend(matches)
        
        # 일반 명사 추출 (2글자 이상 한글)
        general_keywords = re.findall(r'[가-힣]{2,}', query)
        keywords.extend(general_keywords)
        
        # 중복 제거 및 소문자 변환
        unique_keywords = list(set([kw.strip().lower() for kw in keywords if len(kw.strip()) > 1]))
        
        return unique_keywords[:10]  # 최대 10개로 제한
    
    def _calculate_title_relevance(self, title: str, query: str) -> float:
        """문서 제목과 질문의 관련성 점수 계산"""
        if not title:
            return 0.0
            
        title_lower = title.lower()
        query_lower = query.lower()
        
        # 직접 매칭 점수
        direct_match = SequenceMatcher(None, title_lower, query_lower).ratio()
        
        # 키워드 매칭 점수
        query_keywords = self._extract_keywords(query)
        title_keywords = self._extract_keywords(title)
        
        keyword_matches = 0
        for q_kw in query_keywords:
            for t_kw in title_keywords:
                if q_kw in t_kw or t_kw in q_kw:
                    keyword_matches += 1
                    break
        
        keyword_score = keyword_matches / max(len(query_keywords), 1)
        
        # 최종 점수 (직접 매칭 70% + 키워드 매칭 30%)
        final_score = (direct_match * 0.7) + (keyword_score * 0.3)
        
        return min(final_score, 1.0)
    
    def _validate_document_relevance(self, documents: List[Document], query: str) -> List[Document]:
        """문서 관련성 검증 및 필터링"""
        if not settings.enable_document_filtering:
            logger.info(f"Document filtering disabled - returning {len(documents)} documents as-is")
            return documents[:settings.max_reference_sources]
        
        validated_docs = []
        query_keywords = self._extract_keywords(query)
        
        for doc in documents:
            # 1. 제목 관련성 검사
            title = doc.metadata.get('title', '')
            title_relevance = self._calculate_title_relevance(title, query)
            
            # 2. 내용 키워드 매칭 검사
            content_lower = doc.page_content.lower()
            keyword_matches = sum(1 for kw in query_keywords if kw in content_lower)
            content_relevance = keyword_matches / max(len(query_keywords), 1)
            
            # 3. 메타데이터 기반 관련성 검사
            category = doc.metadata.get('category', '')
            class_name = doc.metadata.get('class', '')
            
            # 직업명이 질문에 있는 경우 해당 직업 문서 우선
            metadata_bonus = 0.0
            for keyword in query_keywords:
                if keyword in class_name.lower():
                    metadata_bonus += 0.3
                if keyword in category.lower():
                    metadata_bonus += 0.2
            
            # 최종 관련성 점수 계산
            final_relevance = (title_relevance * 0.4) + (content_relevance * 0.4) + metadata_bonus
            
            # 임계값 이상인 문서만 포함
            if final_relevance >= 0.3:  # 30% 이상 관련성
                doc.metadata['relevance_score'] = final_relevance
                validated_docs.append(doc)
                
                logger.debug(f"Document accepted: {title} (relevance: {final_relevance:.2f})")
            else:
                logger.debug(f"Document filtered out: {title} (relevance: {final_relevance:.2f})")
        
        # 관련성 점수 순으로 정렬
        validated_docs.sort(key=lambda x: x.metadata.get('relevance_score', 0), reverse=True)
        
        return validated_docs[:settings.max_reference_sources]
    
    def _validate_response(self, response: str, documents: List[Document], query: str) -> str:
        """답변 후처리 검증 - 할루시네이션 방지"""
        if not settings.enable_response_validation:
            return response
        
        validated_response = response
        
        # 1. 의심스러운 패턴 검사
        suspicious_patterns = [
            (r'\d+개(?:\s*(?:의|를|을|이|가))?', '구체적 수량'),
            (r'[가-힣]+\s*큐브', '큐브 아이템'),
            (r'[가-힣]+\s*스킬', '스킬명'),
            (r'\d+(?:,\d{3})*\s*(?:메소|포인트|점수)', '수치 정보'),
            (r'(?:대략|약|수십억|다수|여러|일반적으로|보통)', '모호한 표현'),
        ]
        
        warnings = []
        
        for pattern, description in suspicious_patterns:
            matches = re.findall(pattern, validated_response, re.IGNORECASE)
            for match in matches:
                # 문서에서 해당 내용 확인
                if not self._verify_in_documents(match, documents):
                    # 모호한 표현은 제거
                    if description == '모호한 표현':
                        validated_response = re.sub(pattern, '', validated_response, flags=re.IGNORECASE)
                        warnings.append(f"모호한 표현 '{match}' 제거됨")
                    else:
                        warnings.append(f"검증되지 않은 {description}: '{match}'")
        
        # 2. 관련 없는 문서 기반 답변 검사
        query_keywords = self._extract_keywords(query)
        response_keywords = self._extract_keywords(validated_response)
        
        # 답변의 키워드가 질문과 너무 동떨어진 경우
        keyword_overlap = len(set(query_keywords) & set(response_keywords))
        if keyword_overlap == 0 and len(query_keywords) > 0:
            warnings.append("답변이 질문과 관련성이 낮을 수 있음")
        
        # 경고가 있으면 로그에 기록
        if warnings:
            logger.warning(f"Response validation warnings: {'; '.join(warnings)}")
        
        return validated_response.strip()
    
    def _verify_in_documents(self, text: str, documents: List[Document]) -> bool:
        """텍스트가 참고 문서에 포함되어 있는지 확인"""
        text_lower = text.lower().strip()
        
        for doc in documents:
            if text_lower in doc.page_content.lower():
                return True
            
            # 메타데이터에서도 확인
            for key, value in doc.metadata.items():
                if isinstance(value, str) and text_lower in value.lower():
                    return True
        
        return False 
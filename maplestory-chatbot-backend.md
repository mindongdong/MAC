# 메이플스토리 챗봇 백엔드 구현 가이드

## 프로젝트 구조

```
maplestory-chatbot-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 메인 애플리케이션
│   ├── config.py               # 환경 설정
│   ├── models/                 # Pydantic 모델
│   │   ├── __init__.py
│   │   ├── chat.py             # 채팅 요청/응답 모델
│   │   └── document.py         # 문서 모델
│   ├── api/                    # API 라우터
│   │   ├── __init__.py
│   │   ├── chat.py             # 채팅 엔드포인트
│   │   ├── documents.py        # 문서 관리 엔드포인트
│   │   └── health.py           # 헬스체크
│   ├── services/               # 비즈니스 로직
│   │   ├── __init__.py
│   │   ├── langchain_service.py   # LangChain 핵심 서비스
│   │   ├── vector_store.py        # 벡터 스토어 관리
│   │   └── document_processor.py  # 문서 처리
│   ├── chains/                 # LangChain 체인 정의
│   │   ├── __init__.py
│   │   ├── qa_chain.py         # Q&A 체인
│   │   └── prompts.py          # 프롬프트 템플릿
│   └── utils/                  # 유틸리티
│       ├── __init__.py
│       ├── korean_splitter.py  # 한국어 텍스트 분할
│       └── cache.py            # 캐싱 유틸리티
├── data/                       # 데이터 폴더
│   ├── pdfs/                   # PDF 문서
│   └── processed/              # 처리된 문서
├── tests/                      # 테스트
│   ├── __init__.py
│   ├── test_api.py
│   └── test_chains.py
├── scripts/                    # 스크립트
│   ├── ingest_documents.py     # 문서 수집 스크립트
│   └── setup_vectorstore.py    # 벡터스토어 초기화
├── requirements.txt
├── .env.example
├── docker-compose.yml
└── README.md
```

## 1. 환경 설정 (config.py)

```python
# app/config.py
from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # API Keys
    anthropic_api_key: str
    openai_api_key: Optional[str] = None  # 임베딩용
    
    # Claude 설정
    claude_model: str = "claude-3-sonnet-20240229"
    max_tokens: int = 4096
    temperature: float = 0.7
    
    # FastAPI 설정
    app_name: str = "메이플스토리 AI 어시스턴트"
    app_version: str = "1.0.0"
    debug_mode: bool = False
    
    # Vector Store 설정
    vector_store_type: str = "qdrant"  # qdrant, chroma, faiss
    qdrant_url: Optional[str] = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None
    collection_name: str = "maplestory_docs"
    
    # 임베딩 설정
    embedding_model: str = "text-embedding-ada-002"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    # 캐싱 설정
    redis_url: Optional[str] = "redis://localhost:6379"
    cache_ttl: int = 3600  # 1시간
    
    # 보안 설정
    cors_origins: list = ["http://localhost:3000", "https://yourdomain.com"]
    rate_limit_per_minute: int = 10
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

## 2. Pydantic 모델 정의

```python
# app/models/chat.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class ChatMessage(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)

class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    context: Optional[Dict] = None
    stream: bool = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "리부트 월드에서 나이트로드 육성하는 방법 알려줘",
                "user_id": "user123",
                "stream": True
            }
        }

class ChatResponse(BaseModel):
    response: str
    session_id: str
    sources: List[Dict] = []
    metadata: Dict = {}
    timestamp: datetime = Field(default_factory=datetime.now)

class StreamingChatResponse(BaseModel):
    chunk: str
    is_final: bool = False
    sources: Optional[List[Dict]] = None
```

## 3. LangChain 서비스 구현

```python
# app/services/langchain_service.py
from langchain_anthropic import ChatAnthropic
from langchain_openai import OpenAIEmbeddings
from langchain.memory import ConversationBufferWindowMemory
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.callbacks.base import AsyncCallbackHandler
from langchain.schema import Document
from typing import Dict, List, Optional, AsyncGenerator
import asyncio
from app.config import settings
from app.chains.qa_chain import create_qa_chain
from app.services.vector_store import VectorStoreService
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
        """임베딩 모델 초기화"""
        return OpenAIEmbeddings(
            openai_api_key=settings.openai_api_key,
            model=settings.embedding_model
        )
    
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
        response = await qa_chain.ainvoke({
            "question": message,
            "context": context or {}
        })
        
        return {
            "response": response["answer"],
            "sources": self._extract_sources(response.get("source_documents", [])),
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
                {"question": message, "context": context or {}},
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
        sources = self._extract_sources(result.get("source_documents", []))
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
```

## 4. 벡터 스토어 서비스

```python
# app/services/vector_store.py
from langchain_community.vectorstores import Qdrant, Chroma, FAISS
from langchain.schema import Document
from typing import List, Optional
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class VectorStoreService:
    def __init__(self, embeddings):
        self.embeddings = embeddings
        self.vector_store = self._initialize_vector_store()
    
    def _initialize_vector_store(self):
        """벡터 스토어 초기화"""
        if settings.vector_store_type == "qdrant":
            from qdrant_client import QdrantClient
            
            client = QdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key
            )
            
            return Qdrant(
                client=client,
                collection_name=settings.collection_name,
                embeddings=self.embeddings
            )
        
        elif settings.vector_store_type == "chroma":
            return Chroma(
                collection_name=settings.collection_name,
                embedding_function=self.embeddings,
                persist_directory="./data/chroma"
            )
        
        elif settings.vector_store_type == "faiss":
            # FAISS는 로컬에서만 사용
            try:
                return FAISS.load_local(
                    "./data/faiss", 
                    self.embeddings
                )
            except:
                return FAISS.from_texts(
                    ["초기화"], 
                    self.embeddings
                )
        
        else:
            raise ValueError(f"Unknown vector store type: {settings.vector_store_type}")
    
    def get_retriever(self, k: int = 5):
        """리트리버 반환"""
        return self.vector_store.as_retriever(
            search_kwargs={"k": k}
        )
    
    async def add_documents(self, documents: List[Document]):
        """문서 추가"""
        try:
            await self.vector_store.aadd_documents(documents)
            logger.info(f"Added {len(documents)} documents to vector store")
        except Exception as e:
            logger.error(f"Error adding documents: {str(e)}")
            raise
    
    async def search(self, query: str, k: int = 5) -> List[Document]:
        """유사도 검색"""
        return await self.vector_store.asimilarity_search(query, k=k)
```

## 5. QA 체인 구성

```python
# app/chains/qa_chain.py
from langchain.chains import ConversationalRetrievalChain
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from app.chains.prompts import MAPLESTORY_QA_PROMPT, CONDENSE_PROMPT

def create_qa_chain(llm, retriever, memory):
    """메이플스토리 특화 QA 체인 생성"""
    
    # 문서 기반 QA 체인
    doc_chain = load_qa_chain(
        llm,
        chain_type="stuff",
        prompt=MAPLESTORY_QA_PROMPT
    )
    
    # 대화형 검색 체인
    qa_chain = ConversationalRetrievalChain(
        retriever=retriever,
        combine_docs_chain=doc_chain,
        memory=memory,
        return_source_documents=True,
        verbose=True,
        condense_question_prompt=CONDENSE_PROMPT
    )
    
    return qa_chain
```

```python
# app/chains/prompts.py
from langchain.prompts import PromptTemplate

MAPLESTORY_QA_PROMPT = PromptTemplate(
    template="""당신은 메이플스토리 전문 가이드 AI 어시스턴트입니다. 
다음 규칙을 따라 응답해주세요:

1. 항상 정확하고 최신 정보를 제공합니다
2. 게임 용어는 한국어로 사용하되, 영어 약어는 병기합니다
3. 초보자도 이해할 수 있도록 친절하게 설명합니다
4. 단계별 가이드가 필요한 경우 번호를 매겨 설명합니다
5. 관련된 팁이나 주의사항이 있다면 함께 제공합니다

참고 문서:
{context}

질문: {question}

답변:""",
    input_variables=["context", "question"]
)

CONDENSE_PROMPT = PromptTemplate(
    template="""다음 대화 내용과 후속 질문이 주어졌을 때, 후속 질문을 독립적인 질문으로 다시 작성하세요.
대화 내용에서 필요한 컨텍스트를 포함시켜 주세요.

대화 내용:
{chat_history}

후속 질문: {question}

독립적인 질문:""",
    input_variables=["chat_history", "question"]
)
```

## 6. FastAPI 라우터 구현

```python
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
```

## 7. 문서 처리 서비스

```python
# app/services/document_processor.py
from langchain.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.utils.korean_splitter import KoreanTextSplitter
from typing import List
from langchain.schema import Document
import os
import logging

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        self.korean_splitter = KoreanTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
    
    async def process_pdf(self, file_path: str) -> List[Document]:
        """PDF 파일 처리"""
        try:
            loader = PyPDFLoader(file_path)
            pages = loader.load()
            
            # 각 페이지를 청크로 분할
            documents = []
            for page in pages:
                chunks = self.korean_splitter.split_text(page.page_content)
                for i, chunk in enumerate(chunks):
                    doc = Document(
                        page_content=chunk,
                        metadata={
                            "source": os.path.basename(file_path),
                            "page": page.metadata.get("page", 0),
                            "chunk": i,
                            "total_chunks": len(chunks)
                        }
                    )
                    documents.append(doc)
            
            logger.info(f"Processed {file_path}: {len(documents)} chunks")
            return documents
            
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {str(e)}")
            raise
    
    async def process_directory(self, directory: str) -> List[Document]:
        """디렉토리의 모든 PDF 처리"""
        all_documents = []
        
        for filename in os.listdir(directory):
            if filename.endswith('.pdf'):
                file_path = os.path.join(directory, filename)
                documents = await self.process_pdf(file_path)
                all_documents.extend(documents)
        
        return all_documents
```

## 8. 한국어 텍스트 분할기

```python
# app/utils/korean_splitter.py
from typing import List
import re

class KoreanTextSplitter:
    """한국어 특화 텍스트 분할기"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # 한국어 문장 종결 패턴
        self.sentence_endings = re.compile(
            r'[.!?。]\s*|[\n]{2,}'
        )
    
    def split_text(self, text: str) -> List[str]:
        """텍스트를 의미 있는 청크로 분할"""
        # 문장 단위로 분할
        sentences = self.sentence_endings.split(text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # 청크 생성
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # 현재 청크 + 새 문장이 크기 제한 이내인 경우
            if len(current_chunk) + len(sentence) <= self.chunk_size:
                current_chunk += sentence + " "
            else:
                # 현재 청크 저장
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # 새 청크 시작 (오버랩 포함)
                if chunks and self.chunk_overlap > 0:
                    # 이전 청크의 마지막 부분 가져오기
                    overlap_text = chunks[-1][-self.chunk_overlap:]
                    current_chunk = overlap_text + " " + sentence + " "
                else:
                    current_chunk = sentence + " "
        
        # 마지막 청크 저장
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
```

## 9. 메인 애플리케이션

```python
# app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time
from app.config import settings
from app.api import chat, documents, health

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작 시
    logger.info("Starting MapleStory Chatbot Backend...")
    # 여기서 벡터 스토어 초기화 등 수행 가능
    yield
    # 종료 시
    logger.info("Shutting down...")

# FastAPI 앱 생성
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 요청 시간 미들웨어
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# 에러 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# 라우터 등록
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(health.router)

# 루트 엔드포인트
@app.get("/")
async def root():
    return {
        "message": "메이플스토리 AI 어시스턴트 API",
        "version": settings.app_version,
        "docs": "/docs"
    }
```

## 10. Docker 설정

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - QDRANT_URL=http://qdrant:6333
      - REDIS_URL=redis://redis:6379
    depends_on:
      - qdrant
      - redis
    volumes:
      - ./data:/app/data

  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  qdrant_data:
  redis_data:
```

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 복사
COPY . .

# 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 11. Requirements.txt

```txt
# requirements.txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
pydantic-settings==2.1.0

# LangChain
langchain==0.1.0
langchain-anthropic==0.0.1
langchain-openai==0.0.5
langchain-community==0.0.10

# Vector Stores
qdrant-client==1.7.0
chromadb==0.4.22
faiss-cpu==1.7.4

# Document Processing
pypdf==3.17.4
python-multipart==0.0.6

# Korean NLP
kiwipiepy==0.16.1
konlpy==0.6.0

# Utilities
redis==5.0.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
httpx==0.25.2

# Testing
pytest==7.4.4
pytest-asyncio==0.23.3
```

## 12. 환경 변수 예시

```env
# .env.example
# API Keys
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Claude Settings
CLAUDE_MODEL=claude-3-sonnet-20240229
MAX_TOKENS=4096
TEMPERATURE=0.7

# Vector Store
VECTOR_STORE_TYPE=qdrant
QDRANT_URL=http://localhost:6333
COLLECTION_NAME=maplestory_docs

# Redis
REDIS_URL=redis://localhost:6379

# Security
CORS_ORIGINS=["http://localhost:3000"]
RATE_LIMIT_PER_MINUTE=10
```

## 13. 문서 수집 스크립트

```python
# scripts/ingest_documents.py
import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.document_processor import DocumentProcessor
from app.services.langchain_service import LangChainService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """PDF 문서를 벡터 스토어에 수집"""
    processor = DocumentProcessor()
    service = LangChainService()
    
    # PDF 디렉토리 처리
    pdf_dir = "./data/pdfs"
    documents = await processor.process_directory(pdf_dir)
    
    logger.info(f"Total documents: {len(documents)}")
    
    # 벡터 스토어에 추가
    await service.add_documents(documents)
    
    logger.info("Document ingestion completed!")

if __name__ == "__main__":
    asyncio.run(main())
```

## 사용 방법

### 1. 환경 설정
```bash
# .env 파일 생성
cp .env.example .env
# API 키 설정
```

### 2. 의존성 설치
```bash
pip install -r requirements.txt
```

### 3. 벡터 스토어 실행
```bash
docker-compose up -d qdrant redis
```

### 4. 문서 수집
```bash
python scripts/ingest_documents.py
```

### 5. 서버 실행
```bash
uvicorn app.main:app --reload
```

### 6. API 테스트
```bash
# 일반 채팅
curl -X POST "http://localhost:8000/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{"message": "리부트 월드에서 메소 파밍하는 방법 알려줘"}'

# 스트리밍 채팅
curl -X POST "http://localhost:8000/api/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{"message": "보스 레이드 순서 추천해줘", "stream": true}'
```

## 커스터마이징 가이드

### 1. 프롬프트 수정
`app/chains/prompts.py`에서 시스템 프롬프트를 수정하여 챗봇의 성격과 응답 스타일을 변경할 수 있습니다.

### 2. 임베딩 모델 변경
한국어 성능을 높이려면:
```python
# multilingual-e5-large 사용
from sentence_transformers import SentenceTransformer
embeddings = SentenceTransformer('intfloat/multilingual-e5-large')
```

### 3. 캐싱 전략 추가
```python
# app/utils/cache.py
from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
def get_cached_response(query_hash: str):
    # Redis에서 캐시된 응답 조회
    pass
```

### 4. 메트릭 수집
```python
# Prometheus 메트릭 추가
from prometheus_client import Counter, Histogram

chat_requests = Counter('chat_requests_total', 'Total chat requests')
response_time = Histogram('response_time_seconds', 'Response time')
```

이 구현은 프로덕션 준비가 된 확장 가능한 백엔드를 제공합니다. 필요에 따라 각 컴포넌트를 수정하고 확장할 수 있습니다.
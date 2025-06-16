# 기존 프로젝트에 Qdrant RAG 통합 가이드

## 1. 현재 상태 확인 및 수정 필요 파일

기존 백엔드 구조에서 수정이 필요한 파일들:
- `app/services/vector_store.py` - Qdrant 초기화 로직 보완
- `app/services/document_processor.py` - PDF 처리 로직 개선
- `scripts/ingest_documents.py` - 문서 수집 스크립트 개선
- `.env` - 환경 변수 설정

## 2. 단계별 통합 가이드

### Step 1: Qdrant 실행 확인

```bash
# 1. Docker로 Qdrant 실행
docker run -p 6333:6333 -v $(pwd)/qdrant_data:/qdrant/storage qdrant/qdrant

# 2. Qdrant가 실행 중인지 확인
curl http://localhost:6333/collections
# 빈 배열 [] 이 나오면 정상
```

### Step 2: 환경 변수 설정 (.env)

`.env` 파일에 다음 내용이 있는지 확인하고 수정:

```env
# API Keys
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here  # 임베딩용

# Vector Store
VECTOR_STORE_TYPE=qdrant
QDRANT_URL=http://localhost:6333
COLLECTION_NAME=maplestory_docs

# 임베딩 설정
EMBEDDING_MODEL=text-embedding-ada-002
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

### Step 3: Vector Store 서비스 수정

`app/services/vector_store.py`를 다음과 같이 수정:

```python
# app/services/vector_store.py
from langchain_community.vectorstores import Qdrant
from langchain.schema import Document
from typing import List, Optional
from app.config import settings
import logging
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

logger = logging.getLogger(__name__)

class VectorStoreService:
    def __init__(self, embeddings):
        self.embeddings = embeddings
        self.client = None
        self.vector_store = self._initialize_vector_store()
    
    def _initialize_vector_store(self):
        """벡터 스토어 초기화"""
        if settings.vector_store_type == "qdrant":
            # Qdrant 클라이언트 초기화
            self.client = QdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key
            )
            
            # 컬렉션 존재 여부 확인 및 생성
            self._ensure_collection_exists()
            
            # LangChain Qdrant 래퍼 반환
            return Qdrant(
                client=self.client,
                collection_name=settings.collection_name,
                embeddings=self.embeddings
            )
        else:
            raise ValueError(f"Unknown vector store type: {settings.vector_store_type}")
    
    def _ensure_collection_exists(self):
        """컬렉션이 없으면 생성"""
        try:
            # 컬렉션 존재 확인
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if settings.collection_name not in collection_names:
                # 임베딩 차원 확인
                test_embedding = self.embeddings.embed_query("test")
                vector_size = len(test_embedding)
                
                # 컬렉션 생성
                self.client.create_collection(
                    collection_name=settings.collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {settings.collection_name}")
            else:
                logger.info(f"Collection already exists: {settings.collection_name}")
                
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {str(e)}")
            raise
    
    def get_retriever(self, k: int = 5, search_type: str = "similarity"):
        """리트리버 반환"""
        search_kwargs = {"k": k}
        
        # MMR 검색인 경우 추가 파라미터
        if search_type == "mmr":
            search_kwargs.update({
                "fetch_k": k * 4,  # k의 4배 가져와서 다양성 확보
                "lambda_mult": 0.5  # 다양성 vs 관련성 균형
            })
        
        return self.vector_store.as_retriever(
            search_type=search_type,
            search_kwargs=search_kwargs
        )
    
    async def add_documents(self, documents: List[Document]):
        """문서 추가"""
        try:
            # 동기 메서드 사용 (LangChain Qdrant는 async를 완전히 지원하지 않음)
            self.vector_store.add_documents(documents)
            logger.info(f"Added {len(documents)} documents to vector store")
        except Exception as e:
            logger.error(f"Error adding documents: {str(e)}")
            raise
    
    async def search(self, query: str, k: int = 5) -> List[Document]:
        """유사도 검색"""
        # 동기 메서드 사용
        return self.vector_store.similarity_search(query, k=k)
    
    def get_collection_info(self):
        """컬렉션 정보 반환"""
        if self.client:
            collection_info = self.client.get_collection(settings.collection_name)
            return {
                "name": collection_info.name,
                "vectors_count": collection_info.vectors_count,
                "points_count": collection_info.points_count,
                "status": collection_info.status
            }
        return None
```

### Step 4: Document Processor 개선

`app/services/document_processor.py`를 다음과 같이 수정:

```python
# app/services/document_processor.py
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List
from langchain.schema import Document
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ".", "!", "?", "。", " ", ""],
            length_function=len
        )
    
    async def process_pdf(self, file_path: str) -> List[Document]:
        """PDF 파일 처리 - 개선된 버전"""
        try:
            # PDF 로드
            loader = PyPDFLoader(file_path)
            pages = loader.load()
            
            logger.info(f"Loaded PDF: {file_path} ({len(pages)} pages)")
            
            # 전체 문서를 하나로 합치기 (페이지 경계를 무시하고 자연스러운 청킹을 위해)
            full_text = "\n\n".join([page.page_content for page in pages])
            
            # 메타데이터 준비
            filename = os.path.basename(file_path)
            base_metadata = {
                "source": filename,
                "total_pages": len(pages),
                "processed_at": datetime.now().isoformat()
            }
            
            # 파일명에서 자동 태깅
            base_metadata.update(self._extract_metadata_from_filename(filename))
            
            # 텍스트 분할
            chunks = self.text_splitter.split_text(full_text)
            
            # Document 객체 생성
            documents = []
            for i, chunk in enumerate(chunks):
                metadata = base_metadata.copy()
                metadata.update({
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "chunk_size": len(chunk)
                })
                
                # 첫 번째 청크에서 추가 메타데이터 추출 시도
                if i == 0:
                    metadata.update(self._extract_metadata_from_content(chunk))
                
                doc = Document(
                    page_content=chunk,
                    metadata=metadata
                )
                documents.append(doc)
            
            logger.info(f"Processed {file_path}: {len(documents)} chunks created")
            return documents
            
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {str(e)}")
            raise
    
    def _extract_metadata_from_filename(self, filename: str) -> dict:
        """파일명에서 메타데이터 추출"""
        metadata = {}
        
        # 파일명 패턴 분석 (예: "나이트로드_5차스킬_가이드.pdf")
        filename_lower = filename.lower()
        
        # 직업 검출
        classes = ["나이트로드", "보우마스터", "아크메이지", "비숍", "팬텀", "섀도어"]
        for class_name in classes:
            if class_name in filename:
                metadata["class"] = class_name
                break
        
        # 콘텐츠 타입 검출
        if "5차" in filename:
            metadata["content_type"] = "5차스킬"
        elif "보스" in filename:
            metadata["content_type"] = "보스공략"
        elif "사냥터" in filename:
            metadata["content_type"] = "사냥터가이드"
        elif "강화" in filename:
            metadata["content_type"] = "강화가이드"
        
        # 서버 타입 검출
        if "리부트" in filename:
            metadata["server_type"] = "리부트"
        elif "일반" in filename:
            metadata["server_type"] = "일반"
        
        return metadata
    
    def _extract_metadata_from_content(self, content: str) -> dict:
        """콘텐츠에서 메타데이터 추출"""
        metadata = {}
        
        # 간단한 패턴 매칭으로 메타데이터 추출
        lines = content.split('\n')
        for line in lines[:20]:  # 처음 20줄만 확인
            if "작성일:" in line:
                metadata["created_date"] = line.split("작성일:")[-1].strip()
            elif "게임 버전:" in line:
                metadata["game_version"] = line.split("게임 버전:")[-1].strip()
            elif "난이도:" in line:
                metadata["difficulty"] = line.split("난이도:")[-1].strip()
        
        return metadata
    
    async def process_directory(self, directory: str) -> List[Document]:
        """디렉토리의 모든 PDF 처리"""
        all_documents = []
        pdf_files = []
        
        # PDF 파일 찾기
        for filename in os.listdir(directory):
            if filename.endswith('.pdf'):
                pdf_files.append(os.path.join(directory, filename))
        
        logger.info(f"Found {len(pdf_files)} PDF files in {directory}")
        
        # 각 PDF 처리
        for pdf_path in pdf_files:
            try:
                documents = await self.process_pdf(pdf_path)
                all_documents.extend(documents)
            except Exception as e:
                logger.error(f"Failed to process {pdf_path}: {str(e)}")
                continue
        
        return all_documents
```

### Step 5: 개선된 문서 수집 스크립트

`scripts/ingest_documents.py`를 다음과 같이 수정:

```python
# scripts/ingest_documents.py
import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.document_processor import DocumentProcessor
from app.services.langchain_service import LangChainService
from app.config import settings
import logging
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Rich console for better output
console = Console()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def check_qdrant_connection():
    """Qdrant 연결 확인"""
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(url=settings.qdrant_url)
        collections = client.get_collections()
        console.print(f"✅ Qdrant 연결 성공! 현재 컬렉션: {[c.name for c in collections.collections]}", style="green")
        return True
    except Exception as e:
        console.print(f"❌ Qdrant 연결 실패: {str(e)}", style="red")
        return False

async def main():
    """PDF 문서를 벡터 스토어에 수집"""
    console.print("[bold blue]메이플스토리 문서 수집 시작[/bold blue]")
    
    # 1. Qdrant 연결 확인
    if not await check_qdrant_connection():
        console.print("Qdrant를 먼저 실행해주세요: docker run -p 6333:6333 qdrant/qdrant", style="yellow")
        return
    
    # 2. 서비스 초기화
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("서비스 초기화 중...", total=None)
        
        processor = DocumentProcessor(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap
        )
        service = LangChainService()
        
        # 컬렉션 정보 출력
        collection_info = service.vector_store.get_collection_info()
        if collection_info:
            console.print(f"📊 현재 컬렉션 상태: {collection_info['points_count']} 문서", style="cyan")
    
    # 3. PDF 디렉토리 확인
    pdf_dir = "./data/pdfs"
    if not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir)
        console.print(f"📁 PDF 디렉토리 생성: {pdf_dir}", style="yellow")
        console.print("PDF 파일을 이 디렉토리에 넣어주세요.", style="yellow")
        return
    
    # 4. PDF 처리
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("PDF 처리 중...", total=None)
        
        documents = await processor.process_directory(pdf_dir)
        
        if not documents:
            console.print("❌ 처리할 PDF 파일이 없습니다.", style="red")
            return
        
        console.print(f"📄 총 {len(documents)} 개의 청크 생성 완료", style="green")
    
    # 5. 벡터 스토어에 추가
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("벡터 스토어에 업로드 중...", total=None)
        
        await service.add_documents(documents)
        
        console.print("✅ 문서 업로드 완료!", style="green")
    
    # 6. 최종 상태 확인
    final_info = service.vector_store.get_collection_info()
    if final_info:
        console.print(f"📊 최종 컬렉션 상태: {final_info['points_count']} 문서", style="cyan")
    
    console.print("\n[bold green]문서 수집이 완료되었습니다![/bold green]")
    console.print("이제 서버를 실행하고 질문해보세요: uvicorn app.main:app --reload")

if __name__ == "__main__":
    asyncio.run(main())
```

### Step 6: 테스트용 PDF 준비

`data/pdfs/` 디렉토리에 테스트용 PDF를 넣어주세요. 예시 구조:

```
data/
└── pdfs/
    └── 나이트로드_5차스킬_가이드.pdf
```

### Step 7: 간단한 테스트 스크립트

`scripts/test_rag.py` 파일을 만들어 테스트:

```python
# scripts/test_rag.py
import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.langchain_service import LangChainService
from rich.console import Console
from rich.markdown import Markdown

console = Console()

async def test_questions():
    """RAG 시스템 테스트"""
    # 서비스 초기화
    service = LangChainService()
    
    # 테스트 질문들
    test_questions = [
        "나이트로드 5차 스킬 중에 뭐가 제일 중요해?",
        "보스전에서 사용하는 스킬 순서 알려줘",
        "초보자가 나이트로드 시작하려면 어떻게 해야해?"
    ]
    
    for question in test_questions:
        console.print(f"\n[bold yellow]❓ 질문:[/bold yellow] {question}")
        
        try:
            # 질문 실행
            result = await service.chat(
                message=question,
                session_id="test-session",
                stream=False
            )
            
            # 답변 출력
            console.print("\n[bold green]💬 답변:[/bold green]")
            console.print(Markdown(result["response"]))
            
            # 출처 출력
            if result.get("sources"):
                console.print("\n[bold blue]📚 참고 문서:[/bold blue]")
                for source in result["sources"]:
                    console.print(f"- {source['title']} (p.{source['page']})")
            
        except Exception as e:
            console.print(f"[red]오류 발생: {str(e)}[/red]")
        
        console.print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_questions())
```

## 3. 실행 순서

```bash
# 1. 필요한 패키지 설치 (requirements.txt에 추가)
pip install qdrant-client rich

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일 편집하여 API 키 입력

# 3. Qdrant 실행
docker run -p 6333:6333 -v $(pwd)/qdrant_data:/qdrant/storage qdrant/qdrant

# 4. PDF 파일 준비
# data/pdfs/ 디렉토리에 PDF 파일 복사

# 5. 문서 수집
python scripts/ingest_documents.py

# 6. 테스트
python scripts/test_rag.py

# 7. 서버 실행
uvicorn app.main:app --reload
```

## 4. 문제 해결

### 일반적인 문제들

1. **Qdrant 연결 오류**
   ```bash
   # Qdrant가 실행 중인지 확인
   curl http://localhost:6333/collections
   ```

2. **임베딩 오류**
   ```python
   # OpenAI API 키 확인
   echo $OPENAI_API_KEY
   ```

3. **PDF 처리 오류**
   ```bash
   # pypdf 재설치
   pip install --upgrade pypdf
   ```

### 디버깅 팁

1. **로그 레벨 변경**
   ```python
   # app/config.py에 추가
   LOG_LEVEL = "DEBUG"
   ```

2. **컬렉션 상태 확인**
   ```python
   # Python 콘솔에서
   from qdrant_client import QdrantClient
   client = QdrantClient(url="http://localhost:6333")
   print(client.get_collection("maplestory_docs"))
   ```

## 5. 다음 단계

PDF 테스트가 성공하면:

1. **Markdown으로 전환**: PDF 대신 Markdown 사용
2. **성능 최적화**: 캐싱, 배치 처리 추가
3. **UI 개선**: 웹 인터페이스 추가
4. **디스코드 봇**: 디스코드 통합

이제 위 가이드를 따라 진행해보시고, 막히는 부분이 있으면 알려주세요!
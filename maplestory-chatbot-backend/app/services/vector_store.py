# app/services/vector_store.py
try:
    from langchain_qdrant import Qdrant
except ImportError:
    from langchain_community.vectorstores import Qdrant

from langchain_community.vectorstores import Chroma, FAISS
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
            # Qdrant 클라이언트 초기화 - 보안 경고 해결
            client_kwargs = {
                "url": settings.qdrant_url,
            }
            
            # API 키가 있는 경우에만 추가
            if settings.qdrant_api_key:
                client_kwargs["api_key"] = settings.qdrant_api_key
                
            # 로컬 개발 환경에서는 verify=False로 설정 (선택사항)
            if "localhost" in settings.qdrant_url or "127.0.0.1" in settings.qdrant_url:
                client_kwargs["verify"] = False
                
            self.client = QdrantClient(**client_kwargs)
            
            # 컬렉션 존재 여부 확인 및 생성
            self._ensure_collection_exists()
            
            # LangChain Qdrant 래퍼 반환
            return Qdrant(
                client=self.client,
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
    
    def _ensure_collection_exists(self):
        """컬렉션이 없으면 생성"""
        try:
            # 컬렉션 존재 확인
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if settings.collection_name not in collection_names:
                # 임베딩 차원 확인 - 더 안전한 방식
                try:
                    logger.info(f"Testing embeddings with provider: {settings.get_embedding_provider()}")
                    test_embedding = self.embeddings.embed_query("test")
                    vector_size = len(test_embedding)
                    logger.info(f"Embedding dimension: {vector_size}")
                except Exception as embed_error:
                    logger.error(f"Failed to get embedding dimensions: {embed_error}")
                    logger.info(f"Using default dimension for provider: {settings.get_embedding_provider()}")
                    # 기본 차원 설정
                    provider = settings.get_embedding_provider()
                    if provider == "voyage":
                        vector_size = 1024  # voyage-3.5-lite 기본 차원
                    elif provider == "openai":
                        vector_size = 1536  # text-embedding-ada-002 기본 차원
                    else:
                        vector_size = 384   # 대부분의 HuggingFace 모델 기본 차원
                
                # 컬렉션 생성
                self.client.create_collection(
                    collection_name=settings.collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {settings.collection_name} with dimension {vector_size}")
            else:
                logger.info(f"Collection already exists: {settings.collection_name}")
                
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {str(e)}")
            # 더 상세한 오류 정보 제공
            if "API key" in str(e).lower():
                logger.error("This might be an API key issue. Check your OPENAI_API_KEY in .env file")
                logger.info("Falling back to local embeddings...")
                # 로컬 임베딩으로 재시도
                from app.services.embedding_service import EmbeddingService
                self.embeddings = EmbeddingService._get_local_embeddings()
                # 재귀적으로 다시 시도
                self._ensure_collection_exists()
            else:
                raise
    
    def get_retriever(self, k: int = 5, search_type: str = "similarity_score_threshold"):
        """리트리버 반환 - 관련성 강화된 검색 설정"""
        search_kwargs = {"k": k}
        
        # 유사도 점수 임계값 검색 - 가장 정확한 정보 검색에 유리
        if search_type == "similarity_score_threshold":
            search_kwargs.update({
                "score_threshold": settings.min_relevance_score  # 0.7 이상의 관련성 점수만 반환
            })
        
        # MMR 검색인 경우 관련성을 더욱 중시하는 파라미터 설정
        elif search_type == "mmr":
            search_kwargs.update({
                "fetch_k": k * 3,  # k의 3배로 줄여서 더 정확한 후보 확보 (4배 -> 3배)
                "lambda_mult": 0.9  # 관련성을 최대한 중시 (0.8 -> 0.9)
            })
        
        # 기본 유사도 검색 - 가장 관련성 높은 문서 우선
        elif search_type == "similarity":
            # 추가 설정 없이 순수 유사도 기반 검색
            pass
        
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
            try:
                collection_info = self.client.get_collection(settings.collection_name)
                # qdrant-client 최신 버전에서 속성명이 변경됨
                return {
                    "name": getattr(collection_info, 'name', settings.collection_name),
                    "vectors_count": getattr(collection_info, 'vectors_count', 0),
                    "points_count": getattr(collection_info, 'points_count', 0),
                    "status": getattr(collection_info, 'status', 'unknown')
                }
            except Exception as e:
                logger.error(f"Error getting collection info: {str(e)}")
                # 안전한 기본값 반환
                return {
                    "name": settings.collection_name,
                    "vectors_count": 0,
                    "points_count": 0,
                    "status": "unknown"
                }
        return None 
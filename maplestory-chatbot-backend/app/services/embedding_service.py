from typing import Union, List
from app.config import settings
import logging
import os
from langchain.embeddings.base import Embeddings
import voyageai

logger = logging.getLogger(__name__)

class VoyageEmbeddings(Embeddings):
    """Voyage AI 임베딩을 위한 LangChain 호환 클래스"""
    
    def __init__(self, api_key: str = None, model: str = "voyage-3.5-lite"):
        self.client = voyageai.Client(api_key=api_key)
        self.model = model
        logger.info(f"Initialized Voyage AI embeddings with model: {model}")
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """문서 임베딩 생성"""
        try:
            # Voyage AI는 배치 처리를 지원하므로 한 번에 처리
            response = self.client.embed(
                texts=texts,
                model=self.model,
                input_type="document"  # 문서용으로 최적화
            )
            return response.embeddings
        except Exception as e:
            logger.error(f"Error in Voyage AI document embedding: {e}")
            raise
    
    def embed_query(self, text: str) -> List[float]:
        """쿼리 임베딩 생성"""
        try:
            response = self.client.embed(
                texts=[text],
                model=self.model,
                input_type="query"  # 쿼리용으로 최적화
            )
            return response.embeddings[0]
        except Exception as e:
            logger.error(f"Error in Voyage AI query embedding: {e}")
            raise


class EmbeddingService:
    """유연한 임베딩 서비스 - Voyage AI, OpenAI 또는 로컬 모델 사용"""
    
    @staticmethod
    def get_embeddings():
        """설정에 따라 적절한 임베딩 모델 반환"""
        provider = settings.get_embedding_provider()
        
        if provider == "voyage":
            logger.info("Using Voyage AI embeddings")
            return EmbeddingService._get_voyage_embeddings()
        elif provider == "openai":
            logger.info("Using OpenAI embeddings")
            return EmbeddingService._get_openai_embeddings()
        else:
            logger.info("Using local embeddings (HuggingFace)")
            return EmbeddingService._get_local_embeddings()
    
    @staticmethod
    def _get_voyage_embeddings():
        """Voyage AI 임베딩 모델"""
        try:
            api_key = settings.voyage_api_key
            if not api_key or api_key == "your_voyage_api_key_here":
                logger.error("Voyage AI API key not provided")
                logger.info("Falling back to OpenAI embeddings")
                return EmbeddingService._get_openai_embeddings()
            
            return VoyageEmbeddings(
                api_key=api_key,
                model=settings.voyage_model
            )
        except Exception as e:
            logger.error(f"Failed to initialize Voyage AI embeddings: {e}")
            logger.info("Falling back to OpenAI embeddings")
            return EmbeddingService._get_openai_embeddings()
    
    @staticmethod
    def _get_openai_embeddings():
        """OpenAI 임베딩 모델"""
        try:
            from langchain_openai import OpenAIEmbeddings
            
            api_key = settings.openai_api_key
            if not api_key or api_key == "your_openai_api_key_here":
                logger.error("OpenAI API key not provided")
                logger.info("Falling back to local embeddings")
                return EmbeddingService._get_local_embeddings()
            
            return OpenAIEmbeddings(
                openai_api_key=api_key,
                model=settings.embedding_model
            )
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI embeddings: {e}")
            logger.info("Falling back to local embeddings")
            return EmbeddingService._get_local_embeddings()
    
    @staticmethod
    def _get_local_embeddings():
        """로컬 HuggingFace 임베딩 모델 - Rate Limit 문제 해결"""
        try:
            # Hugging Face 토큰 설정 (Rate Limit 회피)
            if settings.huggingface_api_token:
                os.environ['HUGGINGFACE_HUB_TOKEN'] = settings.huggingface_api_token
                logger.info("Hugging Face token configured")
            
            # 새로운 langchain-huggingface 패키지 사용
            from langchain_huggingface import HuggingFaceEmbeddings
            
            # 안정적인 모델 사용
            model_name = settings.local_embedding_model
            
            logger.info(f"Initializing local embeddings with model: {model_name}")
            
            return HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={'device': 'cpu'},  # CPU 사용 (GPU 있으면 'cuda')
                encode_kwargs={'normalize_embeddings': True}
            )
        except ImportError:
            logger.error("HuggingFace embeddings not available. Installing sentence-transformers...")
            # 자동 설치 시도
            import subprocess
            import sys
            subprocess.check_call([sys.executable, "-m", "pip", "install", "sentence-transformers"])
            
            # 재시도
            from langchain_huggingface import HuggingFaceEmbeddings
            return HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
        except Exception as e:
            logger.error(f"Failed to initialize local embeddings with {settings.local_embedding_model}: {e}")
            logger.warning("Attempting fallback to lightweight model...")
            # 최후의 수단: 가장 간단한 모델 사용
            return EmbeddingService._get_fallback_embeddings()
    
    @staticmethod
    def _get_fallback_embeddings():
        """최후의 수단: 가장 경량이고 안정적인 임베딩 모델"""
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
            logger.warning("Using fallback embedding model: all-MiniLM-L6-v2 (90MB)")
            return HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
        except Exception as e:
            logger.error(f"All embedding methods failed: {e}")
            logger.error("Please check your internet connection or provide API keys")
            raise RuntimeError("No embedding model available. Please provide Voyage AI, OpenAI API key or install sentence-transformers.")

# 편의를 위한 함수
def get_embeddings():
    """임베딩 서비스 인스턴스 반환"""
    return EmbeddingService.get_embeddings() 
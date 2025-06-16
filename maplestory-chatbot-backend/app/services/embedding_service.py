from typing import Union, List
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class EmbeddingService:
    """유연한 임베딩 서비스 - OpenAI 또는 로컬 모델 사용"""
    
    @staticmethod
    def get_embeddings():
        """설정에 따라 적절한 임베딩 모델 반환"""
        provider = settings.get_embedding_provider()
        
        if provider == "openai":
            logger.info("Using OpenAI embeddings")
            return EmbeddingService._get_openai_embeddings()
        else:
            logger.info("Using local embeddings (HuggingFace)")
            return EmbeddingService._get_local_embeddings()
    
    @staticmethod
    def _get_openai_embeddings():
        """OpenAI 임베딩 모델"""
        try:
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(
                openai_api_key=settings.openai_api_key,
                model=settings.embedding_model
            )
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI embeddings: {e}")
            logger.info("Falling back to local embeddings")
            return EmbeddingService._get_local_embeddings()
    
    @staticmethod
    def _get_local_embeddings():
        """로컬 HuggingFace 임베딩 모델"""
        try:
            # 새로운 langchain-huggingface 패키지 사용
            from langchain_huggingface import HuggingFaceEmbeddings
            
            # 한국어에 최적화된 모델 사용
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
            logger.error(f"Failed to initialize local embeddings: {e}")
            # 최후의 수단: 가장 간단한 모델 사용
            return EmbeddingService._get_fallback_embeddings()
    
    @staticmethod
    def _get_fallback_embeddings():
        """최후의 수단: 가장 간단한 임베딩 모델"""
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
            logger.warning("Using fallback embedding model: all-MiniLM-L6-v2")
            return HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
        except Exception as e:
            logger.error(f"All embedding methods failed: {e}")
            raise RuntimeError("No embedding model available. Please install sentence-transformers or provide OpenAI API key.")

# 편의 함수
def get_embeddings():
    """임베딩 모델 인스턴스 반환"""
    return EmbeddingService.get_embeddings() 
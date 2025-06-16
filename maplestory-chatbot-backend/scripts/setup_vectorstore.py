import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.services.vector_store import VectorStoreService
from app.services.embedding_service import get_embeddings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_vectorstore():
    """벡터 스토어 초기화"""
    try:
        # 임베딩 모델 초기화 - 유연한 방식
        logger.info(f"Initializing embeddings with provider: {settings.get_embedding_provider()}")
        embeddings = get_embeddings()
        
        # 벡터 스토어 서비스 초기화
        vector_store_service = VectorStoreService(embeddings)
        
        logger.info(f"Vector store type: {settings.vector_store_type}")
        logger.info(f"Collection name: {settings.collection_name}")
        logger.info(f"Embedding provider: {settings.get_embedding_provider()}")
        
        # 벡터 스토어 연결 테스트
        retriever = vector_store_service.get_retriever()
        
        logger.info("✅ Vector store setup completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error setting up vector store: {str(e)}")
        raise

async def clear_vectorstore():
    """벡터 스토어 초기화 (모든 데이터 삭제)"""
    try:
        # 임베딩 모델 초기화 - 유연한 방식
        embeddings = get_embeddings()
        
        vector_store_service = VectorStoreService(embeddings)
        
        if settings.vector_store_type == "qdrant":
            from qdrant_client import QdrantClient
            client = QdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key
            )
            
            # 컬렉션 삭제 후 재생성
            try:
                client.delete_collection(settings.collection_name)
                logger.info(f"Deleted collection: {settings.collection_name}")
            except:
                logger.info(f"Collection {settings.collection_name} does not exist")
            
            # 새 컬렉션 생성은 벡터 스토어 서비스에서 자동으로 처리됨
            
        logger.info("✅ Vector store cleared successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error clearing vector store: {str(e)}")
        raise

async def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Vector store setup utility")
    parser.add_argument("--clear", action="store_true", help="Clear all data from vector store")
    args = parser.parse_args()
    
    if args.clear:
        await clear_vectorstore()
    else:
        await setup_vectorstore()

if __name__ == "__main__":
    asyncio.run(main()) 
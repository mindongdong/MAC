from functools import lru_cache
import hashlib
import json
import redis
from typing import Optional, Any
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class CacheService:
    """Redis 기반 캐시 서비스"""
    
    def __init__(self):
        self.redis_client = None
        if settings.redis_url:
            try:
                self.redis_client = redis.from_url(settings.redis_url)
                self.redis_client.ping()
                logger.info("Redis 연결 성공")
            except Exception as e:
                logger.warning(f"Redis 연결 실패: {e}")
                self.redis_client = None
    
    def _generate_key(self, prefix: str, data: Any) -> str:
        """캐시 키 생성"""
        data_str = json.dumps(data, sort_keys=True)
        hash_key = hashlib.md5(data_str.encode()).hexdigest()
        return f"{prefix}:{hash_key}"
    
    def get(self, key: str) -> Optional[str]:
        """캐시에서 값 조회"""
        if not self.redis_client:
            return None
        
        try:
            return self.redis_client.get(key)
        except Exception as e:
            logger.error(f"캐시 조회 실패: {e}")
            return None
    
    def set(self, key: str, value: str, ttl: int = None) -> bool:
        """캐시에 값 저장"""
        if not self.redis_client:
            return False
        
        try:
            ttl = ttl or settings.cache_ttl
            self.redis_client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.error(f"캐시 저장 실패: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        if not self.redis_client:
            return False
        
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"캐시 삭제 실패: {e}")
            return False

# 전역 캐시 인스턴스
cache_service = CacheService()

@lru_cache(maxsize=100)
def get_cached_response(query_hash: str):
    """메모리 캐시를 사용한 응답 조회"""
    return cache_service.get(f"response:{query_hash}")

def cache_response(query: str, response: str) -> None:
    """응답을 캐시에 저장"""
    query_hash = hashlib.md5(query.encode()).hexdigest()
    cache_service.set(f"response:{query_hash}", response) 
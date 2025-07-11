# app/config/settings.py
from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # API Keys
    anthropic_api_key: str
    openai_api_key: Optional[str] = None  # 임베딩용 (선택사항)
    huggingface_api_token: Optional[str] = None  # Rate Limit 회피용 (선택사항)
    voyage_api_key: Optional[str] = None  # Voyage AI 임베딩용
    
    # Claude 설정
    claude_model: str = "claude-3-5-haiku-20241022"
    max_tokens: int = 4096
    temperature: float = 0.3  # 정확성을 위해 낮춤 (0.7 -> 0.3)
    
    # 프롬프트 설정
    use_system_prompt: bool = True  # 새로운 시스템 프롬프트 사용 여부
    enable_answer_template: bool = False  # 답변 템플릿 사용 여부 (품질 문제로 비활성화)
    
    # 답변 품질 개선 설정
    min_relevance_score: float = 0.75  # 문서 관련성 최소 점수 (0.7 -> 0.75로 강화)
    max_reference_sources: int = 3    # 참고자료 최대 개수
    require_url_in_sources: bool = True  # 참고자료에 URL 필수 여부
    strict_document_matching: bool = True  # 엄격한 문서 매칭 모드
    
    # 검색 최적화 설정
    search_type: str = "similarity_score_threshold"  # similarity, mmr, similarity_score_threshold
    max_retrieval_docs: int = 5  # 검색할 최대 문서 수 (8 -> 5로 줄임)
    enable_document_filtering: bool = True  # 문서 관련성 사전 필터링 활성화
    enable_response_validation: bool = True  # 답변 후처리 검증 활성화
    
    # FastAPI 설정
    app_name: str = "메이플스토리 AI 어시스턴트"
    app_version: str = "1.0.0"
    debug_mode: bool = False
    
    # Vector Store 설정
    vector_store_type: str = "qdrant"  # qdrant, chroma, faiss
    qdrant_url: Optional[str] = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None
    collection_name: str = "maplestory_docs"
    
    # 임베딩 설정 - Voyage AI 우선 사용
    embedding_provider: str = "auto"  # auto, voyage, openai, local
    embedding_model: str = "text-embedding-ada-002"  # OpenAI 모델
    voyage_model: str = "voyage-3.5-lite"  # Voyage AI 모델
    local_embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"  # 안정적인 다국어 모델 (420MB)
    # 대안 모델들 (문제 발생 시 사용):
    # "sentence-transformers/all-MiniLM-L6-v2"  # 초경량 (90MB) - 영어 중심
    # "intfloat/multilingual-e5-large"  # 고성능 (1.24GB) - Rate Limit 위험
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    # 캐싱 설정
    redis_url: Optional[str] = "redis://localhost:6379"
    cache_ttl: int = 3600  # 1시간
    
    # 보안 설정
    cors_origins: list = ["http://localhost:3000", "https://yourdomain.com"]
    rate_limit_per_minute: int = 10
    
    # Discord Bot 설정 (누락된 필드들 추가)
    discord_bot_token: Optional[str] = None
    api_url: str = "http://localhost:8000"
    
    # 로깅 및 기타 설정 (누락된 필드들 추가)
    log_level: str = "INFO"
    max_chunk_size: int = 1000  # chunk_size와 중복이지만 env에 있으므로 추가
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # 정의되지 않은 환경변수 무시
    
    def get_embedding_provider(self) -> str:
        """임베딩 제공자 자동 결정 - Voyage AI 우선"""
        if self.embedding_provider == "auto":
            if self.voyage_api_key and self.voyage_api_key != "your_voyage_api_key_here":
                return "voyage"
            elif self.openai_api_key and self.openai_api_key != "your_openai_api_key_here":
                return "openai"
            else:
                return "local"
        return self.embedding_provider

settings = Settings() 
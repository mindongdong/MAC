# 메이플스토리 RAG 시스템 임베딩 전략

## 🎯 현재 상황 요약

### 문제 정의
- **핵심 이슈**: Hugging Face Rate Limiting (HTTP 429 Error)
- **원인**: `intfloat/multilingual-e5-large` 모델 다운로드 제한 초과
- **영향**: RAG 파이프라인 초기화 실패

### 현재 적용된 임시 해결책
```python
LOCAL_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
# - 크기: 420MB (기존 1.24GB 대비 65% 감소)
# - 차원: 384 (기존 1024 대비 62% 감소) 
# - 안정성: 높음, 성능: 중간
```

## 📊 임베딩 모델 비교 분석

| 모델 | 크기 | 차원 | 한국어 성능 | Rate Limit | 비용 |
|------|------|------|-------------|------------|------|
| **OpenAI Ada-002** | API | 1536 | ⭐⭐⭐⭐⭐ | 없음 | $0.0001/1K tokens |
| **multilingual-e5-large** | 1.24GB | 1024 | ⭐⭐⭐⭐ | 높음 | 무료 |
| **paraphrase-multilingual-MiniLM** | 420MB | 384 | ⭐⭐⭐ | 낮음 | 무료 |
| **all-MiniLM-L6-v2** | 90MB | 384 | ⭐⭐ | 없음 | 무료 |

## 🛠️ 해결 전략

### Phase 1: 즉시 실행 (완료 ✅)
- [x] 안정적인 모델로 변경
- [x] 3단계 Fallback 시스템 구축
- [x] Hugging Face 토큰 지원 추가

### Phase 2: 단기 해결 (권장)

#### 1. Hugging Face 토큰 설정
```bash
# 1. https://huggingface.co/settings/tokens 접속
# 2. "New token" 클릭 → Read 권한으로 토큰 생성
# 3. .env 파일에 추가
HUGGINGFACE_API_TOKEN=hf_your_token_here
```

#### 2. 모델 성능 벤치마킹
```bash
# 각 모델별 성능 테스트
python scripts/test_embeddings.py

# 한국어 특화 테스트
python scripts/test_korean_embeddings.py
```

#### 3. 로컬 모델 캐싱 시스템
```python
# app/services/model_cache.py
class ModelCacheService:
    def __init__(self):
        self.cache_dir = "models/cache"
        
    def download_and_cache(self, model_name):
        """모델을 로컬에 다운로드하여 캐시"""
        # 네트워크 문제 시에도 로컬 캐시 사용 가능
        pass
```

### Phase 3: 장기 해결 (프로덕션)

#### 1. 하이브리드 임베딩 전략
```python
class HybridEmbeddingService:
    """비용과 성능의 균형을 맞춘 하이브리드 전략"""
    
    def __init__(self):
        self.openai_embeddings = OpenAIEmbeddings()  # 고성능
        self.local_embeddings = LocalEmbeddings()    # 안정성
        self.redis_cache = RedisCache()              # 성능 최적화
        
        # 사용량 추적
        self.monthly_budget = 100.0  # $100/월
        self.current_usage = 0.0
    
    async def embed_query(self, text: str):
        # 1. 캐시 확인
        if cached := await self.redis_cache.get(text):
            return cached
            
        # 2. 예산 확인
        if self.should_use_openai():
            try:
                result = await self.openai_embeddings.embed_query(text)
                await self.redis_cache.set(text, result)
                self.track_usage(text)
                return result
            except Exception:
                pass  # Fallback으로 진행
        
        # 3. 로컬 모델 사용
        result = await self.local_embeddings.embed_query(text)
        await self.redis_cache.set(text, result)
        return result
```

#### 2. 비용 최적화 전략
```python
# 쿼리 타입별 전략
embedding_strategy = {
    "initial_indexing": "local",      # 대용량 인덱싱은 로컬
    "user_queries": "openai",         # 사용자 쿼리는 고성능
    "batch_processing": "local",      # 배치 작업은 로컬
    "real_time": "hybrid"            # 실시간은 하이브리드
}
```

## 💰 비용 분석

### OpenAI 임베딩 비용 계산
```python
# 예상 사용량 (월간)
monthly_documents = 10000      # 인덱싱할 문서 수
monthly_queries = 50000       # 사용자 쿼리 수
avg_tokens_per_text = 100     # 평균 토큰 수

# 비용 계산
indexing_cost = (monthly_documents * avg_tokens_per_text) / 1000 * 0.0001
query_cost = (monthly_queries * avg_tokens_per_text) / 1000 * 0.0001
total_monthly_cost = indexing_cost + query_cost

print(f"월 예상 비용: ${total_monthly_cost:.2f}")
# 예상 결과: $0.60/월 (매우 저렴)
```

### 비용 절약 전략
1. **캐싱**: 동일 쿼리 재사용으로 90% 비용 절약
2. **배치 처리**: 대용량 인덱싱은 로컬 모델 사용
3. **스마트 라우팅**: 중요한 쿼리만 OpenAI 사용

## 🎯 권장 실행 계획

### 즉시 실행 (오늘)
1. **Hugging Face 토큰 발급 및 설정**
2. **현재 시스템으로 테스트 실행 확인**
3. **성능 벤치마크 실행**

### 1주일 내
1. **하이브리드 시스템 설계**
2. **비용 추적 시스템 구현**
3. **캐싱 레이어 추가**

### 1개월 내
1. **프로덕션 배포**
2. **모니터링 시스템 구축**
3. **성능 최적화**

## 🚀 Quick Start

### 1. 토큰 설정
```bash
# .env 파일에 추가
HUGGINGFACE_API_TOKEN=hf_your_token_here
EMBEDDING_PROVIDER=local  # 또는 openai
```

### 2. 테스트 실행
```bash
cd maplestory-chatbot-backend
python scripts/test_rag.py
python scripts/test_embeddings.py
```

### 3. 성능 모니터링
```bash
# 로그 확인
tail -f logs/embedding_performance.log

# 비용 추적
python scripts/analyze_embedding_costs.py
```

## 📞 문제 해결

### Rate Limit 발생 시
1. Hugging Face 토큰 확인
2. 더 작은 모델로 Fallback
3. 네트워크 연결 상태 확인

### 성능 이슈 시
1. 캐싱 레이어 활성화
2. 모델 크기 vs 성능 trade-off 재검토
3. 하이브리드 전략 적용

---

**결론**: 현재 임시 해결책으로 안정성을 확보했으나, 장기적으로는 하이브리드 전략을 통해 비용과 성능의 최적 균형점을 찾는 것이 핵심입니다. 
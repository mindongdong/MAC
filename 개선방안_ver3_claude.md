현재 상황을 분석해보니 **개선사항이 너무 엄격하게 적용되어 오히려 사용성이 떨어진 케이스**네요. 적절한 균형점을 찾기 위한 실용적인 개선 방안을 제안드리겠습니다.

## 🎯 문제 분석: 왜 이렇게 극단적인 결과가 나왔나?

### 1. **검색 방식의 급격한 변경**
- 기존: `similarity` (상위 k개 무조건 반환)
- 변경: `similarity_score_threshold` (임계값 미달 시 0개 반환)
- 결과: 유사도 점수가 예상보다 매우 낮아 대부분 필터링됨

### 2. **Voyage AI 임베딩의 특성**
- Voyage AI는 1024차원으로 OpenAI(1536차원)보다 낮음
- 유사도 점수가 전반적으로 낮게 나올 수 있음
- 한국어 게임 용어에 대한 미세조정이 필요할 수 있음

## 💡 단계적 개선 방안

### **1단계: 즉시 적용 가능한 설정 조정**

```python
# app/services/vector_store.py 수정

def get_retriever(self, k: int = 8, search_type: str = "similarity"):
    """개선된 리트리버 - 단계적 접근"""
    
    # 1. 기본은 similarity로 유지 (안정성)
    if search_type == "similarity":
        search_kwargs = {"k": k}
    
    # 2. MMR로 다양성 확보 (중간 단계)
    elif search_type == "mmr":
        search_kwargs = {
            "k": k,
            "fetch_k": k * 3,  # 더 많이 가져와서 선별
            "lambda_mult": 0.7  # 관련성 70%, 다양성 30%
        }
    
    # 3. 임계값 방식은 매우 낮은 값으로
    elif search_type == "similarity_score_threshold":
        search_kwargs = {
            "k": k,
            "score_threshold": 0.01  # 현실적인 임계값
        }
    
    return self.vector_store.as_retriever(
        search_type=search_type,
        search_kwargs=search_kwargs
    )
```

### **2단계: 후처리 필터링으로 품질 개선**

```python
# app/services/langchain_service.py 수정

async def _filter_documents_by_relevance(self, documents: List[Document], query: str) -> List[Document]:
    """문서 관련성 후처리 필터링 - 덜 엄격한 버전"""
    filtered_docs = []
    
    for doc in documents:
        relevance_score = 0
        
        # 1. 제목 매칭 (가중치 높음)
        title = doc.metadata.get('title', '').lower()
        if any(keyword in title for keyword in query.lower().split()):
            relevance_score += 3
        
        # 2. 카테고리 매칭 (중간 가중치)
        category = doc.metadata.get('category', '')
        if self._is_category_relevant(category, query):
            relevance_score += 2
        
        # 3. 내용 키워드 매칭 (낮은 가중치)
        content_lower = doc.page_content.lower()
        query_keywords = query.lower().split()
        matching_keywords = sum(1 for kw in query_keywords if kw in content_lower)
        relevance_score += min(matching_keywords, 3)  # 최대 3점
        
        # 4. 점수 기반 필터링 (느슨한 기준)
        if relevance_score >= 2:  # 최소 2점 이상
            filtered_docs.append(doc)
    
    # 최소한 3개는 반환 (상위 3개)
    if len(filtered_docs) < 3 and len(documents) >= 3:
        return documents[:3]
    
    return filtered_docs[:k]
```

### **3단계: 설정 파일 업데이트 (균형잡힌 설정)**

```python
# app/config/settings.py

# 검색 설정 - 단계적 접근
search_type: str = "similarity"  # mmr이나 similarity 권장
min_relevance_score: float = 0.01  # 매우 낮게 설정
enable_post_filtering: bool = True  # 후처리 필터링 활성화
post_filter_threshold: int = 2  # 느슨한 후처리 기준

# 검색 결과 개수
retriever_k: int = 10  # 더 많이 가져오기
max_final_sources: int = 5  # 최종적으로 5개로 줄이기
```

### **4단계: 키워드 기반 폴백 검색 추가**

```python
# app/services/langchain_service.py에 추가

async def _keyword_fallback_search(self, query: str, k: int = 5) -> List[Document]:
    """벡터 검색 실패 시 키워드 기반 폴백"""
    try:
        # 간단한 키워드 매칭
        all_docs = await self.vector_store.get_all_documents()
        scored_docs = []
        
        query_keywords = query.lower().split()
        
        for doc in all_docs:
            score = 0
            content_lower = doc.page_content.lower()
            title_lower = doc.metadata.get('title', '').lower()
            
            # 제목 매칭 우선
            for keyword in query_keywords:
                if keyword in title_lower:
                    score += 10
                elif keyword in content_lower:
                    score += 1
            
            if score > 0:
                scored_docs.append((score, doc))
        
        # 점수순 정렬
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        
        return [doc for _, doc in scored_docs[:k]]
    
    except Exception as e:
        logger.error(f"Keyword fallback search error: {e}")
        return []
```

### **5단계: 하이브리드 검색 구현**

```python
# app/services/langchain_service.py 수정

async def hybrid_search(self, query: str, k: int = 8) -> List[Document]:
    """벡터 + 키워드 하이브리드 검색"""
    
    # 1. 벡터 검색 (느슨한 기준)
    vector_docs = await self.vector_store.search(query, k=k*2)
    
    # 2. 키워드 검색
    keyword_docs = await self._keyword_fallback_search(query, k=k)
    
    # 3. 결과 병합 및 중복 제거
    all_docs = {}
    
    # 벡터 검색 결과 (높은 가중치)
    for i, doc in enumerate(vector_docs):
        doc_id = f"{doc.metadata.get('source', '')}_{doc.metadata.get('chunk_index', 0)}"
        if doc_id not in all_docs:
            all_docs[doc_id] = {
                'doc': doc,
                'vector_rank': i,
                'keyword_rank': float('inf'),
                'score': 1.0 / (i + 1)  # 순위 기반 점수
            }
    
    # 키워드 검색 결과 추가
    for i, doc in enumerate(keyword_docs):
        doc_id = f"{doc.metadata.get('source', '')}_{doc.metadata.get('chunk_index', 0)}"
        if doc_id in all_docs:
            all_docs[doc_id]['keyword_rank'] = i
            all_docs[doc_id]['score'] += 0.5 / (i + 1)
        else:
            all_docs[doc_id] = {
                'doc': doc,
                'vector_rank': float('inf'),
                'keyword_rank': i,
                'score': 0.5 / (i + 1)
            }
    
    # 종합 점수로 정렬
    sorted_docs = sorted(all_docs.values(), key=lambda x: x['score'], reverse=True)
    
    return [item['doc'] for item in sorted_docs[:k]]
```

## 🎯 권장 적용 순서

### **Phase 1: 빠른 개선 (1일)**
1. `search_type`을 `"similarity"`로 되돌리기
2. 후처리 필터링을 느슨하게 조정
3. k값을 10으로 늘리기

### **Phase 2: 안정화 (3일)**
1. MMR 검색으로 전환 테스트
2. 키워드 폴백 검색 구현
3. 사용자 피드백 수집

### **Phase 3: 최적화 (1주)**
1. 하이브리드 검색 구현
2. 문서 메타데이터 개선
3. 임베딩 모델 파인튜닝 검토

## 📊 기대 효과

| 단계 | 답변률 | 품질 | 속도 |
|------|--------|------|------|
| 현재 (0.01 임계값) | 25% | 높음 | 빠름 |
| Phase 1 적용 후 | 80% | 중간 | 빠름 |
| Phase 2 적용 후 | 85% | 중상 | 보통 |
| Phase 3 적용 후 | 90% | 높음 | 보통 |

## 🚀 즉시 적용 가능한 Quick Fix

```bash
# 1. 환경변수 수정
SEARCH_TYPE=similarity
RETRIEVER_K=10
ENABLE_POST_FILTERING=true
POST_FILTER_THRESHOLD=2

# 2. Docker 재시작
docker-compose down
docker-compose up -d

# 3. 테스트
python scripts/test_rag.py
```

이렇게 단계적으로 접근하면 **극단적인 설정 없이도 실용적인 수준의 성능**을 달성할 수 있을 것입니다. 핵심은 "all or nothing" 접근이 아닌 **점진적 개선**입니다.
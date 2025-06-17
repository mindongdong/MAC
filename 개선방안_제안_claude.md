메이플스토리 RAG 챗봇의 답변 퀄리티 문제를 상세히 분석해주셔서 감사합니다. 제시하신 예시들을 보니 확실히 심각한 문제가 있네요. 핵심 문제들을 정리하고 해결 방안을 제시해드리겠습니다.

## 🔍 핵심 문제 정의

### 1. **문서 검색 정확도 문제**
- 질문과 관련 있는 문서가 있음에도 관련 없는 문서를 참조
- 검색 쿼리와 문서 매칭 알고리즘의 부정확성
- 의미적 유사도만 고려하고 도메인 특화 매칭 부재

### 2. **할루시네이션 (Hallucination) 문제**
- 존재하지 않는 정보 생성 (예: 솔라 슬래시, 레드 큐브 30개)
- 부정확한 수치 정보 (예: 솔 에르다 2,400개)
- 모호한 표현 사용 (예: "다수", "수십억 메소 상당")

### 3. **시스템 프롬프트 문제**
- 문서에 없는 내용을 추측하여 답변하도록 허용
- 정확성보다 완성도 있는 답변을 우선시
- 메이플스토리 도메인 지식 검증 부재

## 💡 개선 방안

### 1. **검색 파이프라인 개선**

```python
# app/services/langchain_service.py 개선안

def get_retriever(self, k: int = 8, search_type: str = "similarity_score_threshold"):
    """개선된 리트리버 - 관련성 점수 임계값 적용"""
    search_kwargs = {
        "k": k,
        "score_threshold": 0.7  # 0.7 이상의 유사도만 반환
    }
    
    # 메타데이터 필터링 추가
    if search_type == "similarity_score_threshold":
        search_kwargs["filter"] = self._get_metadata_filter()
    
    return self.vector_store.as_retriever(
        search_type=search_type,
        search_kwargs=search_kwargs
    )

def _get_metadata_filter(self):
    """문서 카테고리 기반 필터링"""
    # 질문 분석을 통해 적절한 카테고리 선택
    return {
        "category": {"$in": ["guide", "event", "skill", "item"]}
    }
```

### 2. **시스템 프롬프트 강화**

```python
# app/chains/prompts.py 개선안

MAPLESTORY_SYSTEM_PROMPT = """
당신은 메이플스토리 전문 AI 어시스턴트입니다.

## 핵심 원칙
1. **정확성 최우선**: 참고 문서에 없는 정보는 절대 추측하지 마세요. 불확실하면 "정확한 정보를 찾을 수 없습니다"라고 명시하세요.
2. **문서 기반 답변**: 제공된 참고 문서의 내용만을 사용하여 답변하세요. 일반 지식은 보조적으로만 사용하세요.
3. **정확한 용어 사용**: 게임 내 정확한 명칭을 사용하세요 (예: "하드 스우", "이지 매그너스" 등)
4. **구체적 수치 제공**: 문서에 명시된 정확한 수치와 데이터를 우선적으로 사용하세요.

## 엄격한 금지사항
- 문서에 없는 구체적인 수치나 아이템명 창작 금지
- 존재하지 않는 스킬이나 시스템 언급 금지  
- 불확실한 정보를 확실한 것처럼 표현 금지
- 부정확한 게임 용어 사용 금지

## 답변 작성 규칙
- 관련성이 낮은 문서는 무시하고, 질문과 직접 관련된 문서만 참고
- 애매한 표현("일반적으로", "대략", "다수" 등) 사용 금지
- 구체적이고 검증 가능한 정보만 제공
"""
```

### 3. **문서 관련성 검증 강화**

```python
# app/services/langchain_service.py에 추가

async def _validate_document_relevance(self, documents: List[Document], query: str) -> List[Document]:
    """문서 관련성 재검증"""
    relevant_docs = []
    
    for doc in documents:
        # 1. 제목/카테고리 기반 필터링
        if self._is_title_relevant(doc.metadata.get('title', ''), query):
            relevant_docs.append(doc)
            continue
            
        # 2. 내용 기반 키워드 매칭
        if self._has_relevant_keywords(doc.page_content, query):
            relevant_docs.append(doc)
            continue
            
        # 3. 관련성 점수가 높은 경우만 포함
        if doc.metadata.get('score', 0) > 0.8:
            relevant_docs.append(doc)
    
    return relevant_docs[:3]  # 상위 3개만 사용

def _is_title_relevant(self, title: str, query: str) -> bool:
    """제목 관련성 검사"""
    query_keywords = self._extract_keywords(query)
    title_lower = title.lower()
    
    # 키워드 매칭
    for keyword in query_keywords:
        if keyword.lower() in title_lower:
            return True
    return False
```

### 4. **답변 후처리 검증**

```python
# app/services/langchain_service.py에 추가

def _validate_response(self, response: str, documents: List[Document]) -> str:
    """답변 검증 및 수정"""
    # 1. 할루시네이션 체크
    suspicious_patterns = [
        r'\d+개',  # 구체적 수치
        r'[가-힣]+\s*큐브',  # 아이템명
        r'[가-힣]+\s*스킬',  # 스킬명
    ]
    
    for pattern in suspicious_patterns:
        matches = re.findall(pattern, response)
        for match in matches:
            # 문서에서 해당 내용 확인
            if not self._verify_in_documents(match, documents):
                # 문서에 없는 내용이면 제거 또는 수정
                response = response.replace(match, "[문서에서 확인 불가]")
    
    # 2. 애매한 표현 제거
    vague_terms = ["일반적으로", "보통", "대략", "약", "다수", "여러"]
    for term in vague_terms:
        response = response.replace(term, "")
    
    return response
```

### 5. **메타데이터 활용 강화**

```python
# app/config/metadata_config.py 활용

def enhance_query_with_metadata(self, query: str) -> Dict:
    """쿼리에서 메타데이터 추출"""
    metadata_hints = {
        "category": None,
        "content_type": None,
        "class": None
    }
    
    # 카테고리 추론
    if any(word in query for word in ["코인샵", "이벤트", "보상"]):
        metadata_hints["category"] = "event_guide"
    elif any(word in query for word in ["스킬", "빌드", "육성"]):
        metadata_hints["category"] = "class_guide"
    elif any(word in query for word in ["제네시스", "패스", "결제"]):
        metadata_hints["category"] = "system_guide"
    
    # 직업 추출
    for class_name in metadata_config.available_classes:
        if class_name in query:
            metadata_hints["class"] = class_name
            break
    
    return metadata_hints
```

### 6. **설정 파일 업데이트**

```python
# app/config/settings.py에 추가

# 답변 품질 개선 설정
min_relevance_score: float = 0.7  # 문서 관련성 최소 점수
max_reference_sources: int = 3    # 참고자료 최대 개수
require_url_in_sources: bool = True  # 참고자료에 URL 필수
strict_document_matching: bool = True  # 엄격한 문서 매칭
```

## 📋 즉시 적용 가능한 Quick Fix

1. **검색 결과 수 줄이기**: `k=8` → `k=5`
2. **유사도 임계값 설정**: 0.7 이상만 사용
3. **시스템 프롬프트에 할루시네이션 방지 강화**
4. **문서 제목과 쿼리 키워드 매칭 우선**
5. **답변 후처리로 의심스러운 내용 제거**

이러한 개선사항들을 단계적으로 적용하면 답변의 정확도와 관련성이 크게 향상될 것입니다. 특히 문서 검색의 정확도를 높이는 것이 가장 중요하며, 할루시네이션 방지를 위한 시스템 프롬프트 강화도 필수적입니다.
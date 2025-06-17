메이플스토리 RAG 챗봇의 상세한 개선 과정을 공유해주셔서 감사합니다. 벡터 검색이 작동하지 않던 문제를 해결하신 것을 축하드립니다! 제시하신 5가지 질문에 대해 상세히 답변드리겠습니다.

## 1. 🎯 최적 임계값 설정

### 현재 0.5의 평가와 개선 전략

**단계적 임계값 상향 전략:**
```python
# 4단계 점진적 개선 (2-3일 간격)
Stage 1: 0.5 → 문서 검색률 모니터링 (현재)
Stage 2: 0.6 → 할루시네이션 감소 확인
Stage 3: 0.65 → 답변 정확도 vs 거부율 균형점
Stage 4: 0.7 → 최종 품질 목표
```

**임계값별 예상 효과:**
- **0.5**: 대부분 검색 성공, 일부 관련성 낮은 문서 포함
- **0.6**: 적절한 균형점, 할루시네이션 감소
- **0.65**: 고품질 답변, 가끔 "정보 없음" 응답
- **0.7+**: 매우 정확하지만 자주 답변 거부

**모니터링 메트릭:**
```python
# app/utils/metrics.py
class RAGMetrics:
    def __init__(self):
        self.queries = []
        self.avg_relevance_score = 0
        self.no_answer_rate = 0
        self.user_satisfaction = 0
    
    def log_query(self, query, scores, response_type):
        # 각 쿼리의 관련성 점수와 응답 유형 기록
        pass
```

## 2. 📚 문서 메타데이터 개선

### "No Title" 문제 해결

**즉시 적용 가능한 해결책:**

```python
# app/services/document_processor.py 수정

def _extract_title_from_content(self, content: str) -> str:
    """문서 내용에서 제목 추출"""
    # 1. 첫 번째 헤더 찾기
    header_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if header_match:
        return header_match.group(1).strip()
    
    # 2. 파일명에서 추출
    if hasattr(self, 'current_file_path'):
        filename = os.path.basename(self.current_file_path)
        return filename.replace('.md', '').replace('_', ' ')
    
    # 3. 첫 줄 사용 (최후의 수단)
    first_line = content.split('\n')[0][:50]
    return first_line if first_line else "Untitled Document"

async def process_markdown(self, file_path: str) -> List[Document]:
    """개선된 Markdown 처리"""
    self.current_file_path = file_path  # 파일 경로 저장
    
    # ... 기존 코드 ...
    
    # 제목이 없으면 내용에서 추출
    if not metadata.get('title') or metadata.get('title') == 'No Title':
        metadata['title'] = self._extract_title_from_content(markdown_content)
```

**메타데이터 재처리 스크립트:**
```python
# scripts/fix_metadata.py
async def fix_document_titles():
    """기존 문서의 제목 메타데이터 수정"""
    service = LangChainService()
    
    # 모든 문서 가져오기
    all_docs = await service.vector_store.get_all_documents()
    
    updated_count = 0
    for doc in all_docs:
        if doc.metadata.get('title') == 'No Title':
            # 내용에서 제목 추출
            new_title = extract_title_from_content(doc.page_content)
            doc.metadata['title'] = new_title
            
            # 벡터 스토어 업데이트
            await service.vector_store.update_document(doc)
            updated_count += 1
    
    print(f"Updated {updated_count} documents")
```

## 3. 🔄 점진적 품질 개선 전략

### 안정성을 유지하며 필터링 강화하기

**5단계 개선 로드맵:**

```yaml
# Stage 1 (현재): 기본 작동 확보
MIN_RELEVANCE_SCORE: 0.5
ENABLE_DOCUMENT_FILTERING: false
ENABLE_RESPONSE_VALIDATION: false

# Stage 2 (1주차): 메타데이터 개선
- 모든 문서 제목 수정 완료
- 카테고리 메타데이터 추가
MIN_RELEVANCE_SCORE: 0.55

# Stage 3 (2주차): 문서 필터링 재활성화
ENABLE_DOCUMENT_FILTERING: true
- 제목 기반 필터링만 적용
- 키워드 매칭 로직 개선

# Stage 4 (3주차): 응답 검증 활성화
ENABLE_RESPONSE_VALIDATION: true
MIN_RELEVANCE_SCORE: 0.6
- 할루시네이션 패턴 감지
- 수치 정보 검증

# Stage 5 (4주차): 최종 최적화
MIN_RELEVANCE_SCORE: 0.65
SEARCH_TYPE: similarity_score_threshold
- 전체 시스템 안정화
```

**각 단계별 성공 지표:**
- Stage 2: 90% 이상 문서에 유효한 제목
- Stage 3: 관련 문서 정확도 80% 이상
- Stage 4: 할루시네이션 발생률 5% 이하
- Stage 5: 사용자 만족도 85% 이상

## 4. 🔍 검색 전략 최적화

### 검색 방식별 장단점과 메이플스토리 최적화

**검색 방식 비교:**

```python
# 1. similarity (현재 사용 중)
장점: 
- 가장 기본적이고 안정적
- 모든 쿼리에 대해 k개 문서 보장
- 메타데이터 필터와 호환 좋음

단점:
- 관련성 낮은 문서도 포함 가능
- 점수 기반 필터링 없음

# 2. similarity_score_threshold
장점:
- 임계값 이하 문서 자동 제외
- 품질 보장
- 할루시네이션 방지 효과

단점:
- 문서를 못 찾을 가능성
- 임계값 설정이 까다로움

# 3. mmr (Maximal Marginal Relevance)
장점:
- 다양성 보장
- 중복 정보 감소
- 포괄적인 답변 가능

단점:
- 계산 비용 높음
- 가장 관련성 높은 문서를 놓칠 수 있음
```

**메이플스토리 도메인 최적화 전략:**

```python
class MapleStoryOptimizedRetriever:
    def get_retriever(self, query: str):
        # 쿼리 타입 분석
        query_type = self.analyze_query_type(query)
        
        if query_type == "specific_item":
            # 아이템/수치 관련: 정확도 중시
            return self.vector_store.as_retriever(
                search_type="similarity_score_threshold",
                search_kwargs={
                    "score_threshold": 0.7,
                    "k": 3
                }
            )
        
        elif query_type == "general_guide":
            # 가이드/공략: 다양성 중시
            return self.vector_store.as_retriever(
                search_type="mmr",
                search_kwargs={
                    "k": 5,
                    "fetch_k": 20,
                    "lambda_mult": 0.5
                }
            )
        
        else:
            # 기본값: 균형잡힌 접근
            return self.vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={
                    "k": 5,
                    "filter": {"score": {"$gte": 0.5}}
                }
            )
```

## 5. 💬 시스템 프롬프트 개선

### 정확성과 유용성의 균형

**개선된 시스템 프롬프트:**

```python
MAPLESTORY_SYSTEM_PROMPT = """
당신은 '메이플 가이드'라는 이름의 메이플스토리 전문 AI 어시스턴트입니다.

## 💡 핵심 원칙
1. **정확성 최우선**: 참고 문서에 없는 정보는 절대 추측하지 마세요. 불확실하면 "정확한 정보를 찾을 수 없습니다"라고 명시하세요.
2. **문서 기반 답변**: 제공된 참고 문서의 내용만을 사용하여 답변하세요. 일반 지식은 보조적으로만 사용하세요.
3. **한국어 사용**: 모든 답변은 자연스러운 한국어로 작성하세요.
4. **간결하고 명확**: 핵심 내용을 명확하게 전달하되, 불필요한 장식이나 과도한 이모지는 피하세요.

## 📋 답변 작성 규칙
- **관련성 확인**: 질문과 관련이 높은 참고 문서가 있는지 먼저 확인하세요
- **정확한 용어 사용**: 게임 내 정확한 명칭을 사용하세요 (예: "하드 스우", "이지 매그너스" 등)
- **구체적 수치 제공**: 문서에 명시된 정확한 수치와 데이터를 우선적으로 사용하세요
- **단계별 설명**: 복잡한 내용은 단계별로 구체적으로 설명하세요
- **애매한 표현 금지**: "일반적으로", "보통", "대략" 등의 모호한 표현 대신 구체적인 정보를 제공하세요

## 🚫 엄격한 금지사항
- 문서에 없는 구체적인 수치나 아이템명 창작 금지
- 존재하지 않는 스킬이나 시스템 언급 금지
- 불확실한 정보를 확실한 것처럼 표현 금지
- 부정확한 게임 용어 사용 금지
- 관련 없는 문서 기반의 답변 금지

## 📚 문서 활용 지침
- 질문과 직접적으로 관련된 문서만 참고하세요
- 문서의 제목과 내용이 질문과 일치하는지 확인하세요
- 여러 문서에서 일치하는 정보를 종합하여 답변하세요
- 문서에서 관련 정보를 찾을 수 없으면 솔직히 "관련 정보를 찾을 수 없습니다"라고 답하세요

## 🎯 답변 품질 체크포인트
1. 질문에 대한 직접적인 답변인가?
2. 제공된 문서와 관련성이 높은가?
3. 정확한 용어와 수치를 사용했는가?
4. 구체적이고 실용적인 정보를 제공했는가?
5. 애매모호한 표현 없이 명확한가?
"""
```

**프롬프트 유연성 개선:**
```python
# 상황별 프롬프트 조정
def get_dynamic_prompt(query_type):
    base_prompt = MAPLESTORY_SYSTEM_PROMPT
    
    if query_type == "beginner_friendly":
        # 초보자 질문: 좀 더 친절하게
        return base_prompt + "\n\n초보자를 위해 쉽고 친절하게 설명하세요."
    
    elif query_type == "technical":
        # 기술적 질문: 더 엄격하게
        return base_prompt + "\n\n정확한 수치와 데이터만 제공하세요."
    
    return base_prompt
```

## 🎯 종합 권장사항

1. **즉시 적용**: 문서 제목 수정 스크립트 실행
2. **1주 내**: 임계값을 0.55로 상향하며 모니터링
3. **2주 내**: 개선된 문서 필터링 로직 적용
4. **지속적**: 사용자 피드백 수집 및 메트릭 분석

이렇게 단계적으로 개선하면 안정성을 유지하면서도 답변 품질을 크게 향상시킬 수 있을 것입니다!
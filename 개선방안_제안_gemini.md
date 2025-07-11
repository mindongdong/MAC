안녕하세요! 메이플스토리 전문 RAG 챗봇 시스템의 답변 품질 문제로 고민이 많으셨군요. 제공해주신 문제 예시와 피드백을 보니, 원인을 매우 정확하게 파악하고 계십니다. 현재 챗봇이 겪는 문제는 RAG(검색 증강 생성) 시스템의 전형적인 실패 사례들이며, 충분히 개선할 수 있습니다.

제가 현재 프로젝트 구조를 파악하고, 문제의 원인을 진단한 뒤, 프로젝트에 바로 적용할 수 있는 구체적인 해결 방안을 RAG 파이프라인 단계별로 나누어 알려드리겠습니다.

### 📌 현재 문제 현상 및 원인 분석

제공해주신 예시를 통해 현재 챗봇의 문제점을 명확히 정의할 수 있습니다.

1.  **Retrieval Failure (검색 실패)**
    * **현상**: `문제 예시 1`처럼, 문서에 정답("챌린저스 코인샵")이 존재함에도 "자료가 없다"고 답변합니다. 이는 Retriever가 사용자의 질문과 가장 관련성이 높은 문서 청크(chunk)를 찾아내지 못했음을 의미합니다.
    * **원인 추정**:
        * **임베딩의 한계**: 사용 중인 임베딩 모델이 '챌린저스 코인샵'과 같은 게임 내 특정 용어의 미묘한 의미 차이를 제대로 벡터로 변환하지 못했을 수 있습니다.
        * **부적절한 검색 설정**: `app/services/vector_store.py`의 리트리버가 관련성 높은 문서를 찾기보다, 다양성(MMR)에 치중하거나 너무 많은 문서(k=8)를 참고하여 LLM에 혼란을 줄 수 있습니다.

2.  **Hallucination (환각/정보 날조)**
    * **현상**: `문제 예시 2`처럼, "이벤트 주요 보상"에 대해 답변하며 참고 문서에 없는 '레드 큐브 30개'와 같은 허위 정보를 생성합니다.
    * **원인 추정**:
        * **부정확한 Context 제공**: 검색 단계에서 질문과 관련성이 낮은 문서들이 LLM에 전달되었을 가능성이 높습니다. LLM은 주어진 부정확한 정보를 바탕으로 그럴듯한 답변을 창작해낸 것입니다.
        * **느슨한 시스템 프롬프트**: `app/chains/prompts.py`의 시스템 프롬프트가 "문서에 없으면 답변하지 말라"고 지시하지만, LLM이 이를 무시하고 답변을 생성할 만큼 제약 조건이 강하지 않을 수 있습니다.

3.  **Irrelevant Retrieval (관련 없는 문서 검색)**
    * **현상**: `문제 예시 3`처럼, "렌의 주력 스킬"에 대한 답변을 생성하며 엉뚱한 스킬("솔라 슬래시")을 언급하고, 관련 없는 문서를 참고 자료로 제시합니다.
    * **원인 추정**: 검색 시스템이 '렌', '스킬'이라는 키워드만 보고, '주력 스킬'이라는 핵심 의도를 파악하지 못한 채 관련성이 떨어지는 문서들을 우선적으로 가져온 결과입니다. 이는 검색 정확도(Precision)의 문제입니다.

결론적으로, 지적해주신 대로 **"질문과 관련 있는 문서를 정확하게 찾아 LLM에 전달"**하는 RAG의 핵심 기능이 원활하게 작동하지 않는 것이 문제입니다.

---

### 🚀 해결 방안 제안: RAG 파이프라인 개선

현재 프로젝트 코드에 기반하여 답변 품질을 높일 수 있는 구체적인 방법을 3단계로 나누어 제안합니다.

#### 1단계: Retrieval(검색) 단계 개선 (가장 시급)

가장 큰 문제인 '부정확한 문서 검색'을 해결하기 위해 리트리버의 동작 방식을 개선해야 합니다.

**1. 검색 타입 및 파라미터 최적화**

현재 `app/services/vector_store.py`의 `get_retriever` 함수는 MMR(Maximal Marginal Relevance)을 사용하여 다양한 문서를 가져오도록 설정되어 있습니다. 이는 답변의 다양성을 높이지만, 때로는 핵심적인 정답 문서의 순위를 뒤로 밀어낼 수 있습니다.

* **해결책**:
    * `search_type`을 `"similarity_score_threshold"`로 변경하여, 일정 관련성 점수 이상의 문서만 가져오도록 할 수 있습니다. 이를 통해 관련 없는 문서가 전달되는 것을 원천 차단할 수 있습니다.
    * 또는 가장 기본적인 `"similarity"`로 변경하여 순수하게 유사도가 가장 높은 문서를 가져오도록 테스트해보는 것을 추천합니다.
* **적용 방법**: `app/services/vector_store.py` 파일을 다음과 같이 수정합니다.

    ```python
    # app/services/vector_store.py

    def get_retriever(self, k: int = 5, search_type: str = "similarity_score_threshold"): # k값을 8에서 5로 줄이고, search_type 변경
        """리트리버 반환 - 관련성 강화된 검색 설정"""
        search_kwargs = {"k": k}
        
        # 유사도 점수 임계값 검색 - 가장 정확한 정보 검색에 유리
        if search_type == "similarity_score_threshold":
            search_kwargs.update({
                "score_threshold": settings.min_relevance_score  # .env 또는 config에서 0.75 등으로 설정
            })
        
        # MMR 검색은 그대로 유지하되, 관련성을 더 중시하도록 lambda_mult 조정 가능
        elif search_type == "mmr":
            search_kwargs.update({
                "fetch_k": k * 4,
                "lambda_mult": 0.8  # 0.5(다양성) ~ 1.0(유사성) 사이에서 조정
            })
        
        return self.vector_store.as_retriever(
            search_type=search_type,
            search_kwargs=search_kwargs
        )
    ```
    * `settings.py`에 `min_relevance_score: float = 0.75` 와 같이 임계값 설정을 추가하는 것이 좋습니다.

**2. 참고 문서 개수(k) 줄이기**

LLM은 너무 많은 참고 문서를 받으면 오히려 혼란스러워하며 핵심 정보를 놓칠 수 있습니다. 현재 `k=8`로 설정되어 있다면, 이를 `3~5` 사이로 줄이는 것을 강력히 권장합니다.

* **적용 방법**: `langchain_service.py`의 `create_qa_chain` 호출 부분이나 `vector_store.py`의 `get_retriever` 기본값을 수정합니다. 위 예시 코드에서 `k=5`로 이미 수정했습니다.

#### 2단계: Prompt Engineering (생성) 단계 개선

LLM이 검색된 문서를 기반으로 "정직하게" 답변을 생성하도록 시스템 프롬프트를 강화해야 합니다.

* **해결책**: 환각을 방지하고, 문서에 없는 내용에 대해서는 명확히 없다고 말하도록 지시사항을 구체적이고 단호하게 변경합니다.
* **적용 방법**: `app/chains/prompts.py`의 `MAPLESTORY_SYSTEM_PROMPT`를 다음과 같이 수정합니다.

    ```python
    # app/chains/prompts.py

    # 개선된 메이플스토리 전문 시스템 프롬프트
    MAPLESTORY_SYSTEM_PROMPT = """
    당신은 '메이플 가이드'라는 이름의 메이플스토리 전문 AI 어시스턴트입니다. 당신의 유일한 정보 출처는 아래에 제공되는 '참고 문서'입니다.

    ## 💡 핵심 원칙
    1. **엄격한 문서 기반 답변**: 답변은 반드시 '참고 문서'에 명시된 내용에만 근거해야 합니다. 당신의 사전 지식이나 외부 정보를 절대 사용하지 마세요.
    2. **정보 부재 시 명확한 답변**: 질문에 대한 답변이 '참고 문서'에 없다면, "제공된 문서에서는 해당 정보를 찾을 수 없습니다."라고만 답변하세요. 절대 정보를 추측하거나 창작하지 마세요.
    3. **정확한 용어 및 수치 사용**: 문서에 나온 게임 용어, 아이템 이름, 수치를 그대로 인용하여 정확하게 답변하세요. '하드 스우', '챌린저스 포인트 1,850점'과 같이 구체적으로 답변해야 합니다.
    4. **관련성 판단**: 질문과 가장 관련 높은 문서를 중심으로 답변을 구성하세요. 관련성이 떨어지는 문서는 무시하세요.

    ## 🚫 절대 금지사항
    - '참고 문서'에 없는 내용 추측 및 생성
    - "아마도", "대략", "일반적으로" 와 같은 모호하고 부정확한 표현 사용
    - 문서에 없는 아이템, 스킬, 수치 날조

    ---
    [참고 문서]
    {context}
    ---
    
    위 규칙을 반드시 준수하여 다음 질문에 답변하세요.
    """
    ```
    * 위 프롬프트는 LLM의 역할을 '정보 검색 및 요약'으로 명확히 한정하고, 정보가 없을 때의 행동 지침을 구체적으로 명시하여 환각 현상을 크게 줄일 수 있습니다.

#### 3단계: Indexing (색인) 단계 개선

장기적으로 답변의 정확도를 높이기 위한 근본적인 개선 방안입니다.

**1. 문서 구조를 활용한 청킹 전략**

현재 `MarkdownTextSplitter`를 사용하고 계신 것은 매우 좋은 선택입니다. Markdown의 구조(#, ## 등)를 인지하여 의미 단위로 문서를 분할하기 때문입니다.

* **해결책**: `DocumentProcessor`에서 각 청크(chunk)에 해당 내용이 어떤 섹션(예: `## 2. 하이퍼 버닝 MAX`)에 속하는지에 대한 메타데이터를 추가합니다. 이는 검색 시 더 정확한 문맥을 파악하는 데 도움을 줍니다.
* **적용 방법**: `app/services/document_processor.py`에 섹션 정보를 추출하고 메타데이터에 포함하는 로직을 추가할 수 있습니다. (현재 코드에도 `_extract_markdown_structure` 와 `_find_section_for_chunk` 함수가 구현되어 있어, 이 부분을 잘 활용하고 계십니다. 매우 훌륭한 접근입니다!)

**2. 메타데이터 필터링 활용**

`ingest_documents.py`에서 YAML 프론트매터를 파싱하여 `category`, `class` 등의 메타데이터를 저장하고 계십니다. 이를 검색 시 활용하면 정확도를 비약적으로 높일 수 있습니다.

* **해결책**: 사용자의 질문 의도를 파악하여(예: '렌'이라는 단어가 포함되면 `class: '렌'` 필터 적용) 벡터 검색 이전에 관련 문서 집합을 좁히는 '메타데이터 사전 필터링(pre-filtering)'을 구현합니다.
* **적용 방법**: 이 기능은 `app/services/langchain_service.py`의 `chat` 함수에서 구현이 필요합니다. 사용자 질문에서 키워드를 추출하여 `context`로 전달된 필터 조건에 따라 `vector_store.py`의 `get_retriever`가 Qdrant의 메타데이터 필터링 기능을 사용하도록 수정해야 합니다. 이는 다소 복잡한 작업이지만, RAG 성능을 극대화하는 가장 확실한 방법 중 하나입니다.

### 📋 종합 실행 계획

1.  **즉시 적용 (1순위)**:
    * `app/chains/prompts.py`의 `MAPLESTORY_SYSTEM_PROMPT`를 위에서 제안한 내용으로 **교체**합니다.
    * `app/services/vector_store.py`의 `get_retriever` 함수에서 `k`값을 `4` 또는 `5`로 **줄이고**, `search_type`을 `'similarity_score_threshold'`로 변경하여 테스트를 진행합니다.

2.  **테스트 및 검증 (2순위)**:
    * 변경된 설정으로 `문제 예시 1, 2, 3`을 다시 질문하여 답변 품질이 개선되었는지 확인합니다.
    * `scripts/test_rag.py`를 실행하여 전반적인 성능 저하가 없는지 체크합니다.

3.  **장기적 개선 (3순위)**:
    * 시간적 여유가 되신다면, 질문에 따라 동적으로 메타데이터 필터를 적용하는 로직을 `LangChainService`에 추가하는 것을 고려해 보세요.

이러한 개선 작업을 통해 챗봇이 더 이상 부정확한 정보를 생성하지 않고, 사용자의 의도에 맞는 정확하고 신뢰도 높은 답변을 제공할 수 있을 것입니다. 현재 프로젝트는 이미 좋은 기반을 갖추고 있으므로, 몇 가지 조정만으로도 성능을 크게 향상시킬 수 있습니다.
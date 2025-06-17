from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.chains.prompts import MAPLESTORY_QA_PROMPT, CONDENSE_PROMPT, MAPLESTORY_SYSTEM_PROMPT
from app.config.settings import settings

def create_qa_chain(llm, retriever):
    """메이플스토리 특화 QA 체인 생성 - 설정 기반 시스템 프롬프트 적용"""
    
    # 채팅 기록을 고려한 검색 프롬프트 생성
    contextualize_q_prompt = ChatPromptTemplate.from_messages([
        ("system", "Given a chat history and the latest user question which might reference context in the chat history, formulate a standalone question which can be understood without the chat history. Do NOT answer the question, just reformulate it if needed and otherwise return it as is."),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    
    # 기록을 고려한 리트리버 생성
    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_q_prompt
    )
    
    # 설정에 따라 시스템 프롬프트 선택
    if settings.use_system_prompt:
        # 새로운 전문 시스템 프롬프트 사용
        system_message = f"""{MAPLESTORY_SYSTEM_PROMPT}

## 문서 활용 지침
다음은 질문과 관련된 참고 문서입니다. 반드시 이 문서들의 내용을 우선적으로 활용하여 답변하세요:

{{context}}

**중요한 문서 선택 기준:**
1. 문서의 제목이나 내용이 질문과 직접 관련이 있는지 확인하세요
2. 질문에서 언급된 키워드(직업명, 보스명, 시스템명 등)가 문서에 포함되어 있는지 확인하세요
3. 관련 없는 문서는 무시하고, 관련성이 높은 1-2개 문서만 집중적으로 활용하세요
4. 문서에서 관련 정보를 찾을 수 없는 경우에만 "참고 문서에서 관련 정보를 찾을 수 없습니다"라고 명시하세요

**답변 작성 시 확인사항:**
- 사용한 정보가 실제로 제공된 문서에서 나온 것인지 재확인
- 정확한 게임 용어와 수치 사용 (예: "하드 스우", "챌린저스 포인트 1,850점" 등)
- 애매한 표현 대신 구체적인 설명 제공"""
    else:
        # 기존 간단한 시스템 프롬프트 사용
        system_message = """당신은 메이플스토리 전문 가이드 AI 어시스턴트입니다. 
다음 규칙을 따라 응답해주세요:

1. 항상 정확하고 최신 정보를 제공합니다
2. 게임 용어는 한국어로 사용하되, 영어 약어는 병기합니다
3. 초보자도 이해할 수 있도록 친절하게 설명합니다
4. 단계별 가이드가 필요한 경우 번호를 매겨 설명합니다
5. 관련된 팁이나 주의사항이 있다면 함께 제공합니다

참고 문서:
{context}"""
    
    # QA 프롬프트 생성
    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", system_message),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    
    # 문서 결합 체인 생성
    question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
    
    # 최종 RAG 체인 생성
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
    
    return rag_chain 
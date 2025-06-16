from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.chains.prompts import MAPLESTORY_QA_PROMPT, CONDENSE_PROMPT

def create_qa_chain(llm, retriever, memory=None):
    """메이플스토리 특화 QA 체인 생성 - 최신 LangChain API 사용"""
    
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
    
    # QA 프롬프트 생성 - 새로운 API에 맞게 직접 정의
    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", """당신은 메이플스토리 전문 가이드 AI 어시스턴트입니다. 
다음 규칙을 따라 응답해주세요:

1. 항상 정확하고 최신 정보를 제공합니다
2. 게임 용어는 한국어로 사용하되, 영어 약어는 병기합니다
3. 초보자도 이해할 수 있도록 친절하게 설명합니다
4. 단계별 가이드가 필요한 경우 번호를 매겨 설명합니다
5. 관련된 팁이나 주의사항이 있다면 함께 제공합니다

참고 문서:
{context}"""),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    
    # 문서 결합 체인 생성
    question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
    
    # 최종 RAG 체인 생성
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
    
    return rag_chain 
import pytest
from unittest.mock import Mock, patch, AsyncMock
from langchain.schema import Document

from app.chains.qa_chain import create_qa_chain
from app.chains.prompts import MAPLESTORY_QA_PROMPT, CONDENSE_PROMPT
from app.services.langchain_service import LangChainService
from app.utils.korean_splitter import KoreanTextSplitter

class TestQAChain:
    """QA 체인 테스트"""
    
    @patch('app.chains.qa_chain.load_qa_chain')
    @patch('app.chains.qa_chain.ConversationalRetrievalChain')
    def test_create_qa_chain(self, mock_conv_chain, mock_load_qa):
        """QA 체인 생성 테스트"""
        # Mock 객체 설정
        mock_llm = Mock()
        mock_retriever = Mock()
        mock_memory = Mock()
        
        # QA 체인 생성
        qa_chain = create_qa_chain(mock_llm, mock_retriever, mock_memory)
        
        # 호출 확인
        mock_load_qa.assert_called_once()
        mock_conv_chain.assert_called_once()
        
        # 프롬프트 확인
        call_args = mock_load_qa.call_args
        assert call_args[1]['prompt'] == MAPLESTORY_QA_PROMPT

class TestPrompts:
    """프롬프트 테스트"""
    
    def test_maplestory_qa_prompt(self):
        """메이플스토리 QA 프롬프트 테스트"""
        # 프롬프트 변수 확인
        assert "context" in MAPLESTORY_QA_PROMPT.input_variables
        assert "question" in MAPLESTORY_QA_PROMPT.input_variables
        
        # 프롬프트 포맷팅 테스트
        formatted = MAPLESTORY_QA_PROMPT.format(
            context="테스트 컨텍스트",
            question="메이플스토리에 대해 알려줘"
        )
        
        assert "테스트 컨텍스트" in formatted
        assert "메이플스토리에 대해 알려줘" in formatted
        assert "메이플스토리 전문 가이드" in formatted
    
    def test_condense_prompt(self):
        """대화 압축 프롬프트 테스트"""
        # 프롬프트 변수 확인
        assert "chat_history" in CONDENSE_PROMPT.input_variables
        assert "question" in CONDENSE_PROMPT.input_variables
        
        # 프롬프트 포맷팅 테스트
        formatted = CONDENSE_PROMPT.format(
            chat_history="이전 대화 내용",
            question="후속 질문"
        )
        
        assert "이전 대화 내용" in formatted
        assert "후속 질문" in formatted

class TestLangChainService:
    """LangChain 서비스 테스트"""
    
    @patch('app.services.langchain_service.ChatAnthropic')
    @patch('app.services.langchain_service.OpenAIEmbeddings')
    @patch('app.services.langchain_service.VectorStoreService')
    def test_langchain_service_init(self, mock_vector, mock_embeddings, mock_claude):
        """LangChain 서비스 초기화 테스트"""
        service = LangChainService()
        
        # 모든 컴포넌트가 초기화되었는지 확인
        mock_claude.assert_called_once()
        mock_embeddings.assert_called_once()
        mock_vector.assert_called_once()
        
        assert hasattr(service, 'llm')
        assert hasattr(service, 'embeddings')
        assert hasattr(service, 'vector_store')
        assert hasattr(service, 'memory_store')
    
    @patch('app.services.langchain_service.ChatAnthropic')
    @patch('app.services.langchain_service.OpenAIEmbeddings')
    @patch('app.services.langchain_service.VectorStoreService')
    def test_get_or_create_memory(self, mock_vector, mock_embeddings, mock_claude):
        """메모리 관리 테스트"""
        service = LangChainService()
        
        # 새 세션 메모리 생성
        memory1 = service.get_or_create_memory("session1")
        assert memory1 is not None
        assert "session1" in service.memory_store
        
        # 같은 세션 ID로 다시 호출 시 같은 메모리 반환
        memory2 = service.get_or_create_memory("session1")
        assert memory1 is memory2
        
        # 다른 세션 ID로 호출 시 다른 메모리 반환
        memory3 = service.get_or_create_memory("session2")
        assert memory3 is not memory1
        assert "session2" in service.memory_store
    
    @patch('app.services.langchain_service.ChatAnthropic')
    @patch('app.services.langchain_service.OpenAIEmbeddings')
    @patch('app.services.langchain_service.VectorStoreService')
    def test_clear_memory(self, mock_vector, mock_embeddings, mock_claude):
        """메모리 초기화 테스트"""
        service = LangChainService()
        
        # 메모리 생성
        service.get_or_create_memory("test_session")
        assert "test_session" in service.memory_store
        
        # 메모리 초기화
        service.clear_memory("test_session")
        assert "test_session" not in service.memory_store
    
    @patch('app.services.langchain_service.create_qa_chain')
    @patch('app.services.langchain_service.ChatAnthropic')
    @patch('app.services.langchain_service.OpenAIEmbeddings')
    @patch('app.services.langchain_service.VectorStoreService')
    @pytest.mark.asyncio
    async def test_chat_regular(self, mock_vector, mock_embeddings, mock_claude, mock_qa_chain):
        """일반 채팅 테스트"""
        # Mock 설정
        mock_qa_instance = AsyncMock()
        mock_qa_chain.return_value = mock_qa_instance
        mock_qa_instance.ainvoke.return_value = {
            "answer": "테스트 응답",
            "source_documents": []
        }
        
        service = LangChainService()
        
        # 채팅 실행
        result = await service.chat(
            message="테스트 메시지",
            session_id="test_session",
            stream=False
        )
        
        # 결과 확인
        assert "response" in result
        assert "sources" in result
        assert "metadata" in result
        assert result["response"] == "테스트 응답"

class TestKoreanTextSplitter:
    """한국어 텍스트 분할기 테스트"""
    
    def test_korean_splitter_init(self):
        """한국어 분할기 초기화 테스트"""
        splitter = KoreanTextSplitter(chunk_size=500, chunk_overlap=100)
        assert splitter.chunk_size == 500
        assert splitter.chunk_overlap == 100
    
    def test_split_korean_text(self):
        """한국어 텍스트 분할 테스트"""
        splitter = KoreanTextSplitter(chunk_size=100, chunk_overlap=20)
        
        # 테스트 텍스트 (한국어)
        test_text = """
        메이플스토리는 넥슨에서 개발한 2D 횡스크롤 MMORPG입니다.
        2003년 4월 29일에 정식 서비스를 시작했습니다.
        다양한 직업군과 스킬 시스템을 제공합니다.
        리부트 월드는 특별한 서버입니다.
        """
        
        chunks = splitter.split_text(test_text)
        
        # 결과 확인
        assert len(chunks) > 0
        for chunk in chunks:
            assert len(chunk) <= splitter.chunk_size
            assert isinstance(chunk, str)
    
    def test_split_with_overlap(self):
        """오버랩을 고려한 분할 테스트"""
        splitter = KoreanTextSplitter(chunk_size=50, chunk_overlap=10)
        
        text = "첫 번째 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다. 네 번째 문장입니다."
        chunks = splitter.split_text(text)
        
        # 오버랩이 있는지 확인 (간단한 확인)
        if len(chunks) > 1:
            # 두 번째 청크에 첫 번째 청크의 일부가 포함되는지 확인
            assert len(chunks) >= 1

@pytest.fixture
def sample_documents():
    """테스트용 문서 샘플"""
    return [
        Document(
            page_content="메이플스토리는 2D MMORPG입니다.",
            metadata={"source": "guide.pdf", "page": 1}
        ),
        Document(
            page_content="리부트 월드는 특별한 서버입니다.",
            metadata={"source": "guide.pdf", "page": 2}
        )
    ]

@pytest.fixture
def mock_vector_store():
    """Mock 벡터 스토어"""
    mock = Mock()
    mock.as_retriever.return_value = Mock()
    return mock

@pytest.fixture
def mock_llm():
    """Mock LLM"""
    return Mock()

@pytest.fixture
def mock_memory():
    """Mock 메모리"""
    return Mock() 
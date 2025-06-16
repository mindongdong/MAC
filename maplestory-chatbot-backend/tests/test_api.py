import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json

from app.main import app

client = TestClient(app)

class TestHealthAPI:
    """헬스체크 API 테스트"""
    
    def test_health_check(self):
        """헬스체크 엔드포인트 테스트"""
        response = client.get("/api/health/")
        assert response.status_code == 200
        assert "status" in response.json()
        assert response.json()["status"] == "healthy"

class TestChatAPI:
    """채팅 API 테스트"""
    
    @patch('app.api.chat.langchain_service')
    def test_chat_endpoint(self, mock_service):
        """채팅 엔드포인트 테스트"""
        # Mock 응답 설정
        mock_service.chat.return_value = {
            "response": "테스트 응답입니다.",
            "sources": [],
            "metadata": {"model": "claude-3-5-haiku-20241022"}
        }
        
        request_data = {
            "message": "메이플스토리에 대해 알려줘",
            "stream": False
        }
        
        response = client.post("/api/chat/", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "response" in data
        assert "session_id" in data
        assert "sources" in data
        assert "metadata" in data
    
    @patch('app.api.chat.langchain_service')
    def test_chat_with_session_id(self, mock_service):
        """세션 ID를 포함한 채팅 테스트"""
        mock_service.chat.return_value = {
            "response": "세션이 있는 응답입니다.",
            "sources": [],
            "metadata": {"model": "claude-3-5-haiku-20241022"}
        }
        
        request_data = {
            "message": "이전 대화를 기억하나요?",
            "session_id": "test-session-123",
            "stream": False
        }
        
        response = client.post("/api/chat/", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["session_id"] == "test-session-123"
    
    def test_chat_invalid_request(self):
        """잘못된 요청 테스트"""
        response = client.post("/api/chat/", json={})
        assert response.status_code == 422  # Validation error
    
    @patch('app.api.chat.langchain_service')
    def test_chat_stream_endpoint(self, mock_service):
        """스트리밍 채팅 엔드포인트 테스트"""
        async def mock_stream():
            yield "안녕하세요"
            yield " 메이플스토리"
            yield " 도우미입니다."
        
        mock_service.chat.return_value = mock_stream()
        
        request_data = {
            "message": "안녕하세요",
            "stream": True
        }
        
        response = client.post("/api/chat/stream", json=request_data)
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    def test_clear_session(self):
        """세션 초기화 테스트"""
        session_id = "test-session-clear"
        response = client.delete(f"/api/chat/session/{session_id}")
        assert response.status_code == 200
        assert "message" in response.json()

class TestDocumentsAPI:
    """문서 관리 API 테스트"""
    
    @patch('app.services.document_processor.DocumentProcessor')
    @patch('app.services.langchain_service.LangChainService')
    def test_upload_document(self, mock_service, mock_processor):
        """문서 업로드 테스트"""
        # Mock 파일 업로드
        mock_processor.return_value.process_pdf.return_value = []
        mock_service.return_value.add_documents.return_value = None
        
        # 테스트 파일 생성
        test_file_content = b"PDF file content"
        
        response = client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", test_file_content, "application/pdf")}
        )
        
        # 실제 구현에 따라 상태 코드가 다를 수 있음
        assert response.status_code in [200, 201]

class TestRootEndpoint:
    """루트 엔드포인트 테스트"""
    
    def test_root_endpoint(self):
        """루트 엔드포인트 테스트"""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data

@pytest.fixture
def mock_langchain_service():
    """LangChain 서비스 Mock"""
    with patch('app.services.langchain_service.LangChainService') as mock:
        yield mock

@pytest.fixture  
def sample_chat_request():
    """샘플 채팅 요청 데이터"""
    return {
        "message": "리부트 월드에서 나이트로드 스킬트리 알려줘",
        "user_id": "test_user",
        "stream": False
    }

@pytest.fixture
def sample_chat_response():
    """샘플 채팅 응답 데이터"""
    return {
        "response": "나이트로드는 도적 직업군의 4차 전직으로...",
        "sources": [
            {
                "title": "나이트로드 가이드.pdf",
                "page": "1",
                "content": "나이트로드 스킬트리..."
            }
        ],
        "metadata": {
            "model": "claude-3-5-haiku-20241022",
            "tokens_used": 150
        }
    } 
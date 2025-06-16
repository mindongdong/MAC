프로젝트의 기능들을 파악하고 테스트 명령어들을 제공해드리겠습니다. 먼저 프로젝트 구조와 주요 파일들을 확인해보겠습니다.
Read file: maplestory-chatbot-backend/README.md
Ran tool
Ran tool
Ran tool
Read file: maplestory-chatbot-backend/docker-compose.yml
Read file: maplestory-chatbot-backend/app/main.py

Read file: maplestory-chatbot-backend/env.example
이제 `maplestory-chatbot-backend` 프로젝트의 구조와 기능들을 파악했습니다. 다음은 프로젝트의 기능들을 테스트할 수 있는 **순차적인 명령어들**입니다:

## 1. 환경 설정 및 설치

```bash
# 프로젝트 디렉토리로 이동
cd maplestory-chatbot-backend

# 가상환경 생성 및 활성화 (권장)
python -m venv venv
source venv/bin/activate  # macOS/Linux

# 의존성 설치
pip install -r requirements.txt
```

## 2. 환경 변수 설정

```bash
# 환경 변수 파일 생성
cp env.example .env

# .env 파일 편집 (필수: ANTHROPIC_API_KEY 설정)
nano .env
```

## 3. 벡터 데이터베이스 실행

```bash
# Docker Compose로 Qdrant와 Redis 실행
docker-compose up -d qdrant redis

# 또는 개별 실행
docker run -d -p 6333:6333 qdrant/qdrant
docker run -d -p 6379:6379 redis:alpine
```

## 4. 벡터 스토어 초기화

```bash
# 벡터 스토어 설정
python scripts/setup_vectorstore.py
```

## 5. 문서 처리 및 수집

```bash
# 메타데이터 검증 (문서 구조 확인)
python scripts/validate_metadata.py

# 문서 수집 및 벡터 스토어 저장
python scripts/ingest_documents.py
```

## 6. 개별 기능 테스트

```bash
# 임베딩 기능 테스트
python scripts/test_embeddings.py

# RAG (검색-증강 생성) 시스템 테스트
python scripts/test_rag.py
```


## 7. API 서버 실행

```bash
# 개발 서버 실행
uvicorn app.main:app --reload --port 8000

# 백그라운드 실행
uvicorn app.main:app --reload --port 8000 &
```

## 8. API 테스트

```bash
# 헬스 체크
curl http://localhost:8000/health

# 기본 채팅 테스트
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "안녕하세요",
    "session_id": "test123"
  }'

# 메이플스토리 관련 질문 테스트
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "나이트로드 스킬 추천해줘",
    "session_id": "test123"
  }'

# 메타데이터 필터링 테스트
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "보스 공략법 알려줘",
    "session_id": "test123",
    "context": {
      "category": "boss_guide",
      "difficulty": "advanced"
    }
  }'
```

## 9. 자동화된 테스트 실행

```bash
# 단위 테스트 실행
python -m pytest tests/ -v

# API 테스트만 실행
python -m pytest tests/test_api.py -v

# 체인 테스트만 실행
python -m pytest tests/test_chains.py -v
```

## 10. 전체 시스템 테스트 (Docker Compose)

```bash
# 전체 시스템 Docker로 실행
docker-compose up --build

# 백그라운드 실행
docker-compose up -d --build

# 로그 확인
docker-compose logs -f app
```

## 11. API 문서 확인

```bash
# 브라우저에서 다음 URL 접속:
# http://localhost:8000/docs (Swagger UI)
# http://localhost:8000/redoc (ReDoc)
```

## 12. 성능 및 상태 모니터링

```bash
# 시스템 상태 확인
curl http://localhost:8000/health

# 문서 상태 확인
curl http://localhost:8000/documents/status

# 프로세스 시간 확인 (응답 헤더의 X-Process-Time)
curl -I http://localhost:8000/health
```

## 13. 종료 및 정리

```bash
# Docker 컨테이너 중지
docker-compose down

# 가상환경 비활성화
deactivate
```

이 순서대로 진행하시면 메이플스토리 챗봇 백엔드의 모든 기능들을 체계적으로 테스트할 수 있습니다. 각 단계에서 문제가 발생하면 로그를 확인하여 디버깅하실 수 있습니다.

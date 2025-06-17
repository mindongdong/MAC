# 메이플스토리 RAG 챗봇 백엔드 테스트 가이드

메이플스토리 RAG 챗봇 백엔드의 모든 기능들을 체계적으로 테스트할 수 있는 **완전한 순차적 명령어 가이드**입니다.

## 📋 목차

1. [환경 설정 및 설치](#1-환경-설정-및-설치)
2. [환경 변수 설정](#2-환경-변수-설정)
3. [데이터베이스 서비스 실행](#3-데이터베이스-서비스-실행)
4. [벡터 스토어 초기화](#4-벡터-스토어-초기화)
5. [문서 처리 및 수집](#5-문서-처리-및-수집)
6. [개별 기능 테스트](#6-개별-기능-테스트)
7. [API 서버 실행 및 테스트](#7-api-서버-실행-및-테스트)
8. [Discord 봇 기능 테스트](#8-discord-봇-기능-테스트)
9. [자동화된 테스트 실행](#9-자동화된-테스트-실행)
10. [Docker Compose 전체 시스템 테스트](#10-docker-compose-전체-시스템-테스트)
11. [성능 및 상태 모니터링](#11-성능-및-상태-모니터링)
12. [종료 및 정리](#12-종료-및-정리)

---

## 1. 환경 설정 및 설치

```bash
# 프로젝트 디렉토리로 이동
cd maplestory-chatbot-backend

# 가상환경 생성 및 활성화 (권장)
python -m venv venv
source venv/bin/activate  # macOS/Linux
# Windows: venv\Scripts\activate

# 의존성 설치 (Discord 봇 포함)
pip install -r requirements.txt
```

## 2. 환경 변수 설정

```bash
# 환경 변수 파일 생성
cp env.example .env

# .env 파일 편집 (필수 설정)
nano .env
```

### 필수 환경 변수 설정:

```env
# API Keys (최소한 ANTHROPIC_API_KEY 필수)
ANTHROPIC_API_KEY=your-anthropic-api-key
VOYAGE_API_KEY=your-voyage-api-key  # 권장
OPENAI_API_KEY=your-openai-api-key  # 선택사항

# Discord 봇 (선택사항)
DISCORD_BOT_TOKEN=your-discord-bot-token

# Claude 설정
CLAUDE_MODEL=claude-sonnet-4-20250514
USE_SYSTEM_PROMPT=true
ENABLE_ANSWER_TEMPLATE=true

# 벡터 스토어
QDRANT_URL=http://localhost:6333
COLLECTION_NAME=maplestory_docs

# 임베딩 설정
EMBEDDING_PROVIDER=auto  # auto, voyage, openai, local
```

## 3. 데이터베이스 서비스 실행

### 개별 서비스 실행:

```bash
# Qdrant 벡터 데이터베이스 실행
docker run -d -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant

# Redis 캐시 서버 실행
docker run -d -p 6379:6379 -v redis_data:/data redis:alpine
```

### Docker Compose 사용 (권장):

```bash
# 데이터베이스 서비스만 실행
docker-compose up -d qdrant redis

# 모든 서비스 실행
docker-compose up -d
```

### 서비스 상태 확인:

```bash
# Qdrant 연결 확인
curl http://localhost:6333/collections

# Redis 연결 확인
redis-cli ping
```

## 4. 벡터 스토어 초기화

```bash
# 벡터 스토어 설정 및 컬렉션 생성
python scripts/setup_vectorstore.py
```

## 5. 문서 처리 및 수집

```bash
# 1. 메타데이터 검증 (문서 구조 확인)
python scripts/validate_metadata.py

# 2. 문서 수집 및 벡터 스토어 저장
python scripts/ingest_documents.py

# 3. 임베딩 상태 확인
python scripts/test_embeddings.py
```

## 6. 개별 기능 테스트

### 임베딩 시스템 테스트:

```bash
# 임베딩 모델별 성능 테스트
python scripts/test_embeddings.py

# 특정 임베딩 모델 테스트
EMBEDDING_PROVIDER=voyage python scripts/test_embeddings.py
EMBEDDING_PROVIDER=openai python scripts/test_embeddings.py
EMBEDDING_PROVIDER=local python scripts/test_embeddings.py
```

### RAG 시스템 테스트:

```bash
# 종합 RAG 시스템 테스트
python scripts/test_rag.py

# 특정 카테고리 테스트
python scripts/test_rag.py --category=class_guide
python scripts/test_rag.py --category=boss_guide
```

## 7. API 서버 실행 및 테스트

### API 서버 시작:

```bash
# 개발 서버 실행
uvicorn app.main:app --reload --port 8000

# 백그라운드 실행
uvicorn app.main:app --reload --port 8000 &
```

### 기본 API 테스트:

```bash
# 헬스 체크
curl http://localhost:8000/api/health

# 상세 상태 확인
curl http://localhost:8000/api/health/status

# 문서 상태 확인
curl http://localhost:8000/api/documents/status
```

### 채팅 API 테스트:

```bash
# 기본 채팅 테스트
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "안녕하세요",
    "session_id": "test123"
  }'

# 메이플스토리 관련 질문
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "나이트로드 스킬 추천해줘",
    "session_id": "test123"
  }'

# 메타데이터 필터링 테스트
curl -X POST "http://localhost:8000/api/chat" \
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

### 스트리밍 API 테스트:

```bash
# 스트리밍 응답 테스트
curl -X POST "http://localhost:8000/api/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "리부트 월드 추천 직업",
    "session_id": "test123"
  }' \
  --no-buffer
```

## 8. Discord 봇 기능 테스트

### Discord 봇 실행:

```bash
# 방법 1: 간편 스크립트 사용 (권장)
./start_discord_bot.sh

# 방법 2: 스크립트를 통한 실행
python scripts/run_discord_bot.py

# 방법 3: 직접 실행
python discord_bot.py
```

### Discord 봇 테스트 (목킹):

```bash
# Discord 연결 없이 봇 기능 테스트
python test_discord_bot.py
```

### Discord 봇 명령어 테스트:

Discord 서버에서 다음 명령어들을 테스트하세요:

```
# 기본 명령어
!메이플 렌 스킬트리 알려줘
!스트림 리부트 월드 가이드
!진행바 하이퍼버닝 이벤트

# 관리 명령어
!리셋
!상태
!도움말

# 별명 명령어
!maple 보스 레이드 순서
!ㅁㅇㅍ 스타포스 강화 가이드
```

### Docker Compose로 Discord 봇 실행:

```bash
# 전체 시스템 (API + Discord 봇) 실행
docker-compose up -d

# Discord 봇 로그 확인
docker-compose logs -f discord-bot
```

## 9. 자동화된 테스트 실행

### 단위 테스트:

```bash
# 전체 테스트 실행
python -m pytest tests/ -v

# API 테스트만 실행
python -m pytest tests/test_api.py -v

# 체인 테스트만 실행
python -m pytest tests/test_chains.py -v

# 커버리지와 함께 실행
python -m pytest tests/ --cov=app --cov-report=html
```

### 통합 테스트:

```bash
# RAG 시스템 전체 테스트
python scripts/test_rag.py --verbose

# 임베딩 성능 테스트
python scripts/test_embeddings.py --benchmark

# 메타데이터 유효성 검사
python scripts/validate_metadata.py --strict
```

## 10. Docker Compose 전체 시스템 테스트

### 전체 시스템 실행:

```bash
# 전체 시스템 빌드 및 실행
docker-compose up --build -d

# 개발 모드로 실행 (로그 출력)
docker-compose up --build

# 특정 서비스만 실행
docker-compose up -d app qdrant redis
```

### 컨테이너 상태 확인:

```bash
# 컨테이너 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs app
docker-compose logs discord-bot
docker-compose logs qdrant
docker-compose logs redis

# 실시간 로그 모니터링
docker-compose logs -f
```

### Docker 환경에서 API 테스트:

```bash
# Docker 컨테이너 내부 API 테스트
docker-compose exec app curl http://localhost:8000/api/health

# 외부에서 Docker API 테스트
curl http://localhost:8000/api/health
```

## 11. 성능 및 상태 모니터링

### API 상태 모니터링:

```bash
# 종합 상태 확인
curl http://localhost:8000/api/health/status

# 문서 컬렉션 상태
curl http://localhost:8000/api/documents/status

# 응답 시간 확인 (헤더의 X-Process-Time)
curl -I http://localhost:8000/api/health
```

### 벡터 스토어 상태 확인:

```bash
# Qdrant 컬렉션 정보
curl http://localhost:6333/collections/maplestory_docs

# 벡터 개수 확인
curl http://localhost:6333/collections/maplestory_docs/points/count
```

### 리소스 사용량 모니터링:

```bash
# Docker 컨테이너 리소스 사용량
docker stats

# 개별 컨테이너 모니터링
docker stats maplestory-chatbot-backend-app-1
docker stats maplestory-chatbot-backend-discord-bot-1
```

### 로그 모니터링:

```bash
# 실시간 로그 확인
tail -f logs/app.log
tail -f logs/discord_bot.log

# Docker 로그
docker-compose logs -f --tail=100
```

## 12. 종료 및 정리

### 서비스 종료:

```bash
# API 서버 종료 (Ctrl+C 또는)
pkill -f "uvicorn app.main:app"

# Discord 봇 종료
pkill -f "python discord_bot.py"

# Docker 컨테이너 중지
docker-compose down

# 볼륨 포함 완전 정리
docker-compose down -v

# 이미지까지 제거
docker-compose down --rmi all -v
```

### 개발 환경 정리:

```bash
# 가상환경 비활성화
deactivate

# 캐시 정리
pip cache purge

# 임시 파일 정리
rm -rf __pycache__/ .pytest_cache/ .coverage htmlcov/
```

---

## 🔍 문제 해결 가이드

### 일반적인 문제들:

```bash
# 1. 포트 충돌 해결
lsof -ti:8000 | xargs kill -9  # API 서버 포트
lsof -ti:6333 | xargs kill -9  # Qdrant 포트
lsof -ti:6379 | xargs kill -9  # Redis 포트

# 2. Docker 네트워크 문제
docker network prune
docker-compose down && docker-compose up -d

# 3. 벡터 스토어 초기화
docker-compose down -v
docker-compose up -d qdrant
python scripts/setup_vectorstore.py
python scripts/ingest_documents.py

# 4. 의존성 문제
pip install --upgrade -r requirements.txt
```

### 환경별 설정:

```bash
# 개발 환경
export DEBUG_MODE=true
export LOG_LEVEL=DEBUG

# 프로덕션 환경
export DEBUG_MODE=false
export LOG_LEVEL=INFO
export CORS_ORIGINS='["https://yourdomain.com"]'
```

---

## 📊 테스트 체크리스트

### ✅ 필수 테스트 항목:

- [ ] 환경 변수 설정 완료
- [ ] Qdrant & Redis 서비스 실행
- [ ] 벡터 스토어 초기화
- [ ] 문서 수집 및 임베딩
- [ ] API 서버 헬스 체크
- [ ] 기본 채팅 API 테스트
- [ ] 스트리밍 API 테스트
- [ ] Discord 봇 연결 (선택사항)
- [ ] 단위 테스트 통과
- [ ] Docker Compose 실행

### 🔧 성능 테스트 항목:

- [ ] 임베딩 모델별 성능 비교
- [ ] RAG 응답 시간 측정
- [ ] 동시 사용자 부하 테스트
- [ ] 메모리 사용량 모니터링
- [ ] 스트리밍 응답 안정성

이 가이드를 순서대로 따라하시면 메이플스토리 RAG 챗봇 백엔드의 모든 기능을 체계적으로 테스트하실 수 있습니다. 각 단계에서 문제가 발생하면 문제 해결 가이드를 참고하세요.

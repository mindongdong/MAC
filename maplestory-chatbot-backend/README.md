# 메이플스토리 AI 챗봇 백엔드

메이플스토리 가이드 문서를 기반으로 한 AI 챗봇 백엔드 서비스입니다. **Markdown 기반 RAG (Retrieval-Augmented Generation)** 시스템을 사용하여 정확하고 유용한 게임 정보를 제공합니다.

## 🚀 주요 기능

- **📝 Markdown 기반 문서 처리**: PDF 대신 Markdown으로 더 빠르고 정확한 처리
- **🔍 스마트 메타데이터 관리**: 유연한 카테고리와 태그 시스템
- **🎯 정밀한 검색**: 직업, 콘텐츠 타입, 난이도별 필터링
- **⚡ 고성능 벡터 검색**: Qdrant를 활용한 의미 기반 검색
- **🔧 확장 가능한 구조**: 새로운 문서 타입 쉽게 추가 가능

## 📁 프로젝트 구조

```
maplestory-chatbot-backend/
├── app/
│   ├── config/
│   │   ├── metadata_config.py    # 메타데이터 설정 (유연한 구조)
│   │   └── __init__.py
│   ├── services/
│   │   ├── document_processor.py  # Markdown + PDF 처리기
│   │   ├── vector_store.py
│   │   └── langchain_service.py
│   ├── api/
│   ├── models/
│   └── main.py
├── data/
│   ├── markdown/                  # 🆕 Markdown 문서 저장소
│   │   ├── class_guides/         # 직업 가이드
│   │   ├── boss_guides/          # 보스 공략
│   │   ├── system_guides/        # 시스템 가이드
│   │   ├── farming_guides/       # 사냥터 가이드
│   │   ├── equipment_guides/     # 장비 가이드
│   │   └── enhancement_guides/   # 강화 가이드
│   └── pdfs/                     # 기존 PDF 지원
├── scripts/
│   ├── ingest_documents.py       # 🔄 문서 수집 (Markdown 우선)
│   ├── test_rag.py              # 🧪 RAG 테스트
│   ├── validate_metadata.py     # 🆕 메타데이터 검증
│   └── setup_vectorstore.py
└── requirements.txt
```

## 🛠️ 설치 및 설정

### 1. 환경 설정

```bash
# 저장소 클론
git clone <repository-url>
cd maplestory-chatbot-backend

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정

```bash
# .env 파일 생성
cp env.example .env

# .env 파일 편집
ANTHROPIC_API_KEY=your_anthropic_api_key
VOYAGE_API_KEY=your_voyage_api_key  # 임베딩용 (권장)
OPENAI_API_KEY=your_openai_api_key  # 임베딩용 (선택사항)
QDRANT_URL=http://localhost:6333
```

### 3. 임베딩 모델 설정

프로젝트는 다양한 임베딩 모델을 지원합니다 (우선순위 순):

1. **Voyage AI (권장)**: `voyage-3.5-lite` 모델 사용

   - 최신 1024차원 임베딩
   - 한국어 지원 우수
   - 높은 성능과 품질

2. **OpenAI**: `text-embedding-ada-002` 모델

   - 1536차원 임베딩
   - 안정적인 성능

3. **로컬 모델**: HuggingFace 모델
   - 인터넷 연결 불필요
   - 무료 사용 가능

설정에서 `EMBEDDING_PROVIDER=auto`로 설정하면 자동으로 우선순위에 따라 선택됩니다.

### 4. Qdrant 벡터 데이터베이스 실행

```bash
# Docker로 Qdrant 실행
docker run -p 6333:6333 qdrant/qdrant

# 또는 docker-compose 사용
docker-compose up -d
```

## 📝 문서 작성 가이드

### Markdown 문서 구조

모든 Markdown 문서는 YAML 프론트매터를 포함해야 합니다:

```markdown
---
title: 문서 제목 (필수)
category: class_guide (필수)
author: 작성자명
created_date: 2024-01-15
updated_date: 2024-01-20
game_version: latest
difficulty: medium # beginner, intermediate, advanced
server_type: both # 리부트, 일반, both
class: 나이트로드 # 직업 가이드인 경우
content_type: 5차스킬 # 콘텐츠 타입
tags:
  - 태그1
  - 태그2
keywords:
  - 키워드1
  - 키워드2
---

# 문서 내용

여기에 Markdown으로 내용을 작성합니다...
```

### 지원하는 카테고리

- `class_guide`: 직업 가이드
- `boss_guide`: 보스 공략
- `system_guide`: 시스템 가이드
- `farming_guide`: 사냥터 가이드
- `equipment_guide`: 장비 가이드
- `enhancement_guide`: 강화 가이드

### 파일 배치 예시

```
data/markdown/
├── class_guides/
│   ├── 나이트로드_5차스킬_가이드.md
│   ├── 보우마스터_스킬빌드.md
│   └── 아크메이지_사냥가이드.md
├── boss_guides/
│   ├── 카오스벨룸_공략.md
│   ├── 하드윌_공략.md
│   └── 루시드_파티플레이.md
└── system_guides/
    ├── 스타포스_강화가이드.md
    └── 잠재능력_세팅.md
```

## 🚀 실행 방법

### 1. 문서 수집

```bash
# Markdown 파일을 data/markdown/ 디렉토리에 배치 후 실행
python scripts/ingest_documents.py
```

### 2. 메타데이터 검증

```bash
# 문서의 메타데이터 검증
python scripts/validate_metadata.py
```

### 3. 서버 실행

```bash
# 개발 서버 실행
uvicorn app.main:app --reload

# 프로덕션 서버 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 4. 테스트

```bash
# RAG 시스템 테스트
python scripts/test_rag.py
```

## 🧪 API 사용 예시

### 기본 질문

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "나이트로드 5차 스킬 추천해줘",
    "session_id": "user123"
  }'
```

### 메타데이터 필터링

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "보스 공략법 알려줘",
    "session_id": "user123",
    "context": {
      "category": "boss_guide",
      "difficulty": "advanced"
    }
  }'
```

## 🔧 커스터마이징

### 메타데이터 설정 수정

`app/config/metadata_config.py`에서 메타데이터 규칙을 수정할 수 있습니다:

```python
class MetadataConfig(BaseModel):
    # 필수 필드 추가/제거
    required_fields: List[str] = ["title", "category"]

    # 새로운 카테고리 추가
    category_aliases: Dict[str, str] = {
        "새카테고리": "new_guide",
        # ...
    }

    # 새로운 직업 추가
    available_classes: List[str] = [
        "새직업",
        # ...
    ]
```

### 새로운 문서 타입 지원

`app/services/document_processor.py`에서 새로운 파일 형식을 추가할 수 있습니다:

```python
async def process_json(self, file_path: str) -> List[Document]:
    """JSON 파일 처리"""
    # 구현...

async def process_file(self, file_path: str) -> List[Document]:
    if file_path.endswith('.json'):
        return await self.process_json(file_path)
    # 기존 로직...
```

## 📊 성능 비교

| 항목            | PDF 기반 | Markdown 기반 |
| --------------- | -------- | ------------- |
| 처리 속도       | ~2초/MB  | ~0.3초/MB     |
| 메타데이터 추출 | 어려움   | 매우 쉬움     |
| 청킹 정확도     | 보통     | 매우 좋음     |
| 버전 관리       | 불가능   | Git 지원      |
| 편집 용이성     | 어려움   | 매우 쉬움     |

## 🛠️ 개발 도구

### 유용한 스크립트

```bash
# 메타데이터 일괄 업데이트
python scripts/update_metadata.py

# 문서 통계 확인
python scripts/document_stats.py

# 벡터 스토어 상태 확인
python scripts/check_vectorstore.py
```

### 디버깅

로그 레벨을 DEBUG로 설정하여 자세한 정보를 확인할 수 있습니다:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🤝 기여하기

1. 새로운 가이드 문서 작성
2. 메타데이터 스키마 개선
3. 새로운 기능 제안
4. 버그 리포트

### 문서 작성 가이드라인

- 정확한 메타데이터 포함
- 명확한 제목과 구조
- 실용적인 정보 제공
- 최신 게임 버전 반영

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 제공됩니다.

## 🆘 문제 해결

### 자주 발생하는 문제

**Q: 문서가 검색되지 않아요**
A: 메타데이터가 올바르게 설정되었는지 `validate_metadata.py`로 확인해보세요.

**Q: Qdrant 연결 오류가 발생해요**
A: Docker로 Qdrant가 실행 중인지 확인하고, 포트 6333이 열려있는지 확인하세요.

**Q: 임베딩 생성이 느려요**
A: OpenAI API 키가 올바르게 설정되었는지 확인하세요.

---

📚 더 자세한 정보는 [개발 문서](docs/)를 참조하세요.
🐛 버그 리포트나 기능 제안은 [Issues](../../issues)에 남겨주세요.

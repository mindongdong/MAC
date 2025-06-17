# Voyage AI 임베딩 설정 가이드

메이플스토리 챗봇 백엔드에서 Voyage AI의 `voyage-3.5-lite` 모델을 사용하는 방법을 안내합니다.

## 🚀 Voyage AI 장점

- **고품질**: 최신 임베딩 기술로 한국어 지원 우수
- **효율성**: 1024차원으로 저장 공간 최적화
- **성능**: 빠른 응답 속도와 정확한 검색 결과
- **비용**: OpenAI 대비 경쟁력 있는 가격

## 📋 설정 단계

### 1. Voyage AI API 키 발급

1. [Voyage AI 대시보드](https://dash.voyageai.com)에 접속
2. 계정 생성 또는 로그인
3. **API keys** 섹션으로 이동
4. **Create new secret key** 버튼 클릭
5. API 키 복사 및 안전한 곳에 저장

### 2. 환경 변수 설정

`.env` 파일에 다음 내용을 추가:

```bash
# Voyage AI 설정
VOYAGE_API_KEY=your_voyage_api_key_here

# 임베딩 제공자 설정 (auto = Voyage AI 우선 사용)
EMBEDDING_PROVIDER=auto
VOYAGE_MODEL=voyage-3.5-lite
```

### 3. 의존성 설치

```bash
pip install voyageai>=0.2.3
```

### 4. 설정 확인

```bash
# 임베딩 테스트 실행
python scripts/test_embeddings.py
```

## 🔧 사용법

### 기본 사용

환경 변수 설정 후 프로젝트를 실행하면 자동으로 Voyage AI가 선택됩니다:

```bash
# 문서 재수집 (새로운 임베딩 모델 적용)
python scripts/ingest_documents.py

# 서버 실행
uvicorn app.main:app --reload

# 테스트
python scripts/test_rag.py
```

### Rate Limit 관리

Voyage AI Rate Limits:

- **Tier 1**: 2000 RPM, 8M TPM
- **Tier 2**: 4000 RPM, 16M TPM (>$100 사용)
- **Tier 3**: 6000 RPM, 24M TPM (>$1000 사용)

## 🔄 마이그레이션

기존 모델에서 Voyage AI로 전환:

```bash
# 1. 환경 변수 설정
echo "VOYAGE_API_KEY=your_api_key_here" >> .env

# 2. 벡터 스토어 재구성
python scripts/setup_vectorstore.py --recreate

# 3. 문서 재수집
python scripts/ingest_documents.py --force-recreate

# 4. 테스트
python scripts/test_embeddings.py
```

## 🛠️ 문제 해결

### API 키 오류

```bash
# 환경 변수 확인
echo $VOYAGE_API_KEY
```

### 차원 불일치

Voyage AI는 1024차원을 사용합니다. 기존 벡터 스토어와 차원이 다를 경우 컬렉션 재생성이 필요합니다.

## 📊 성능 비교

| 모델                   | 차원    | 성능       | 비용   | 한국어 지원 |
| ---------------------- | ------- | ---------- | ------ | ----------- |
| voyage-3.5-lite        | 1024    | ⭐⭐⭐⭐⭐ | 💰💰   | ⭐⭐⭐⭐⭐  |
| text-embedding-ada-002 | 1536    | ⭐⭐⭐⭐   | 💰💰💰 | ⭐⭐⭐⭐    |
| 로컬 모델              | 384-768 | ⭐⭐⭐     | 무료   | ⭐⭐⭐      |

## 🔗 참고 자료

- [Voyage AI 공식 문서](https://docs.voyageai.com/)
- [프로젝트 내 voyage_api_document.md](voyage_api_document.md)
- [임베딩 모델 비교](https://docs.voyageai.com/docs/embeddings)

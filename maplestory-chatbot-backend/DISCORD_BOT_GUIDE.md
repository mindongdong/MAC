# 🤖 메이플스토리 RAG 챗봇 디스코드 봇 가이드

FastAPI 기반 메이플스토리 RAG 챗봇을 디스코드에서 사용할 수 있는 봇 기능을 제공합니다.
**실시간 스트리밍 응답**과 **진행바 표시** 기능을 지원합니다!

## 📋 목차

1. [디스코드 봇 생성](#-디스코드-봇-생성)
2. [환경 설정](#-환경-설정)
3. [실행 방법](#-실행-방법)
4. [사용법](#-사용법)
5. [스트리밍 기능](#-스트리밍-기능)
6. [문제 해결](#-문제-해결)

## 🎯 디스코드 봇 생성

### 1. Discord Developer Portal 접속
1. [Discord Developer Portal](https://discord.com/developers/applications)에 접속
2. "New Application" 클릭하여 새 애플리케이션 생성
3. 애플리케이션 이름 입력 (예: "메이플 가이드 봇")

### 2. 봇 생성
1. 좌측 메뉴에서 "Bot" 클릭
2. "Add Bot" 클릭
3. 봇 이름과 아바타 설정

### 3. 봇 토큰 복사
1. "Token" 섹션에서 "Copy" 클릭하여 토큰 복사
2. **⚠️ 토큰을 안전하게 보관하세요 (공개하지 마세요)**

### 4. 봇 권한 설정
1. "OAuth2" → "URL Generator" 메뉴 선택
2. **Scopes**: `bot` 체크
3. **Bot Permissions**:
   - Send Messages
   - Use Slash Commands
   - Embed Links
   - Read Message History
   - Use External Emojis
4. 생성된 URL로 봇을 서버에 초대

## ⚙️ 환경 설정

### 1. 환경변수 설정

`.env` 파일에 다음 항목을 추가하세요:

```env
# Discord Bot 설정
DISCORD_BOT_TOKEN=your-discord-bot-token-here
API_URL=http://localhost:8000

# 기존 API 설정
ANTHROPIC_API_KEY=your-anthropic-api-key
OPENAI_API_KEY=your-openai-api-key
QDRANT_URL=http://localhost:6333
REDIS_URL=redis://localhost:6379
```

### 2. 의존성 설치

디스코드 봇 관련 패키지가 이미 `requirements.txt`에 포함되어 있습니다:

```bash
pip install -r requirements.txt
```

## 🚀 실행 방법

### 방법 1: Docker Compose 사용 (권장)

```bash
# 전체 서비스 (API + Discord Bot) 실행
docker-compose up -d

# 로그 확인
docker-compose logs discord-bot
```

### 방법 2: 로컬 실행

```bash
# 1. FastAPI 서버 실행 (별도 터미널)
cd maplestory-chatbot-backend
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 2. 디스코드 봇 실행 (새 터미널)
python scripts/run_discord_bot.py
```

### 방법 3: 직접 실행

```bash
# FastAPI 서버가 실행 중인 상태에서
python discord_bot.py
```

## 💬 사용법

### 기본 명령어

| 명령어 | 설명 | 예시 |
|--------|------|------|
| `!메이플 [질문]` | 일반 답변 (빠른 응답) | `!메이플 렌 스킬트리 알려줘` |
| `!스트림 [질문]` | **실시간 스트리밍 답변** | `!스트림 리부트 월드 가이드` |
| `!진행바 [질문]` | **프로그레스 바 표시** | `!진행바 하이퍼버닝 이벤트` |
| `!리셋` | 대화 기록 초기화 | `!리셋` |
| `!도움말` | 봇 사용법 표시 | `!도움말` |
| `!상태` | 봇 및 API 서버 상태 확인 | `!상태` |

### 별명 명령어

- `!maple`, `!ㅁㅇㅍ` → `!메이플`
- `!stream`, `!ㅅㅌㄹ` → `!스트림`
- `!progress`, `!ㅈㅎㅂ` → `!진행바`
- `!reset`, `!clear` → `!리셋`
- `!help`, `!commands` → `!도움말`
- `!status`, `!ping` → `!상태`

### 질문 예시

```
# 일반 응답 (빠른 결과)
!메이플 렌 직업 어때?
!메이플 스타포스 22성 비용은?

# 실시간 스트리밍 (생성 과정 확인)
!스트림 리부트 월드 추천 직업은?
!스트림 챌린저스 서버 가이드

# 진행바 표시 (단계별 진행 상황)
!진행바 하이퍼버닝 이벤트 정보
!진행바 보스 레이드 순서 알려줘
```

## ✨ 스트리밍 기능

### 🔴 실시간 스트리밍 (`!스트림`)

답변 생성 과정을 실시간으로 확인할 수 있습니다:

1. **질문 분석 단계** (🔍 질문을 분석하고 있습니다...)
2. **문서 검색 단계** (📚 관련 문서를 검색하고 있습니다...)
3. **답변 생성 단계** (🤔 최적의 답변을 생성하고 있습니다...)
4. **실시간 답변 작성** (✍️ 답변을 작성하고 있습니다...)
5. **최종 완료** (✅ 완료)

**특징:**
- 답변이 생성되는 과정을 실시간으로 확인
- 긴 답변도 자연스럽게 스트리밍
- 네트워크 지연 시에도 진행 상황 파악 가능

### 📊 진행바 표시 (`!진행바`)

시각적인 프로그레스 바로 처리 상황을 확인할 수 있습니다:

```
🔄 진행 상황
🟦🟦🟦🟦🟦🟦🟦⬜⬜⬜ 70%
```

**진행 단계:**
1. 질문 분석 (10%)
2. 문서 검색 (30%)
3. 정보 추출 (50%)
4. 답변 생성 (70%)
5. 최종 검토 (90%)
6. 완료 (100%)

### 🆚 응답 방식 비교

| 기능 | 속도 | 시각적 피드백 | 권장 사용 |
|------|------|---------------|-----------|
| `!메이플` | ⚡ 빠름 | 타이핑 표시만 | 간단한 질문 |
| `!스트림` | 🐌 보통 | ✨ 실시간 텍스트 | 복잡한 질문, 긴 답변 |
| `!진행바` | 🐌 보통 | 📊 프로그레스 바 | 처리 과정 확인 필요 시 |

## 🔧 설정 옵션

### discord_bot.py 설정

```python
# 환경변수
API_URL = os.getenv("API_URL", "http://localhost:8000")
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# 봇 설정
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# 타임아웃 설정
timeout = aiohttp.ClientTimeout(total=60)  # 60초
```

### 스트리밍 옵션 조정

```python
# discord_bot.py 내부 설정
class MapleBot:
    async def ask_chatbot_stream(self, ...):
        # 업데이트 빈도 조정
        should_update = (
            current_time - last_update_time >= 3 or  # 3초마다
            update_counter % 10 == 0 or             # 10개 청크마다
            any(end in chunk_buffer for end in ['.', '!', '?', '\n'])  # 문장 끝
        )
```

### Docker Compose 설정

```yaml
discord-bot:
  build: .
  command: ["python", "discord_bot.py"]
  environment:
    - DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN}
    - API_URL=http://app:8000  # 내부 네트워크 주소
  depends_on:
    - app
  restart: unless-stopped
```

## 🛠️ 문제 해결

### 일반적인 문제

#### 1. 봇이 서버에 접속하지 않음
- Discord Bot Token이 올바른지 확인
- 봇이 서버에 초대되었는지 확인
- 인터넷 연결 상태 확인

#### 2. API 서버 연결 실패
```
⚠️ API 서버 연결 실패: [Errno 111] Connection refused
```
- FastAPI 서버가 실행 중인지 확인: `curl http://localhost:8000/api/health`
- API_URL 환경변수가 올바른지 확인

#### 3. 스트리밍 응답이 작동하지 않음
```
❌ 서버 오류 (404): /api/chat/stream 엔드포인트를 찾을 수 없습니다
```
- FastAPI 서버에 `/api/chat/stream` 엔드포인트가 있는지 확인
- 스트리밍 기능이 활성화되어 있는지 확인

#### 4. 메시지 편집 속도 제한
```
discord.errors.HTTPException: 429 Too Many Requests
```
- Discord API 편집 속도 제한 (정상적인 현상)
- 봇이 자동으로 처리하므로 무시해도 됨

#### 5. 권한 오류
```
discord.errors.Forbidden: 403 Forbidden (error code: 50013)
```
- 봇이 메시지를 보낼 권한이 있는지 확인
- 채널 권한 설정 확인

#### 6. 의존성 오류
```
ModuleNotFoundError: No module named 'discord'
```
```bash
pip install discord.py aiohttp python-dotenv
```

### 로그 확인

#### Docker 로그
```bash
# 전체 로그
docker-compose logs discord-bot

# 실시간 로그
docker-compose logs -f discord-bot
```

#### 로컬 실행 로그
로그는 콘솔에 출력되며, 다음 수준으로 제어됩니다:
- INFO: 일반 정보
- WARNING: 경고
- ERROR: 오류

### 디버그 모드

디버그 정보를 더 자세히 보려면:

```python
# discord_bot.py 상단에 추가
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📈 성능 최적화

### 1. 스트리밍 최적화
- 업데이트 빈도 조정: 너무 자주 업데이트하면 Discord API 제한에 걸림
- 청크 버퍼링: 작은 청크들을 모아서 한 번에 업데이트
- 문장 단위 업데이트: 자연스러운 읽기 경험 제공

### 2. 메모리 관리
- 세션 정리: 비활성 사용자 세션 자동 정리
- 캐시 최적화: Redis 캐시 활용

### 3. 응답 시간 최적화
- API 타임아웃 조정
- 비동기 처리 최적화

### 4. 에러 처리
- 재시도 로직 구현
- Graceful shutdown

## 🔒 보안 고려사항

1. **토큰 관리**
   - Discord Bot Token을 코드에 하드코딩하지 마세요
   - `.env` 파일을 `.gitignore`에 추가하세요

2. **API 보안**
   - API 서버에 적절한 인증 추가 고려
   - Rate limiting 구현

3. **사용자 데이터**
   - 개인정보 로깅 금지
   - 세션 데이터 암호화 고려

4. **스트리밍 보안**
   - 스트리밍 중 민감한 정보 노출 방지
   - 응답 내용 사전 필터링

## 📚 추가 자료

- [Discord.py 공식 문서](https://discordpy.readthedocs.io/)
- [Discord Developer Portal](https://discord.com/developers/docs/)
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [Server-Sent Events (SSE)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)

## 🤝 기여하기

디스코드 봇 기능 개선을 위한 제안이나 버그 리포트는 언제든 환영합니다!

1. 이슈 생성
2. 기능 제안
3. Pull Request 제출

## 📝 버전 히스토리

### v2.0 (현재)
- ✨ 실시간 스트리밍 응답 추가
- 📊 프로그레스 바 표시 기능
- 🔄 향상된 사용자 경험

### v1.0
- 🤖 기본 디스코드 봇 기능
- 💬 일반 질의응답
- 🧠 세션 메모리 관리 
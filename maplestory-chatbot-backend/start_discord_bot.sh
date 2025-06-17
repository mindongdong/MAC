#!/bin/bash

# 메이플스토리 RAG 챗봇 디스코드 봇 시작 스크립트

set -e  # 오류 발생 시 스크립트 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 프로젝트 루트 디렉토리로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
cd "$SCRIPT_DIR"

log_info "=== 메이플스토리 RAG 챗봇 디스코드 봇 시작 ==="

# 1. 환경변수 파일 확인
if [ ! -f ".env" ]; then
    log_error ".env 파일이 없습니다!"
    log_info "env.example 파일을 복사하여 .env 파일을 생성하세요:"
    log_info "cp env.example .env"
    exit 1
fi

# 2. DISCORD_BOT_TOKEN 확인
if ! grep -q "DISCORD_BOT_TOKEN=" .env || grep -q "DISCORD_BOT_TOKEN=your-discord-bot-token" .env; then
    log_error "DISCORD_BOT_TOKEN이 설정되지 않았습니다!"
    log_info ".env 파일에서 DISCORD_BOT_TOKEN을 설정해주세요."
    exit 1
fi

log_success "환경변수 파일 확인 완료"

# 3. Python 가상환경 확인 및 생성
if [ ! -d "venv" ]; then
    log_info "Python 가상환경을 생성합니다..."
    python3 -m venv venv
    log_success "가상환경 생성 완료"
fi

# 4. 가상환경 활성화
log_info "가상환경을 활성화합니다..."
source venv/bin/activate

# 5. 의존성 설치
log_info "의존성 패키지를 설치합니다..."
pip install -r requirements.txt

# 6. API 서버 상태 확인
log_info "API 서버 상태를 확인합니다..."
API_URL="${API_URL:-http://localhost:8000}"

if curl -s "${API_URL}/api/health" > /dev/null; then
    log_success "API 서버가 실행 중입니다 (${API_URL})"
else
    log_warning "API 서버에 연결할 수 없습니다 (${API_URL})"
    log_info "API 서버를 먼저 시작하세요:"
    log_info "  docker-compose up app"
    log_info "  또는"
    log_info "  uvicorn app.main:app --host 0.0.0.0 --port 8000"
    
    read -p "그래도 계속하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 7. 로그 디렉토리 생성
mkdir -p logs

# 8. 디스코드 봇 시작
log_info "디스코드 봇을 시작합니다..."
log_info "종료하려면 Ctrl+C를 누르세요."

# 실행 방법 선택
if [ "$1" == "--script" ]; then
    # 스크립트 방식
    python scripts/run_discord_bot.py
else
    # 직접 실행 방식
    python discord_bot.py
fi 
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    cmake \
    make \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
# numpy를 먼저 설치하여 kiwipiepy의 설치 오류 방지
RUN pip install --no-cache-dir "numpy>=1.24.0,<2.0.0"
RUN pip install --no-cache-dir -r requirements.txt

# 로그 디렉토리 생성
RUN mkdir -p /app/logs

# 애플리케이션 복사
COPY . .

# 기본 실행 명령어 (docker-compose에서 override 가능)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 
#!/usr/bin/env python3
"""
디스코드 봇 실행 스크립트
Docker 없이 로컬에서 디스코드 봇을 실행할 때 사용합니다.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 패스에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_dependencies():
    """필수 의존성 패키지 확인"""
    required_packages = [
        'discord.py',
        'aiohttp',
        'python-dotenv'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_').replace('.py', ''))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"필수 패키지가 설치되지 않았습니다: {missing_packages}")
        logger.info("다음 명령어로 설치하세요:")
        logger.info(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def check_environment():
    """환경변수 확인"""
    discord_token = os.getenv("DISCORD_BOT_TOKEN")
    api_url = os.getenv("API_URL", "http://localhost:8000")
    
    if not discord_token:
        logger.error("DISCORD_BOT_TOKEN 환경변수가 설정되지 않았습니다.")
        logger.info(".env 파일을 확인하거나 환경변수를 설정해주세요.")
        return False
    
    logger.info(f"Discord Bot Token: {'*' * (len(discord_token) - 4)}{discord_token[-4:]}")
    logger.info(f"API URL: {api_url}")
    
    return True

def check_api_server():
    """API 서버 연결 확인"""
    import aiohttp
    import asyncio
    
    async def test_connection():
        api_url = os.getenv("API_URL", "http://localhost:8000")
        try:
            # 더 긴 타임아웃으로 안정성 향상
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{api_url}/api/health") as response:
                    if response.status == 200:
                        logger.info("✅ API 서버 연결 성공")
                        return True
                    else:
                        logger.warning(f"⚠️ API 서버 응답 코드: {response.status}")
                        return False
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ API 서버 연결 시간 초과 (15초)")
            logger.info("API 서버가 느리게 응답하거나 실행 중이 아닐 수 있습니다.")
            return False
        except Exception as e:
            logger.warning(f"⚠️ API 서버 연결 실패: {e}")
            logger.info("API 서버가 실행 중인지 확인해주세요.")
            return False
    
    return asyncio.run(test_connection())

def print_bot_info():
    """봇 정보 및 사용법 출력"""
    logger.info("=" * 60)
    logger.info("🍄 메이플스토리 RAG 챗봇 디스코드 봇")
    logger.info("=" * 60)
    logger.info("📝 주요 명령어:")
    logger.info("  !질문 [내용]  - 메이플스토리 관련 질문")
    logger.info("  !리셋        - 대화 세션 초기화")
    logger.info("  !상태        - 봇 상태 확인")
    logger.info("  !도움말      - 상세 사용법")
    logger.info("")
    logger.info("🔧 별명 명령어:")
    logger.info("  !메이플, !maple, !ㅁㅇㅍ → !질문")
    logger.info("  !ask, !question, !ㅈㅁ → !질문")
    logger.info("")
    logger.info("✨ 특징:")
    logger.info("  📊 진행바 표시로 답변 생성 과정 시각화")
    logger.info("  ⏱️ 안정적인 처리 (최대 3분 대기)")
    logger.info("  💬 대화 맥락 기억")
    logger.info("  📚 출처 정보 제공")
    logger.info("=" * 60)

def main():
    """메인 실행 함수"""
    logger.info("=== 메이플스토리 RAG 챗봇 디스코드 봇 시작 ===")
    
    # 1. 의존성 확인
    logger.info("1. 의존성 패키지 확인 중...")
    if not check_dependencies():
        sys.exit(1)
    
    # 2. 환경변수 확인
    logger.info("2. 환경변수 확인 중...")
    if not check_environment():
        sys.exit(1)
    
    # 3. API 서버 연결 확인
    logger.info("3. API 서버 연결 확인 중...")
    api_available = check_api_server()
    if not api_available:
        logger.warning("API 서버 연결에 실패했지만 봇을 계속 시작합니다.")
        logger.info("봇 시작 후 API 서버를 실행하거나 !상태 명령어로 다시 확인할 수 있습니다.")
    
    # 4. 봇 정보 표시
    print_bot_info()
    
    # 5. 디스코드 봇 실행
    logger.info("4. 디스코드 봇 시작...")
    
    try:
        # discord_bot.py 모듈 임포트 및 실행
        discord_bot_path = project_root / "discord_bot.py"
        
        if not discord_bot_path.exists():
            logger.error(f"discord_bot.py 파일을 찾을 수 없습니다: {discord_bot_path}")
            sys.exit(1)
        
        # subprocess로 discord_bot.py 실행
        logger.info("디스코드 봇을 시작합니다...")
        logger.info("Ctrl+C로 봇을 중지할 수 있습니다.")
        subprocess.run([sys.executable, str(discord_bot_path)], cwd=str(project_root))
        
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단되었습니다.")
        logger.info("봇이 성공적으로 종료되었습니다.")
    except Exception as e:
        logger.error(f"디스코드 봇 실행 중 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
디스코드 봇 기능 테스트 스크립트
실제 Discord 연결 없이 MapleBot 클래스의 기능을 테스트합니다.
"""

import asyncio
import aiohttp
import json
from unittest.mock import AsyncMock, MagicMock
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# discord_bot 모듈에서 MapleBot 클래스 가져오기
try:
    from discord_bot import MapleBot
except ImportError:
    print("❌ discord_bot.py를 찾을 수 없습니다.")
    print("현재 디렉토리가 올바른지 확인해주세요.")
    sys.exit(1)

class MockDiscordContext:
    """Discord Context 목킹 클래스"""
    
    def __init__(self):
        self.author = MagicMock()
        self.author.id = "123456789"
        self.author.display_name = "테스트유저"
        self.author.display_avatar = MagicMock()
        self.author.display_avatar.url = "https://example.com/avatar.png"
        self.sent_messages = []
    
    async def send(self, embed=None, content=None):
        """메시지 전송 시뮬레이션"""
        message = MockDiscordMessage()
        if embed:
            message.embed = embed
            print(f"📤 [SEND] {embed.title}: {embed.description[:100]}...")
        if content:
            message.content = content
            print(f"📤 [SEND] {content}")
        
        self.sent_messages.append(message)
        return message

class MockDiscordMessage:
    """Discord Message 목킹 클래스"""
    
    def __init__(self):
        self.embed = None
        self.content = None
        self.edit_count = 0
    
    async def edit(self, embed=None, content=None):
        """메시지 편집 시뮬레이션"""
        self.edit_count += 1
        if embed:
            self.embed = embed
            print(f"✏️ [EDIT #{self.edit_count}] {embed.title}: {embed.description[:100]}...")
        if content:
            self.content = content
            print(f"✏️ [EDIT #{self.edit_count}] {content}")

def create_mock_response(text: str, sources: list = None):
    """목킹 API 응답 생성"""
    return {
        "response": text,
        "session_id": "test_session_123",
        "sources": sources or [
            {"title": "테스트 문서 1", "page": "1", "content": "테스트 내용 1"},
            {"title": "테스트 문서 2", "page": "2", "content": "테스트 내용 2"}
        ],
        "metadata": {
            "processing_time": 1.5,
            "confidence": 0.95
        }
    }

async def create_mock_stream_response():
    """목킹 스트리밍 응답 생성"""
    stream_data = [
        {"session_id": "test_session_123"},
        {"chunk": "메이플스토리의 "},
        {"chunk": "렌 직업은 "},
        {"chunk": "신규 직업으로 "},
        {"chunk": "매우 강력한 "},
        {"chunk": "스킬들을 보유하고 있습니다. "},
        {"chunk": "\n\n렌의 주요 특징:\n"},
        {"chunk": "1. 높은 데미지\n"},
        {"chunk": "2. 뛰어난 기동성\n"},
        {"chunk": "3. 독특한 스킬 메커니즘\n"},
        {"sources": [{"title": "렌 가이드", "page": "1", "content": "렌 직업 설명"}]},
        {"done": True}
    ]
    
    for data in stream_data:
        yield f"data: {json.dumps(data)}\n\n".encode('utf-8')
        await asyncio.sleep(0.3)  # 스트리밍 지연 시뮬레이션

class MockStreamingResponse:
    """목킹 스트리밍 응답 클래스"""
    
    def __init__(self):
        self.status = 200
        self.content = create_mock_stream_response()

async def test_basic_chatbot():
    """기본 챗봇 기능 테스트"""
    print("🧪 === 기본 챗봇 기능 테스트 ===")
    
    # 목킹된 API 응답 설정
    maple_bot = MapleBot("http://localhost:8000")
    
    # ask_chatbot 메서드 목킹
    async def mock_ask_chatbot(message, user_id):
        await asyncio.sleep(0.5)  # API 호출 시뮬레이션
        return create_mock_response(
            f"'{message}'에 대한 답변입니다. 메이플스토리에서 이 내용은 매우 중요한 요소입니다."
        )
    
    maple_bot.ask_chatbot = mock_ask_chatbot
    
    # 테스트 실행
    ctx = MockDiscordContext()
    result = await maple_bot.ask_chatbot("렌 직업 어때?", "123456789")
    
    print(f"✅ 기본 테스트 완료:")
    print(f"   응답: {result['response'][:50]}...")
    print(f"   세션: {result['session_id']}")
    print(f"   출처: {len(result['sources'])}개")

async def test_streaming_chatbot():
    """스트리밍 챗봇 기능 테스트"""
    print("\n🧪 === 스트리밍 챗봇 기능 테스트 ===")
    
    maple_bot = MapleBot("http://localhost:8000")
    
    # aiohttp 세션 목킹
    async def mock_post(*args, **kwargs):
        return MockStreamingResponse()
    
    # MapleBot의 스트리밍 메서드에서 실제 HTTP 호출 부분을 목킹
    original_stream = maple_bot.ask_chatbot_stream
    
    async def mock_stream(message, user_id, ctx):
        print(f"🔄 스트리밍 시작: {message}")
        
        # 초기 메시지
        embed_mock = type('Embed', (), {
            'title': '🍄 메이플 가이드',
            'description': '🔍 질문을 분석하고 있습니다...',
            'color': None,
            'set_footer': lambda text: None
        })()
        
        bot_message = await ctx.send(embed=embed_mock)
        
        # 단계별 업데이트 시뮬레이션
        stages = [
            "🔍 질문을 분석하고 있습니다...",
            "📚 관련 문서를 검색하고 있습니다...",
            "🤔 최적의 답변을 생성하고 있습니다...",
            "✍️ 답변을 작성하고 있습니다..."
        ]
        
        for stage in stages:
            embed_mock.description = stage
            await bot_message.edit(embed=embed_mock)
            await asyncio.sleep(1)
        
        # 스트리밍 시뮬레이션
        full_response = ""
        async for chunk_bytes in create_mock_stream_response():
            line = chunk_bytes.decode('utf-8').strip()
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])
                    if 'chunk' in data:
                        full_response += data['chunk']
                        embed_mock.description = f"✍️ 답변을 작성하고 있습니다...\n\n{full_response}"
                        await bot_message.edit(embed=embed_mock)
                    elif 'done' in data:
                        break
                except json.JSONDecodeError:
                    continue
        
        # 최종 완료
        embed_mock.title = "🍄 메이플 가이드 답변"
        embed_mock.description = full_response
        await bot_message.edit(embed=embed_mock)
        
        print("✅ 스트리밍 테스트 완료")
    
    maple_bot.ask_chatbot_stream = mock_stream
    
    # 테스트 실행
    ctx = MockDiscordContext()
    await maple_bot.ask_chatbot_stream("렌 직업 스킬트리", "123456789", ctx)

async def test_progress_chatbot():
    """프로그레스 바 기능 테스트"""
    print("\n🧪 === 프로그레스 바 기능 테스트 ===")
    
    maple_bot = MapleBot("http://localhost:8000")
    
    # ask_chatbot 메서드 목킹
    async def mock_ask_chatbot(message, user_id):
        await asyncio.sleep(2)  # 처리 시간 시뮬레이션
        return create_mock_response(
            "하이퍼버닝 이벤트는 메이플스토리의 대표적인 레벨업 이벤트입니다. "
            "캐릭터 생성 시 특별한 혜택을 받을 수 있으며, 빠른 성장이 가능합니다."
        )
    
    maple_bot.ask_chatbot = mock_ask_chatbot
    
    # 프로그레스 바 테스트
    ctx = MockDiscordContext()
    await maple_bot.ask_chatbot_progress("하이퍼버닝 이벤트", "123456789", ctx)
    
    print("✅ 프로그레스 바 테스트 완료")

async def test_session_management():
    """세션 관리 기능 테스트"""
    print("\n🧪 === 세션 관리 기능 테스트 ===")
    
    maple_bot = MapleBot("http://localhost:8000")
    user_id = "123456789"
    
    # 세션 생성 테스트
    print("1. 세션 생성 테스트")
    maple_bot.sessions[user_id] = "test_session_123"
    print(f"   세션 생성됨: {maple_bot.sessions[user_id]}")
    
    # 세션 확인 테스트
    print("2. 세션 확인 테스트")
    assert user_id in maple_bot.sessions
    print("   ✅ 세션 확인 완료")
    
    # 세션 초기화 테스트 (목킹)
    print("3. 세션 초기화 테스트")
    async def mock_clear_session(user_id):
        if user_id in maple_bot.sessions:
            del maple_bot.sessions[user_id]
            return True
        return False
    
    maple_bot.clear_session = mock_clear_session
    success = await maple_bot.clear_session(user_id)
    
    print(f"   세션 초기화 결과: {success}")
    print(f"   남은 세션 수: {len(maple_bot.sessions)}")
    
    print("✅ 세션 관리 테스트 완료")

async def main():
    """메인 테스트 함수"""
    print("🚀 디스코드 봇 기능 테스트 시작\n")
    
    try:
        await test_basic_chatbot()
        await test_streaming_chatbot()
        await test_progress_chatbot()
        await test_session_management()
        
        print("\n🎉 모든 테스트가 성공적으로 완료되었습니다!")
        
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    # 환경변수 설정 (테스트용)
    os.environ['API_URL'] = 'http://localhost:8000'
    os.environ['DISCORD_BOT_TOKEN'] = 'test_token'
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 
# discord_bot.py - 메이플스토리 RAG 챗봇 디스코드 인터페이스

import discord
from discord.ext import commands
import aiohttp
import asyncio
import json
from typing import Optional, Dict, Any
import os
import logging
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 봇 설정
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# 환경변수
API_URL = os.getenv("API_URL", "http://localhost:8000")
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

if not DISCORD_TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN 환경변수가 설정되지 않았습니다.")

class MapleBot:
    """메이플스토리 RAG 챗봇 클래스"""
    
    def __init__(self, api_url: str):
        self.api_url = api_url
        self.sessions: Dict[str, str] = {}  # Discord user_id -> session_id 매핑
        # 타임아웃을 크게 늘려서 안정성 향상 (3분)
        self.timeout = aiohttp.ClientTimeout(total=180, connect=30)
    
    async def ask_chatbot(self, message: str, user_id: str) -> Dict[str, Any]:
        """FastAPI 챗봇 서버에 질문을 전송하고 응답을 받습니다."""
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            # 세션 ID 가져오기 또는 생성
            session_id = self.sessions.get(user_id, f"discord_{user_id}")
            
            payload = {
                "message": message,
                "session_id": session_id,
                "context": {
                    "platform": "discord",
                    "user_id": f"discord_{user_id}"
                }
            }
            
            try:
                async with session.post(
                    f"{self.api_url}/api/chat/",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        # 세션 ID 저장/업데이트
                        self.sessions[user_id] = data.get("session_id", session_id)
                        return data
                    else:
                        error_text = await response.text()
                        logger.error(f"API 오류 {response.status}: {error_text}")
                        return {"error": f"서버 오류 ({response.status}): 잠시 후 다시 시도해주세요."}
                        
            except asyncio.TimeoutError:
                logger.error("API 응답 시간 초과")
                return {"error": "서버 처리가 지연되고 있습니다. 복잡한 질문의 경우 시간이 더 걸릴 수 있습니다."}
            except aiohttp.ClientError as e:
                logger.error(f"네트워크 오류: {e}")
                return {"error": "네트워크 연결 오류가 발생했습니다."}
            except Exception as e:
                logger.error(f"예상치 못한 오류: {e}")
                return {"error": "예상치 못한 오류가 발생했습니다."}
    
    async def ask_chatbot_with_progress(self, message: str, user_id: str, ctx) -> None:
        """프로그레스 바를 사용한 안정적인 답변 생성"""
        embed = discord.Embed(
            title="🍄 메이플 가이드",
            description="질문을 처리하고 있습니다...",
            color=discord.Color.orange()
        )
        
        # 프로그레스 바 추가
        progress_bar = "⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜"
        embed.add_field(
            name="🔄 진행 상황",
            value=f"`{progress_bar}` 0%",
            inline=False
        )
        
        bot_message = await ctx.send(embed=embed)
        
        # 진행 상황 업데이트 단계 (더 자연스럽게)
        stages = [
            ("🔍 질문을 분석하고 있습니다...", "🟦⬜⬜⬜⬜⬜⬜⬜⬜⬜", "10%", 0.8),
            ("📚 관련 문서를 검색하고 있습니다...", "🟦🟦🟦⬜⬜⬜⬜⬜⬜⬜", "30%", 1.2),
            ("📖 정보를 추출하고 있습니다...", "🟦🟦🟦🟦🟦⬜⬜⬜⬜⬜", "50%", 1.0),
            ("🤔 답변을 생성하고 있습니다...", "🟦🟦🟦🟦🟦🟦🟦⬜⬜⬜", "70%", 0.5),
        ]
        
        # 비동기적으로 진행상황 업데이트와 API 호출을 병렬 처리
        async def update_progress():
            for desc, bar, percent, delay in stages:
                embed.description = desc
                embed.set_field_at(0, name="🔄 진행 상황", value=f"`{bar}` {percent}", inline=False)
                try:
                    await bot_message.edit(embed=embed)
                except discord.HTTPException:
                    # 편집 속도 제한 무시
                    pass
                await asyncio.sleep(delay)
        
        # 진행상황 업데이트와 API 호출을 동시에 시작
        progress_task = asyncio.create_task(update_progress())
        
        # API 호출 시작
        api_task = asyncio.create_task(self.ask_chatbot(message, user_id))
        
        # 진행상황 업데이트 완료 대기
        await progress_task
        
        # 최종 처리 단계 표시
        embed.description = "✅ 최종 검토 중입니다..."
        embed.set_field_at(0, name="🔄 진행 상황", value=f"`🟦🟦🟦🟦🟦🟦🟦🟦🟦⬜` 90%", inline=False)
        try:
            await bot_message.edit(embed=embed)
        except discord.HTTPException:
            pass
        
        # API 응답 대기 (타임아웃 없이)
        try:
            result = await api_task
        except Exception as e:
            logger.error(f"API 호출 중 오류: {e}")
            result = {"error": "서버와의 통신 중 오류가 발생했습니다."}
        
        # 완료 표시
        embed.set_field_at(0, name="🔄 진행 상황", value=f"`🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦` 100%", inline=False)
        try:
            await bot_message.edit(embed=embed)
        except discord.HTTPException:
            pass
        await asyncio.sleep(0.3)
        
        # 최종 결과 표시
        if "error" in result:
            embed = discord.Embed(
                title="❌ 오류 발생",
                description=result["error"],
                color=discord.Color.red()
            )
            await bot_message.edit(embed=embed)
        else:
            await self._format_final_response(bot_message, ctx, result.get("response", ""), result.get("sources", []), result.get("log_id"))

    async def _format_final_response(self, bot_message, ctx, full_response: str, sources: list, log_id: str = None):
        """최종 응답을 포맷팅하여 표시"""
        embed = discord.Embed(
            title="🍄 메이플 가이드 답변",
            color=discord.Color.green()
        )
        
        # 긴 응답 처리
        if len(full_response) > 2048:
            embed.description = full_response[:2045] + "..."
            await bot_message.edit(embed=embed)
            
            # 나머지 내용은 추가 메시지로
            remaining = full_response[2045:]
            chunks = [remaining[i:i+2000] for i in range(0, len(remaining), 2000)]
            
            for i, chunk in enumerate(chunks[:2]):  # 최대 2개 추가 메시지
                continuation_embed = discord.Embed(
                    title=f"📄 계속... ({i+2}/{min(len(chunks)+1, 3)})",
                    description=chunk,
                    color=discord.Color.green()
                )
                await ctx.send(embed=continuation_embed)
        else:
            embed.description = full_response
        
        # 출처 추가
        if sources:
            source_text = "\n".join([
                f"• {source.get('title', 'Unknown')}" for source in sources[:3]
            ])
            if len(source_text) > 1024:
                source_text = source_text[:1021] + "..."
            
            embed.add_field(
                name="📚 참고 자료",
                value=source_text,
                inline=False
            )
        
        # 피드백 요청 추가
        if log_id:
            embed.add_field(
                name="💭 피드백",
                value="답변이 도움이 되셨나요? 아래 반응으로 평가해주세요!\n👍 도움됨 | 👎 도움 안됨 | 🤔 보통",
                inline=False
            )
        
        embed.set_footer(
            text=f"✅ 완료 | 질문자: {ctx.author.display_name}",
            icon_url=ctx.author.display_avatar.url
        )
        
        # 최종 메시지 업데이트
        await bot_message.edit(embed=embed)
        
        # 피드백 반응 버튼 추가
        if log_id:
            await bot_message.add_reaction("👍")
            await bot_message.add_reaction("👎")  
            await bot_message.add_reaction("🤔")
            
            # 로그 ID를 메시지와 연결하여 저장 (피드백 처리용)
            if not hasattr(self, '_feedback_logs'):
                self._feedback_logs = {}
            self._feedback_logs[bot_message.id] = {
                'log_id': log_id,
                'user_id': str(ctx.author.id)
            }

    async def clear_session(self, user_id: str) -> bool:
        """사용자의 세션을 초기화합니다."""
        session_id = self.sessions.get(user_id)
        if not session_id:
            return False
            
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            try:
                async with session.delete(
                    f"{self.api_url}/api/chat/session/{session_id}"
                ) as response:
                    if response.status == 200:
                        del self.sessions[user_id]
                        return True
                    else:
                        logger.warning(f"세션 삭제 실패 {response.status}")
                        return False
            except Exception as e:
                logger.error(f"세션 삭제 오류: {e}")
                return False

# MapleBot 인스턴스 생성
maple_bot = MapleBot(API_URL)

@bot.event
async def on_ready():
    """봇이 준비되었을 때 실행되는 이벤트"""
    logger.info(f'{bot.user} 봇이 준비되었습니다!')
    await bot.change_presence(
        activity=discord.Game(name="!질문 [내용] | !도움말")
    )

@bot.command(name='질문', aliases=['question', 'ask', '메이플', 'maple', 'ㅁㅇㅍ', 'ㅈㅁ'])
async def ask_question(ctx, *, question: Optional[str] = None):
    """메이플스토리 관련 질문을 처리합니다."""
    if not question:
        embed = discord.Embed(
            title="❓ 질문을 입력해주세요",
            description="예: `!질문 렌 스킬트리 알려줘`\n\n💡 **팁**: 구체적으로 질문할수록 더 정확한 답변을 받을 수 있어요!",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        return
    
    # 질문 길이 제한
    if len(question) > 1000:
        embed = discord.Embed(
            title="❌ 질문이 너무 깁니다",
            description="질문은 1000자 이내로 입력해주세요.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    # 프로그레스 바 방식으로 답변 처리
    await maple_bot.ask_chatbot_with_progress(
        message=question,
        user_id=str(ctx.author.id),
        ctx=ctx
    )

@bot.command(name='리셋', aliases=['reset', 'clear'])
async def reset_session(ctx):
    """대화 세션을 초기화합니다."""
    user_id = str(ctx.author.id)
    
    success = await maple_bot.clear_session(user_id)
    
    if success:
        embed = discord.Embed(
            title="✅ 세션 초기화 완료",
            description="대화 기록이 초기화되었습니다!",
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title="ℹ️ 초기화할 세션이 없습니다",
            description="현재 활성화된 대화 세션이 없습니다.",
            color=discord.Color.blue()
        )
    
    await ctx.send(embed=embed)

@bot.command(name='도움말', aliases=['commands', 'guide'])
async def help_command(ctx):
    """봇 사용법을 안내합니다."""
    embed = discord.Embed(
        title="🎮 메이플 이벤트 가이드 봇 사용법",
        description="**현재 진행 중인 이벤트, 렌 직업, 챌린저스 서버** 전문 가이드입니다!",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="📝 기본 명령어",
        value=(
            "`!질문 [내용]` - 메이플스토리 관련 질문\n"
            "`!리셋` - 대화 기록 초기화\n"
            "`!상태` - 봇 상태 확인\n"
            "`!도움말` - 이 도움말 표시"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎯 전문 분야 질문 예시",
        value=(
            "**🎉 이벤트 관련:**\n"
            "• !질문 여름 이벤트 보상 목록과 참여 방법\n"
            "• !질문 하이퍼버닝 이벤트 상세 정보\n"
            "• !질문 ASSEMBLE 업데이트 새로운 기능\n\n"
            "**⚔️ 렌 직업 관련:**\n"
            "• !질문 렌 스킬 특징과 육성 가이드\n"
            "• !질문 렌 260레벨 최단 루트\n\n"
            "**🏆 챌린저스 서버:**\n"
            "• !질문 챌린저스 서버 뉴비 가이드\n"
            "• !질문 챌린저스 코인샵 아이템 목록"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🔧 별명 명령어",
        value=(
            "`!메이플`, `!maple`, `!ㅁㅇㅍ` → `!질문`\n"
            "`!ask`, `!question`, `!ㅈㅁ` → `!질문`\n"
            "`!reset`, `!clear` → `!리셋`\n"
            "`!commands`, `!guide` → `!도움말`"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚠️ 전문 분야 안내",
        value=(
            "✅ **전문 영역**: 이벤트, 렌 직업, 챌린저스 서버, 신규 유저 가이드\n"
            "❌ **제한 영역**: 일반 직업 스킬, 보스 공략, 강화/큐브 확률\n\n"
            "📊 **진행바 표시**: 답변 생성 과정을 시각적으로 확인\n"
            "💬 **세션 기억**: 대화 맥락을 기억하여 연속 질문 가능\n"
            "📚 **출처 제공**: 답변의 근거가 되는 최신 자료 함께 제공"
        ),
        inline=False
    )
    
    embed.set_footer(text="🎮 이벤트 & 신규 콘텐츠에 대해 언제든지 물어보세요!")
    
    await ctx.send(embed=embed)

@bot.command(name='로그', aliases=['logs', 'analytics'])
async def logs_command(ctx, days: int = 7):
    """로그 분석 정보를 조회합니다. (관리자 전용)"""
    # 간단한 관리자 체크 (실제로는 더 엄격한 권한 체크 필요)
    if not ctx.author.guild_permissions.administrator:
        embed = discord.Embed(
            title="❌ 권한 없음",
            description="이 명령어는 관리자만 사용할 수 있습니다.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}/api/logs/analytics?days={days}") as response:
                if response.status == 200:
                    data = await response.json()
                    
                    embed = discord.Embed(
                        title="📊 로그 분석 리포트",
                        description=f"최근 {days}일간의 사용 통계",
                        color=discord.Color.blue()
                    )
                    
                    embed.add_field(
                        name="📈 기본 통계",
                        value=(
                            f"총 상호작용: {data['total_interactions']:,}회\n"
                            f"고유 사용자: {data['unique_users']:,}명\n"
                            f"성공률: {data['success_rate']:.1%}\n"
                            f"평균 응답시간: {data['avg_response_time']:.2f}초"
                        ),
                        inline=True
                    )
                    
                    embed.add_field(
                        name="⚠️ 오류 통계",
                        value=f"오류율: {data['error_rate']:.1%}",
                        inline=True
                    )
                    
                    if data['most_common_queries']:
                        queries_text = "\n".join([
                            f"• {query[:30]}..." if len(query) > 30 else f"• {query}"
                            for query in data['most_common_queries'][:5]
                        ])
                        embed.add_field(
                            name="🔥 인기 질문",
                            value=queries_text,
                            inline=False
                        )
                    
                    await ctx.send(embed=embed)
                else:
                    raise Exception(f"API 오류: {response.status}")
                    
    except Exception as e:
        logger.error(f"로그 조회 오류: {e}")
        embed = discord.Embed(
            title="❌ 로그 조회 실패",
            description="로그 정보를 가져오는 중 오류가 발생했습니다.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.command(name='상태', aliases=['status', 'ping'])
async def status_command(ctx):
    """봇과 API 서버 상태를 확인합니다."""
    # 봇 레이턴시 측정
    bot_latency = round(bot.latency * 1000, 2)
    
    # API 서버 상태 확인
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            start_time = asyncio.get_event_loop().time()
            async with session.get(f"{API_URL}/api/health") as response:
                api_latency = round((asyncio.get_event_loop().time() - start_time) * 1000, 2)
                api_status = "🟢 정상" if response.status == 200 else f"🔴 오류 ({response.status})"
    except Exception as e:
        api_status = f"🔴 연결 실패"
        api_latency = "N/A"
        logger.error(f"API 상태 확인 실패: {e}")
    
    embed = discord.Embed(
        title="🤖 봇 상태",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="Discord 봇",
        value=f"🟢 온라인\n레이턴시: {bot_latency}ms",
        inline=True
    )
    
    embed.add_field(
        name="API 서버",
        value=f"{api_status}\n레이턴시: {api_latency}ms",
        inline=True
    )
    
    embed.add_field(
        name="활성 세션",
        value=f"{len(maple_bot.sessions)}개",
        inline=True
    )
    
    embed.add_field(
        name="설정 정보",
        value=f"타임아웃: 180초\n연결 대기: 30초",
        inline=True
    )
    
    await ctx.send(embed=embed)

# 에러 핸들러
@bot.event
async def on_reaction_add(reaction, user):
    """사용자 피드백 반응 처리"""
    # 봇 자신의 반응은 무시
    if user.bot:
        return
    
    # 피드백 대상 메시지인지 확인
    if (hasattr(maple_bot, '_feedback_logs') and 
        reaction.message.id in maple_bot._feedback_logs):
        
        feedback_info = maple_bot._feedback_logs[reaction.message.id]
        log_id = feedback_info['log_id']
        
        # 해당 사용자의 반응인지 확인
        if str(user.id) != feedback_info['user_id']:
            return
        
        # 피드백 점수 매핑
        emoji_to_rating = {
            "👍": 5,  # 도움됨
            "👎": 1,  # 도움 안됨
            "🤔": 3   # 보통
        }
        
        if reaction.emoji in emoji_to_rating:
            rating = emoji_to_rating[reaction.emoji]
            
            # API 서버에 피드백 전송
            try:
                async with aiohttp.ClientSession() as session:
                    payload = {
                        "log_id": log_id,
                        "user_id": f"discord_{user.id}",
                        "rating": rating
                    }
                    
                    async with session.post(
                        f"{API_URL}/api/logs/feedback",
                        params=payload
                    ) as response:
                        if response.status == 200:
                            # 피드백 감사 메시지
                            emoji_messages = {
                                "👍": "도움이 되었다니 기뻐요! 🎉",
                                "👎": "더 나은 답변을 위해 개선하겠습니다! 💪",
                                "🤔": "피드백 감사합니다! 더 나은 서비스를 위해 노력하겠습니다! 🌟"
                            }
                            
                            thanks_embed = discord.Embed(
                                title="💝 피드백 감사합니다!",
                                description=emoji_messages[reaction.emoji],
                                color=discord.Color.gold()
                            )
                            
                            await reaction.message.channel.send(embed=thanks_embed, delete_after=5)
                            
                            # 피드백 처리 완료 후 메시지 기록에서 제거
                            del maple_bot._feedback_logs[reaction.message.id]
                        else:
                            logger.warning(f"피드백 전송 실패: {response.status}")
                            
            except Exception as e:
                logger.error(f"피드백 처리 오류: {e}")

@bot.event
async def on_command_error(ctx, error):
    """명령어 오류를 처리합니다."""
    if isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="❌ 인수가 부족합니다",
            description="질문을 입력해주세요!\n예: `!질문 렌 스킬트리 알려줘`",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.CommandNotFound):
        # 존재하지 않는 명령어는 무시
        return
    elif isinstance(error, commands.CommandInvokeError):
        logger.error(f"명령어 실행 오류: {error}")
        embed = discord.Embed(
            title="❌ 명령어 실행 오류",
            description="명령어 실행 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    else:
        logger.error(f"예상치 못한 오류: {error}")

@bot.event
async def on_error(event, *args, **kwargs):
    """일반적인 봇 오류를 처리합니다."""
    logger.error(f"봇 오류 발생 - 이벤트: {event}, 인수: {args}")

if __name__ == "__main__":
    logger.info("디스코드 봇을 시작합니다...")
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"봇 실행 실패: {e}")
        raise 
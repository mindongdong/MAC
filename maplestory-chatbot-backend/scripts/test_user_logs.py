#!/usr/bin/env python3
"""
사용자 로그 수집 기능 테스트 스크립트
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.user_log_service import user_log_service
from app.models.user_log import LogSource, LogStatus
import json

async def test_log_collection():
    """로그 수집 기능 테스트"""
    print("🧪 사용자 로그 수집 기능 테스트 시작...")
    
    # 1. 테스트 로그 생성
    print("\n1️⃣ 테스트 로그 생성 중...")
    
    test_logs = [
        {
            "user_id": "test_user_001",
            "session_id": "session_001",
            "platform": LogSource.DISCORD,
            "user_message": "렌 직업에 대해 알려줘",
            "bot_response": "렌은 메이플스토리의 새로운...",
            "response_time_ms": 1500,
            "status": LogStatus.SUCCESS,
            "sources_used": [
                {
                    "title": "렌 가이드.md",
                    "score": 0.85,
                    "content_preview": "렌은 신규 직업..."
                }
            ],
            "vector_scores": [0.85, 0.78],
            "model_used": "claude-3-sonnet",
            "tokens_used": 250
        },
        {
            "user_id": "test_user_002", 
            "session_id": "session_002",
            "platform": LogSource.API,
            "user_message": "아델 스킬트리 추천해줘",
            "bot_response": "아델의 스킬트리는...",
            "response_time_ms": 2100,
            "status": LogStatus.SUCCESS,
            "sources_used": [
                {
                    "title": "아델 스킬가이드.md",
                    "score": 0.92,
                    "content_preview": "아델 스킬 분석..."
                }
            ],
            "vector_scores": [0.92, 0.88, 0.75],
            "model_used": "claude-3-sonnet",
            "tokens_used": 320
        },
        {
            "user_id": "test_user_001",
            "session_id": "session_003", 
            "platform": LogSource.DISCORD,
            "user_message": "오류 테스트",
            "bot_response": None,
            "response_time_ms": 500,
            "status": LogStatus.ERROR,
            "error_message": "테스트 오류입니다"
        }
    ]
    
    log_ids = []
    for log_data in test_logs:
        log_id = await user_log_service.log_interaction(**log_data)
        log_ids.append(log_id)
        print(f"  ✅ 로그 생성됨: {log_id}")
    
    # 2. 최근 로그 조회 테스트
    print("\n2️⃣ 최근 로그 조회 테스트...")
    recent_logs = await user_log_service.get_recent_logs(limit=5)
    print(f"  📊 최근 로그 {len(recent_logs)}개 조회됨")
    
    for i, log in enumerate(recent_logs[-3:], 1):  # 최근 3개만 출력
        print(f"    {i}. {log.user_id}: {log.user_message[:30]}...")
    
    # 3. 특정 사용자 로그 조회 테스트
    print("\n3️⃣ 특정 사용자 로그 조회 테스트...")
    user_logs = await user_log_service.get_user_logs("test_user_001", days=7)
    print(f"  👤 test_user_001의 로그 {len(user_logs)}개 조회됨")
    
    # 4. 분석 데이터 생성 테스트
    print("\n4️⃣ 분석 데이터 생성 테스트...")
    analytics = await user_log_service.get_analytics(days=1)
    
    print(f"  📈 총 상호작용: {analytics.total_interactions}")
    print(f"  👥 고유 사용자: {analytics.unique_users}")
    print(f"  ✅ 성공률: {analytics.success_rate:.1%}")
    print(f"  ⏱️ 평균 응답시간: {analytics.avg_response_time:.2f}초")
    print(f"  ❌ 오류율: {analytics.error_rate:.1%}")
    
    if analytics.most_common_queries:
        print("  🔥 인기 질문:")
        for query in analytics.most_common_queries[:3]:
            print(f"    • {query}")
    
    # 5. 피드백 추가 테스트
    print("\n5️⃣ 피드백 추가 테스트...")
    if log_ids:
        feedback_success = await user_log_service.add_feedback(
            log_id=log_ids[0],
            user_id="test_user_001",
            rating=5,
            feedback_text="매우 도움이 되었습니다!"
        )
        print(f"  💭 피드백 추가: {'성공' if feedback_success else '실패'}")
    
    print("\n✅ 모든 테스트 완료!")
    print(f"📁 로그 파일 위치: {user_log_service.log_dir}")

async def test_concurrent_logging():
    """동시 로그 처리 성능 테스트"""
    print("\n🚀 동시 로그 처리 성능 테스트...")
    
    import time
    
    async def create_log(i):
        return await user_log_service.log_interaction(
            user_id=f"perf_user_{i % 10}",
            session_id=f"perf_session_{i}",
            platform=LogSource.API,
            user_message=f"성능 테스트 질문 {i}",
            bot_response=f"성능 테스트 답변 {i}",
            response_time_ms=1000 + (i % 500),
            status=LogStatus.SUCCESS
        )
    
    start_time = time.time()
    
    # 100개 로그를 동시에 생성
    tasks = [create_log(i) for i in range(100)]
    log_ids = await asyncio.gather(*tasks)
    
    end_time = time.time()
    
    success_count = sum(1 for log_id in log_ids if log_id)
    
    print(f"  📊 {len(tasks)}개 로그 처리 완료")
    print(f"  ✅ 성공: {success_count}개")
    print(f"  ⏱️ 처리 시간: {end_time - start_time:.2f}초")
    print(f"  🔄 처리율: {len(tasks)/(end_time - start_time):.1f} logs/sec")

if __name__ == "__main__":
    print("=" * 50)
    print("🍄 메이플스토리 챗봇 - 사용자 로그 테스트")
    print("=" * 50)
    
    asyncio.run(test_log_collection())
    asyncio.run(test_concurrent_logging())
    
    print("\n" + "=" * 50)
    print("테스트 완료! 로그 파일을 확인해보세요.")
    print("=" * 50) 
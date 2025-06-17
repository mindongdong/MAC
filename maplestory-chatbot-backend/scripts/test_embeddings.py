#!/usr/bin/env python3
"""
메이플스토리 특화 임베딩 시스템 테스트 스크립트
- 실제 문서 내용 기반 임베딩 성능 테스트
- 메이플스토리 전문 용어 및 한국어 게임 용어 이해도 평가
- 도메인별 유사도 및 카테고리 구분 능력 테스트
- 수치 정보 맥락 이해 능력 검증
"""

import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.services.embedding_service import get_embeddings
from rich.console import Console
from rich.table import Table
import time

console = Console()

def test_embedding_provider():
    """임베딩 제공자 확인"""
    console.print("\n[bold blue]🔍 임베딩 제공자 확인[/bold blue]")
    
    provider = settings.get_embedding_provider()
    console.print(f"[cyan]설정된 제공자:[/cyan] {provider}")
    
    table = Table(title="환경 변수 상태")
    table.add_column("변수", style="cyan")
    table.add_column("상태", style="green")
    table.add_column("값", style="yellow")
    
    anthropic_key = settings.anthropic_api_key
    openai_key = settings.openai_api_key
    voyage_key = settings.voyage_api_key
    
    table.add_row(
        "ANTHROPIC_API_KEY",
        "✅ 설정됨" if anthropic_key and anthropic_key != "your_anthropic_api_key_here" else "❌ 미설정",
        f"{anthropic_key[:10]}..." if anthropic_key and len(anthropic_key) > 10 else "None"
    )
    
    table.add_row(
        "VOYAGE_API_KEY",
        "✅ 설정됨" if voyage_key and voyage_key != "your_voyage_api_key_here" else "❌ 미설정",
        f"{voyage_key[:10]}..." if voyage_key and len(voyage_key) > 10 else "None"
    )
    
    table.add_row(
        "OPENAI_API_KEY",
        "✅ 설정됨" if openai_key and openai_key != "your_openai_api_key_here" else "❌ 미설정",
        f"{openai_key[:10]}..." if openai_key and len(openai_key) > 10 else "None"
    )
    
    console.print(table)
    return provider

def test_embedding_initialization():
    """임베딩 모델 초기화 테스트"""
    console.print("\n[bold blue]🚀 임베딩 모델 초기화 테스트[/bold blue]")
    
    try:
        with console.status("[spinner]임베딩 모델 로딩 중..."):
            start_time = time.time()
            embeddings = get_embeddings()
            load_time = time.time() - start_time
        
        console.print(f"✅ 임베딩 모델 로딩 성공! (소요 시간: {load_time:.2f}초)")
        console.print(f"[dim]모델 타입: {type(embeddings).__name__}[/dim]")
        
        return embeddings
        
    except Exception as e:
        console.print(f"❌ 임베딩 모델 로딩 실패: {str(e)}")
        return None

def test_embedding_generation(embeddings):
    """임베딩 생성 테스트"""
    console.print("\n[bold blue]🧮 임베딩 생성 테스트[/bold blue]")
    
    # 실제 문서 내용 기반 테스트 텍스트
    test_texts = [
        # 캐릭터 육성 관련
        "렌 캐릭터 전용 이벤트 보상",
        "하이퍼 버닝 MAX와 버닝 비욘드의 차이점",
        "챌린저스 월드 4만점 달성 방법",
        "테라 블링크를 통한 200레벨 점핑",
        
        # 이벤트 관련
        "황혼빛 전야제 에버니움 교환소",
        "썸머 카운트다운 선물과 썸머 선물",
        "시간의 모래 주간 10개 수집",
        "피어나의 약초 바구니 보약 스킬",
        
        # 제네시스 관련
        "제네시스 무기 해방을 위한 어둠의 흔적 6500개",
        "제네시스 패스 3배 혜택과 6인 파티",
        "군단장 격파 미션과 해방 기간",
        
        # 게임 용어 및 줄임말
        "딸농 11판으로 210레벨에서 240레벨까지",
        "극성비와 VIP 부스터 사용법",
        "노블레스 길드 스킬의 중요성",
        "직작용 카르마 블랙 큐브",
        "이벤잠과 페어리 아트 주문서",
        
        # PC방 및 캐시 아이템
        "달콤한 정령 자석펫 30일",
        "MVP 레드 혜택과 비용 효율",
        "챌린저스 프리미엄 패스 19,800 메이플포인트",
        "웰컴 메이플 패키지 통달의 비약"
    ]
    
    results = []
    
    for text in test_texts:
        try:
            with console.status(f"[spinner]'{text[:30]}...' 임베딩 생성 중..."):
                start_time = time.time()
                embedding = embeddings.embed_query(text)
                embed_time = time.time() - start_time
            
            results.append({
                "text": text,
                "dimension": len(embedding),
                "time": embed_time,
                "first_few": embedding[:3]
            })
            
            console.print(f"✅ [{embed_time:.3f}초] {text[:50]}{'...' if len(text) > 50 else ''}")
            
        except Exception as e:
            console.print(f"❌ '{text[:30]}...' 임베딩 생성 실패: {str(e)}")
            results.append({"text": text, "error": str(e)})
    
    return results

def test_similarity_search(embeddings):
    """유사도 검색 테스트"""
    console.print("\n[bold blue]🔄 유사도 검색 테스트[/bold blue]")
    
    try:
        # 메이플스토리 도메인 기반 유사도 테스트
        similarity_tests = [
            {
                "name": "렌 캐릭터 관련 유사도",
                "text1": "렌 캐릭터 전용 이벤트 보상",
                "text2": "신규 직업 렌 육성 가이드", 
                "text3": "제네시스 무기 해방 방법"
            },
            {
                "name": "버닝 시스템 유사도",
                "text1": "하이퍼 버닝 MAX 260레벨까지",
                "text2": "버닝 비욘드 270레벨까지",
                "text3": "황혼빛 전야제 이벤트 코인샵"
            },
            {
                "name": "이벤트 보상 유사도",
                "text1": "에버니움 교환소 강화 상점 우선순위",
                "text2": "시간의 흔적 조사 보스 코인샵",
                "text3": "챌린저스 월드 4만점 달성"
            },
            {
                "name": "게임 용어 유사도",
                "text1": "딸농 11판으로 240레벨 달성",
                "text2": "황금 딸기 농장 효율적 사용법",
                "text3": "제네시스 패스 3만원 구매"
            }
        ]
        
        import numpy as np
        
        def cosine_similarity(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        
        for test in similarity_tests:
            console.print(f"\n[cyan]🧪 {test['name']} 테스트[/cyan]")
            
            with console.status(f"[spinner]{test['name']} 임베딩 생성 및 유사도 계산 중..."):
                embed1 = embeddings.embed_query(test['text1'])
                embed2 = embeddings.embed_query(test['text2'])
                embed3 = embeddings.embed_query(test['text3'])
                
                sim_1_2 = cosine_similarity(embed1, embed2)  # 관련 있는 텍스트들
                sim_1_3 = cosine_similarity(embed1, embed3)  # 관련 없는 텍스트
            
            console.print(f"  관련 텍스트 유사도: {sim_1_2:.4f}")
            console.print(f"    '{test['text1'][:40]}...'")
            console.print(f"    vs '{test['text2'][:40]}...'")
            console.print(f"  비관련 텍스트 유사도: {sim_1_3:.4f}")
            console.print(f"    '{test['text1'][:40]}...'")
            console.print(f"    vs '{test['text3'][:40]}...'")
            
            if sim_1_2 > sim_1_3:
                console.print("    ✅ 유사도 검색이 정상 작동")
            else:
                console.print("    ⚠️ 유사도 결과가 예상과 다름")
                
        console.print(f"\n✅ 전체 유사도 검색 테스트 완료")
            
    except Exception as e:
        console.print(f"❌ 유사도 검색 테스트 실패: {str(e)}")

def test_domain_similarity(embeddings):
    """메이플스토리 도메인 특화 유사도 테스트"""
    console.print("\n[bold blue]🎮 메이플스토리 도메인 유사도 테스트[/bold blue]")
    
    try:
        # 유사한 개념들의 그룹
        similarity_groups = [
            {
                "name": "렌 캐릭터 관련",
                "texts": [
                    "렌 전용 이벤트 유랑자의 여행기",
                    "신규 직업 렌 육성 가이드",
                    "렌 캐릭터 스텝업 미션 보상"
                ]
            },
            {
                "name": "버닝 시스템",
                "texts": [
                    "하이퍼 버닝 MAX 260레벨까지",
                    "버닝 비욘드 270레벨까지",
                    "아이템 버닝 연습 모드"
                ]
            },
            {
                "name": "제네시스 해방",
                "texts": [
                    "어둠의 흔적 6500개 수집",
                    "군단장 격파 미션",
                    "제네시스 패스 3배 혜택"
                ]
            },
            {
                "name": "이벤트 코인샵",
                "texts": [
                    "에버니움 교환소 강화 상점",
                    "시간의 흔적 조사 보스 코인샵",
                    "이벤잠과 유잠 구매 우선순위"
                ]
            }
        ]
        
        import numpy as np
        
        def cosine_similarity(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        
        for group in similarity_groups:
            console.print(f"\n[cyan]📂 {group['name']} 그룹 유사도 분석[/cyan]")
            
            embeddings_list = []
            with console.status(f"[spinner]{group['name']} 임베딩 생성 중..."):
                for text in group['texts']:
                    embedding = embeddings.embed_query(text)
                    embeddings_list.append((text, embedding))
            
            # 그룹 내 유사도 계산
            similarities = []
            for i in range(len(embeddings_list)):
                for j in range(i + 1, len(embeddings_list)):
                    text1, embed1 = embeddings_list[i]
                    text2, embed2 = embeddings_list[j]
                    sim = cosine_similarity(embed1, embed2)
                    similarities.append(sim)
                    console.print(f"  {sim:.4f} - {text1[:25]}... vs {text2[:25]}...")
            
            avg_similarity = np.mean(similarities)
            console.print(f"[green]평균 그룹 내 유사도: {avg_similarity:.4f}[/green]")
            
    except Exception as e:
        console.print(f"❌ 도메인 유사도 테스트 실패: {str(e)}")

def test_cross_category_distinction(embeddings):
    """카테고리 간 구분 능력 테스트"""
    console.print("\n[bold blue]🔍 카테고리 간 구분 능력 테스트[/bold blue]")
    
    try:
        # 서로 다른 카테고리의 텍스트들
        categories = {
            "캐릭터 육성": [
                "렌 캐릭터 200레벨에서 260레벨까지 육성",
                "하이퍼 버닝으로 빠른 레벨업",
                "테라 블링크 200레벨 점핑"
            ],
            "이벤트 보상": [
                "황혼빛 전야제 에버니움 코인 교환",
                "썸머 선물 극한 성장의 비약",
                "시간의 모래 20개 특별 보상"
            ],
            "제네시스 해방": [
                "어둠의 흔적 노멀 스우 10개 획득",
                "제네시스 패스 6인 파티 격파",
                "군단장 소울 공격력 확정 지급"
            ],
            "캐시 아이템": [
                "챌린저스 프리미엄 패스 19,800원",
                "제네시스 패스 3만원 넥슨 캐시",
                "웰컴 메이플 패키지 9,900원"
            ]
        }
        
        import numpy as np
        
        def cosine_similarity(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        
        category_embeddings = {}
        
        # 각 카테고리별 임베딩 생성
        with console.status("[spinner]카테고리별 임베딩 생성 중..."):
            for category, texts in categories.items():
                embeddings_list = []
                for text in texts:
                    embedding = embeddings.embed_query(text)
                    embeddings_list.append(embedding)
                category_embeddings[category] = embeddings_list
        
        # 카테고리 내 vs 카테고리 간 유사도 비교
        within_category_sims = []
        cross_category_sims = []
        
        category_names = list(categories.keys())
        
        for i, cat1 in enumerate(category_names):
            for j, cat2 in enumerate(category_names):
                if i <= j:  # 중복 방지
                    continue
                    
                # 카테고리 간 유사도
                for embed1 in category_embeddings[cat1]:
                    for embed2 in category_embeddings[cat2]:
                        sim = cosine_similarity(embed1, embed2)
                        cross_category_sims.append(sim)
        
        # 카테고리 내 유사도
        for category, embeds in category_embeddings.items():
            for i in range(len(embeds)):
                for j in range(i + 1, len(embeds)):
                    sim = cosine_similarity(embeds[i], embeds[j])
                    within_category_sims.append(sim)
        
        avg_within = np.mean(within_category_sims)
        avg_cross = np.mean(cross_category_sims)
        
        console.print(f"[green]평균 카테고리 내 유사도: {avg_within:.4f}[/green]")
        console.print(f"[yellow]평균 카테고리 간 유사도: {avg_cross:.4f}[/yellow]")
        console.print(f"[cyan]구분 능력 지수: {avg_within - avg_cross:.4f}[/cyan]")
        
        if avg_within > avg_cross:
            console.print("✅ 카테고리 구분 능력이 우수합니다!")
        else:
            console.print("⚠️ 카테고리 구분 능력이 부족할 수 있습니다.")
            
    except Exception as e:
        console.print(f"❌ 카테고리 구분 테스트 실패: {str(e)}")

def test_korean_game_terms(embeddings):
    """한국어 게임 용어 임베딩 테스트"""
    console.print("\n[bold blue]🗣️ 한국어 게임 용어 임베딩 테스트[/bold blue]")
    
    try:
        # 게임 용어와 그 설명
        term_pairs = [
            ("딸농", "황금 딸기 농장"),
            ("극성비", "극한 성장의 비약"),
            ("노블", "노블레스 길드 스킬"),
            ("직작", "직접 제작"),
            ("이벤잠", "이벤트링 전용 레전드리 잠재능력 부여 주문서"),
            ("유잠", "유니크 잠재능력 부여 주문서"),
            ("에디잠", "에디셔널 잠재능력 부여 주문서"),
            ("자석펫", "달콤한 정령 자석펫"),
            ("프악공", "프리미엄 악세서리 공격력 주문서"),
            ("푸공", "프리미엄 공격력 주문서")
        ]
        
        import numpy as np
        
        def cosine_similarity(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        
        console.print("게임 용어와 정식 명칭 간 유사도:")
        
        similarities = []
        for short_term, full_term in term_pairs:
            with console.status(f"[spinner]'{short_term}' vs '{full_term}' 비교 중..."):
                embed1 = embeddings.embed_query(short_term)
                embed2 = embeddings.embed_query(full_term)
                sim = cosine_similarity(embed1, embed2)
                similarities.append(sim)
            
            console.print(f"  {sim:.4f} - '{short_term}' ↔ '{full_term}'")
        
        avg_similarity = np.mean(similarities)
        console.print(f"\n[green]평균 용어-설명 유사도: {avg_similarity:.4f}[/green]")
        
        if avg_similarity > 0.7:
            console.print("✅ 한국어 게임 용어 이해도가 우수합니다!")
        elif avg_similarity > 0.5:
            console.print("⚠️ 한국어 게임 용어 이해도가 보통입니다.")
        else:
            console.print("❌ 한국어 게임 용어 이해도가 부족합니다.")
            
    except Exception as e:
        console.print(f"❌ 한국어 게임 용어 테스트 실패: {str(e)}")

def test_numerical_context_understanding(embeddings):
    """수치 정보 맥락 이해 테스트"""
    console.print("\n[bold blue]🔢 수치 정보 맥락 이해 테스트[/bold blue]")
    
    try:
        # 유사한 수치 정보를 가진 텍스트들
        numerical_contexts = [
            {
                "group": "레벨 구간",
                "texts": [
                    "200레벨에서 260레벨까지 하이퍼 버닝",
                    "260레벨에서 270레벨까지 버닝 비욘드",
                    "210레벨에서 240레벨까지 딸농 11판"
                ]
            },
            {
                "group": "포인트/점수",
                "texts": [
                    "챌린저스 월드 4만점 목표",
                    "챌린저스 월드 6만점 하드 플레이",
                    "노블 포인트 47P 이상 길드"
                ]
            },
            {
                "group": "수집 아이템",
                "texts": [
                    "어둠의 흔적 6500개 필요",
                    "시간의 모래 주간 최대 10개",
                    "에버니움 400개 획득"
                ]
            },
            {
                "group": "가격/비용",
                "texts": [
                    "챌린저스 프리미엄 패스 19,800 메이플포인트",
                    "제네시스 패스 3만원",
                    "웰컴 메이플 패키지 9,900원"
                ]
            }
        ]
        
        import numpy as np
        
        def cosine_similarity(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        
        for group_info in numerical_contexts:
            console.print(f"\n[cyan]📊 {group_info['group']} 맥락 이해도[/cyan]")
            
            embeddings_list = []
            with console.status(f"[spinner]{group_info['group']} 임베딩 생성 중..."):
                for text in group_info['texts']:
                    embedding = embeddings.embed_query(text)
                    embeddings_list.append((text, embedding))
            
            # 그룹 내 유사도 계산
            similarities = []
            for i in range(len(embeddings_list)):
                for j in range(i + 1, len(embeddings_list)):
                    text1, embed1 = embeddings_list[i]
                    text2, embed2 = embeddings_list[j]
                    sim = cosine_similarity(embed1, embed2)
                    similarities.append(sim)
                    console.print(f"  {sim:.4f} - {text1[:30]}... vs {text2[:30]}...")
            
            if similarities:
                avg_similarity = np.mean(similarities)
                console.print(f"[green]평균 맥락 유사도: {avg_similarity:.4f}[/green]")
            
    except Exception as e:
        console.print(f"❌ 수치 맥락 이해 테스트 실패: {str(e)}")

async def main():
    """메인 테스트 함수"""
    console.print("[bold green]🧪 메이플스토리 특화 임베딩 시스템 테스트 시작[/bold green]")
    
    # 1. 제공자 확인
    provider = test_embedding_provider()
    
    # 2. 임베딩 초기화
    embeddings = test_embedding_initialization()
    if not embeddings:
        console.print("\n[red]❌ 임베딩 초기화 실패로 테스트를 중단합니다.[/red]")
        return
    
    # 3. 기본 임베딩 생성 테스트 (메이플스토리 도메인 특화)
    results = test_embedding_generation(embeddings)
    
    # 4. 기본 유사도 검색 테스트
    test_similarity_search(embeddings)
    
    # 5. 메이플스토리 도메인 유사도 테스트
    test_domain_similarity(embeddings)
    
    # 6. 카테고리 간 구분 능력 테스트
    test_cross_category_distinction(embeddings)
    
    # 7. 한국어 게임 용어 이해도 테스트
    test_korean_game_terms(embeddings)
    
    # 8. 수치 정보 맥락 이해 테스트
    test_numerical_context_understanding(embeddings)
    
    # 9. 최종 결과 및 성능 분석
    console.print("\n" + "="*60)
    console.print("[bold green]🎉 메이플스토리 특화 임베딩 시스템 테스트 완료![/bold green]")
    console.print("="*60)
    
    # 성능 요약
    if results:
        valid_results = [r for r in results if "error" not in r]
        failed_results = [r for r in results if "error" in r]
        
        if valid_results:
            avg_time = sum(r["time"] for r in valid_results) / len(valid_results)
            avg_dim = sum(r["dimension"] for r in valid_results) / len(valid_results)
            
            console.print(f"\n[bold cyan]📊 종합 성능 분석[/bold cyan]")
            
            # 기본 성능 지표
            performance_table = Table(title="임베딩 성능 지표")
            performance_table.add_column("항목", style="cyan")
            performance_table.add_column("값", style="green") 
            performance_table.add_column("평가", style="yellow")
            
            performance_table.add_row("임베딩 제공자", provider, "✅ 정상")
            performance_table.add_row("평균 생성 시간", f"{avg_time:.3f}초", 
                                    "✅ 빠름" if avg_time < 1.0 else "⚠️ 보통" if avg_time < 3.0 else "❌ 느림")
            performance_table.add_row("임베딩 차원", f"{int(avg_dim)}", "✅ 적정")
            performance_table.add_row("성공률", f"{len(valid_results)}/{len(results)} ({len(valid_results)/len(results)*100:.1f}%)", 
                                    "✅ 우수" if len(valid_results) == len(results) else "⚠️ 주의")
            
            console.print(performance_table)
            
            # 실패한 케이스가 있으면 표시
            if failed_results:
                console.print(f"\n[red]❌ 실패한 테스트 케이스 ({len(failed_results)}개):[/red]")
                for failed in failed_results:
                    console.print(f"  • {failed['text'][:50]}... - {failed['error']}")
            
            # 도메인 특화 평가
            console.print(f"\n[bold magenta]🎮 메이플스토리 도메인 적합성 평가[/bold magenta]")
            console.print("• 게임 전문 용어 임베딩: 테스트 완료")
            console.print("• 한국어 줄임말 이해: 테스트 완료") 
            console.print("• 카테고리 구분 능력: 테스트 완료")
            console.print("• 수치 정보 맥락 이해: 테스트 완료")
            console.print("• 유사 개념 그룹화: 테스트 완료")
            
            # 권장사항
            console.print(f"\n[bold blue]💡 권장사항[/bold blue]")
            if avg_time < 1.0:
                console.print("• 임베딩 생성 속도가 우수하여 실시간 검색에 적합합니다")
            else:
                console.print("• 임베딩 생성 속도를 개선하면 사용자 경험이 향상될 수 있습니다")
                
            if len(valid_results) == len(results):
                console.print("• 모든 테스트 케이스가 정상 처리되어 안정성이 높습니다")
            else:
                console.print("• 일부 실패 케이스를 점검하여 시스템 안정성을 높이세요")
                
            console.print("• 메이플스토리 도메인 특화 테스트가 모두 완료되었습니다")
            console.print("• RAG 시스템과 연동하여 실제 검색 성능을 확인해보세요")
            
        else:
            console.print("\n[red]❌ 유효한 테스트 결과가 없습니다.[/red]")
    else:
        console.print("\n[red]❌ 테스트 결과가 없습니다.[/red]")
    
    console.print(f"\n[dim]💡 다음 단계: python scripts/test_rag.py 실행으로 RAG 성능을 테스트해보세요![/dim]")

if __name__ == "__main__":
    asyncio.run(main()) 
#!/usr/bin/env python3
"""
임베딩 시스템 테스트 스크립트
OpenAI API 키 유무에 관계없이 임베딩이 정상 작동하는지 테스트
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
    
    table.add_row(
        "ANTHROPIC_API_KEY",
        "✅ 설정됨" if anthropic_key and anthropic_key != "your_anthropic_api_key_here" else "❌ 미설정",
        f"{anthropic_key[:10]}..." if anthropic_key and len(anthropic_key) > 10 else "None"
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
    
    test_texts = [
        "안녕하세요",
        "나이트로드 5차 스킬",
        "메이플스토리 보스 공략",
        "Hello world"
    ]
    
    results = []
    
    for text in test_texts:
        try:
            with console.status(f"[spinner]'{text}' 임베딩 생성 중..."):
                start_time = time.time()
                embedding = embeddings.embed_query(text)
                embed_time = time.time() - start_time
            
            results.append({
                "text": text,
                "dimension": len(embedding),
                "time": embed_time,
                "first_few": embedding[:3]
            })
            
            console.print(f"✅ '{text}' - 차원: {len(embedding)}, 시간: {embed_time:.3f}초")
            
        except Exception as e:
            console.print(f"❌ '{text}' 임베딩 생성 실패: {str(e)}")
            results.append({"text": text, "error": str(e)})
    
    return results

def test_similarity_search(embeddings):
    """유사도 검색 테스트"""
    console.print("\n[bold blue]🔄 유사도 검색 테스트[/bold blue]")
    
    try:
        # 두 개의 비슷한 텍스트
        text1 = "나이트로드 스킬 가이드"
        text2 = "나이트로드 스킬 설명"
        text3 = "보스 몬스터 공략법"
        
        with console.status("[spinner]임베딩 생성 및 유사도 계산 중..."):
            embed1 = embeddings.embed_query(text1)
            embed2 = embeddings.embed_query(text2)
            embed3 = embeddings.embed_query(text3)
            
            # 코사인 유사도 계산
            import numpy as np
            
            def cosine_similarity(a, b):
                return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
            
            sim_1_2 = cosine_similarity(embed1, embed2)
            sim_1_3 = cosine_similarity(embed1, embed3)
        
        console.print(f"✅ 유사도 테스트 완료")
        console.print(f"[cyan]'{text1}' vs '{text2}':[/cyan] {sim_1_2:.4f}")
        console.print(f"[cyan]'{text1}' vs '{text3}':[/cyan] {sim_1_3:.4f}")
        
        if sim_1_2 > sim_1_3:
            console.print("✅ 유사도 검색이 정상적으로 작동합니다!")
        else:
            console.print("⚠️ 유사도 결과가 예상과 다릅니다.")
            
    except Exception as e:
        console.print(f"❌ 유사도 검색 테스트 실패: {str(e)}")

async def main():
    """메인 테스트 함수"""
    console.print("[bold green]🧪 임베딩 시스템 테스트 시작[/bold green]")
    
    # 1. 제공자 확인
    provider = test_embedding_provider()
    
    # 2. 임베딩 초기화
    embeddings = test_embedding_initialization()
    if not embeddings:
        console.print("\n[red]❌ 임베딩 초기화 실패로 테스트를 중단합니다.[/red]")
        return
    
    # 3. 임베딩 생성 테스트
    results = test_embedding_generation(embeddings)
    
    # 4. 유사도 검색 테스트
    test_similarity_search(embeddings)
    
    # 5. 최종 결과
    console.print("\n[bold green]🎉 임베딩 시스템 테스트 완료![/bold green]")
    
    # 성능 요약
    if results:
        valid_results = [r for r in results if "error" not in r]
        if valid_results:
            avg_time = sum(r["time"] for r in valid_results) / len(valid_results)
            avg_dim = sum(r["dimension"] for r in valid_results) / len(valid_results)
            
            console.print(f"\n[bold cyan]📊 성능 요약[/bold cyan]")
            console.print(f"임베딩 제공자: {provider}")
            console.print(f"평균 생성 시간: {avg_time:.3f}초")
            console.print(f"임베딩 차원: {int(avg_dim)}")
            console.print(f"성공률: {len(valid_results)}/{len(results)}")

if __name__ == "__main__":
    asyncio.run(main()) 
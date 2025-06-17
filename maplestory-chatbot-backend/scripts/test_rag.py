# scripts/test_rag.py
import asyncio
import os
import sys
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.langchain_service import LangChainService
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.panel import Panel

console = Console()

# 테스트 결과를 저장할 전역 변수
test_results = []

def save_test_result(test_name, query, response, sources_count, error=None):
    """테스트 결과를 저장"""
    result = {
        "test_name": test_name,
        "query": query,
        "response": response,
        "sources_count": sources_count,
        "error": error,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    test_results.append(result)

async def test_basic_search():
    """기본 검색 테스트"""
    service = LangChainService()
    
    console.print(Panel("[bold blue]기본 RAG 검색 테스트[/bold blue]", expand=False))
    
    # 대표 질문 1개만 선택
    query = "메이플스토리 뉴비가 처음에 뭘 해야 해?"
    
    console.print(f"\n[bold yellow]❓ 질문:[/bold yellow] {query}")
    
    try:
        result = await service.chat(
            message=query,
            session_id="test-session",
            stream=False
        )
        
        console.print("[bold green]💬 답변:[/bold green]")
        console.print(Markdown(result["response"]))
        
        sources_count = len(result.get("sources", []))
        if result.get("sources"):
            console.print(f"[dim]📚 참고 문서: {sources_count}개[/dim]")
        
        # 테스트 결과 저장
        save_test_result("기본 RAG 검색 테스트", query, result["response"], sources_count)
        
    except Exception as e:
        console.print(f"[red]❌ 오류: {str(e)}[/red]")
        save_test_result("기본 RAG 검색 테스트", query, None, 0, str(e))
    
    console.print("-" * 50)

async def test_metadata_filtering():
    """메타데이터 필터링 테스트"""
    service = LangChainService()
    
    console.print(Panel("[bold blue]메타데이터 필터링 테스트[/bold blue]", expand=False))
    
    # 대표 테스트 케이스 1개만 선택
    test_case = {
        "question": "렌 캐릭터만의 전용 이벤트 보상이 뭐가 있어?",
        "filter": {"category": "game_event_guide"},
        "description": "이벤트 가이드 필터링"
    }
    
    console.print(f"\n[bold cyan]🔍 {test_case['description']}[/bold cyan]")
    console.print(f"[bold yellow]❓ 질문:[/bold yellow] {test_case['question']}")
    console.print(f"[dim]필터: {test_case['filter']}[/dim]")
    
    try:
        result = await service.chat(
            message=test_case['question'],
            session_id="test-metadata",
            context=test_case['filter'],
            stream=False
        )
        
        console.print("[bold green]💬 답변:[/bold green]")
        console.print(Markdown(result["response"]))
        
        sources_count = len(result.get("sources", []))
        
        # 출처 정보를 테이블로 표시
        if result.get("sources"):
            table = Table(title="참고 문서", show_header=True, header_style="bold magenta")
            table.add_column("파일명", style="cyan", width=30)
            table.add_column("카테고리", style="green", width=15)
            table.add_column("작성자", style="blue", width=10)
            table.add_column("메타데이터", style="yellow", width=30)
            
            for source in result["sources"][:3]:  # 처음 3개만 표시
                metadata = source.get('metadata', {})
                
                # 주요 메타데이터만 표시
                key_metadata = {}
                for key in ['category', 'author', 'target_audience', 'confidence_level']:
                    if metadata.get(key):
                        key_metadata[key] = metadata[key]
                
                table.add_row(
                    metadata.get('title', 'Unknown')[:28] + "..." if len(metadata.get('title', '')) > 30 else metadata.get('title', 'Unknown'),
                    metadata.get('category', 'N/A'),
                    metadata.get('author', 'N/A'),
                    str(key_metadata) if key_metadata else "N/A"
                )
            
            console.print(table)
        
        # 테스트 결과 저장
        save_test_result("메타데이터 필터링 테스트", test_case['question'], result["response"], sources_count)
        
    except Exception as e:
        console.print(f"[red]❌ 오류: {str(e)}[/red]")
        save_test_result("메타데이터 필터링 테스트", test_case['question'], None, 0, str(e))
    
    console.print("-" * 80)

async def test_collection_info():
    """컬렉션 정보 확인"""
    service = LangChainService()
    
    console.print(Panel("[bold blue]벡터 스토어 상태 확인[/bold blue]", expand=False))
    
    try:
        info = service.vector_store.get_collection_info()
        if info:
            console.print(f"📊 [bold]컬렉션 정보[/bold]")
            console.print(f"   • 총 문서 수: {info.get('points_count', 'N/A')}")
            console.print(f"   • 벡터 차원: {info.get('config', {}).get('params', {}).get('vectors', {}).get('size', 'N/A')}")
            console.print(f"   • 거리 메트릭: {info.get('config', {}).get('params', {}).get('vectors', {}).get('distance', 'N/A')}")
            
            # 테스트 결과 저장
            info_text = f"총 문서 수: {info.get('points_count', 'N/A')}, 벡터 차원: {info.get('config', {}).get('params', {}).get('vectors', {}).get('size', 'N/A')}, 거리 메트릭: {info.get('config', {}).get('params', {}).get('vectors', {}).get('distance', 'N/A')}"
            save_test_result("벡터 스토어 상태 확인", "컬렉션 정보 조회", info_text, 0)
        else:
            console.print("[red]❌ 컬렉션 정보를 가져올 수 없습니다.[/red]")
            save_test_result("벡터 스토어 상태 확인", "컬렉션 정보 조회", None, 0, "컬렉션 정보를 가져올 수 없음")
    
    except Exception as e:
        console.print(f"[red]❌ 오류: {str(e)}[/red]")
        save_test_result("벡터 스토어 상태 확인", "컬렉션 정보 조회", None, 0, str(e))

async def test_document_types():
    """문서 타입별 분포 확인"""
    console.print(Panel("[bold blue]문서 타입 분포 분석[/bold blue]", expand=False))
    
    try:
        service = LangChainService()
        
        # 샘플 검색으로 문서 메타데이터 확인
        sample_results = await service.vector_store.search("메이플스토리", k=20)
        
        if sample_results:
            # 메타데이터 분석
            categories = {}
            source_types = {}
            
            for doc in sample_results:
                metadata = doc.metadata
                
                # 카테고리 분석
                category = metadata.get('category', 'unknown')
                categories[category] = categories.get(category, 0) + 1
                
                # 소스 타입 분석
                source_type = metadata.get('source_type', 'unknown')
                source_types[source_type] = source_types.get(source_type, 0) + 1
            
            # 카테고리별 분포만 표시 (간단하게)
            if categories:
                table = Table(title="카테고리별 분포", show_header=True)
                table.add_column("항목", style="cyan")
                table.add_column("개수", style="magenta")
                table.add_column("비율", style="green")
                
                total = sum(categories.values())
                for item, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                    percentage = (count / total) * 100
                    table.add_row(item, str(count), f"{percentage:.1f}%")
                
                console.print(table)
            
            # 테스트 결과 저장
            analysis_text = f"총 {len(sample_results)}개 문서 분석 완료. 카테고리: {len(categories)}개, 소스 타입: {len(source_types)}개"
            save_test_result("문서 타입 분포 분석", "메이플스토리 문서 메타데이터 분석", analysis_text, len(sample_results))
        
        else:
            console.print("[yellow]⚠️ 검색 결과가 없습니다. 문서를 먼저 수집해주세요.[/yellow]")
            save_test_result("문서 타입 분포 분석", "메이플스토리 문서 메타데이터 분석", None, 0, "검색 결과 없음")
    
    except Exception as e:
        console.print(f"[red]❌ 오류: {str(e)}[/red]")
        save_test_result("문서 타입 분포 분석", "메이플스토리 문서 메타데이터 분석", None, 0, str(e))

async def test_specific_document_queries():
    """문서별 특정 질문 테스트"""
    service = LangChainService()
    
    console.print(Panel("[bold blue]문서별 특정 질문 테스트[/bold blue]", expand=False))
    
    # 대표 질문 1개만 선택
    query = "제네시스 해방에 필요한 어둠의 흔적은 총 몇 개야?"
    
    console.print(f"\n[bold yellow]❓ 구체적 질문:[/bold yellow] {query}")
    
    try:
        result = await service.chat(
            message=query,
            session_id="test-specific",
            stream=False
        )
        
        console.print("[bold green]💬 답변:[/bold green]")
        console.print(Markdown(result["response"]))
        
        sources_count = len(result.get("sources", []))
        if result.get("sources"):
            console.print(f"[dim]📚 참고 문서: {sources_count}개[/dim]")
            # 첫 번째 소스의 제목만 간단히 표시
            first_source = result["sources"][0].get("metadata", {})
            if first_source.get("title"):
                console.print(f"[dim]주요 출처: {first_source['title'][:50]}...[/dim]")
        
        # 테스트 결과 저장
        save_test_result("문서별 특정 질문 테스트", query, result["response"], sources_count)
        
    except Exception as e:
        console.print(f"[red]❌ 오류: {str(e)}[/red]")
        save_test_result("문서별 특정 질문 테스트", query, None, 0, str(e))
    
    console.print("-" * 60)

async def test_comparative_queries():
    """비교/분석 질문 테스트"""
    service = LangChainService()
    
    console.print(Panel("[bold blue]비교/분석 질문 테스트[/bold blue]", expand=False))
    
    # 대표 질문 1개만 선택
    query = "하이퍼 버닝과 버닝 비욘드의 차이점과 각각 언제 사용해야 해?"
    
    console.print(f"\n[bold cyan]🔍 비교/분석 질문:[/bold cyan] {query}")
    
    try:
        result = await service.chat(
            message=query,
            session_id="test-comparative",
            stream=False
        )
        
        console.print("[bold green]💬 답변:[/bold green]")
        console.print(Markdown(result["response"]))
        
        sources_count = len(result.get("sources", []))
        if result.get("sources"):
            console.print(f"[dim]📚 참고 문서: {sources_count}개[/dim]")
        
        # 테스트 결과 저장
        save_test_result("비교/분석 질문 테스트", query, result["response"], sources_count)
        
    except Exception as e:
        console.print(f"[red]❌ 오류: {str(e)}[/red]")
        save_test_result("비교/분석 질문 테스트", query, None, 0, str(e))
    
    console.print("-" * 70)

async def test_realistic_scenarios():
    """실제 사용자 시나리오 테스트"""
    service = LangChainService()
    
    console.print(Panel("[bold blue]실제 사용자 시나리오 테스트[/bold blue]", expand=False))
    
    # 대표 질문 1개만 선택
    query = "메이플 5년만에 복귀했는데 뭘 해야 할지 모르겠어"
    
    console.print(f"\n[bold magenta]🎮 시나리오 질문:[/bold magenta] {query}")
    
    try:
        result = await service.chat(
            message=query,
            session_id="test-scenario",
            stream=False
        )
        
        console.print("[bold green]💬 답변:[/bold green]")
        console.print(Markdown(result["response"]))
        
        sources_count = len(result.get("sources", []))
        if result.get("sources"):
            console.print(f"[dim]📚 참고 문서: {sources_count}개[/dim]")
        
        # 테스트 결과 저장
        save_test_result("실제 사용자 시나리오 테스트", query, result["response"], sources_count)
        
    except Exception as e:
        console.print(f"[red]❌ 오류: {str(e)}[/red]")
        save_test_result("실제 사용자 시나리오 테스트", query, None, 0, str(e))
    
    console.print("-" * 65)

async def test_korean_nlp():
    """한국어 자연어 처리 능력 테스트"""
    service = LangChainService()
    
    console.print(Panel("[bold blue]한국어 자연어 처리 능력 테스트[/bold blue]", expand=False))
    
    # 대표 질문 1개만 선택
    query = "딸농이 뭐야?"
    
    console.print(f"\n[bold blue]🗣️ 한국어 표현 테스트:[/bold blue] {query}")
    
    try:
        result = await service.chat(
            message=query,
            session_id="test-korean-nlp",
            stream=False
        )
        
        console.print("[bold green]💬 답변:[/bold green]")
        console.print(Markdown(result["response"]))
        
        sources_count = len(result.get("sources", []))
        if result.get("sources"):
            console.print(f"[dim]📚 참고 문서: {sources_count}개[/dim]")
        
        # 테스트 결과 저장
        save_test_result("한국어 자연어 처리 능력 테스트", query, result["response"], sources_count)
        
    except Exception as e:
        console.print(f"[red]❌ 오류: {str(e)}[/red]")
        save_test_result("한국어 자연어 처리 능력 테스트", query, None, 0, str(e))
    
    console.print("-" * 55)

def save_results_to_file():
    """테스트 결과를 마크다운 파일로 저장"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"maplestory-chatbot-backend/test_results/rag_test_results_{timestamp}.md"
    
    # 결과 디렉토리 생성
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# 메이플스토리 RAG 시스템 테스트 결과\n\n")
        f.write(f"**테스트 실행 시간:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**총 테스트 개수:** {len(test_results)}\n\n")
        
        # 성공/실패 통계
        success_count = sum(1 for result in test_results if result['error'] is None)
        fail_count = len(test_results) - success_count
        
        f.write(f"**성공:** {success_count}개\n")
        f.write(f"**실패:** {fail_count}개\n\n")
        
        f.write("---\n\n")
        
        # 각 테스트 결과 상세
        for i, result in enumerate(test_results, 1):
            f.write(f"## {i}. {result['test_name']}\n\n")
            f.write(f"**질문:** {result['query']}\n\n")
            
            if result['error']:
                f.write(f"**상태:** ❌ 실패\n")
                f.write(f"**오류:** {result['error']}\n\n")
            else:
                f.write(f"**상태:** ✅ 성공\n")
                f.write(f"**참고 문서 수:** {result['sources_count']}개\n\n")
                f.write("**답변:**\n")
                f.write(f"{result['response']}\n\n")
            
            f.write(f"**실행 시간:** {result['timestamp']}\n\n")
            f.write("---\n\n")
    
    console.print(f"\n[bold green]📄 테스트 결과가 저장되었습니다: {filename}[/bold green]")
    return filename

async def main():
    """메인 테스트 함수"""
    console.print("[bold blue]🧪 메이플스토리 RAG 시스템 테스트 시작[/bold blue]\n")
    
    # 연결 테스트
    try:
        service = LangChainService()
        console.print("✅ 서비스 초기화 성공")
    except Exception as e:
        console.print(f"❌ 서비스 초기화 실패: {str(e)}")
        return
    
    # 테스트 실행
    tests = [
        ("컬렉션 정보 확인", test_collection_info),
        ("문서 타입 분포 분석", test_document_types), 
        ("기본 검색 테스트", test_basic_search),
        ("메타데이터 필터링 테스트", test_metadata_filtering),
        ("문서별 특정 질문 테스트", test_specific_document_queries),
        ("비교/분석 질문 테스트", test_comparative_queries),
        ("실제 사용자 시나리오 테스트", test_realistic_scenarios),
        ("한국어 자연어 처리 능력 테스트", test_korean_nlp)
    ]
    
    for test_name, test_func in tests:
        console.print(f"\n{'='*60}")
        console.print(f"[bold cyan]🔬 {test_name}[/bold cyan]")
        console.print('='*60)
        
        try:
            await test_func()
        except Exception as e:
            console.print(f"[red]❌ 테스트 '{test_name}' 실패: {str(e)}[/red]")
        
        console.print("\n")
    
    console.print("[bold green]🎉 모든 테스트 완료![/bold green]")
    
    # 테스트 결과를 파일로 저장
    result_file = save_results_to_file()
    
    console.print(f"\n[dim]💡 팁: 더 나은 결과를 위해 Markdown 파일에 메타데이터를 추가해보세요![/dim]")
    console.print(f"[dim]📊 상세 결과는 {result_file}에서 확인하세요![/dim]")

if __name__ == "__main__":
    asyncio.run(main()) 
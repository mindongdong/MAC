# scripts/test_rag.py
import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.langchain_service import LangChainService
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.panel import Panel

console = Console()

async def test_basic_search():
    """기본 검색 테스트"""
    service = LangChainService()
    
    console.print(Panel("[bold blue]기본 RAG 검색 테스트[/bold blue]", expand=False))
    
    test_queries = [
        "메이플스토리에서 레벨업하는 방법",
        "나이트로드 스킬 추천",
        "보스 공략법",
        "장비 강화 팁"
    ]
    
    for query in test_queries:
        console.print(f"\n[bold yellow]❓ 질문:[/bold yellow] {query}")
        
        try:
            result = await service.chat(
                message=query,
                session_id="test-session",
                stream=False
            )
            
            console.print("[bold green]💬 답변:[/bold green]")
            console.print(Markdown(result["response"]))
            
            if result.get("sources"):
                console.print(f"[dim]📚 참고 문서: {len(result['sources'])}개[/dim]")
            
        except Exception as e:
            console.print(f"[red]❌ 오류: {str(e)}[/red]")
        
        console.print("-" * 50)

async def test_metadata_filtering():
    """메타데이터 필터링 테스트"""
    service = LangChainService()
    
    console.print(Panel("[bold blue]메타데이터 필터링 테스트[/bold blue]", expand=False))
    
    # 메타데이터 필터링 테스트 케이스
    test_cases = [
        {
            "question": "나이트로드 5차 스킬 중에 뭐가 제일 중요해?",
            "filter": {"class": "나이트로드"},
            "description": "직업별 필터링"
        },
        {
            "question": "카오스 벨룸 공략법 알려줘",
            "filter": {"category": "boss_guide"},
            "description": "카테고리별 필터링"
        },
        {
            "question": "리부트 서버에서 메소 파밍 방법",
            "filter": {"server_type": "리부트"},
            "description": "서버타입별 필터링"
        },
        {
            "question": "초보자를 위한 가이드",
            "filter": {"difficulty": "beginner"},
            "description": "난이도별 필터링"
        }
    ]
    
    for test in test_cases:
        console.print(f"\n[bold cyan]🔍 {test['description']}[/bold cyan]")
        console.print(f"[bold yellow]❓ 질문:[/bold yellow] {test['question']}")
        console.print(f"[dim]필터: {test['filter']}[/dim]")
        
        try:
            result = await service.chat(
                message=test['question'],
                session_id="test-metadata",
                context=test['filter'],
                stream=False
            )
            
            console.print("[bold green]💬 답변:[/bold green]")
            console.print(Markdown(result["response"]))
            
            # 출처 정보를 테이블로 표시
            if result.get("sources"):
                table = Table(title="참고 문서", show_header=True, header_style="bold magenta")
                table.add_column("파일명", style="cyan", width=30)
                table.add_column("카테고리", style="green", width=15)
                table.add_column("타입", style="blue", width=10)
                table.add_column("메타데이터", style="yellow", width=30)
                
                for source in result["sources"][:3]:  # 처음 3개만 표시
                    metadata = source.get('metadata', {})
                    
                    # 주요 메타데이터만 표시
                    key_metadata = {}
                    for key in ['class', 'content_type', 'difficulty', 'server_type']:
                        if metadata.get(key):
                            key_metadata[key] = metadata[key]
                    
                    table.add_row(
                        metadata.get('source', 'Unknown')[:28] + "..." if len(metadata.get('source', '')) > 30 else metadata.get('source', 'Unknown'),
                        metadata.get('category', 'N/A'),
                        metadata.get('source_type', 'N/A'),
                        str(key_metadata) if key_metadata else "N/A"
                    )
                
                console.print(table)
            
        except Exception as e:
            console.print(f"[red]❌ 오류: {str(e)}[/red]")
        
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
        else:
            console.print("[red]❌ 컬렉션 정보를 가져올 수 없습니다.[/red]")
    
    except Exception as e:
        console.print(f"[red]❌ 오류: {str(e)}[/red]")

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
            classes = {}
            
            for doc in sample_results:
                metadata = doc.metadata
                
                # 카테고리 분석
                category = metadata.get('category', 'unknown')
                categories[category] = categories.get(category, 0) + 1
                
                # 소스 타입 분석
                source_type = metadata.get('source_type', 'unknown')
                source_types[source_type] = source_types.get(source_type, 0) + 1
                
                # 직업 분석
                if metadata.get('class'):
                    class_name = metadata.get('class')
                    classes[class_name] = classes.get(class_name, 0) + 1
            
            # 결과 테이블 생성
            tables = [
                ("카테고리별 분포", categories),
                ("소스 타입별 분포", source_types),
                ("직업별 분포", classes)
            ]
            
            for title, data in tables:
                if data:
                    table = Table(title=title, show_header=True)
                    table.add_column("항목", style="cyan")
                    table.add_column("개수", style="magenta")
                    table.add_column("비율", style="green")
                    
                    total = sum(data.values())
                    for item, count in sorted(data.items(), key=lambda x: x[1], reverse=True):
                        percentage = (count / total) * 100
                        table.add_row(item, str(count), f"{percentage:.1f}%")
                    
                    console.print(table)
                    console.print()
        
        else:
            console.print("[yellow]⚠️ 검색 결과가 없습니다. 문서를 먼저 수집해주세요.[/yellow]")
    
    except Exception as e:
        console.print(f"[red]❌ 오류: {str(e)}[/red]")

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
        ("메타데이터 필터링 테스트", test_metadata_filtering)
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
    console.print("\n[dim]💡 팁: 더 나은 결과를 위해 Markdown 파일에 메타데이터를 추가해보세요![/dim]")

if __name__ == "__main__":
    asyncio.run(main()) 
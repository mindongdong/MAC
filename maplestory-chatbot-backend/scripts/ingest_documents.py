import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.document_processor import DocumentProcessor
from app.services.langchain_service import LangChainService
from app.config import settings
import logging
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Rich console for better output
console = Console()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def check_qdrant_connection():
    """Qdrant 연결 확인"""
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(url=settings.qdrant_url)
        collections = client.get_collections()
        console.print(f"✅ Qdrant 연결 성공! 현재 컬렉션: {[c.name for c in collections.collections]}", style="green")
        return True
    except Exception as e:
        console.print(f"❌ Qdrant 연결 실패: {str(e)}", style="red")
        return False

async def scan_documents(directories: dict) -> dict:
    """디렉토리에서 문서 스캔"""
    file_counts = {"pdf": 0, "markdown": 0}
    file_list = {"pdf": [], "markdown": []}
    
    for doc_type, directory in directories.items():
        if os.path.exists(directory):
            # 재귀적으로 파일 찾기
            for root, dirs, files in os.walk(directory):
                for filename in files:
                    if doc_type == "pdf" and filename.endswith('.pdf'):
                        file_list["pdf"].append(os.path.relpath(os.path.join(root, filename), directory))
                    elif doc_type == "markdown" and filename.endswith('.md'):
                        file_list["markdown"].append(os.path.relpath(os.path.join(root, filename), directory))
            
            file_counts[doc_type] = len(file_list[doc_type])
    
    return file_counts, file_list

async def main():
    """문서를 벡터 스토어에 수집 (PDF + Markdown 지원)"""
    console.print("[bold blue]메이플스토리 문서 수집 시작[/bold blue]")
    
    # 1. Qdrant 연결 확인
    if not await check_qdrant_connection():
        console.print("Qdrant를 먼저 실행해주세요: docker run -p 6333:6333 qdrant/qdrant", style="yellow")
        return
    
    # 2. 서비스 초기화
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("서비스 초기화 중...", total=None)
        
        processor = DocumentProcessor(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap
        )
        service = LangChainService()
        
        collection_info = service.vector_store.get_collection_info()
        if collection_info:
            console.print(f"📊 현재 컬렉션 상태: {collection_info['points_count']} 문서", style="cyan")
    
    # 3. 문서 디렉토리 설정
    directories = {
        "pdf": "./data/pdfs",
        "markdown": "./data/markdown"
    }
    
    # 디렉토리 생성
    for directory in directories.values():
        if not os.path.exists(directory):
            os.makedirs(directory)
            console.print(f"📁 디렉토리 생성: {directory}", style="yellow")
    
    # Markdown 하위 디렉토리 생성
    markdown_subdirs = [
        "class_guides", "boss_guides", "system_guides", 
        "farming_guides", "equipment_guides", "enhancement_guides"
    ]
    for subdir in markdown_subdirs:
        subdir_path = os.path.join(directories["markdown"], subdir)
        if not os.path.exists(subdir_path):
            os.makedirs(subdir_path)
    
    # 4. 문서 스캔
    file_counts, file_list = await scan_documents(directories)
    
    # 파일 목록 테이블 출력
    table = Table(title="발견된 문서")
    table.add_column("타입", style="cyan")
    table.add_column("개수", style="magenta")
    table.add_column("파일명 (처음 3개)", style="green")
    
    for doc_type in ["markdown", "pdf"]:  # Markdown 우선 표시
        if file_counts[doc_type] > 0:
            file_preview = ", ".join(file_list[doc_type][:3])
            if len(file_list[doc_type]) > 3:
                file_preview += f" ... (+{len(file_list[doc_type]) - 3}개 더)"
            
            table.add_row(
                doc_type.upper(),
                str(file_counts[doc_type]),
                file_preview
            )
    
    console.print(table)
    
    if sum(file_counts.values()) == 0:
        console.print("❌ 처리할 문서가 없습니다.", style="red")
        console.print(f"📁 Markdown 파일: {directories['markdown']}", style="yellow")
        console.print(f"📁 PDF 파일: {directories['pdf']}", style="yellow")
        console.print("\n[dim]Markdown 파일 예시 구조:[/dim]")
        console.print("data/markdown/class_guides/나이트로드_5차스킬_가이드.md")
        console.print("data/markdown/boss_guides/카오스벨룸_공략.md")
        return
    
    # 5. 사용자 확인
    console.print(f"\n총 {sum(file_counts.values())}개의 문서를 처리합니다.")
    if file_counts["markdown"] > 0:
        console.print(f"  📝 Markdown: {file_counts['markdown']}개", style="green")
    if file_counts["pdf"] > 0:
        console.print(f"  📄 PDF: {file_counts['pdf']}개", style="blue")
    
    confirm = console.input("[yellow]계속하시겠습니까? (y/n): [/yellow]")
    
    if confirm.lower() != 'y':
        console.print("취소되었습니다.", style="red")
        return
    
    # 6. 문서 처리
    all_documents = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        # Markdown 처리 (우선)
        if file_counts["markdown"] > 0:
            task = progress.add_task(f"Markdown 파일 {file_counts['markdown']}개 처리 중...", total=None)
            md_docs = await processor.process_directory(directories["markdown"], ['.md'])
            all_documents.extend(md_docs)
            console.print(f"✅ Markdown: {len(md_docs)} 청크 생성", style="green")
        
        # PDF 처리
        if file_counts["pdf"] > 0:
            task = progress.add_task(f"PDF 파일 {file_counts['pdf']}개 처리 중...", total=None)
            pdf_docs = await processor.process_directory(directories["pdf"], ['.pdf'])
            all_documents.extend(pdf_docs)
            console.print(f"✅ PDF: {len(pdf_docs)} 청크 생성", style="blue")
    
    console.print(f"\n📄 총 {len(all_documents)} 개의 청크 생성 완료", style="green")
    
    # 7. 문서 메타데이터 요약
    if all_documents:
        metadata_summary = {}
        for doc in all_documents:
            doc_type = doc.metadata.get('source_type', 'unknown')
            category = doc.metadata.get('category', 'uncategorized')
            key = f"{doc_type}_{category}"
            metadata_summary[key] = metadata_summary.get(key, 0) + 1
        
        console.print("\n[dim]문서 유형별 분포:[/dim]")
        for key, count in sorted(metadata_summary.items()):
            console.print(f"  {key}: {count}개")
    
    # 8. 벡터 스토어에 추가
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("벡터 스토어에 업로드 중...", total=None)
        
        await service.add_documents(all_documents)
        
        console.print("✅ 문서 업로드 완료!", style="green")
    
    # 9. 최종 상태 확인
    final_info = service.vector_store.get_collection_info()
    if final_info:
        console.print(f"📊 최종 컬렉션 상태: {final_info['points_count']} 문서", style="cyan")
    
    console.print("\n[bold green]문서 수집이 완료되었습니다![/bold green]")
    console.print("🚀 서버 실행: [dim]uvicorn app.main:app --reload[/dim]")
    console.print("🧪 테스트 실행: [dim]python scripts/test_rag.py[/dim]")

if __name__ == "__main__":
    asyncio.run(main()) 
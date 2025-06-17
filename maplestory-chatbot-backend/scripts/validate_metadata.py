import os
import sys
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config.metadata_config import metadata_config

console = Console()

def validate_markdown_files(directory: str):
    """모든 Markdown 파일의 메타데이터 검증"""
    
    console.print(Panel(f"[bold blue]📋 Markdown 메타데이터 검증[/bold blue]\n디렉토리: {directory}", expand=False))
    
    # 결과 테이블 준비
    table = Table(title="메타데이터 검증 결과")
    table.add_column("파일명", style="cyan", width=30)
    table.add_column("상태", style="green", width=10)
    table.add_column("누락된 필드", style="red", width=20)
    table.add_column("경고", style="yellow", width=25)
    
    total_files = 0
    valid_files = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("파일 검증 중...", total=None)
        
        for root, dirs, files in os.walk(directory):
            for filename in files:
                if filename.endswith('.md'):
                    file_path = os.path.join(root, filename)
                    relative_path = os.path.relpath(file_path, directory)
                    
                    total_files += 1
                    status, missing, warnings = validate_file(file_path)
                    
                    if status:
                        valid_files += 1
                    
                    # 파일명 줄이기
                    display_name = relative_path
                    if len(display_name) > 28:
                        display_name = "..." + display_name[-25:]
                    
                    table.add_row(
                        display_name,
                        "✅ OK" if status else "❌ Error",
                        ", ".join(missing) if missing else "-",
                        ", ".join(warnings[:2]) if warnings else "-"  # 최대 2개만
                    )
    
    console.print(table)
    
    # 요약 정보
    console.print(f"\n📊 [bold]검증 요약[/bold]")
    console.print(f"   • 총 파일 수: {total_files}")
    console.print(f"   • 유효한 파일: {valid_files}")
    console.print(f"   • 문제 있는 파일: {total_files - valid_files}")
    
    if total_files > 0:
        success_rate = (valid_files / total_files) * 100
        console.print(f"   • 성공률: {success_rate:.1f}%")

def validate_file(file_path: str):
    """개별 파일 검증"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, [f"파일 읽기 오류: {str(e)}"], []
    
    # 프론트매터 추출
    metadata = {}
    
    # 코드 블록으로 감싸진 경우 처리
    if content.startswith('```'):
        # 첫 번째 ```와 마지막 ``` 제거
        first_backtick_end = content.find('\n', 3)
        last_backtick_start = content.rfind('\n```')
        if first_backtick_end != -1 and last_backtick_start != -1:
            content = content[first_backtick_end + 1:last_backtick_start]
    
    # 프론트매터 파싱
    if content.startswith('---'):
        end_index = content.find('---', 3)
        if end_index != -1:
            yaml_content = content[3:end_index].strip()
            
            # 한 줄로 연결된 YAML 처리
            if '\n' not in yaml_content or yaml_content.count('\n') < 3:
                # YAML이 한 줄로 연결되어 있다면 수정 시도
                try:
                    # 간단한 정규식으로 한 줄 YAML을 여러 줄로 변환
                    import re
                    # 따옴표로 둘러싸인 값 뒤의 공백과 새 키를 찾아 줄바꿈 추가
                    fixed_yaml = re.sub(r'"\s+([a-zA-Z_][a-zA-Z0-9_]*:)', r'"\n\1', yaml_content)
                    # tags: 뒤의 줄바꿈 처리
                    fixed_yaml = re.sub(r'tags:\s*-', r'tags:\n-', fixed_yaml)
                    # sources: 뒤의 줄바꿈 처리  
                    fixed_yaml = re.sub(r'sources:\s*-', r'sources:\n-', fixed_yaml)
                    # keywords: 뒤의 줄바꿈 처리
                    fixed_yaml = re.sub(r'keywords:\s*-', r'keywords:\n-', fixed_yaml)
                    
                    metadata = yaml.safe_load(fixed_yaml) or {}
                except yaml.YAMLError as e:
                    return False, [f"YAML 파싱 오류 (한 줄 형식): {str(e)[:100]}..."], []
                except Exception as e:
                    return False, [f"YAML 수정 실패: {str(e)[:100]}..."], []
            else:
                try:
                    metadata = yaml.safe_load(yaml_content) or {}
                except yaml.YAMLError as e:
                    return False, [f"YAML 파싱 오류: {str(e)[:100]}..."], []
    else:
        return False, ["프론트매터 없음"], []
    
    # 필수 필드 검사
    missing = []
    for field in metadata_config.required_fields:
        if field not in metadata or not metadata[field]:
            missing.append(field)
    
    # 경고 사항 검사
    warnings = []
    
    # YAML 형식 문제 확인
    if content.startswith('---'):
        end_index = content.find('---', 3)
        if end_index != -1:
            yaml_content = content[3:end_index].strip()
            if '\n' not in yaml_content or yaml_content.count('\n') < 3:
                warnings.append("YAML 한 줄 형식 (수정 필요)")
    
    # 업데이트 날짜 확인
    if not metadata.get('updated_date'):
        warnings.append("updated_date 없음")
    
    # 태그 확인
    if not metadata.get('tags') or not isinstance(metadata.get('tags'), list):
        warnings.append("tags 없음 또는 잘못된 형식")
    
    # 카테고리 유효성 확인
    category = metadata.get('category')
    if category and category not in metadata_config.category_aliases.values():
        # 별칭 확인
        if category in metadata_config.category_aliases:
            warnings.append(f"카테고리 별칭 사용: {category}")
        else:
            warnings.append(f"알 수 없는 카테고리: {category}")
    
    # 직업 유효성 확인
    class_name = metadata.get('class')
    if class_name and class_name not in metadata_config.available_classes:
        warnings.append(f"알 수 없는 직업: {class_name}")
    
    # 서버 타입 확인
    server_type = metadata.get('server_type')
    if server_type and server_type not in metadata_config.server_types:
        warnings.append(f"알 수 없는 서버 타입: {server_type}")
    
    return len(missing) == 0, missing, warnings

def suggest_improvements(directory: str):
    """개선 제안 생성"""
    console.print(Panel("[bold blue]📝 메타데이터 개선 제안[/bold blue]", expand=False))
    
    suggestions = []
    
    # 카테고리별 파일 수 확인
    category_count = {}
    for root, dirs, files in os.walk(directory):
        for filename in files:
            if filename.endswith('.md'):
                file_path = os.path.join(root, filename)
                _, _, _ = validate_file(file_path)  # 간단한 검증
                
                # 디렉토리 기반 카테고리 추정
                rel_path = os.path.relpath(file_path, directory)
                path_parts = rel_path.split(os.sep)
                if len(path_parts) > 1:
                    category = path_parts[0]
                    category_count[category] = category_count.get(category, 0) + 1
    
    # 제안 생성
    if category_count:
        console.print("🗂️  [bold]디렉토리별 파일 분포:[/bold]")
        for category, count in sorted(category_count.items()):
            console.print(f"   • {category}: {count}개")
    
    console.print(f"\n💡 [bold]추천 메타데이터 구조:[/bold]")
    console.print("""
[dim]---
title: 파일 제목 (필수)
category: class_guide (필수)
author: 작성자명
created_date: 2024-01-15
updated_date: 2024-01-20
game_version: latest
difficulty: medium
server_type: both
tags:
  - 태그1
  - 태그2
class: 나이트로드  # 직업 가이드인 경우
content_type: 5차스킬  # 콘텐츠 타입
keywords:
  - 키워드1
  - 키워드2
---[/dim]
""")

def main():
    """메인 함수"""
    console.print("[bold blue]🔍 메이플스토리 Markdown 메타데이터 검증기[/bold blue]\n")
    
    # 디렉토리 확인
    markdown_dir = "./data/markdown"
    
    if not os.path.exists(markdown_dir):
        console.print(f"[red]❌ Markdown 디렉토리가 없습니다: {markdown_dir}[/red]")
        console.print("[yellow]먼저 문서를 준비해주세요.[/yellow]")
        return
    
    # 파일 수 확인
    md_files = []
    for root, dirs, files in os.walk(markdown_dir):
        for filename in files:
            if filename.endswith('.md'):
                md_files.append(os.path.join(root, filename))
    
    if not md_files:
        console.print(f"[yellow]⚠️ {markdown_dir}에 Markdown 파일이 없습니다.[/yellow]")
        suggest_improvements(markdown_dir)
        return
    
    console.print(f"📁 검증할 파일: {len(md_files)}개\n")
    
    # 검증 실행
    validate_markdown_files(markdown_dir)
    
    # 개선 제안
    console.print("\n")
    suggest_improvements(markdown_dir)
    
    console.print(f"\n[bold green]✅ 검증 완료![/bold green]")
    console.print("[dim]팁: 문제가 있는 파일을 수정한 후 다시 실행해보세요.[/dim]")

if __name__ == "__main__":
    main() 
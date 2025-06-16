# PDF에서 Markdown으로 RAG 전환 가이드 (개선판)

## 1. 핵심 개선사항

- 하드코딩된 메타데이터 추출 제거
- 프론트매터 중심의 메타데이터 관리
- 설정 파일 기반 확장 가능한 구조
- 유연한 파일명 규칙

## 2. Document Processor 수정 (유연한 버전)

### Step 1: 설정 파일 추가

먼저 메타데이터 규칙을 관리할 설정 파일을 만듭니다:

```python
# app/config/metadata_config.py
from typing import Dict, List, Optional
from pydantic import BaseModel

class MetadataConfig(BaseModel):
    """메타데이터 설정 - 사용자가 쉽게 확장 가능"""
    
    # 필수 메타데이터 필드
    required_fields: List[str] = [
        "title",
        "category"
    ]
    
    # 선택적 메타데이터 필드 및 기본값
    optional_fields: Dict[str, any] = {
        "created_date": None,
        "updated_date": None,
        "author": "Unknown",
        "tags": [],
        "keywords": []
    }
    
    # 파일명 파싱 규칙 (선택사항)
    # 예: "카테고리_제목_기타정보.md" 형식인 경우
    filename_pattern: Optional[str] = r"^(?P<category>[^_]+)_(?P<title>[^_]+)(?:_(?P<extra>.+))?\.md$"
    
    # 카테고리 별칭 (선택사항)
    category_aliases: Dict[str, str] = {
        "class": "class_guide",
        "boss": "boss_guide",
        "quest": "quest_guide",
        "system": "system_guide"
    }

# 설정 인스턴스
metadata_config = MetadataConfig()
```

### Step 2: 개선된 Document Processor

```python
# app/services/document_processor.py
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter, MarkdownTextSplitter
from typing import List, Dict, Union, Optional
from langchain.schema import Document
import os
import logging
from datetime import datetime
import yaml
import re
from app.config.metadata_config import metadata_config

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        # 텍스트 분할기
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ".", "!", "?", "。", " ", ""],
            length_function=len
        )
        
        self.markdown_splitter = MarkdownTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        # 메타데이터 설정 로드
        self.metadata_config = metadata_config
    
    async def process_markdown(self, file_path: str) -> List[Document]:
        """Markdown 파일 처리 - 유연한 메타데이터 처리"""
        try:
            # 파일 읽기
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 메타데이터 추출 (프론트매터 우선)
            metadata, markdown_content = self._extract_frontmatter(content)
            
            # 파일명에서 보조 메타데이터 추출 (선택사항)
            filename = os.path.basename(file_path)
            file_metadata = self._parse_filename(filename)
            
            # 기본 메타데이터 설정
            base_metadata = {
                "source": filename,
                "source_type": "markdown",
                "file_path": file_path,
                "processed_at": datetime.now().isoformat()
            }
            
            # 메타데이터 병합 (우선순위: 프론트매터 > 파일명 > 기본값)
            final_metadata = self._merge_metadata(
                base_metadata,
                file_metadata,
                metadata
            )
            
            # 필수 필드 검증
            self._validate_metadata(final_metadata, file_path)
            
            # 문서 구조 분석
            sections = self._extract_markdown_structure(markdown_content)
            if sections:
                final_metadata["sections"] = [s["title"] for s in sections]
            
            # 텍스트 분할
            chunks = self.markdown_splitter.split_text(markdown_content)
            
            # Document 객체 생성
            documents = []
            for i, chunk in enumerate(chunks):
                chunk_metadata = final_metadata.copy()
                
                # 청크별 메타데이터
                chunk_metadata.update({
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "chunk_size": len(chunk)
                })
                
                # 청크가 속한 섹션 찾기
                section_info = self._find_section_for_chunk(chunk, sections)
                if section_info:
                    chunk_metadata.update(section_info)
                
                doc = Document(
                    page_content=chunk,
                    metadata=chunk_metadata
                )
                documents.append(doc)
            
            logger.info(f"Processed Markdown {file_path}: {len(documents)} chunks created")
            return documents
            
        except Exception as e:
            logger.error(f"Error processing Markdown {file_path}: {str(e)}")
            raise
    
    def _extract_frontmatter(self, content: str) -> tuple:
        """YAML 프론트매터 추출"""
        metadata = {}
        markdown_content = content
        
        if content.startswith('---'):
            try:
                end_index = content.find('---', 3)
                if end_index != -1:
                    yaml_content = content[3:end_index].strip()
                    metadata = yaml.safe_load(yaml_content) or {}
                    markdown_content = content[end_index+3:].strip()
            except yaml.YAMLError as e:
                logger.warning(f"Failed to parse YAML frontmatter: {e}")
        
        return metadata, markdown_content
    
    def _parse_filename(self, filename: str) -> Dict:
        """파일명에서 메타데이터 추출 (선택적, 패턴 기반)"""
        metadata = {}
        
        # 설정에 파일명 패턴이 있으면 사용
        if self.metadata_config.filename_pattern:
            pattern = re.compile(self.metadata_config.filename_pattern)
            match = pattern.match(filename)
            if match:
                metadata = match.groupdict()
                
                # 카테고리 별칭 처리
                if 'category' in metadata and metadata['category'] in self.metadata_config.category_aliases:
                    metadata['category'] = self.metadata_config.category_aliases[metadata['category']]
        
        # 파일명 패턴이 없으면 기본 추출
        else:
            # 확장자 제거
            name_without_ext = os.path.splitext(filename)[0]
            
            # 언더스코어나 하이픈으로 분리
            parts = re.split(r'[_\-]', name_without_ext)
            
            # 첫 번째 부분을 카테고리로 추정 (선택사항)
            if len(parts) > 1:
                potential_category = parts[0].lower()
                if potential_category in self.metadata_config.category_aliases:
                    metadata['category'] = self.metadata_config.category_aliases[potential_category]
        
        return metadata
    
    def _merge_metadata(self, base: Dict, file: Dict, frontmatter: Dict) -> Dict:
        """메타데이터 병합 (우선순위: frontmatter > file > base)"""
        # 기본값으로 시작
        merged = base.copy()
        
        # 선택적 필드 기본값 추가
        for field, default_value in self.metadata_config.optional_fields.items():
            if field not in merged:
                merged[field] = default_value
        
        # 파일명에서 추출한 메타데이터 병합
        merged.update(file)
        
        # 프론트매터 메타데이터 병합 (최우선)
        merged.update(frontmatter)
        
        return merged
    
    def _validate_metadata(self, metadata: Dict, file_path: str):
        """필수 메타데이터 검증"""
        missing_fields = []
        
        for field in self.metadata_config.required_fields:
            if field not in metadata or not metadata[field]:
                missing_fields.append(field)
        
        if missing_fields:
            logger.warning(
                f"Missing required metadata fields in {file_path}: {missing_fields}. "
                f"Please add these fields to the frontmatter."
            )
    
    def _extract_markdown_structure(self, content: str) -> List[Dict]:
        """Markdown 문서 구조 추출"""
        sections = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if header_match:
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                sections.append({
                    "level": level,
                    "title": title,
                    "line_number": i
                })
        
        return sections
    
    def _find_section_for_chunk(self, chunk: str, sections: List[Dict]) -> Dict:
        """청크가 속한 섹션 정보 반환"""
        if not sections:
            return {}
        
        # 청크에 포함된 헤더 찾기
        for section in sections:
            if section["title"] in chunk:
                return {
                    "section": section["title"],
                    "section_level": section["level"]
                }
        
        return {}
    
    async def process_pdf(self, file_path: str) -> List[Document]:
        """PDF 처리 (기존 코드 유지)"""
        try:
            loader = PyPDFLoader(file_path)
            pages = loader.load()
            
            logger.info(f"Loaded PDF: {file_path} ({len(pages)} pages)")
            
            full_text = "\n\n".join([page.page_content for page in pages])
            
            filename = os.path.basename(file_path)
            base_metadata = {
                "source": filename,
                "source_type": "pdf",
                "file_path": file_path,
                "total_pages": len(pages),
                "processed_at": datetime.now().isoformat()
            }
            
            # PDF도 동일한 메타데이터 병합 로직 사용
            file_metadata = self._parse_filename(filename)
            final_metadata = self._merge_metadata(base_metadata, file_metadata, {})
            
            chunks = self.text_splitter.split_text(full_text)
            
            documents = []
            for i, chunk in enumerate(chunks):
                metadata = final_metadata.copy()
                metadata.update({
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "chunk_size": len(chunk)
                })
                
                doc = Document(
                    page_content=chunk,
                    metadata=metadata
                )
                documents.append(doc)
            
            logger.info(f"Processed PDF {file_path}: {len(documents)} chunks created")
            return documents
            
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {str(e)}")
            raise
    
    async def process_file(self, file_path: str) -> List[Document]:
        """파일 타입에 따라 처리"""
        if file_path.endswith('.pdf'):
            return await self.process_pdf(file_path)
        elif file_path.endswith('.md'):
            return await self.process_markdown(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_path}")
    
    async def process_directory(self, directory: str, file_extensions: List[str] = None) -> List[Document]:
        """디렉토리 처리"""
        if file_extensions is None:
            file_extensions = ['.pdf', '.md']
        
        all_documents = []
        files_to_process = []
        
        # 재귀적으로 파일 찾기
        for root, dirs, files in os.walk(directory):
            for filename in files:
                if any(filename.endswith(ext) for ext in file_extensions):
                    files_to_process.append(os.path.join(root, filename))
        
        logger.info(f"Found {len(files_to_process)} files to process in {directory}")
        
        # 파일 처리
        for file_path in files_to_process:
            try:
                documents = await self.process_file(file_path)
                all_documents.extend(documents)
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {str(e)}")
                continue
        
        return all_documents
```

### Step 3: 설정 파일 커스터마이징 가이드

```python
# config/custom_metadata_config.py
"""
사용자 정의 메타데이터 설정 예시
이 파일을 수정하여 프로젝트에 맞는 메타데이터 규칙을 정의하세요.
"""

from app.config.metadata_config import MetadataConfig

# 예시 1: 게임 가이드 프로젝트
game_guide_config = MetadataConfig(
    # 필수 필드
    required_fields=[
        "title",      # 문서 제목
        "category"    # 문서 카테고리
    ],
    
    # 선택 필드와 기본값
    optional_fields={
        "author": "Anonymous",
        "version": "latest",
        "difficulty": "medium",
        "tags": [],
        "created_date": None,
        "updated_date": None
    },
    
    # 파일명 패턴 (정규식)
    # 예: "boss_카오스벨룸_공략.md" → category: boss, name: 카오스벨룸_공략
    filename_pattern=r"^(?P<category>[^_]+)_(?P<name>.+)\.md$",
    
    # 카테고리 별칭
    category_aliases={
        "boss": "boss_guide",
        "class": "class_guide",
        "farming": "farming_guide",
        "gear": "equipment_guide"
    }
)

# 예시 2: 기술 문서 프로젝트
tech_docs_config = MetadataConfig(
    required_fields=["title", "type", "version"],
    optional_fields={
        "author": "Tech Team",
        "status": "draft",
        "tags": [],
        "related_docs": []
    },
    filename_pattern=r"^(?P<version>v\d+\.\d+)_(?P<type>[^_]+)_(?P<name>.+)\.md$",
    category_aliases={
        "api": "api_documentation",
        "guide": "user_guide",
        "ref": "reference"
    }
)

# 현재 프로젝트에서 사용할 설정 선택
current_config = game_guide_config
```

## 3. Markdown 작성 가이드 (유연한 구조)

### 최소 요구사항 Markdown

```markdown
---
title: 문서 제목 (필수)
category: 카테고리 (필수)
---

# 문서 내용

여기에 내용을 작성합니다.
```

### 권장 Markdown 구조

```markdown
---
# 필수 필드
title: 나이트로드 5차 스킬 가이드
category: class_guide

# 선택 필드 (프로젝트에 따라 추가)
author: 작성자명
created_date: 2024-01-15
updated_date: 2024-01-20
tags: 
  - 나이트로드
  - 5차스킬
  - 스킬가이드

# 커스텀 필드 (자유롭게 추가 가능)
custom_field1: value1
custom_field2: value2
---

# 나이트로드 5차 스킬 가이드

## 개요

내용...

## 상세 내용

### 섹션 1

내용...
```

## 4. 검색 시 메타데이터 활용

### 유연한 필터링 구현

```python
# app/services/search_service.py
from typing import Dict, List, Optional
from app.services.vector_store import VectorStoreService

class SearchService:
    def __init__(self, vector_store: VectorStoreService):
        self.vector_store = vector_store
    
    async def search_with_metadata(
        self, 
        query: str, 
        metadata_filters: Optional[Dict] = None,
        k: int = 5
    ) -> List[Document]:
        """메타데이터 필터를 활용한 검색"""
        
        if not metadata_filters:
            # 필터 없이 일반 검색
            return await self.vector_store.search(query, k=k)
        
        # Qdrant 필터 구성 (동적으로 생성)
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        conditions = []
        for field, value in metadata_filters.items():
            # 메타데이터 필드 경로 구성
            field_path = f"metadata.{field}"
            
            if isinstance(value, list):
                # 리스트인 경우 OR 조건
                for v in value:
                    conditions.append(
                        FieldCondition(
                            key=field_path,
                            match=MatchValue(value=v)
                        )
                    )
            else:
                # 단일 값
                conditions.append(
                    FieldCondition(
                        key=field_path,
                        match=MatchValue(value=value)
                    )
                )
        
        filter = Filter(must=conditions) if conditions else None
        
        # 필터가 적용된 검색
        retriever = self.vector_store.get_retriever(k=k)
        retriever.search_kwargs["filter"] = filter
        
        return await retriever.aget_relevant_documents(query)
```

### 검색 예시

```python
# 카테고리로 필터링
results = await search_service.search_with_metadata(
    query="5차 스킬 추천",
    metadata_filters={"category": "class_guide"}
)

# 여러 조건으로 필터링
results = await search_service.search_with_metadata(
    query="보스 공략법",
    metadata_filters={
        "category": "boss_guide",
        "difficulty": "hard"
    }
)

# 태그로 필터링
results = await search_service.search_with_metadata(
    query="사냥터 추천",
    metadata_filters={"tags": ["레벨업", "경험치"]}
)
```

## 5. 메타데이터 관리 도구

### 메타데이터 검증 스크립트

```python
# scripts/validate_metadata.py
import os
import yaml
from rich.console import Console
from rich.table import Table
from app.config.metadata_config import metadata_config

console = Console()

def validate_markdown_files(directory: str):
    """모든 Markdown 파일의 메타데이터 검증"""
    
    table = Table(title="메타데이터 검증 결과")
    table.add_column("파일명", style="cyan")
    table.add_column("상태", style="green")
    table.add_column("누락된 필드", style="red")
    table.add_column("경고", style="yellow")
    
    for root, dirs, files in os.walk(directory):
        for filename in files:
            if filename.endswith('.md'):
                file_path = os.path.join(root, filename)
                status, missing, warnings = validate_file(file_path)
                
                table.add_row(
                    filename,
                    "✅ OK" if status else "❌ Error",
                    ", ".join(missing) if missing else "-",
                    ", ".join(warnings) if warnings else "-"
                )
    
    console.print(table)

def validate_file(file_path: str):
    """개별 파일 검증"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 프론트매터 추출
    metadata = {}
    if content.startswith('---'):
        end_index = content.find('---', 3)
        if end_index != -1:
            yaml_content = content[3:end_index].strip()
            try:
                metadata = yaml.safe_load(yaml_content) or {}
            except:
                return False, ["YAML 파싱 오류"], []
    
    # 필수 필드 검사
    missing = []
    for field in metadata_config.required_fields:
        if field not in metadata:
            missing.append(field)
    
    # 경고 사항 검사
    warnings = []
    if not metadata.get('updated_date'):
        warnings.append("updated_date 없음")
    
    return len(missing) == 0, missing, warnings

if __name__ == "__main__":
    validate_markdown_files("data/markdown")
```

### 메타데이터 일괄 업데이트

```python
# scripts/update_metadata.py
import os
import yaml
from datetime import datetime

def update_metadata_field(directory: str, field: str, value: any):
    """특정 필드를 일괄 업데이트"""
    
    for root, dirs, files in os.walk(directory):
        for filename in files:
            if filename.endswith('.md'):
                file_path = os.path.join(root, filename)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 프론트매터 파싱 및 업데이트
                if content.startswith('---'):
                    end_index = content.find('---', 3)
                    if end_index != -1:
                        yaml_content = content[3:end_index].strip()
                        metadata = yaml.safe_load(yaml_content) or {}
                        
                        # 필드 업데이트
                        metadata[field] = value
                        
                        # 파일 다시 쓰기
                        new_yaml = yaml.dump(metadata, allow_unicode=True)
                        new_content = f"---\n{new_yaml}---\n{content[end_index+3:]}"
                        
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        
                        print(f"Updated {filename}")

# 사용 예시
if __name__ == "__main__":
    # 모든 파일에 updated_date 추가
    update_metadata_field(
        "data/markdown", 
        "updated_date", 
        datetime.now().strftime("%Y-%m-%d")
    )
```

## 6. 프로젝트별 커스터마이징 가이드

### 새로운 프로젝트를 위한 체크리스트

1. **메타데이터 설정 정의**
   ```python
   # 1. metadata_config.py 수정
   # 2. 필수 필드 정의
   # 3. 선택 필드와 기본값 설정
   # 4. 파일명 규칙 정의 (선택사항)
   ```

2. **Markdown 템플릿 생성**
   ```python
   # scripts/create_template.py
   def create_project_template(template_name: str):
       """프로젝트별 Markdown 템플릿 생성"""
       template = f"""---
{yaml.dump(metadata_config.optional_fields, allow_unicode=True)}---

# 제목

## 섹션 1

내용을 입력하세요.
"""
       
       with open(f"templates/{template_name}.md", 'w') as f:
           f.write(template)
   ```

3. **검색 필터 정의**
   ```python
   # 프로젝트별 자주 사용하는 필터 정의
   COMMON_FILTERS = {
       "beginner_guides": {"difficulty": "beginner"},
       "latest_content": {"updated_date": {"$gte": "2024-01-01"}},
       "official_only": {"author": "Official"}
   }
   ```

### 확장 예시

```python
# 새로운 문서 타입 추가 시
class ExtendedDocumentProcessor(DocumentProcessor):
    async def process_json(self, file_path: str) -> List[Document]:
        """JSON 파일 처리 추가"""
        # JSON 처리 로직
        pass
    
    async def process_file(self, file_path: str) -> List[Document]:
        if file_path.endswith('.json'):
            return await self.process_json(file_path)
        return await super().process_file(file_path)
```

## 7. 모범 사례

### DO ✅
- 모든 메타데이터는 프론트매터에 명시
- 카테고리는 일관된 명명 규칙 사용
- 필수 필드는 최소화
- 메타데이터 검증 도구 활용

### DON'T ❌
- 파일명에만 의존하는 메타데이터
- 하드코딩된 카테고리나 태그
- 너무 많은 필수 필드
- 검증 없는 메타데이터 사용

이제 더 유연하고 확장 가능한 시스템이 되었습니다!
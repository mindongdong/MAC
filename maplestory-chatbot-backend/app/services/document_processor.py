# app/services/document_processor.py
from langchain_community.document_loaders import PyPDFLoader
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
        
        # 스마트 메타데이터 추출 (파일명이나 내용에서)
        metadata.update(self._extract_smart_metadata(filename))
        
        return metadata
    
    def _extract_smart_metadata(self, filename: str) -> Dict:
        """파일명에서 스마트 메타데이터 추출"""
        metadata = {}
        filename_lower = filename.lower()
        
        # 직업 검출
        for class_name in self.metadata_config.available_classes:
            if class_name in filename:
                metadata["class"] = class_name
                break
        
        # 콘텐츠 타입 검출
        for keyword, content_type in self.metadata_config.content_type_aliases.items():
            if keyword in filename:
                metadata["content_type"] = content_type
                break
        
        # 서버 타입 검출
        for server_type in self.metadata_config.server_types:
            if server_type in filename:
                metadata["server_type"] = server_type
                break
        
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
        """PDF 처리 (기존 코드 개선)"""
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
        """디렉토리 처리 (PDF와 Markdown 모두 지원)"""
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
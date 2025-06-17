#!/usr/bin/env python3
# scripts/fix_metadata.py

"""
문서 메타데이터 수정 스크립트
- "No Title" 문제 해결
- 문서 제목 자동 추출 및 업데이트
"""

import asyncio
import sys
import os
from pathlib import Path
import re
import logging
from typing import Dict, List, Optional

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStoreService
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, UpdateStatus
from app.services.langchain_service import LangChainService
from app.services.document_processor import DocumentProcessor

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MetadataFixer:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.embeddings = self.embedding_service.get_embeddings()
        self.vector_store_service = VectorStoreService(self.embeddings)
        self.client = self.vector_store_service.client
        self.langchain_service = LangChainService()
        self.doc_processor = DocumentProcessor()

    def extract_title_from_content(self, content: str, file_path: str) -> str:
        """문서 내용에서 제목을 견고하게 추출"""
        try:
            # 1. YAML frontmatter에서 title 추출 시도
            if content.startswith("---"):
                end_idx = content.find("---", 3)
                if end_idx != -1:
                    import yaml
                    try:
                        yaml_content = content[3:end_idx].strip()
                        metadata = yaml.safe_load(yaml_content)
                        if isinstance(metadata, dict) and metadata.get('title'):
                            title = metadata['title'].strip()
                            if title and title != "No Title":
                                return title
                    except Exception:
                        pass
            
            # 2. 첫 번째 # 헤더 찾기
            lines = content.split('\n')
            for line in lines[:20]:  # 처음 20줄만 확인
                line = line.strip()
                if line.startswith('# ') and len(line) > 2:
                    title = line[2:].strip()
                    # 특수문자나 숫자만 있는 제목 제외
                    if re.search(r'[가-힣a-zA-Z]', title):
                        return title
            
            # 3. ## 헤더 찾기 (대안)
            for line in lines[:20]:
                line = line.strip()
                if line.startswith('## ') and len(line) > 3:
                    title = line[3:].strip()
                    if re.search(r'[가-힣a-zA-Z]', title):
                        return title
            
            # 4. 파일명에서 추출
            filename = os.path.basename(file_path)
            title = os.path.splitext(filename)[0]
            
            # 파일명 정리
            title = title.replace('_', ' ').replace('-', ' ')
            # 연속된 공백 제거
            title = re.sub(r'\s+', ' ', title).strip()
            
            return title if title else "Untitled Document"
            
        except Exception as e:
            logger.error(f"제목 추출 중 오류: {e}")
            return os.path.splitext(os.path.basename(file_path))[0]
    
    def categorize_document(self, title: str, content: str) -> str:
        """문서 내용을 기반으로 카테고리 분류"""
        title_lower = title.lower()
        content_lower = content.lower()
        
        # 키워드 기반 카테고리 분류
        if any(keyword in title_lower or keyword in content_lower 
               for keyword in ['스킬', '빌드', '육성', '어빌리티', '하이퍼스탯']):
            return 'class_guide'
        elif any(keyword in title_lower or keyword in content_lower 
                 for keyword in ['이벤트', '보상', '코인샵', '패스']):
            return 'event_guide'
        elif any(keyword in title_lower or keyword in content_lower 
                 for keyword in ['보스', '레이드', '공략', '드랍']):
            return 'boss_guide'
        elif any(keyword in title_lower or keyword in content_lower 
                 for keyword in ['시스템', '가이드', '설정', '방법']):
            return 'system_guide'
        elif any(keyword in title_lower or keyword in content_lower 
                 for keyword in ['업데이트', '패치', '릴리즈']):
            return 'update_info'
        else:
            return 'general'
    
    async def fix_document_metadata(self) -> Dict[str, int]:
        """모든 문서의 메타데이터 수정"""
        try:
            stats = {
                'total_processed': 0,
                'titles_fixed': 0,
                'categories_added': 0,
                'errors': 0
            }
            
            # 문서 데이터 디렉토리 확인
            data_dir = project_root / "data" / "markdown"
            if not data_dir.exists():
                logger.error(f"데이터 디렉토리를 찾을 수 없습니다: {data_dir}")
                return stats
            
            # 모든 마크다운 파일 찾기
            md_files = list(data_dir.rglob("*.md"))
            logger.info(f"{len(md_files)}개의 마크다운 파일을 발견했습니다.")
            
            for file_path in md_files:
                try:
                    stats['total_processed'] += 1
                    
                    # 파일 내용 읽기
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 제목 추출
                    new_title = self.extract_title_from_content(content, str(file_path))
                    
                    # 카테고리 분류
                    category = self.categorize_document(new_title, content)
                    
                    # YAML frontmatter 업데이트 또는 추가
                    updated_content = self._update_frontmatter(
                        content, new_title, category, str(file_path)
                    )
                    
                    # 파일에 다시 쓰기
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(updated_content)
                    
                    stats['titles_fixed'] += 1
                    stats['categories_added'] += 1
                    
                    logger.info(f"수정됨: {file_path.name} -> {new_title} [{category}]")
                    
                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f"파일 처리 중 오류 {file_path}: {e}")
            
            return stats
            
        except Exception as e:
            logger.error(f"메타데이터 수정 중 오류: {e}")
            return {'total_processed': 0, 'titles_fixed': 0, 'categories_added': 0, 'errors': 1}
    
    def _update_frontmatter(self, content: str, title: str, category: str, file_path: str) -> str:
        """YAML frontmatter 업데이트 또는 추가"""
        try:
            # 상대 경로 계산
            rel_path = str(Path(file_path).relative_to(project_root))
            
            new_frontmatter = f"""---
title: "{title}"
category: {category}
source: "{rel_path}"
last_updated: "{self._get_file_mtime(file_path)}"
---

"""
            
            # 기존 frontmatter 제거 후 새로운 것 추가
            if content.startswith("---"):
                # 기존 frontmatter 찾기
                end_idx = content.find("---", 3)
                if end_idx != -1:
                    # 기존 frontmatter 제거
                    content_without_fm = content[end_idx + 3:].lstrip('\n')
                    return new_frontmatter + content_without_fm
            
            # frontmatter가 없으면 추가
            return new_frontmatter + content.lstrip('\n')
            
        except Exception as e:
            logger.error(f"Frontmatter 업데이트 중 오류: {e}")
            return content
    
    def _get_file_mtime(self, file_path: str) -> str:
        """파일 수정 시간 가져오기"""
        try:
            import datetime
            mtime = os.path.getmtime(file_path)
            return datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
        except:
            return datetime.datetime.now().strftime('%Y-%m-%d')

async def main():
    """메인 실행 함수"""
    print("🔧 메타데이터 수정 작업을 시작합니다...")
    
    fixer = MetadataFixer()
    stats = await fixer.fix_document_metadata()
    
    print("\n📊 작업 완료 통계:")
    print(f"  - 처리된 파일: {stats['total_processed']}개")
    print(f"  - 제목 수정: {stats['titles_fixed']}개")
    print(f"  - 카테고리 추가: {stats['categories_added']}개")
    print(f"  - 오류: {stats['errors']}개")
    
    if stats['errors'] == 0:
        print("\n✅ 모든 메타데이터가 성공적으로 수정되었습니다!")
        print("📝 다음 단계: python scripts/ingest_documents.py 실행하여 벡터 스토어를 업데이트하세요.")
    else:
        print(f"\n⚠️  {stats['errors']}개의 오류가 발생했습니다. 로그를 확인하세요.")

if __name__ == "__main__":
    asyncio.run(main()) 
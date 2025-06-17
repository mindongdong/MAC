#!/usr/bin/env python3
# scripts/test_search_quality.py

"""
벡터 검색 품질 분석 스크립트
- 실제 유사도 점수 확인
- 문서별 검색 성능 분석
- 임베딩 품질 평가
"""

import asyncio
import sys
import os
from pathlib import Path
import logging
from typing import List, Dict

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.services.vector_store import VectorStoreService
from app.services.embedding_service import EmbeddingService
from app.config import settings

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SearchQualityAnalyzer:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        embeddings = self.embedding_service.get_embeddings()
        self.vector_store = VectorStoreService(embeddings)
        
    async def analyze_search_quality(self, query: str, k: int = 10):
        """검색 품질 분석"""
        logger.info(f"분석할 쿼리: '{query}'")
        
        # 1. 기본 similarity 검색 (점수 제한 없음)
        similarity_retriever = self.vector_store.get_retriever(
            k=k, 
            search_type="similarity"
        )
        
        similarity_docs = similarity_retriever.get_relevant_documents(query)
        
        # 2. similarity_score_threshold 검색
        threshold_retriever = self.vector_store.get_retriever(
            k=k,
            search_type="similarity_score_threshold"
        )
        
        try:
            threshold_docs = threshold_retriever.get_relevant_documents(query)
        except Exception as e:
            logger.warning(f"임계값 검색 실패: {e}")
            threshold_docs = []
        
        # 3. 원시 벡터 검색으로 실제 점수 확인
        embeddings = self.embedding_service.get_embeddings()
        query_vector = embeddings.embed_query(query)
        
        # Qdrant에서 직접 검색
        from qdrant_client.models import Filter
        raw_results = self.vector_store.client.search(
            collection_name=settings.collection_name,
            query_vector=query_vector,
            limit=k,
            with_payload=True,
            with_vectors=False,
            score_threshold=0.0001  # 매우 낮은 임계값
        )
        
        print(f"\n🔍 검색 품질 분석: '{query}'")
        print("=" * 60)
        
        print(f"\n📊 기본 Similarity 검색 결과 ({len(similarity_docs)}개)")
        for i, doc in enumerate(similarity_docs[:5]):
            print(f"{i+1}. {doc.metadata.get('title', 'No Title')[:50]}...")
            print(f"   Source: {doc.metadata.get('source', 'Unknown')}")
            print(f"   Content: {doc.page_content[:100]}...")
            print()
        
        print(f"\n🎯 Threshold 검색 결과 ({len(threshold_docs)}개)")
        for i, doc in enumerate(threshold_docs[:5]):
            print(f"{i+1}. {doc.metadata.get('title', 'No Title')[:50]}...")
            print(f"   Source: {doc.metadata.get('source', 'Unknown')}")
            print(f"   Content: {doc.page_content[:100]}...")
            print()
        
        print(f"\n🔢 실제 유사도 점수 (상위 {min(10, len(raw_results))}개)")
        for i, result in enumerate(raw_results[:10]):
            title = result.payload.get('metadata', {}).get('title', 'No Title')
            source = result.payload.get('metadata', {}).get('source', 'Unknown')
            content = result.payload.get('page_content', '')[:80]
            
            print(f"{i+1}. 점수: {result.score:.6f}")
            print(f"   제목: {title[:50]}")
            print(f"   소스: {source}")
            print(f"   내용: {content}...")
            print()
        
        # 임계값별 통과 문서 수 분석
        thresholds = [0.001, 0.005, 0.01, 0.05, 0.1, 0.2, 0.3]
        print(f"\n📈 임계값별 통과 문서 수")
        for threshold in thresholds:
            passed = sum(1 for r in raw_results if r.score >= threshold)
            print(f"   {threshold:5.3f}: {passed:2d}개 문서 통과")
        
        return {
            "query": query,
            "similarity_count": len(similarity_docs),
            "threshold_count": len(threshold_docs),
            "raw_results": len(raw_results),
            "max_score": raw_results[0].score if raw_results else 0,
            "min_score": raw_results[-1].score if raw_results else 0,
            "score_distribution": [r.score for r in raw_results]
        }

async def main():
    analyzer = SearchQualityAnalyzer()
    
    # 테스트할 쿼리들 (실패했던 것들 포함)
    test_queries = [
        "렌의 주력 스킬은 뭐야?",
        "챌린저스 코인샵에서 뭘 살 수 있어?",
        "하이퍼 버닝 이벤트 보상은?",  # 성공했던 쿼리
        "솔 에르다는 어떻게 얻어?",
        "메이플 패스 혜택이 뭐야?",
        "보스 몬스터 추천해줘",
        "링크 스킬 추천",
        "신규 유저 가이드",  # 성공했던 쿼리
        # 추가 테스트 쿼리
        "메이플스토리",
        "스킬",
        "이벤트",
        "아이템"
    ]
    
    print("=== 메이플스토리 RAG 검색 품질 분석 ===")
    print("각 쿼리별로 실제 검색 점수와 문서 품질을 분석합니다.\n")
    
    results = []
    for query in test_queries:
        try:
            result = await analyzer.analyze_search_quality(query)
            results.append(result)
            
            # 사용자 입력 대기 (선택사항)
            user_input = input("\n다음 쿼리로 계속하시겠습니까? (Enter: 계속, 'q': 종료): ")
            if user_input.lower() == 'q':
                break
                
        except Exception as e:
            logger.error(f"쿼리 '{query}' 분석 중 오류: {e}")
            continue
    
    # 전체 결과 요약
    print("\n" + "="*60)
    print("📋 전체 분석 결과 요약")
    print("="*60)
    
    for result in results:
        print(f"쿼리: {result['query'][:30]:<30} | "
              f"기본: {result['similarity_count']:2d}개 | "
              f"임계값: {result['threshold_count']:2d}개 | "
              f"최대점수: {result['max_score']:.6f}")

if __name__ == "__main__":
    asyncio.run(main()) 
#!/usr/bin/env python3
"""
유사도 점수 분석 스크립트 - 임계값 최적화를 위한 데이터 분석
"""

import asyncio
import sys
import logging
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.langchain_service import LangChainService
from app.services.embedding_service import get_embeddings
from app.config.settings import settings

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimilarityAnalyzer:
    def __init__(self):
        self.langchain_service = LangChainService()
        self.embeddings = get_embeddings()
        
        # 테스트 질문들 (다양한 카테고리)
        self.test_questions = [
            {"question": "렌의 주력 스킬은 뭐야?", "category": "class_skill", "expected_keywords": ["렌", "스킬", "매화검"]},
            {"question": "챌린저스 코인샵에서 뭘 살 수 있어?", "category": "system_shop", "expected_keywords": ["챌린저스", "코인샵", "구매"]},
            {"question": "하이퍼 버닝 이벤트 보상은?", "category": "event_reward", "expected_keywords": ["하이퍼", "버닝", "보상"]},
            {"question": "솔 에르다는 어떻게 얻어?", "category": "item_obtain", "expected_keywords": ["솔 에르다", "획득", "얻는법"]},
            {"question": "메이플 패스 혜택이 뭐야?", "category": "system_benefit", "expected_keywords": ["메이플 패스", "혜택", "특전"]},
            {"question": "보스 몬스터 추천해줘", "category": "boss_guide", "expected_keywords": ["보스", "몬스터", "추천"]},
            {"question": "링크 스킬 추천", "category": "character_system", "expected_keywords": ["링크", "스킬", "추천"]},
            {"question": "신규 유저 가이드", "category": "beginner_guide", "expected_keywords": ["신규", "초보", "가이드"]},
            {"question": "렌 육성 가이드", "category": "class_guide", "expected_keywords": ["렌", "육성", "가이드"]},
            {"question": "여름 이벤트 정보", "category": "event_info", "expected_keywords": ["여름", "이벤트", "정보"]}
        ]
    
    def cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """코사인 유사도 계산"""
        v1_np = np.array(v1)
        v2_np = np.array(v2)
        
        dot_product = np.dot(v1_np, v2_np)
        norm_v1 = np.linalg.norm(v1_np)
        norm_v2 = np.linalg.norm(v2_np)
        
        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
        
        return float(dot_product / (norm_v1 * norm_v2))
    
    async def analyze_question_document_similarity(self) -> Dict:
        """질문과 문서 간 유사도 분석"""
        logger.info("질문-문서 유사도 분석을 시작합니다...")
        
        analysis_results = {
            "timestamp": datetime.now().isoformat(),
            "embedding_model": settings.voyage_model,
            "questions_analyzed": len(self.test_questions),
            "question_results": [],
            "overall_stats": {},
            "recommendations": {}
        }
        
        all_scores = []
        
        for test_q in self.test_questions:
            question = test_q["question"]
            category = test_q["category"]
            expected_keywords = test_q["expected_keywords"]
            
            logger.info(f"분석 중: {question}")
            
            # 질문 임베딩
            question_embedding = self.embeddings.embed_query(question)
            
            # 벡터 검색으로 상위 10개 문서 가져오기
            try:
                retriever = self.langchain_service.vector_store.get_retriever(k=10, search_type="similarity")
                documents = retriever.get_relevant_documents(question)
                
                question_result = {
                    "question": question,
                    "category": category,
                    "expected_keywords": expected_keywords,
                    "documents_found": len(documents),
                    "document_scores": [],
                    "max_score": 0.0,
                    "min_score": 1.0,
                    "avg_score": 0.0,
                    "relevant_docs_count": 0
                }
                
                # 각 문서와의 유사도 계산
                for i, doc in enumerate(documents):
                    doc_embedding = self.embeddings.embed_documents([doc.page_content])[0]
                    similarity_score = self.cosine_similarity(question_embedding, doc_embedding)
                    
                    # 키워드 매칭 확인
                    content_lower = doc.page_content.lower()
                    title_lower = doc.metadata.get('title', '').lower()
                    keyword_matches = sum(1 for kw in expected_keywords if kw.lower() in content_lower or kw.lower() in title_lower)
                    is_relevant = keyword_matches >= 1
                    
                    doc_info = {
                        "rank": i + 1,
                        "title": doc.metadata.get('title', 'No Title'),
                        "source": doc.metadata.get('source', ''),
                        "similarity_score": round(similarity_score, 6),
                        "keyword_matches": keyword_matches,
                        "is_relevant": is_relevant,
                        "content_preview": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
                    }
                    
                    question_result["document_scores"].append(doc_info)
                    all_scores.append(similarity_score)
                    
                    if is_relevant:
                        question_result["relevant_docs_count"] += 1
                
                # 통계 계산
                if question_result["document_scores"]:
                    scores = [d["similarity_score"] for d in question_result["document_scores"]]
                    question_result["max_score"] = max(scores)
                    question_result["min_score"] = min(scores)
                    question_result["avg_score"] = sum(scores) / len(scores)
                
                analysis_results["question_results"].append(question_result)
                
            except Exception as e:
                logger.error(f"질문 '{question}' 분석 중 오류: {e}")
                question_result["error"] = str(e)
                analysis_results["question_results"].append(question_result)
        
        # 전체 통계 계산
        if all_scores:
            analysis_results["overall_stats"] = {
                "total_scores": len(all_scores),
                "max_score": max(all_scores),
                "min_score": min(all_scores),
                "avg_score": sum(all_scores) / len(all_scores),
                "median_score": np.median(all_scores),
                "std_score": np.std(all_scores),
                "percentiles": {
                    "p25": np.percentile(all_scores, 25),
                    "p50": np.percentile(all_scores, 50),
                    "p75": np.percentile(all_scores, 75),
                    "p90": np.percentile(all_scores, 90),
                    "p95": np.percentile(all_scores, 95)
                }
            }
            
            # 임계값 추천
            stats = analysis_results["overall_stats"]
            analysis_results["recommendations"] = {
                "conservative_threshold": round(stats["percentiles"]["p25"], 3),  # 보수적 (25%ile)
                "balanced_threshold": round(stats["percentiles"]["p50"], 3),      # 균형 (50%ile)
                "aggressive_threshold": round(stats["percentiles"]["p75"], 3),    # 공격적 (75%ile)
                "current_threshold": settings.min_relevance_score,
                "suggested_threshold": round(max(0.001, stats["percentiles"]["p25"]), 3)
            }
        
        return analysis_results
    
    async def test_threshold_performance(self, thresholds: List[float]) -> Dict:
        """다양한 임계값에서의 성능 테스트"""
        logger.info(f"임계값 성능 테스트: {thresholds}")
        
        performance_results = {
            "timestamp": datetime.now().isoformat(),
            "thresholds_tested": thresholds,
            "threshold_results": []
        }
        
        for threshold in thresholds:
            logger.info(f"임계값 {threshold} 테스트 중...")
            
            threshold_result = {
                "threshold": threshold,
                "questions_answered": 0,
                "questions_total": len(self.test_questions),
                "relevant_answers": 0,
                "question_details": []
            }
            
            for test_q in self.test_questions:
                question = test_q["question"]
                
                try:
                    # 임시로 임계값 변경하여 검색
                    original_score = settings.min_relevance_score
                    settings.min_relevance_score = threshold
                    
                    # 검색 실행
                    retriever = self.langchain_service.vector_store.get_retriever(
                        k=5, 
                        search_type="similarity_score_threshold"
                    )
                    documents = retriever.get_relevant_documents(question)
                    
                    # 설정 복원
                    settings.min_relevance_score = original_score
                    
                    answered = len(documents) > 0
                    if answered:
                        threshold_result["questions_answered"] += 1
                        
                        # 관련성 확인 (간단한 키워드 매칭)
                        content = " ".join([doc.page_content for doc in documents]).lower()
                        keywords_found = sum(1 for kw in test_q["expected_keywords"] if kw.lower() in content)
                        is_relevant = keywords_found >= 1
                        
                        if is_relevant:
                            threshold_result["relevant_answers"] += 1
                    
                    threshold_result["question_details"].append({
                        "question": question,
                        "answered": answered,
                        "documents_count": len(documents),
                        "relevant": answered and is_relevant if answered else False
                    })
                    
                except Exception as e:
                    logger.error(f"임계값 {threshold} 테스트 중 오류: {e}")
                    threshold_result["question_details"].append({
                        "question": question,
                        "answered": False,
                        "error": str(e)
                    })
            
            # 성능 메트릭 계산
            total = threshold_result["questions_total"]
            answered = threshold_result["questions_answered"]
            relevant = threshold_result["relevant_answers"]
            
            threshold_result["answer_rate"] = answered / total if total > 0 else 0
            threshold_result["precision"] = relevant / answered if answered > 0 else 0
            threshold_result["recall"] = relevant / total if total > 0 else 0
            
            # F1 스코어
            p = threshold_result["precision"]
            r = threshold_result["recall"]
            threshold_result["f1_score"] = 2 * p * r / (p + r) if (p + r) > 0 else 0
            
            performance_results["threshold_results"].append(threshold_result)
        
        return performance_results
    
    def save_results(self, results: Dict, filename: str):
        """결과를 JSON 파일로 저장"""
        output_file = project_root / "logs" / filename
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"결과가 저장되었습니다: {output_file}")

async def main():
    """메인 실행 함수"""
    print("🔍 유사도 점수 분석을 시작합니다...")
    
    analyzer = SimilarityAnalyzer()
    
    # 1. 질문-문서 유사도 분석
    print("\n1️⃣ 질문-문서 유사도 분석 중...")
    similarity_results = await analyzer.analyze_question_document_similarity()
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    analyzer.save_results(similarity_results, f"similarity_analysis_{timestamp}.json")
    
    # 결과 요약 출력
    stats = similarity_results.get("overall_stats", {})
    if stats:
        print(f"\n📊 유사도 점수 통계:")
        print(f"  - 최대 점수: {stats['max_score']:.6f}")
        print(f"  - 평균 점수: {stats['avg_score']:.6f}")
        print(f"  - 중간 점수: {stats['median_score']:.6f}")
        print(f"  - 최소 점수: {stats['min_score']:.6f}")
        
        recommendations = similarity_results.get("recommendations", {})
        if recommendations:
            print(f"\n💡 임계값 추천:")
            print(f"  - 현재 설정: {recommendations['current_threshold']}")
            print(f"  - 추천 값: {recommendations['suggested_threshold']}")
            print(f"  - 보수적: {recommendations['conservative_threshold']}")
            print(f"  - 균형적: {recommendations['balanced_threshold']}")
    
    # 2. 임계값 성능 테스트
    print(f"\n2️⃣ 임계값 성능 테스트 중...")
    test_thresholds = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05]
    performance_results = await analyzer.test_threshold_performance(test_thresholds)
    
    analyzer.save_results(performance_results, f"threshold_performance_{timestamp}.json")
    
    # 성능 결과 요약
    print(f"\n📈 임계값별 성능:")
    for result in performance_results["threshold_results"]:
        threshold = result["threshold"]
        answer_rate = result["answer_rate"] * 100
        f1_score = result["f1_score"]
        print(f"  - {threshold:5.3f}: 답변률 {answer_rate:5.1f}%, F1 {f1_score:.3f}")
    
    print(f"\n✅ 분석 완료! 결과는 logs/ 디렉토리에 저장되었습니다.")

if __name__ == "__main__":
    asyncio.run(main()) 
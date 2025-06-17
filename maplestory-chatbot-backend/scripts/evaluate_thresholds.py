#!/usr/bin/env python3
# scripts/evaluate_thresholds.py

"""
RAG 임계값 최적화 평가 스크립트
- 다양한 MIN_RELEVANCE_SCORE 값에 대한 성능 평가
- Golden Set 기반 정확도 측정
"""

import asyncio
import sys
import os
from pathlib import Path
import json
import logging
import time
from typing import List, Dict, Tuple

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.services.langchain_service import LangChainService
from app.config import settings

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ThresholdEvaluator:
    def __init__(self):
        self.langchain_service = LangChainService()
        
        # Golden Set: 평가용 질문과 기대되는 키워드들
        self.golden_set = [
            {
                "question": "렌의 주력 스킬은 뭐야?",
                "expected_keywords": ["렌", "스킬", "주력"],
                "category": "class_skill"
            },
            {
                "question": "챌린저스 코인샵에서 뭘 살 수 있어?",
                "expected_keywords": ["챌린저스", "코인샵", "구매"],
                "category": "system_shop"
            },
            {
                "question": "하이퍼 버닝 이벤트 보상은?",
                "expected_keywords": ["하이퍼", "버닝", "이벤트", "보상"],
                "category": "event_reward"
            },
            {
                "question": "솔 에르다는 어떻게 얻어?",
                "expected_keywords": ["솔", "에르다", "획득"],
                "category": "item_obtain"
            },
            {
                "question": "메이플 패스 혜택이 뭐야?",
                "expected_keywords": ["메이플", "패스", "혜택"],
                "category": "system_benefit"
            },
            {
                "question": "보스 몬스터 추천해줘",
                "expected_keywords": ["보스", "몬스터", "추천"],
                "category": "boss_guide"
            },
            {
                "question": "링크 스킬 추천",
                "expected_keywords": ["링크", "스킬"],
                "category": "character_system"
            },
            {
                "question": "신규 유저 가이드",
                "expected_keywords": ["신규", "유저", "가이드", "초보"],
                "category": "beginner_guide"
            }
        ]

    async def evaluate_threshold(self, threshold: float) -> Dict:
        """특정 임계값에 대한 성능 평가"""
        logger.info(f"Evaluating threshold: {threshold}")
        
        # 임시로 설정 변경
        original_threshold = settings.min_relevance_score
        original_search_type = settings.search_type
        settings.min_relevance_score = threshold
        settings.search_type = "similarity_score_threshold"  # 명시적으로 임계값 검색 사용
        
        # 새로운 retriever 생성 (설정 변경 반영)
        new_retriever = self.langchain_service.vector_store.get_retriever(
            k=settings.max_retrieval_docs,
            search_type=settings.search_type
        )
        
        # 기존 retriever 백업 및 교체
        original_retriever = self.langchain_service.retriever
        self.langchain_service.retriever = new_retriever
        
        results = {
            "threshold": threshold,
            "total_questions": len(self.golden_set),
            "answered": 0,
            "no_answer": 0,
            "relevant_answers": 0,
            "detailed_results": []
        }
        
        for item in self.golden_set:
            question = item["question"]
            expected_keywords = item["expected_keywords"]
            category = item["category"]
            
            try:
                # 질문 처리
                start_time = time.time()
                response_data = await self.langchain_service.chat(
                    message=question,
                    session_id="threshold_evaluator"
                )
                processing_time = time.time() - start_time
                
                response = response_data.get("response", "")
                sources_count = response_data.get("sources_count", 0)
                metadata = response_data.get("metadata", {})
                
                # 답변 분석
                is_answered = not ("찾을 수 없습니다" in response or "관련 정보가 없습니다" in response)
                is_relevant = self._check_relevance(response, expected_keywords)
                
                if is_answered:
                    results["answered"] += 1
                    if is_relevant:
                        results["relevant_answers"] += 1
                else:
                    results["no_answer"] += 1
                
                # 상세 결과 저장
                detailed_result = {
                    "question": question,
                    "category": category,
                    "answered": is_answered,
                    "relevant": is_relevant,
                    "sources_count": sources_count,
                    "processing_time": round(processing_time, 2),
                    "response_length": len(response),
                    "metadata": metadata
                }
                results["detailed_results"].append(detailed_result)
                
                logger.info(f"Q: {question[:30]}... | Answered: {is_answered} | Relevant: {is_relevant} | Sources: {sources_count}")
                
            except Exception as e:
                logger.error(f"Error processing question '{question}': {str(e)}")
                results["detailed_results"].append({
                    "question": question,
                    "category": category,
                    "answered": False,
                    "relevant": False,
                    "error": str(e)
                })
        
        # 성능 지표 계산
        if results["answered"] > 0:
            results["precision"] = results["relevant_answers"] / results["answered"]
        else:
            results["precision"] = 0
            
        results["recall"] = results["answered"] / results["total_questions"]
        
        if results["precision"] + results["recall"] > 0:
            results["f1_score"] = 2 * (results["precision"] * results["recall"]) / (results["precision"] + results["recall"])
        else:
            results["f1_score"] = 0
        
        # 설정 및 retriever 복원
        settings.min_relevance_score = original_threshold
        settings.search_type = original_search_type
        self.langchain_service.retriever = original_retriever
        
        return results

    def _check_relevance(self, response: str, expected_keywords: List[str]) -> bool:
        """답변의 관련성 확인"""
        response_lower = response.lower()
        
        # 최소 절반 이상의 키워드가 포함되어야 관련성 있다고 판단
        matched_keywords = 0
        for keyword in expected_keywords:
            if keyword.lower() in response_lower:
                matched_keywords += 1
        
        return matched_keywords >= len(expected_keywords) * 0.5

    async def compare_thresholds(self, thresholds: List[float]) -> Dict:
        """여러 임계값 비교 평가"""
        logger.info(f"Comparing thresholds: {thresholds}")
        
        comparison_results = {
            "thresholds": thresholds,
            "results": [],
            "best_threshold": None,
            "best_f1_score": 0
        }
        
        for threshold in thresholds:
            result = await self.evaluate_threshold(threshold)
            comparison_results["results"].append(result)
            
            # 최고 F1 스코어 추적
            if result["f1_score"] > comparison_results["best_f1_score"]:
                comparison_results["best_f1_score"] = result["f1_score"]
                comparison_results["best_threshold"] = threshold
        
        return comparison_results

    def save_results(self, results: Dict, filename: str = None):
        """결과를 JSON 파일로 저장"""
        if not filename:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"threshold_evaluation_{timestamp}.json"
        
        results_dir = project_root / "logs"
        results_dir.mkdir(exist_ok=True)
        
        file_path = results_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Results saved to: {file_path}")
        return file_path

    def print_summary(self, results: Dict):
        """결과 요약 출력"""
        print("\n" + "="*60)
        print("📊 임계값 평가 결과 요약")
        print("="*60)
        
        if "results" in results:
            # 여러 임계값 비교 결과
            print(f"평가된 임계값: {results['thresholds']}")
            print(f"최적 임계값: {results['best_threshold']} (F1: {results['best_f1_score']:.3f})")
            print("\n상세 결과:")
            print(f"{'임계값':<8} {'응답률':<8} {'정확도':<8} {'F1 점수':<8}")
            print("-" * 40)
            
            for result in results["results"]:
                print(f"{result['threshold']:<8} {result['recall']:<8.3f} {result['precision']:<8.3f} {result['f1_score']:<8.3f}")
        
        else:
            # 단일 임계값 결과
            print(f"임계값: {results['threshold']}")
            print(f"총 질문 수: {results['total_questions']}")
            print(f"답변한 질문: {results['answered']}")
            print(f"답변 거부: {results['no_answer']}")
            print(f"관련성 있는 답변: {results['relevant_answers']}")
            print(f"응답률 (Recall): {results['recall']:.3f}")
            print(f"정확도 (Precision): {results['precision']:.3f}")
            print(f"F1 점수: {results['f1_score']:.3f}")

async def main():
    """메인 실행 함수"""
    evaluator = ThresholdEvaluator()
    
    print("=== RAG 임계값 최적화 평가 도구 ===")
    print("1. 단일 임계값 평가")
    print("2. 여러 임계값 비교 (추천)")
    print("3. 빠른 테스트 (0.5, 0.6, 0.7)")
    print("4. 낮은 임계값 테스트 (0.001, 0.01, 0.1)")
    print("5. 종료")
    
    while True:
        choice = input("\n선택하세요 (1-5): ").strip()
        
        if choice == '1':
            threshold = float(input("평가할 임계값을 입력하세요 (예: 0.6): "))
            result = await evaluator.evaluate_threshold(threshold)
            evaluator.print_summary(result)
            
            save = input("결과를 저장하시겠습니까? (y/N): ").strip().lower()
            if save == 'y':
                evaluator.save_results(result)
        
        elif choice == '2':
            thresholds_input = input("평가할 임계값들을 입력하세요 (예: 0.5,0.6,0.7): ")
            thresholds = [float(x.strip()) for x in thresholds_input.split(',')]
            
            result = await evaluator.compare_thresholds(thresholds)
            evaluator.print_summary(result)
            
            save = input("결과를 저장하시겠습니까? (y/N): ").strip().lower()
            if save == 'y':
                evaluator.save_results(result)
        
        elif choice == '3':
            thresholds = [0.5, 0.6, 0.7]
            result = await evaluator.compare_thresholds(thresholds)
            evaluator.print_summary(result)
            
            save = input("결과를 저장하시겠습니까? (y/N): ").strip().lower()
            if save == 'y':
                evaluator.save_results(result)
        
        elif choice == '4':
            print("현재 시스템에서 검색되는 실제 점수 범위 테스트...")
            thresholds = [0.001, 0.01, 0.1]
            result = await evaluator.compare_thresholds(thresholds)
            evaluator.print_summary(result)
            
            save = input("결과를 저장하시겠습니까? (y/N): ").strip().lower()
            if save == 'y':
                evaluator.save_results(result)
        
        elif choice == '5':
            print("프로그램을 종료합니다.")
            break
        
        else:
            print("잘못된 선택입니다. 1-5 중에서 선택해주세요.")

if __name__ == "__main__":
    asyncio.run(main()) 
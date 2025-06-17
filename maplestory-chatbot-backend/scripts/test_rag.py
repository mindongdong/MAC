#!/usr/bin/env python
# scripts/test_rag.py

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
from datetime import datetime
from typing import List, Dict
from pathlib import Path

from app.services.langchain_service import LangChainService
from app.config.settings import settings
from app.chains.prompts import MAPLESTORY_SYSTEM_PROMPT, MAPLESTORY_ANSWER_TEMPLATE

async def test_basic_qa():
    """기본 QA 테스트"""
    print("🧪 기본 QA 테스트 시작...")
    
    service = LangChainService()
    
    test_questions = [
        "렌 직업의 특징이 뭐야?",
        "메이플스토리에서 레벨업이 빠른 방법을 알려줘",
        "챌린저스 월드가 뭐야?",
        "제네시스 패스는 어떤 거야?",
        "하이퍼버닝 이벤트에 대해 설명해줘"
    ]
    
    results = []
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n📝 질문 {i}: {question}")
        
        try:
            response = await service.chat(
                message=question,
                session_id=f"test_session_{i}"
            )
            
            print(f"✅ 답변: {response['response'][:200]}...")
            print(f"📊 메타데이터: {response['metadata']}")
            print(f"📚 출처 개수: {len(response['sources'])}")
            
            results.append({
                "question": question,
                "answer": response['response'],
                "sources_count": len(response['sources']),
                "metadata": response['metadata'],
                "success": True
            })
            
        except Exception as e:
            print(f"❌ 오류: {e}")
            results.append({
                "question": question,
                "error": str(e),
                "success": False
            })
    
    return results

async def test_system_prompt_variations():
    """시스템 프롬프트 변형 테스트"""
    print("\n🧪 시스템 프롬프트 변형 테스트 시작...")
    
    # 원본 설정 저장
    original_use_system_prompt = settings.use_system_prompt
    original_enable_answer_template = settings.enable_answer_template
    
    test_question = "렌 직업 추천 이유와 육성 방법을 알려줘"
    variations = [
        {"use_system_prompt": False, "enable_answer_template": False, "name": "기본 프롬프트"},
        {"use_system_prompt": True, "enable_answer_template": False, "name": "새 시스템 프롬프트"},
        {"use_system_prompt": False, "enable_answer_template": True, "name": "기본 프롬프트 + 템플릿"},
        {"use_system_prompt": True, "enable_answer_template": True, "name": "새 시스템 프롬프트 + 템플릿"},
    ]
    
    results = []
    
    for variation in variations:
        print(f"\n🔧 테스트 설정: {variation['name']}")
        
        # 설정 변경
        settings.use_system_prompt = variation["use_system_prompt"]
        settings.enable_answer_template = variation["enable_answer_template"]
        
        service = LangChainService()  # 새로운 인스턴스 생성
        
        try:
            response = await service.chat(
                message=test_question,
                session_id=f"variation_test_{variation['name']}"
            )
            
            print(f"✅ 답변 길이: {len(response['response'])} 글자")
            print(f"📊 메타데이터: {response['metadata']}")
            
            results.append({
                "variation": variation['name'],
                "settings": variation,
                "answer_length": len(response['response']),
                "answer_preview": response['response'][:300] + "...",
                "metadata": response['metadata'],
                "success": True
            })
            
        except Exception as e:
            print(f"❌ 오류: {e}")
            results.append({
                "variation": variation['name'],
                "error": str(e),
                "success": False
            })
    
    # 원본 설정 복원
    settings.use_system_prompt = original_use_system_prompt
    settings.enable_answer_template = original_enable_answer_template
    
    return results

async def test_streaming():
    """스트리밍 테스트"""
    print("\n🧪 스트리밍 테스트 시작...")
    
    service = LangChainService()
    question = "메이플스토리 신규 유저에게 필요한 핵심 가이드를 자세히 알려줘"
    
    print(f"📝 질문: {question}")
    print("📡 스트리밍 응답:")
    print("-" * 50)
    
    try:
        full_response = ""
        async for chunk in service.chat(
            message=question,
            session_id="streaming_test",
            stream=True
        ):
            print(chunk, end="", flush=True)
            full_response += str(chunk)
        
        print("\n" + "-" * 50)
        print(f"✅ 완료! 총 응답 길이: {len(full_response)} 글자")
        return {"success": True, "response_length": len(full_response)}
        
    except Exception as e:
        print(f"\n❌ 스트리밍 오류: {e}")
        return {"success": False, "error": str(e)}

async def test_memory_persistence():
    """메모리 지속성 테스트"""
    print("\n🧪 메모리 지속성 테스트 시작...")
    
    service = LangChainService()
    session_id = "memory_test"
    
    conversation = [
        "렌이라는 직업에 대해 알려줘",
        "그럼 렌의 스킬 특징은 어떻게 돼?",
        "렌 육성할 때 주의할 점은 뭐야?",
        "앞서 말한 렌의 장점을 다시 요약해줘"
    ]
    
    results = []
    
    for i, message in enumerate(conversation, 1):
        print(f"\n💬 대화 {i}: {message}")
        
        try:
            response = await service.chat(
                message=message,
                session_id=session_id
            )
            
            print(f"🤖 답변: {response['response'][:200]}...")
            
            results.append({
                "turn": i,
                "question": message,
                "answer": response['response'],
                "success": True
            })
            
        except Exception as e:
            print(f"❌ 오류: {e}")
            results.append({
                "turn": i,
                "question": message,
                "error": str(e),
                "success": False
            })
    
    return results

async def test_improved_qa():
    """개선된 QA 테스트 - 문제가 된 질문들 포함"""
    print("🧪 개선된 QA 테스트 시작...")
    
    service = LangChainService()
    
    # 사용자가 제공한 문제 예시들 포함
    test_questions = [
        {
            "question": "챌린저스 서버에서 이벤트로 얻을 수 있는 주요 보상들을 정리해줘.",
            "expected_keywords": ["챌린저스", "포인트", "코인", "하드 스우", "정확한 수치"],
            "category": "챌린저스 월드"
        },
        {
            "question": "제네시스 패스를 통해 얻을 수 있는 혜택들을 정리해줘.",
            "expected_keywords": ["제네시스 패스", "혜택", "패스"],
            "category": "시스템 가이드"
        },
        {
            "question": "렌 직업의 특징이 뭐야?",
            "expected_keywords": ["렌", "직업", "스킬", "특징"],
            "category": "직업 가이드"
        },
        {
            "question": "메이플스토리에서 레벨업이 빠른 방법을 알려줘",
            "expected_keywords": ["레벨업", "경험치", "사냥터"],
            "category": "육성 가이드"
        },
        {
            "question": "하이퍼버닝 이벤트에 대해 설명해줘",
            "expected_keywords": ["하이퍼버닝", "이벤트", "레벨"],
            "category": "이벤트"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_questions, 1):
        question = test_case["question"]
        print(f"\n📝 질문 {i}: {question}")
        
        try:
            response = await service.chat(
                message=question,
                session_id=f"improved_test_{i}"
            )
            
            # 답변 품질 분석
            answer = response['response']
            sources = response['sources']
            metadata = response['metadata']
            
            # 개선 사항 확인
            has_valid_sources = metadata.get('valid_sources_count', 0) > 0
            answer_length = len(answer)
            contains_keywords = any(keyword in answer.lower() for keyword in test_case['expected_keywords'])
            
            # 부정확한 표현 검사
            vague_expressions = ["일반적으로", "보통", "대략", "약간", "어느정도"]
            has_vague_expressions = any(expr in answer for expr in vague_expressions)
            
            # 파일명 직접 출력 검사
            has_md_filename = ".md" in answer and "참고자료" not in answer.split(".md")[0]
            
            print(f"✅ 답변 길이: {answer_length} 글자")
            print(f"📊 유효한 참고자료: {metadata.get('valid_sources_count', 0)}개")
            print(f"🎯 키워드 포함: {'✓' if contains_keywords else '✗'}")
            print(f"🚫 애매한 표현: {'✗' if has_vague_expressions else '✓'}")
            print(f"📄 파일명 직접 출력: {'✗' if has_md_filename else '✓'}")
            print(f"🔗 유효한 링크: {'✓' if has_valid_sources else '✗'}")
            
            # 답변 미리보기
            preview = answer[:300] + "..." if len(answer) > 300 else answer
            print(f"💬 답변 미리보기: {preview}")
            
            results.append({
                "question": question,
                "category": test_case["category"],
                "answer": answer,
                "answer_length": answer_length,
                "valid_sources_count": metadata.get('valid_sources_count', 0),
                "contains_keywords": contains_keywords,
                "has_vague_expressions": has_vague_expressions,
                "has_md_filename": has_md_filename,
                "has_valid_sources": has_valid_sources,
                "metadata": metadata,
                "success": True
            })
            
        except Exception as e:
            print(f"❌ 오류: {e}")
            results.append({
                "question": question,
                "category": test_case["category"],
                "error": str(e),
                "success": False
            })
    
    return results

def save_test_results(all_results: Dict):
    """테스트 결과 저장"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # test_results 디렉토리 생성
    results_dir = Path("maplestory-chatbot-backend/test_results")
    results_dir.mkdir(exist_ok=True)
    
    # 결과 파일 저장
    results_file = results_dir / f"rag_test_results_{timestamp}.md"
    
    with open(results_file, 'w', encoding='utf-8') as f:
        f.write(f"# 메이플스토리 RAG 시스템 테스트 결과\n\n")
        f.write(f"**테스트 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Claude 모델**: {settings.claude_model}\n")
        f.write(f"**시스템 프롬프트 사용**: {settings.use_system_prompt}\n")
        f.write(f"**답변 템플릿 사용**: {settings.enable_answer_template}\n\n")
        
        # 기본 QA 테스트 결과
        f.write("## 1. 기본 QA 테스트\n\n")
        basic_results = all_results['basic_qa']
        success_count = sum(1 for r in basic_results if r.get('success', False))
        f.write(f"**성공률**: {success_count}/{len(basic_results)} ({success_count/len(basic_results)*100:.1f}%)\n\n")
        
        for result in basic_results:
            if result.get('success'):
                f.write(f"### Q: {result['question']}\n")
                f.write(f"**A**: {result['answer'][:500]}...\n")
                f.write(f"**출처 개수**: {result['sources_count']}\n")
                f.write(f"**메타데이터**: {result['metadata']}\n\n")
            else:
                f.write(f"### ❌ Q: {result['question']}\n")
                f.write(f"**오류**: {result['error']}\n\n")
        
        # 시스템 프롬프트 변형 테스트 결과
        f.write("## 2. 시스템 프롬프트 변형 테스트\n\n")
        variation_results = all_results['system_prompt_variations']
        for result in variation_results:
            if result.get('success'):
                f.write(f"### {result['variation']}\n")
                f.write(f"**설정**: {result['settings']}\n")
                f.write(f"**답변 길이**: {result['answer_length']} 글자\n")
                f.write(f"**답변 미리보기**: {result['answer_preview']}\n")
                f.write(f"**메타데이터**: {result['metadata']}\n\n")
            else:
                f.write(f"### ❌ {result['variation']}\n")
                f.write(f"**오류**: {result['error']}\n\n")
        
        # 스트리밍 테스트 결과
        f.write("## 3. 스트리밍 테스트\n\n")
        streaming_result = all_results['streaming']
        if streaming_result.get('success'):
            f.write(f"**결과**: ✅ 성공\n")
            f.write(f"**응답 길이**: {streaming_result['response_length']} 글자\n\n")
        else:
            f.write(f"**결과**: ❌ 실패\n")
            f.write(f"**오류**: {streaming_result['error']}\n\n")
        
        # 메모리 지속성 테스트 결과
        f.write("## 4. 메모리 지속성 테스트\n\n")
        memory_results = all_results['memory_persistence']
        success_count = sum(1 for r in memory_results if r.get('success', False))
        f.write(f"**성공률**: {success_count}/{len(memory_results)} ({success_count/len(memory_results)*100:.1f}%)\n\n")
        
        for result in memory_results:
            if result.get('success'):
                f.write(f"### 대화 {result['turn']}\n")
                f.write(f"**Q**: {result['question']}\n")
                f.write(f"**A**: {result['answer'][:300]}...\n\n")
            else:
                f.write(f"### ❌ 대화 {result['turn']}\n")
                f.write(f"**Q**: {result['question']}\n")
                f.write(f"**오류**: {result['error']}\n\n")
        
        # 새로운 기능 정보
        f.write("## 5. 새로운 기능 정보\n\n")
        f.write("### 시스템 프롬프트 기능\n")
        f.write("- **새로운 전문 시스템 프롬프트**: '메이플 가이드' 페르소나 적용\n")
        f.write("- **설정 기반 프롬프트 전환**: `use_system_prompt` 설정으로 제어\n")
        f.write("- **상세한 답변 가이드라인**: 20년 경험 전문가 설정\n\n")
        
        f.write("### 답변 템플릿 기능\n")
        f.write("- **구조화된 답변 형식**: 제목, 내용, 팁, 마무리 구조\n")
        f.write("- **자동 템플릿 적용**: `enable_answer_template` 설정으로 제어\n")
        f.write("- **일관된 답변 품질**: 모든 답변에 동일한 구조 적용\n\n")
    
    print(f"\n📄 테스트 결과가 저장되었습니다: {results_file}")
    return results_file

async def main():
    """메인 테스트 실행 함수"""
    print("🚀 메이플스토리 RAG 시스템 종합 테스트 시작\n")
    
    # 현재 설정 출력
    print("⚙️  현재 설정:")
    print(f"   - Claude 모델: {settings.claude_model}")
    print(f"   - 시스템 프롬프트 사용: {settings.use_system_prompt}")
    print(f"   - 답변 템플릿 사용: {settings.enable_answer_template}")
    print(f"   - 벡터 스토어: {settings.vector_store_type}")
    print(f"   - 임베딩 제공자: {settings.get_embedding_provider()}")
    
    try:
        # 모든 테스트 실행
        all_results = {}
        
        # 1. 기본 QA 테스트
        all_results['basic_qa'] = await test_basic_qa()
        
        # 2. 시스템 프롬프트 변형 테스트
        all_results['system_prompt_variations'] = await test_system_prompt_variations()
        
        # 3. 스트리밍 테스트
        all_results['streaming'] = await test_streaming()
        
        # 4. 메모리 지속성 테스트
        all_results['memory_persistence'] = await test_memory_persistence()
        
        # 5. 개선된 QA 테스트
        all_results['improved_qa'] = await test_improved_qa()
        
        # 결과 저장
        results_file = save_test_results(all_results)
        
        print(f"\n🎉 모든 테스트가 완료되었습니다!")
        print(f"📊 상세 결과는 {results_file}에서 확인할 수 있습니다.")
        
    except Exception as e:
        print(f"\n💥 테스트 중 오류 발생: {e}")
        raise

if __name__ == "__main__":
    # 이벤트 루프 실행
    asyncio.run(main()) 
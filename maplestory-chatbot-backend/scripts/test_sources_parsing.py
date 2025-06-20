#!/usr/bin/env python3
"""
참고자료 파싱 테스트 스크립트
새로운 {creator} - {title} : {url} 형식 확인
"""

import sys
import os
import asyncio
from typing import List, Dict

# 프로젝트 루트 경로를 sys.path에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app.services.langchain_service import LangChainService
from langchain_core.documents import Document

class SourcesParsingTester:
    """참고자료 파싱 테스트 클래스"""
    
    def __init__(self):
        self.service = LangChainService()
    
    def test_yaml_parsing(self):
        """YAML front matter에서 sources 파싱 테스트"""
        print("🔍 YAML sources 파싱 테스트 시작...")
        
        # 테스트용 문서 내용 (실제 문서 형식)
        test_content = '''---
title: "메이플 2025 여름 메인 이벤트 (황혼빛 전야제) 요약"
category: "game_event_guide"
author: "도루"
sources:
- url: "https://youtu.be/FKO2dUSLFFw?si=zplgq_JJnd8gwrL"
  title: ""신창섭, 이렇게 퍼주면 뭐가 남나요?" - 메이플 역대급 메인 이벤트 요약"
  creator: "도루"
- url: "https://www.inven.co.kr/board/maple/5974/5130182"
  title: "챌섭 첫날 260찍기 완성본 [270까지도 포함]"
  creator: "리부트2선생"
---

# 메이플 2025 여름 메인 이벤트 요약

본 문서는 메이플스토리 2025 여름 이벤트 중 "황혼빛 전야제"의 주요 내용을 요약합니다...
'''
        
        # 파싱 테스트
        sources = self.service._parse_sources_from_document(test_content)
        
        print(f"📊 파싱된 sources 개수: {len(sources)}")
        for i, source in enumerate(sources, 1):
            print(f"  {i}. Creator: {source.get('creator', 'N/A')}")
            print(f"     Title: {source.get('title', 'N/A')}")
            print(f"     URL: {source.get('url', 'N/A')}")
            print()
        
        return sources
    
    def test_extract_sources(self, test_sources):
        """_extract_sources 메서드 테스트"""
        print("🔍 _extract_sources 메서드 테스트 시작...")
        
        # 테스트용 Document 객체 생성
        test_doc = Document(
            page_content='''---
title: "메이플 2025 여름 메인 이벤트 (황혼빛 전야제) 요약"
category: "game_event_guide"
author: "도루"
sources:
- url: "https://youtu.be/FKO2dUSLFFw?si=zplgq_JJnd8gwrL"
  title: ""신창섭, 이렇게 퍼주면 뭐가 남나요?" - 메이플 역대급 메인 이벤트 요약"
  creator: "도루"
- url: "https://www.inven.co.kr/board/maple/5974/5130182"
  title: "챌섭 첫날 260찍기 완성본 [270까지도 포함]"
  creator: "리부트2선생"
---

# 메이플 2025 여름 메인 이벤트 요약
본 문서는 메이플스토리 2025 여름 이벤트 중 "황혼빛 전야제"의 주요 내용을 요약합니다...
''',
            metadata={
                'source': 'test_document.md',
                'title': '메이플 2025 여름 메인 이벤트 요약',
                'category': 'game_event_guide',
                'chunk_index': 0
            }
        )
        
        # _extract_sources 메서드 테스트
        extracted_sources = self.service._extract_sources([test_doc])
        
        print(f"📊 추출된 sources 개수: {len(extracted_sources)}")
        for i, source in enumerate(extracted_sources, 1):
            print(f"  {i}. Creator: {source.get('creator', 'N/A')}")
            print(f"     Title: {source.get('title', 'N/A')}")
            print(f"     URL: {source.get('url', 'N/A')}")
            print(f"     Has URL: {source.get('has_url', False)}")
            print()
        
        return extracted_sources
    
    def test_format_output(self, sources):
        """참고자료 출력 형식 테스트 - URL만 표시"""
        print("🔍 참고자료 출력 형식 테스트 시작...")
        
        sources_with_urls = [s for s in sources if s.get('has_url') and s.get('url')]
        
        if sources_with_urls:
            print("📚 참고자료 (URL만 표시):")
            for source in sources_with_urls:
                url = source.get('url', '')
                
                if url.startswith(('http://', 'https://', 'www.')):
                    print(f"  * {url}")
        else:
            print("❌ URL이 있는 참고자료가 없습니다.")
    
    async def test_full_chat_flow(self):
        """전체 채팅 플로우에서 참고자료 출력 테스트"""
        print("🔍 전체 채팅 플로우 테스트 시작...")
        
        try:
            # 실제 챗봇에 질문
            result = await self.service.chat(
                message="메이플 여름 이벤트에 대해 알려줘",
                session_id="test_sources_parsing"
            )
            
            print(f"📝 응답 길이: {len(result['response'])} 글자")
            
            # 참고자료 부분 확인
            if "## 📚 참고자료" in result['response']:
                lines = result['response'].split('\n')
                ref_start = False
                print("\n📚 응답에 포함된 참고자료:")
                for line in lines:
                    if "## 📚 참고자료" in line:
                        ref_start = True
                        continue
                    elif ref_start and line.startswith('* **'):
                        print(f"  {line}")
                    elif ref_start and line.strip() == "":
                        continue
                    elif ref_start and not line.startswith('* **'):
                        break
            else:
                print("❌ 응답에 참고자료 섹션이 없습니다.")
            
            # sources 메타데이터 확인
            sources = result.get('sources', [])
            print(f"\n📊 메타데이터 sources: {len(sources)}개")
            for i, source in enumerate(sources[:3], 1):
                print(f"  {i}. {source.get('title', 'N/A')} (creator: {source.get('creator', 'N/A')})")
            
        except Exception as e:
            print(f"❌ 테스트 실행 중 오류: {e}")

def main():
    """메인 함수"""
    print("🚀 참고자료 파싱 테스트 시작\n")
    
    tester = SourcesParsingTester()
    
    # 1. YAML 파싱 테스트
    parsed_sources = tester.test_yaml_parsing()
    print("-" * 50)
    
    # 2. _extract_sources 테스트
    extracted_sources = tester.test_extract_sources(parsed_sources)
    print("-" * 50)
    
    # 3. 출력 형식 테스트
    tester.test_format_output(extracted_sources)
    print("-" * 50)
    
    # 4. 전체 플로우 테스트 (선택적)
    print("📋 전체 플로우 테스트를 실행하시겠습니까? (y/n): ", end="")
    choice = input().strip().lower()
    
    if choice == 'y':
        print("-" * 50)
        asyncio.run(tester.test_full_chat_flow())
    
    print("\n✅ 테스트 완료!")

if __name__ == "__main__":
    main() 
from typing import List
import re

class KoreanTextSplitter:
    """한국어 특화 텍스트 분할기"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # 한국어 문장 종결 패턴
        self.sentence_endings = re.compile(
            r'[.!?。]\s*|[\n]{2,}'
        )
    
    def split_text(self, text: str) -> List[str]:
        """텍스트를 의미 있는 청크로 분할"""
        # 문장 단위로 분할
        sentences = self.sentence_endings.split(text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # 청크 생성
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # 현재 청크 + 새 문장이 크기 제한 이내인 경우
            if len(current_chunk) + len(sentence) <= self.chunk_size:
                current_chunk += sentence + " "
            else:
                # 현재 청크 저장
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # 새 청크 시작 (오버랩 포함)
                if chunks and self.chunk_overlap > 0:
                    # 이전 청크의 마지막 부분 가져오기
                    overlap_text = chunks[-1][-self.chunk_overlap:]
                    current_chunk = overlap_text + " " + sentence + " "
                else:
                    current_chunk = sentence + " "
        
        # 마지막 청크 저장
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks 
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

class MetadataConfig(BaseModel):
    """메타데이터 설정 - 사용자가 쉽게 확장 가능"""
    
    # 필수 메타데이터 필드
    required_fields: List[str] = [
        "title",
        "category"
    ]
    
    # 선택적 메타데이터 필드 및 기본값
    optional_fields: Dict[str, Any] = {
        "created_date": None,
        "updated_date": None,
        "author": "MapleExpert",
        "game_version": "latest",
        "difficulty": "medium",
        "server_type": "both",
        "tags": [],
        "keywords": [],
        "related_classes": [],
        "content_type": None
    }
    
    # 파일명 파싱 규칙 (선택사항)
    # 예: "카테고리_제목_기타정보.md" 형식인 경우
    filename_pattern: Optional[str] = r"^(?P<category>[^_]+)_(?P<title>[^_]+)(?:_(?P<extra>.+))?\.md$"
    
    # 카테고리 별칭 (선택사항)
    category_aliases: Dict[str, str] = {
        "class": "class_guide",
        "직업": "class_guide",
        "boss": "boss_guide",
        "보스": "boss_guide",
        "quest": "quest_guide",
        "퀘스트": "quest_guide",
        "system": "system_guide",
        "시스템": "system_guide",
        "farming": "farming_guide",
        "사냥": "farming_guide",
        "gear": "equipment_guide",
        "장비": "equipment_guide",
        "enhance": "enhancement_guide",
        "강화": "enhancement_guide"
    }
    
    # 콘텐츠 타입 별칭
    content_type_aliases: Dict[str, str] = {
        "5차": "5차스킬",
        "5th": "5차스킬",
        "보스": "보스공략",
        "boss": "보스공략",
        "사냥터": "사냥터가이드",
        "hunting": "사냥터가이드",
        "강화": "강화가이드",
        "enhancement": "강화가이드",
        "스타포스": "강화가이드",
        "잠재": "잠재능력",
        "potential": "잠재능력"
    }
    
    # 직업 목록 (확장 가능)
    available_classes: List[str] = [
        "나이트로드", "섀도어", "듀얼블레이드", "보우마스터", "패스파인더", "윈드브레이커",
        "아크메이지", "비숍", "플레임위자드", "배틀메이지", "에반", "루미너스", "키네시스",
        "히어로", "팔라딘", "다크나이트", "데몬슬레이어", "데몬어벤저", "아란", "미하일",
        "바이퍼", "캐논슈터", "스트라이커", "은월", "제로", "일리움", "아크", "호영",
        "카데나", "카인", "라라", "칼리"
    ]
    
    # 서버 타입
    server_types: List[str] = ["리부트", "일반", "both"]
    
    # 난이도 레벨
    difficulty_levels: List[str] = ["beginner", "intermediate", "advanced"]

# 설정 인스턴스
metadata_config = MetadataConfig() 
import pandas as pd
import os
import re
from datetime import datetime
from typing import Dict, List
from anthropic import Anthropic
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

def clean_text(text):
    """텍스트 정제 함수"""
    if pd.isna(text):
        return ""
    # HTML 태그 제거
    text = re.sub(r'<[^>]+>', '', text)
    # 특수문자 제거
    text = re.sub(r'[^\w\s가-힣]', ' ', text)
    # 연속된 공백 제거
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def create_system_prompt() -> str:
    """시스템 프롬프트 생성"""
    return """당신은 메이플스토리 커뮤니티 유저 중 한명입니다. 
게시글과 댓글을 살펴보고 직업별 여론을 간단하게 요약해서 메이플스토리 유저에게 전달해야 합니다.
음슴체(~했음, ~한듯)를 사용하여 친근한 톤으로 작성해주세요.
게임과 직접 관련된 내용만 포함하고, 공식적인 표현은 피해주세요."""

def create_example_messages(job_name: str) -> List[Dict[str, str]]:
    """예시 메시지 생성"""
    return [
        {
            "role": "user",
            "content": f"{job_name} 직업 게시판 게시글과 댓글을 요약해줘."
        },
        {
            "role": "assistant",
            "content": f"""{job_name} 유저들 완전 멘탈 나갔네! 7연속 너프에 직업에 대한 애정이 식을대로 식은 듯. 주요 불만은 지속적인 하향과 그로 인한 성능 저하인데, 방송인 지원 부족까지 겹쳐 더 서러운 상황인 것 같음.

*   **7연속 너프:** 가장 큰 불만! 유저들은 지속적인 하향에 분노하고 있음.
*   **방송인 부재:** 지원 부족으로 인해 직업에 대한 관심이 더 줄어드는 악순환
*   **개선 요구:** 최종데미지 증가, 스킬 개선 등 다양한 개선안 제시"""
        },
        {
            "role": "user",
            "content": f"{job_name} 직업 게시판 게시글과 댓글을 요약해줘."
        },
        {
            "role": "assistant",
            "content": f"""오호, {job_name} 유저들 패치 이후 딜뽕에 맛들었나 보네! 시드링 교체 빡세던 거 사라지고 딜량도 준수하게 올라가서 전반적으로 기분 좋아 보이는데, 보스별 딜 변화폭은 조금씩 다르다고 함.

*   **시드링 & 스위칭:** 시드링 교체 빈도가 줄어들어 스위칭 부담이 크게 감소
*   **딜 상승 & 보스별 변화:** 전반적인 딜량은 상승했지만 보스별로 차이가 있음
*   **장비 세팅 & 최적화:** 패치 이후 효율적인 장비 세팅에 대한 고민이 많음"""
        }
    ]

def analyze_board_sentiment(csv_path: str):
    """CSV 파일을 분석하여 게시판 여론을 분석하는 함수"""
    try:
        # CSV 파일 읽기
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        
        # 직업명 추출
        job_name = os.path.basename(csv_path).replace('.csv', '')
        
        # 최근 10개 게시물만 분석
        recent_posts = df.head(10)
        
        # 게시물과 댓글 내용 정제
        posts_content = []
        for _, row in recent_posts.iterrows():
            title = clean_text(row['제목'])
            content = clean_text(row['내용'])
            comments = clean_text(row['댓글'])
            
            post_summary = f"제목: {title}\n내용: {content}\n댓글: {comments}\n"
            posts_content.append(post_summary)
        
        # 모든 게시물 내용을 하나의 문자열로 합치기
        all_content = "\n\n".join(posts_content)
        
        # Anthropic 클라이언트 생성
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        # 메시지 구성
        messages = [
            *create_example_messages(job_name),
            {
                "role": "user",
                "content": f"{job_name} 직업 게시판 게시글과 댓글을 요약해줘.\n\n게시글 내용:\n{all_content}"
            }
        ]
        
        # Claude API 호출
        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1000,
            system=create_system_prompt(),
            messages=messages
        )
        
        # 결과를 마크다운 파일로 저장
        output_file = f"analysis_{job_name}.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# {job_name} 직업 게시판 여론 분석\n\n")
            f.write(f"분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(response.content[0].text)
        
        print(f"{job_name} 직업 분석이 완료되었습니다. 결과는 {output_file}에 저장되었습니다.")
        
    except Exception as e:
        print(f"오류 발생: {str(e)}")

def main():
    # inven_data 디렉토리의 모든 CSV 파일 분석
    data_dir = "inven_data"
    for file in os.listdir(data_dir):
        if file.endswith('.csv'):
            csv_path = os.path.join(data_dir, file)
            analyze_board_sentiment(csv_path)

if __name__ == "__main__":
    main()

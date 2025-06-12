import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import time
import csv
import os

def get_board_posts(url):
    # 게시판 페이지 가져오기
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 게시물 목록 찾기
    board_list = soup.find('div', class_='board-list')
    if not board_list:
        print("게시판을 찾을 수 없습니다.")
        return []
    
    posts = []
    # 각 게시물 행 처리
    for tr in board_list.find_all('tr')[1:]:  # 첫 번째 행은 헤더이므로 제외
        date_td = tr.find('td', class_='date')
        if not date_td:
            continue
            
        # 시간 형식 확인 (HH:MM)
        time_text = date_td.text.strip()
        if not re.match(r'^\d{2}:\d{2}$', time_text):
            continue
            
        # 게시물 링크 찾기
        title_link = tr.find('a', class_='subject-link')
        if not title_link or not title_link.get('href'):
            continue
            
        post_url = title_link['href']
        if not post_url.startswith('http'):
            post_url = 'https://www.inven.co.kr' + post_url
            
        # 댓글 정보 찾기
        comment_info = tr.find('span', class_='con-comment')
        if comment_info:
            come_idx = comment_info.get('data-opinion-bbs-comeidx')
            uid = comment_info.get('data-opinion-bbs-uid')
        else:
            come_idx = None
            uid = None
            
        posts.append({
            'url': post_url,
            'come_idx': come_idx,
            'uid': uid
        })
            
        # 서버 부하 방지를 위한 딜레이
        time.sleep(1)
        
    return posts

def get_post_content(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 게시물 제목 가져오기
        article_title = soup.find('div', class_='articleTitle')
        if not article_title:
            return None
            
        title = article_title.find('h1').text.strip()
        
        # 게시물 내용 가져오기
        article_content = soup.find('div', class_='articleContent')
        if not article_content:
            return None
            
        # powerbbsContent 내의 내용 가져오기
        content_div = article_content.find('div', id='powerbbsContent')
        if not content_div:
            return None
            
        content = ''
        # div 요소가 있는 경우
        inner_divs = content_div.find_all('div')
        if inner_divs:
            for div in inner_divs:
                content += div.get_text(separator='\n').strip() + '\n'
        else:
            # div 요소가 없는 경우 직접 텍스트 가져오기
            content = content_div.get_text(separator='\n').strip()
        
        content = content.strip()
        
        return {
            'title': title,
            'content': content
        }
    except Exception as e:
        print(f"게시물 처리 중 오류 발생: {url}")
        print(f"오류 내용: {str(e)}")
        return None

def get_post_comments(come_idx, uid):
    if not come_idx or not uid:
        return []
        
    comments = []
    try:
        headers = {
            'authority': 'www.inven.co.kr',
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7,zh-CN;q=0.6,zh;q=0.5',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://www.inven.co.kr',
            'referer': f'https://www.inven.co.kr/board/opinionbbs.php?come_idx={come_idx}&l={uid}&iskin=',
            'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest'
        }
        
        # 댓글 API URL
        comment_url = "https://www.inven.co.kr/common/board/comment.json.php"
        
        # 요청 데이터 준비
        data = {
            'dummy': str(int(time.time() * 1000)),  # 현재 시간을 밀리초로
            'comeidx': come_idx,
            'articlecode': uid,
            'sortorder': 'date',
            'act': 'list',
            'out': 'json',
            'replynick': '',
            'replyidx': '0',
            'uploadurl': '',
            'imageposition': '',
            'videoloading': 'lazy'
        }
        
        print(f"[디버깅] 댓글 API URL: {comment_url}")
        print(f"[디버깅] 요청 데이터: {data}")
        
        # POST 요청으로 댓글 데이터 가져오기
        comment_response = requests.post(comment_url, headers=headers, data=data)
        print(f"[디버깅] 댓글 API 응답 상태 코드: {comment_response.status_code}")
        
        # JSON 응답 파싱
        try:
            json_data = comment_response.json()
            print(f"[디버깅] JSON 응답 데이터 구조: {json_data.keys() if isinstance(json_data, dict) else 'Not a dictionary'}")
            
            # 댓글 데이터 추출
            if isinstance(json_data, dict) and 'commentlist' in json_data:
                for comment_group in json_data['commentlist']:
                    if 'list' in comment_group:
                        for comment in comment_group['list']:
                            if 'o_comment' in comment:
                                # HTML 엔티티를 일반 문자로 변환
                                comment_text = comment['o_comment']
                                comment_text = comment_text.replace('&amp;nbsp;', ' ')
                                comment_text = comment_text.replace('&lt;', '<')
                                comment_text = comment_text.replace('&gt;', '>')
                                comment_text = comment_text.replace('&quot;', '"')
                                comment_text = comment_text.replace('&amp;', '&')
                                
                                # 댓글 작성자와 날짜 정보 추가
                                author = comment.get('o_name', '익명')
                                date = comment.get('o_date', '')
                                formatted_comment = f"[{author}] {comment_text} ({date})"
                                
                                comments.append(formatted_comment)
                                print(f"[디버깅] 댓글 추가: {formatted_comment[:50]}...")
                
                print(f"[디버깅] 총 {len(comments)}개의 댓글을 찾았습니다.")
            else:
                print("[디버깅] commentlist 키를 찾을 수 없습니다.")
                print(f"[디버깅] 사용 가능한 키: {json_data.keys()}")
        except Exception as e:
            print(f"[디버깅] JSON 파싱 실패: {str(e)}")
            print(f"[디버깅] 응답 내용: {comment_response.text[:500]}...")  # 응답의 처음 500자만 출력
                
    except Exception as e:
        print(f"[디버깅] 댓글 API 호출 중 오류 발생: {str(e)}")
        
    return comments

def main():
    # 사용자 입력 받기
    job_name = input("크롤링할 직업명을 입력하세요: ")
    url = input("게시판 URL을 입력하세요: ")
    
    # 파일명 생성
    filename = f"{job_name}.csv"
    
    print(f"\n{job_name} 게시판 크롤링을 시작합니다...")
    posts = get_board_posts(url)
    
    # 결과 출력
    for i, post in enumerate(posts, 1):
        print(f"\n게시물 {i}")
        print(f"URL: {post['url']}")
        print(f"댓글 정보 - come_idx: {post['come_idx']}, uid: {post['uid']}")
        
        # 게시물 내용 가져오기
        post_content = get_post_content(post['url'])
        if post_content:
            print(f"제목: {post_content['title']}")
            print(f"내용: {post_content['content'][:200]}...")  # 내용의 처음 200자만 출력
            
            # 댓글 가져오기
            comments = get_post_comments(post['come_idx'], post['uid'])
            print(f"댓글 수: {len(comments)}")
            
            # CSV 파일에 저장할 데이터 준비
            save_data = {
                'title': post_content['title'],
                'content': post_content['content'],
                'comments': comments
            }
            
            # CSV 파일에 저장
            save_to_csv([save_data], filename, i == 1)  # 첫 번째 게시물일 때만 헤더 작성
        print("-" * 50)
        
        # 서버 부하 방지를 위한 딜레이
        time.sleep(1)

def save_to_csv(posts, filename, write_header=False):
    # CSV 파일 저장
    with open(filename, 'a', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        # 첫 번째 게시물일 때만 헤더 작성
        if write_header:
            writer.writerow(['제목', '내용', '댓글'])
        
        # 게시물 데이터 작성
        for post in posts:
            # 댓글을 줄바꿈으로 구분하여 하나의 문자열로 합치기
            comments_text = '\n'.join(post['comments'])
            writer.writerow([post['title'], post['content'], comments_text])
    
    print(f"\n게시물이 {filename}에 저장되었습니다.")

if __name__ == "__main__":
    main() 
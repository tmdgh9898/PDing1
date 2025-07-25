#!/usr/bin/env python3
# candfans_m3u8.py
import sys
import json

try:
    import cloudscraper
except ImportError:
    print("ERROR: cloudscraper 패키지가 없습니다. 'pip install cloudscraper' 로 설치하세요.")
    sys.exit(1)

def fetch_timeline(comment_id):
    """
    cloudscraper를 사용해 API 호출.
    브라우저 동일한 헤더로 챌린지 우회.
    """
    url = f'https://candfans.jp/api/contents/get-timeline/{comment_id}'
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'firefox', 'platform': 'windows', 'desktop': True}
    )
    headers = {
        'User-Agent':       'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:71.0) Gecko/20100101 Firefox/71.0',
        'Accept':           'application/json, text/plain, */*',
        'Accept-Language':  'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding':  'gzip, deflate, br',
        'Referer':          f'https://candfans.jp/posts/comment/show/{comment_id}',
        'Origin':           'https://candfans.jp',
        'Connection':       'keep-alive',
        # 필요 시 브라우저에서 복사한 Cookie 헤더를 여기에 추가하세요.
        # 'Cookie': 'SESSIONID=xxxx; other=yyy; …'
    }
    resp = scraper.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()

def generate_m3u8_link(data):
    """
    JSON에서 user_id, post_id, default_path(uuid) 추출 후
    최종 m3u8 링크 생성.
    """
    post = data.get('data', {}).get('post', {})
    user_id = post.get('user_id')
    post_id = post.get('post_id')
    default_path = (
        post.get('default_path')
        or (post.get('attachments') or [{}])[0].get('uuid')
        or post.get('video_key')
    )
    if not (user_id and post_id and default_path):
        raise ValueError("필요한 필드를 찾을 수 없습니다. JSON 구조를 확인하세요.")
    return f'https://video.candfans.jp/user/{user_id}/post/{post_id}/{default_path}.m3u8'

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} COMMENT_ID")
        sys.exit(1)
    comment_id = sys.argv[1]

    # 1) JSON 가져오기
    try:
        data = fetch_timeline(comment_id)
    except Exception as e:
        print(f"[ERROR] API 호출 실패: {e}")
        sys.exit(1)

    # 2) pretty-print
    print(json.dumps(data, indent=4, ensure_ascii=False))

    # 3) m3u8 링크 생성
    try:
        link = generate_m3u8_link(data)
    except Exception as e:
        print(f"[ERROR] m3u8 링크 생성 실패: {e}")
        sys.exit(1)

    # 4) 결과 출력
    print(f"\nGenerated m3u8 link:\n{link}")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
import sys
import json
import re
import cloudscraper

def fetch_timeline(comment_id: str) -> dict:
    """
    cloudscraper로 get-timeline API 호출
    """
    url = f'https://candfans.jp/api/contents/get-timeline/{comment_id}'
    scraper = cloudscraper.create_scraper()
    headers = {
        'Referer':    f'https://candfans.jp/posts/comment/show/{comment_id}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    }
    resp = scraper.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()

def extract_m3u8_link(data: dict) -> str:
    """
    1) JSON 내부에 전체 URL이 있으면 바로 리턴
    2) attachments[].uuid, default_path, video_key 순으로 조합
    """
    blob = json.dumps(data)
    m = re.search(
        r'https://video\.candfans\.jp/user/\d+/post/\d+/[0-9a-fA-F\-]+\.m3u8',
        blob
    )
    if m:
        return m.group(0)

    post = data.get('data', {}).get('post', {})
    user_id = post.get('user_id')
    post_id = post.get('post_id')
    if not (user_id and post_id):
        raise ValueError("user_id 또는 post_id가 없습니다.")

    # attachments에서 uuid
    for att in post.get('attachments', []):
        uuid = att.get('uuid')
        if uuid:
            return f'https://video.candfans.jp/user/{user_id}/post/{post_id}/{uuid}.m3u8'

    # default_path / video_key
    for key in ('default_path','video_key'):
        if post.get(key):
            return f'https://video.candfans.jp/user/{user_id}/post/{post_id}/{post[key]}.m3u8'

    raise ValueError("m3u8 생성용 키를 찾을 수 없습니다.")

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <comment_id>")
        sys.exit(1)

    cid = sys.argv[1]
    try:
        data = fetch_timeline(cid)
    except Exception as e:
        print(f"[ERROR] API 호출 실패: {e}")
        sys.exit(1)

    # JSON pretty-print (원하면 제거해도 됩니다)
    print(json.dumps(data, indent=4, ensure_ascii=False))

    try:
        link = extract_m3u8_link(data)
        print(f"\n▶ Generated m3u8 link:\n{link}")
    except Exception as e:
        print(f"[ERROR] 링크 생성 실패: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
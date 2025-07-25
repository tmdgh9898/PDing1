#!/usr/bin/env python3 import sys import json import re import cloudscraper

def fetch_timeline(comment_id: str) -> dict: """ cloudscraper로 get-timeline API 호출 """ url = f'https://candfans.jp/api/contents/get-timeline/{comment_id}' scraper = cloudscraper.create_scraper() headers = { 'Referer':    f'https://candfans.jp/posts/comment/show/{comment_id}', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', } resp = scraper.get(url, headers=headers, timeout=15) resp.raise_for_status() return resp.json()

def extract_m3u8_link(data: dict) -> str: """ 1) JSON 내부에 전체 URL이 있으면 바로 리턴 2) post_attachments[].default_path 사용 3) sample_file 사용 4) 기본 attachments, default_path, video_key 순으로 조합 """ # 1) JSON blob에서 전체 URL 검색 blob = json.dumps(data) match = re.search( r'https://video.candfans.jp/user/\d+/post/\d+/[0-9a-fA-F-]+.m3u8', blob ) if match: return match.group(0)

post = data.get('data', {}).get('post', {})
user_id = post.get('user_id')
post_id = post.get('post_id')
if not (user_id and post_id):
    raise ValueError("user_id 또는 post_id가 없습니다.")

# 2) post_attachments에서 default_path
for att in post.get('post_attachments', []):
    dp = att.get('default_path')
    if dp:
        return f'https://video.candfans.jp/user/{user_id}/post/{post_id}/{dp}'

# 3) sample_file 사용
sample = post.get('sample_file')
if sample:
    # sample_file은 "/user/.../xxx.m3u8" 형태
    return f'https://video.candfans.jp{sample}'

# 4) 구버전 attachments, default_path, video_key
# attachments[].uuid
for att in post.get('attachments', []):
    uuid = att.get('uuid')
    if uuid:
        return f'https://video.candfans.jp/user/{user_id}/post/{post_id}/{uuid}.m3u8'
# default_path, video_key
for key in ('default_path', 'video_key'):
    val = post.get(key)
    if val:
        return f'https://video.candfans.jp/user/{user_id}/post/{post_id}/{val}.m3u8'

raise ValueError("m3u8 생성용 키를 찾을 수 없습니다.")

def main(): if len(sys.argv) != 2: print(f"Usage: {sys.argv[0]} <comment_id>") sys.exit(1)

cid = sys.argv[1]
try:
    data = fetch_timeline(cid)
except Exception as e:
    print(f"[ERROR] API 호출 실패: {e}")
    sys.exit(1)

# JSON pretty-print
print(json.dumps(data, indent=4, ensure_ascii=False))

try:
    link = extract_m3u8_link(data)
    print(f"\n▶ Generated m3u8 link:\n{link}")
except Exception as e:
    print(f"[ERROR] 링크 생성 실패: {e}")
    sys.exit(1)

if name == "main": main()


#!/data/data/com.termux/files/usr/bin/env python3
import sys, json
import cloudscraper

def fetch_timeline(cid):
    scraper = cloudscraper.create_scraper(
        browser={'browser':'chrome','platform':'android','mobile':True}
    )
    url = f'https://candfans.jp/api/contents/get-timeline/{cid}'
    headers = {
        'Referer': f'https://candfans.jp/posts/comment/show/{cid}',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 11; Mobile) Chrome/112.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest'
    }
    return scraper.get(url, headers=headers, timeout=15).json()

def make_m3u8_link(data):
    p = data.get('data', {}).get('post', {})
    uid, pid = p.get('user_id'), p.get('post_id')
    key = (
        p.get('default_path')
        or (p.get('attachments') or [{}])[0].get('uuid')
        or p.get('video_key')
    )
    if not (uid and pid and key):
        raise ValueError("필드 누락: JSON 구조를 확인하세요.")
    return f'https://video.candfans.jp/user/{uid}/post/{pid}/{key}.m3u8'

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

    print(json.dumps(data, indent=4, ensure_ascii=False))
    try:
        link = make_m3u8_link(data)
        print(f"\n▶ Generated m3u8 link:\n{link}")
    except Exception as e:
        print(f"[ERROR] 링크 생성 실패: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

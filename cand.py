#!/usr/bin/env python3
import sys, json
import cloudscraper

def fetch(cid):
    url = f'https://candfans.jp/api/contents/get-timeline/{cid}'
    s = cloudscraper.create_scraper()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:71.0) Gecko/20100101 Firefox/71.0',
        'Referer': f'https://candfans.jp/posts/comment/show/{cid}',
        'X-Requested-With': 'XMLHttpRequest',
    }
    return s.get(url, headers=headers, timeout=15).json()

def make_link(data):
    p = data['data']['post']
    uid, pid = p['user_id'], p['post_id']
    key = p.get('default_path') or p.get('attachments',[{}])[0].get('uuid') or p.get('video_key')
    return f'https://video.candfans.jp/user/{uid}/post/{pid}/{key}.m3u8'

if __name__ == '__main__':
    if len(sys.argv)!=2:
        print(f'Usage: {sys.argv[0]} COMMENT_ID'); sys.exit(1)
    d = fetch(sys.argv[1])
    print(json.dumps(d, indent=4, ensure_ascii=False))
    print('\n▶︎', make_link(d))
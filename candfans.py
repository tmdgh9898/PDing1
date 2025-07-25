# 1) 필요한 패키지 설치
pkg update && pkg upgrade -y
pkg install -y python
pip install --upgrade pip
pip install cloudscraper

# 2) 스크립트 생성
cat > ~/candfans.py << 'EOF'
#!/data/data/com.termux/files/usr/bin/env python3
import sys, json
import cloudscraper

def fetch_timeline(cid):
    scraper = cloudscraper.create_scraper(
        browser={'browser':'chrome','platform':'android','mobile':True}
    )
    url = f'https://candfans.jp/api/contents/get-timeline/{cid}'
    headers = {
        'Referer':           f'https://candfans.jp/posts/comment/show/{cid}',
        'User-Agent':        'Mozilla/5.0 (Linux; Android 11; Mobile) Chrome/112.0.0.0 Safari/537.36',
        'X-Requested-With':  'XMLHttpRequest',
        'Cookie': (
            "candfans_lang=ko; app_id=zYaBw5kiLF1zrGP0yUV3xzhb6DOq6rb6VorHDSYqZDdtv8qZc5; "
            "AWSALB=ZXxeXlLkZ9POo6lRvmdohn5Qb27GNt2W3UhVOZZDLgB0TotWQji9nMDiT2A854qWtSa8Jtw8mI8d79nAWB/m/SDUjXvmf3cdxXuoJ/"
            "PpETv050j+nW+uDMBKy5NYVAgTvkrLT6WFAHNEoC7F39PStXAdxJtwROWMeIfSy0cRJ/2MJVvGMiIf9ZhmGuKSkQ==; "
            "AWSALBCORS=ZXxeXlLkZ9POo6lRvmdohn5Qb27GNt2W3UhVOZZDLgB0TotWQji9nMDiT2A854qWtSa8Jtw8mI8d79nAWB/m/SDUjXvmf3cdxXuoJ/"
            "PpETv050j+nW+uDMBKy5NYVAgTvkrLT6WFAHNEoC7F39PStXAdxJtwROWMeIfSy0cRJ/2MJVvGMiIf9ZhmGuKSkQ==; "
            "lang=ko; secure_candfans_session=eyJpdiI6ImMwSi96bXRLV2dPYWlRMUZYeGxGaVE9PSIsInZhbHVlIjoiR2VsRktmQzVSMXJpR29MM1IrL2lheXhNRklBNWhzY2pEbVVpdG40N2svSG9IUGxxVXVEYzBxcVN4VjVzK0RsV0VXbTN5RVdtUFVZdUV6a3B1d3dIUExFY3A5MDRPY1BoVTAyVGZlSTVTU2g1RS85U1lEQlovVEtVRkVKY2xVTUIiLCJtYWMiOiIwNTU1ZmUxZmZiODc5NTA2Y2YzZjZmZjY2OTBhYjkxZTM2MTUyNGQ2NDA0ODFlZjEzNjU0M2UyN2RlNGM3YTc4IiwidGFnIjoiIn0%3D; "
            "XSRF-TOKEN=eyJpdiI6ImthZ1BuWk52MnptdnRYSmZuUXVuTkE9PSIsInZhbHVlIjoiRFJIMFdQNk0xeXkvWDh0MS9VUnhjL1liSjZ2MzdEV2xTQ0hQVnlBZGZXZkFic1B2RDFzK3lpbnNMK1N6dEtHenBSSFRscS93VEY0MFFQUkxrMVJFdllFUTcxMlVyMHdsZUNOT1JVNHJITW51VGh0SHNpbHp5bWF0ZTJOeDAwZUkiLCJtYWMiOiI2NWRmMWM2ZDIzM2EwNTMwYTk0MTc0NWFiZWE4NGU5NjVlMGE4YzMyNDNlN2EzMmQ4NjExMDlhNzNhN2I5ZDIxIiwidGFnIjoiIn0%3D"
        )
    }
    resp = scraper.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()

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
EOF

# 3) 실행 권한
chmod +x ~/candfans.py

# 4) 사용 예
~/candfans.py 968402
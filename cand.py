import time
import requests
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def make_session_with_retries(
    total_retries=5,
    backoff_factor=1,
    status_forcelist=(500, 502, 503, 504),
):
    session = requests.Session()
    retry = Retry(
        total=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def generate_m3u8_link(comment_id):
    api_url = f'https://candfans.jp/api/contents/get-timeline/{comment_id}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:71.0) Gecko/20100101 Firefox/71.0',
        'Accept': 'application/json, text/plain, */*',
        'Connection': 'keep-alive'
    }

    session = make_session_with_retries()

    try:
        # timeout=(connect_timeout, read_timeout)
        resp = session.get(api_url, headers=headers, timeout=(5, 15))
        resp.raise_for_status()
    except (requests.exceptions.RetryError,
            requests.exceptions.ConnectionError,
            requests.exceptions.HTTPError) as e:
        print(f"[ERROR] 요청 실패: {e!r}")
        return None

    data = resp.json()
    print(json.dumps(data, indent=4, ensure_ascii=False))

    post = data.get('data', {}).get('post', {})
    user_id = post.get('user_id')
    post_id = post.get('post_id')

    # 실제 JSON 구조에 맞춰 이 부분을 조정하세요
    default_path = (
        post.get('default_path')
        or (post.get('attachments') or [{}])[0].get('uuid')
        or post.get('video_key')
    )
    if not (user_id and post_id and default_path):
        print("[ERROR] 필요한 필드를 찾을 수 없습니다. JSON 구조를 확인하세요.")
        return None

    return f'https://video.candfans.jp/user/{user_id}/post/{post_id}/{default_path}.m3u8'

if __name__ == '__main__':
    cid = 968402
    link = generate_m3u8_link(cid)
    if link:
        print("\nGenerated m3u8 link:\n", link)
    else:
        print("m3u8 링크 생성에 실패했습니다.")
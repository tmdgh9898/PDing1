import requests
import json

def generate_m3u8_link(comment_id):
    api_url = f'https://candfans.jp/api/contents/get-timeline/{comment_id}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:71.0) Gecko/20100101 Firefox/71.0'
    }

    # 1) JSON fetch
    resp = requests.get(api_url, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    # 2) pretty-print (console 확인용)
    print(json.dumps(data, indent=4, ensure_ascii=False))

    # 3) 필요한 필드 추출
    post = data['data']['post']
    user_id    = post['user_id']
    post_id    = post['post_id']

    # JSON 구조에 따라 달라질 수 있으니, 실제 필드명을 확인하고 수정하세요.
    # 예: post.get('default_path') 또는 post['attachments'][0]['uuid'] 등
    default_path = (
        post.get('default_path') 
        or (post.get('attachments') or [{}])[0].get('uuid')
        or post.get('video_key')
    )
    if not default_path:
        raise ValueError("default_path를 찾을 수 없습니다. JSON 구조를 확인하세요.")

    # 4) 최종 m3u8 URL 생성
    return f'https://video.candfans.jp/user/{user_id}/post/{post_id}/{default_path}.m3u8'


if __name__ == '__main__':
    cid = 968402
    try:
        link = generate_m3u8_link(cid)
        print("\nGenerated m3u8 link:\n", link)
    except Exception as e:
        print("Error:", e)
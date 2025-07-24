import requests
import json

def get_candfans_video_url(comment_show_url):
    try:
        post_id = comment_show_url.split('/')[-1]
        api_url = f"https://candfans.jp/api/contents/get-timeline/{post_id}"

        # 여기에 User-Agent 헤더 추가
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36'
        }

        response = requests.get(api_url, headers=headers) # headers 인자 추가
        response.raise_for_status()

        data = response.json()

        content_data = data.get('data', {}).get('list', [])[0].get('content', {})
        content_path = content_data.get('path', '')
        path_parts = content_path.split('/')

        user_id = None
        extracted_post_id = None

        for i, part in enumerate(path_parts):
            if part == 'user' and i + 1 < len(path_parts):
                user_id = path_parts[i+1]
            elif part == 'post' and i + 1 < len(path_parts):
                extracted_post_id = path_parts[i+1]

        default_path = content_data.get('default_path', '')

        if user_id and extracted_post_id and default_path:
            video_url = (
                f"https://video.candfans.jp/user/{user_id}/post/"
                f"{extracted_post_id}/{default_path}"
            )
            return video_url
        else:
            print("Could not extract all necessary components for the video URL.")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from API: {e}")
        return None
    except json.JSONDecodeError:
        print("Error decoding JSON from API response.")
        return None
    except IndexError:
        print("Could not find the expected data structure in the API response.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

comment_url = "https://candfans.jp/posts/comment/show/951869"
final_video_url = get_candfans_video_url(comment_url)

if final_video_url:
    print(f"Generated video URL: {final_video_url}")
else:
    print("Failed to generate the video URL.")

import requests
import json

def get_candfans_video_url(comment_show_url):
    """
    Extracts the user ID, post ID, and default path from the Candfans API 
    and constructs the direct video URL.

    Args:
        comment_show_url (str): The URL in the format 
                                "https://candfans.jp/posts/comment/show/{post_id}"

    Returns:
        str: The direct video URL or None if an error occurs.
    """
    try:
        # Extract the post_id from the comment_show_url
        post_id = comment_show_url.split('/')[-1]
        api_url = f"https://candfans.jp/api/contents/get-timeline/{post_id}"

        response = requests.get(api_url)
        response.raise_for_status()  # Raise an exception for HTTP errors

        data = response.json()

        # Extract user_id, post_id, and default_path
        # The structure is data['data']['list'][0]['content'] for the first item
        content_data = data.get('data', {}).get('list', [])[0].get('content', {})
        
        # The path often contains /user/{user_id}/post/{post_id}/
        # We need to find the user_id and post_id from this path
        content_path = content_data.get('path', '')
        path_parts = content_path.split('/')
        
        user_id = None
        extracted_post_id = None

        # Find user_id and post_id from the path_parts
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

# --- How to use it ---
comment_url = "https://candfans.jp/posts/comment/show/951869"
final_video_url = get_candfans_video_url(comment_url)

if final_video_url:
    print(f"Generated video URL: {final_video_url}")
else:
    print("Failed to generate the video URL.")

import os
import re
import requests
import io
import shutil
import subprocess
from contextlib import redirect_stdout, redirect_stderr
from concurrent.futures import ThreadPoolExecutor, as_completed
from b_cdn_drm_vod_dl import BunnyVideoDRM

# CDN prefixes
PRIMARY_PREFIX = "vz-f9765c3e-82b"
SECONDARY_PREFIX = "vz-bcc18906-38f"
TERTIARY_PREFIX = "vz-b3fe6a46-b2b"
QUATERNARY_PREFIX = "vz-40d00b68-e91"
QUINARY_PREFIX = "vz-6b30db03-fbb"

# Fallback MP4 qualities
MP4_QUALITIES = ["play_720p.mp4", "play_480p.mp4", "play_360p.mp4", "play_240p.mp4"]
# Advanced video/audio lists
VIDEO_RESOLUTIONS = ["2160p", "1440p", "1080p", "720p", "480p", "360p"]
AUDIO_QUALITIES = ["256a", "192a", "128a", "96a"]

# Directories
TEMP_DIR = os.path.join(os.getcwd(), "downloads")
ANDROID_DOWNLOAD_DIR = "/storage/emulated/0/Download"
INVALID_CHARS = r'[<>:"/\\|?*]'

def sanitize_filename(name: str) -> str:
    return re.sub(INVALID_CHARS, '_', name)

def get_video_uuid(url: str) -> str:
    """URL에서 v= 뒤 UUID 추출"""
    m = re.search(r"v=([a-f0-9\-]+)", url)
    if not m:
        print("[WARN] URL에서 video_id 추출 실패 → fallback 이름 사용")
        return None
    return m.group(1)

def fetch_title(url: str) -> str:
    """
    API에서 title만 받아오기. (UUID 추출도 포함)
    """
    uuid = get_video_uuid(url)
    if not uuid:
        return "video_fallback"
    api_url = f"https://backend.prod.pd-ing.com/api/cdn/video/{uuid}"
    try:
        resp = requests.get(api_url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        title = data.get("title") or data.get("name")
        if not title:
            return "video_fallback"
        title = title.strip()
        # 후처리: 구분자 있으면 뒤쪽만
        if '|' in title:
            title = title.split('|', 1)[1].strip()
        elif '_' in title:
            parts = re.split(r'_\s*', title, 1)
            title = parts[1].strip() if len(parts) > 1 else title
        return title
    except Exception as e:
        print(f"[WARN] API에서 제목 가져오기 실패: {e}")
        return "video_fallback"

def build_video_info(url: str) -> dict:
    m = re.search(r"v=([a-f0-9\-]+)", url)
    if not m:
        raise ValueError(f"video_id not found in URL: {url}")
    vid = m.group(1)
    name = sanitize_filename(fetch_title(url))
    return {"referer": url, "video_id": vid, "name": name}

def move_to_android(src: str, name: str) -> None:
    os.makedirs(ANDROID_DOWNLOAD_DIR, exist_ok=True)
    dst = os.path.join(ANDROID_DOWNLOAD_DIR, f"{name}.mp4")
    shutil.move(src, dst)

def download_video(info: dict) -> dict:
    vid, name, referer = info['video_id'], info['name'], info['referer']
    headers = {"User-Agent": "Mozilla/5.0", "Referer": referer}
    os.makedirs(TEMP_DIR, exist_ok=True)

    def _attempt_mp4_download(prefix):
        for q in MP4_QUALITIES:
            try:
                url = f"https://{prefix}.b-cdn.net/{vid}/{q}"
                resp = requests.get(url, headers=headers, stream=True, timeout=10)
                resp.raise_for_status()
                temp_file = os.path.join(TEMP_DIR, f"{name}.mp4")
                with open(temp_file, 'wb') as f:
                    for chunk in resp.iter_content(1024 * 1024):
                        f.write(chunk)
                move_to_android(temp_file, name)
                return {"name": referer, "success": True, "source": prefix}
            except Exception:
                continue
        return None

    # PRIMARY: playlist.m3u8 only
    try:
        url = f"https://{PRIMARY_PREFIX}.b-cdn.net/{vid}/playlist.m3u8"
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(buf):
            BunnyVideoDRM(referer=referer, m3u8_url=url, name=name, path=TEMP_DIR).download()
        temp_file = os.path.join(TEMP_DIR, f"{name}.mp4")
        if os.path.exists(temp_file):
            move_to_android(temp_file, name)
            return {"name": referer, "success": True, "source": PRIMARY_PREFIX}
    except:
        pass

    # SECONDARY, QUATERNARY, QUINARY: MP4 only
    for prefix in [SECONDARY_PREFIX, QUATERNARY_PREFIX, QUINARY_PREFIX]:
        result = _attempt_mp4_download(prefix)
        if result:
            return result

    # TERTIARY: advanced stream
    if download_advanced(info, TERTIARY_PREFIX):
        return {"name": referer, "success": True, "source": TERTIARY_PREFIX}

    return {"name": referer, "success": False, "source": None}

def download_advanced(info: dict, prefix: str) -> bool:
    vid, name, referer = info['video_id'], info['name'], info['referer']
    headers = {"User-Agent": "Mozilla/5.0", "Referer": referer}
    os.makedirs(TEMP_DIR, exist_ok=True)

    for res in VIDEO_RESOLUTIONS:
        video_m3u8 = f"https://{prefix}.b-cdn.net/{vid}/video/{res}/video.m3u8"
        video_name = f"{name}_video"
        try:
            buf = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(buf):
                BunnyVideoDRM(referer=referer, m3u8_url=video_m3u8, name=video_name, path=TEMP_DIR).download()
            video_path = os.path.join(TEMP_DIR, f"{video_name}.mp4")
            if not os.path.exists(video_path):
                continue
        except Exception:
            continue

        for aq in AUDIO_QUALITIES:
            audio_m3u8 = f"https://{prefix}.b-cdn.net/{vid}/audio/{aq}/audio.m3u8"
            audio_name = f"{name}_audio"
            try:
                buf = io.StringIO()
                with redirect_stdout(buf), redirect_stderr(buf):
                    BunnyVideoDRM(referer=referer, m3u8_url=audio_m3u8, name=audio_name, path=TEMP_DIR).download()
                audio_path = os.path.join(TEMP_DIR, f"{audio_name}.mp4")
                if not os.path.exists(audio_path):
                    continue
            except Exception:
                continue

            merged = os.path.join(TEMP_DIR, f"{name}.mp4")
            try:
                subprocess.run([
                    "ffmpeg", "-i", video_path, "-i", audio_path, "-c", "copy", "-y", merged
                ], check=True)
                move_to_android(merged, name)
                return True
            except Exception:
                continue
    return False

def main():
    raw = input("Enter URLs (space/comma-separated):\n").strip()
    urls = [u for u in re.split(r"[\s,;]+", raw) if u]
    if not urls:
        print("No URLs provided.")
        return

    results = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(download_video, build_video_info(u)) for u in urls]
        for f in as_completed(futures):
            results.append(f.result())

    print("\n=== Results ===")
    for r in results:
        if r['success']:
            print(f"[OK] {r['name']} (via {r['source']})")

    fails = [r['name'] for r in results if not r['success']]
    if fails:
        print("\n=== Failed ===")
        for e in fails:
            print(f"- {e}")

if __name__ == "__main__":
    main()

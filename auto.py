import os
import re
import requests
import io
import shutil
from contextlib import redirect_stdout, redirect_stderr
from b_cdn_drm_vod_dl import BunnyVideoDRM
from concurrent.futures import ThreadPoolExecutor, as_completed

# CDN prefixes
PRIMARY_PREFIX = "vz-f9765c3e-82b"
SECONDARY_PREFIX = "vz-bcc18906-38f"
TERTIARY_PREFIX = "vz-b3fe6a46-b2b"
QUATERNARY_PREFIX = "vz-40d00b68-e91"

# mp4 quality options
MP4_QUALITIES = [
    "play_720p.mp4",
    "play_480p.mp4",
    "play_360p.mp4",
    "play_240p.mp4"
]

# Local temp download directory and Android Download directory
TEMP_DIR = os.path.join(os.getcwd(), "downloads")
ANDROID_DOWNLOAD_DIR = "/storage/emulated/0/Download"
INVALID_FILENAME_CHARS = r'[<>:"/\\|?*]'


def sanitize_filename(name: str) -> str:
    """
    Remove characters invalid in filenames.
    """
    return re.sub(INVALID_FILENAME_CHARS, '_', name)


def fetch_title(url: str) -> str:
    """
    Fetch <title> from given URL and sanitize.
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    match = re.search(r"<title[^>]*>(.*?)</title>", resp.text, re.IGNORECASE | re.DOTALL)
    if not match:
        raise ValueError("Page title not found")
    title = match.group(1).strip()
    # Remove prefix before '|' or first underscore
    if '|' in title:
        title = title.split('|', 1)[1].strip()
    elif '_' in title:
        parts = re.split(r'_\s*', title, 1)
        title = parts[1].strip() if len(parts) > 1 else title
    return title


def build_video_info(url: str) -> dict:
    """
    Extract video_id and sanitize filename.
    """
    match = re.search(r"v=([a-f0-9\-]+)", url)
    if not match:
        raise ValueError(f"video_id not found in URL: {url}")
    video_id = match.group(1)
    name = sanitize_filename(fetch_title(url))
    return {"referer": url, "video_id": video_id, "safe_name": name}


def move_to_android(src: str, name: str) -> None:
    """
    Move downloaded file from temp to Android Download folder.
    """
    os.makedirs(ANDROID_DOWNLOAD_DIR, exist_ok=True)
    dest = os.path.join(ANDROID_DOWNLOAD_DIR, f"{name}.mp4")
    shutil.move(src, dest)


def download_video(info: dict) -> dict:
    """
    Try m3u8 and mp4 (best quality) across prefixes, then move file to Android folder.
    """
    vid = info['video_id']
    name = info['safe_name']
    os.makedirs(TEMP_DIR, exist_ok=True)
    temp_path = os.path.join(TEMP_DIR, f"{name}.mp4")
    headers = {"User-Agent": "Mozilla/5.0", "Referer": info['referer']}
    prefixes = [PRIMARY_PREFIX, SECONDARY_PREFIX, TERTIARY_PREFIX]

    # Attempt order: m3u8 then mp4 qualities for each prefix
    for prefix in prefixes:
        # m3u8 attempt
        m3u8_url = f"https://{prefix}.b-cdn.net/{vid}/playlist.m3u8"
        try:
            buf = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(buf):
                job = BunnyVideoDRM(
                    referer=info['referer'],
                    m3u8_url=m3u8_url,
                    name=name,
                    path=TEMP_DIR
                )
                job.download()
            if os.path.exists(temp_path):
                move_to_android(temp_path, name)
                return {"name": info['referer'], "success": True}
        except Exception:
            pass
        # mp4 fallback
        for quality in MP4_QUALITIES:
            mp4_url = f"https://{prefix}.b-cdn.net/{vid}/{quality}"
            try:
                resp = requests.get(mp4_url, headers=headers, stream=True, timeout=10)
                resp.raise_for_status()
                with open(temp_path, 'wb') as f:
                    for chunk in resp.iter_content(1024*1024):
                        f.write(chunk)
                move_to_android(temp_path, name)
                return {"name": info['referer'], "success": True}
            except Exception:
                continue
    return {"name": info['referer'], "success": False}


def main():
    raw = input("Enter URLs (space/comma-separated):\n").strip()
    urls = [u for u in re.split(r"[\s,;]+", raw) if u]
    if not urls:
        print("No URLs provided.")
        return
    jobs = [build_video_info(u) for u in urls]
    results = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(download_video, job) for job in jobs]
        for f in as_completed(futures):
            results.append(f.result())

    print("\n=== Results ===")
    for r in results:
        if r['success']:
            print(f"[OK] {r['name']}")
    errs = [r['name'] for r in results if not r['success']]
    if errs:
        print("\n=== Failed ===")
        for e in errs:
            print(f"- {e}")

if __name__ == "__main__":
    main()

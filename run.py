import os
import re
import requests
import io
import shutil
import subprocess
from contextlib import redirect_stdout, redirect_stderr
from b_cdn_drm_vod_dl import BunnyVideoDRM
from concurrent.futures import ThreadPoolExecutor, as_completed

# CDN prefixes
PRIMARY_PREFIX = "vz-f9765c3e-82b"
SECONDARY_PREFIX = "vz-bcc18906-38f"
TERTIARY_PREFIX = "vz-b3fe6a46-b2b"
QUATERNARY_PREFIX = "vz-40d00b68-e91"

# Quality options
MP4_QUALITIES = ["play_720p.mp4", "play_480p.mp4", "play_360p.mp4", "play_240p.mp4"]
QUATERNARY_VIDEO_RESOLUTIONS = ["2160p", "1440p", "1080p", "720p", "480p", "360p"]
QUATERNARY_AUDIO_RESOLUTIONS = ["256a", "192a", "128a", "96a"]

# Directories
TEMP_DIR = os.path.join(os.getcwd(), "downloads")
ANDROID_DOWNLOAD_DIR = "/storage/emulated/0/Download"
INVALID_CHARS = r'[<>:"/\\|?*]'


def sanitize_filename(name: str) -> str:
    return re.sub(INVALID_CHARS, '_', name)


def fetch_title(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    match = re.search(r"<title[^>]*>(.*?)</title>", resp.text, re.IGNORECASE | re.DOTALL)
    if not match:
        raise ValueError("Page title not found")
    title = match.group(1).strip()
    if '|' in title:
        title = title.split('|', 1)[1].strip()
    elif '_' in title:
        parts = re.split(r'_\s*', title, 1)
        title = parts[1].strip() if len(parts) > 1 else title
    return title


def build_video_info(url: str) -> dict:
    match = re.search(r"v=([a-f0-9\-]+)", url)
    if not match:
        raise ValueError(f"video_id not found in URL: {url}")
    vid = match.group(1)
    name = sanitize_filename(fetch_title(url))
    return {"referer": url, "video_id": vid, "name": name}


def move_to_android(src: str, name: str) -> None:
    os.makedirs(ANDROID_DOWNLOAD_DIR, exist_ok=True)
    dst = os.path.join(ANDROID_DOWNLOAD_DIR, f"{name}.mp4")
    shutil.move(src, dst)


def merge_audio_video(video_path: str, audio_m3u8: str, output_path: str) -> None:
    cmd = ["ffmpeg", "-i", video_path, "-i", audio_m3u8, "-c", "copy", "-y", output_path]
    subprocess.run(cmd, check=True)


def download_video(info: dict) -> dict:
    vid = info['video_id']
    name = info['name']
    os.makedirs(TEMP_DIR, exist_ok=True)
    temp_vid = os.path.join(TEMP_DIR, f"{name}.mp4")
    temp_out = os.path.join(TEMP_DIR, f"{name}_merged.mp4")
    headers = {"User-Agent": "Mozilla/5.0", "Referer": info['referer']}
    prefixes = [PRIMARY_PREFIX, SECONDARY_PREFIX, TERTIARY_PREFIX, QUATERNARY_PREFIX]

    for p in prefixes:
        if p != QUATERNARY_PREFIX:
            # Standard m3u8
            url = f"https://{p}.b-cdn.net/{vid}/playlist.m3u8"
            try:
                buf = io.StringIO()
                with redirect_stdout(buf), redirect_stderr(buf):
                    BunnyVideoDRM(referer=info['referer'], m3u8_url=url, name=name, path=TEMP_DIR).download()
                if os.path.exists(temp_vid):
                    move_to_android(temp_vid, name)
                    return {"name": info['referer'], "success": True}
            except:
                pass
            # Direct MP4 fallback
            for q in MP4_QUALITIES:
                mp4_url = f"https://{p}.b-cdn.net/{vid}/{q}"
                try:
                    resp = requests.get(mp4_url, headers=headers, stream=True, timeout=10)
                    resp.raise_for_status()
                    with open(temp_vid, 'wb') as f:
                        for chunk in resp.iter_content(1024*1024): f.write(chunk)
                    move_to_android(temp_vid, name)
                    return {"name": info['referer'], "success": True}
                except:
                    continue
        else:
            # Quaternary: resolution-specific video + best audio merge
            for res in QUATERNARY_VIDEO_RESOLUTIONS:
                video_url = f"https://{p}.b-cdn.net/{vid}/video/{res}/video.m3u8"
                try:
                    buf = io.StringIO()
                    with redirect_stdout(buf), redirect_stderr(buf):
                        BunnyVideoDRM(referer=info['referer'], m3u8_url=video_url, name=name, path=TEMP_DIR).download()
                    if not os.path.exists(temp_vid):
                        continue
                    # Try best audio first
                    for ares in QUATERNARY_AUDIO_RESOLUTIONS:
                        audio_url = f"https://{p}.b-cdn.net/{vid}/audio/{ares}/audio.m3u8"
                        try:
                            merge_audio_video(temp_vid, audio_url, temp_out)
                            move_to_android(temp_out, name)
                            return {"name": info['referer'], "success": True}
                        except:
                            continue
                except:
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
        for f in as_completed(futures): results.append(f.result())

    print("\n=== Results ===")
    for r in results:
        if r['success']: print(f"[OK] {r['name']}")
    fails = [r['name'] for r in results if not r['success']]
    if fails:
        print("\n=== Failed ===")
        for e in fails: print(f"- {e}")

if __name__ == "__main__":
    main()

import os
import re
import requests
import io
import shutil
import subprocess
from contextlib import redirect_stdout, redirect_stderr
from concurrent.futures import ThreadPoolExecutor, as_completed
from b_cdn_drm_vod_dl import BunnyVideoDRM

# CDN prefixes\ 
PRIMARY_PREFIX = "vz-f9765c3e-82b"
SECONDARY_PREFIX = "vz-bcc18906-38f"
TERTIARY_PREFIX = "vz-b3fe6a46-b2b"
QUATERNARY_PREFIX = "vz-40d00b68-e91"

# Fallback MP4 qualities
MP4_QUALITIES = ["play_720p.mp4", "play_480p.mp4", "play_360p.mp4", "play_240p.mp4"]
# Advanced prefixes video/audio lists
VIDEO_RESOLUTIONS = ["2160p", "1440p", "1080p", "720p", "480p", "360p"]
AUDIO_QUALITIES = ["256a", "192a", "128a", "96a"]

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
    m = re.search(r"<title[^>]*>(.*?)</title>", resp.text, re.IGNORECASE | re.DOTALL)
    if not m:
        raise ValueError("Page title not found")
    title = m.group(1).strip()
    if '|' in title:
        title = title.split('|',1)[1].strip()
    elif '_' in title:
        parts = re.split(r'_\s*', title,1)
        title = parts[1].strip() if len(parts)>1 else title
    return title


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


def download_advanced(info: dict, prefix: str) -> bool:
    vid, name, referer = info['video_id'], info['name'], info['referer']
    os.makedirs(TEMP_DIR, exist_ok=True)
    temp_video = os.path.join(TEMP_DIR, f"{name}_video.mp4")
    temp_merged = os.path.join(TEMP_DIR, f"{name}.mp4")
    # download highest resolution video + highest quality audio
    for res in VIDEO_RESOLUTIONS:
        video_m3u8 = f"https://{prefix}.b-cdn.net/{vid}/video/{res}/video.m3u8"
        try:
            buf = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(buf):
                BunnyVideoDRM(referer=referer, m3u8_url=video_m3u8, name=f"{name}_video", path=TEMP_DIR).download()
            if not os.path.exists(temp_video):
                continue
        except:
            continue
        # audio merge
        for aq in AUDIO_QUALITIES:
            audio_m3u8 = f"https://{prefix}.b-cdn.net/{vid}/audio/{aq}/audio.m3u8"
            try:
                buf = io.StringIO()
                with redirect_stdout(buf), redirect_stderr(buf):
                    BunnyVideoDRM(referer=referer, m3u8_url=audio_m3u8, name=f"{name}_audio", path=TEMP_DIR).download()
                audio_path = os.path.join(TEMP_DIR, f"{name}_audio.mp4")
                if not os.path.exists(audio_path):
                    continue
                subprocess.run(["ffmpeg", "-i", temp_video, "-i", audio_path, "-c", "copy", "-y", temp_merged], check=True)
                move_to_android(temp_merged, name)
                return True
            except:
                continue
    return False


def download_video(info: dict) -> dict:
    vid, name, referer = info['video_id'], info['name'], info['referer']
    headers = {"User-Agent": "Mozilla/5.0", "Referer": referer}
    prefixes = [PRIMARY_PREFIX, SECONDARY_PREFIX, TERTIARY_PREFIX]
    os.makedirs(TEMP_DIR, exist_ok=True)
    # primary, secondary, tertiary basic logic
    for p in prefixes:
        # advanced for tertiary
        if p == TERTIARY_PREFIX:
            if download_advanced(info, p):
                return {"name": referer, "success": True}
            continue
        # basic m3u8
        url = f"https://{p}.b-cdn.net/{vid}/playlist.m3u8"
        try:
            buf = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(buf):
                BunnyVideoDRM(referer=referer, m3u8_url=url, name=name, path=TEMP_DIR).download()
            temp_file = os.path.join(TEMP_DIR, f"{name}.mp4")
            if os.path.exists(temp_file):
                move_to_android(temp_file, name)
                return {"name": referer, "success": True}
        except:
            pass
        # mp4 fallback
        for q in MP4_QUALITIES:
            mp4_url = f"https://{p}.b-cdn.net/{vid}/{q}"
            try:
                resp = requests.get(mp4_url, headers=headers, stream=True, timeout=10)
                resp.raise_for_status()
                temp_file = os.path.join(TEMP_DIR, f"{name}.mp4")
                with open(temp_file, 'wb') as f:
                    for chunk in resp.iter_content(1024*1024): f.write(chunk)
                move_to_android(temp_file, name)
                return {"name": referer, "success": True}
            except:
                continue
    return {"name": referer, "success": False}


def main():
    raw = input("Enter URLs (space/comma-separated):\n").strip()
    urls = [u for u in re.split(r"[\s,;]+", raw) if u]
    if not urls:
        print("No URLs provided.")
        return
    jobs = [build_video_info(u) for u in urls]
    results = []
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = [ex.submit(download_video, job) for job in jobs]
        for f in as_completed(futures):
            results.append(f.result())

    print("\n=== Results ===")
    for r in results:
        if r['success']:
            print(f"[OK] {r['name']}")
    fails = [r['name'] for r in results if not r['success']]
    if fails:
        print("\n=== Failed ===")
        for e in fails:
            print(f"- {e}")

if __name__ == "__main__":
    main()

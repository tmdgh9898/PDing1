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

# MP4 fallback options
MP4_QUALITIES = ["play_720p.mp4", "play_480p.mp4", "play_360p.mp4", "play_240p.mp4"]
# Quaternary prefix: explicit video and audio m3u8 lists
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


def merge_with_ffmpeg(video_file: str, audio_m3u8: str, output_file: str) -> None:
    cmd = ["ffmpeg", "-i", video_file, "-i", audio_m3u8, "-c", "copy", "-y", output_file]
    subprocess.run(cmd, check=True)


def download_quaternary(info: dict) -> bool:
    vid, name, referer = info['video_id'], info['name'], info['referer']
    os.makedirs(TEMP_DIR, exist_ok=True)
    temp_video = os.path.join(TEMP_DIR, f"{name}_video.mp4")
    temp_merged = os.path.join(TEMP_DIR, f"{name}.mp4")
    headers = {"User-Agent":"Mozilla/5.0","Referer":referer}
    # Try video resolutions
    for res in VIDEO_RESOLUTIONS:
        video_m3u8 = f"https://{QUATERNARY_PREFIX}.b-cdn.net/{vid}/video/{res}/video.m3u8"
        try:
            buf=io.StringIO()
            with redirect_stdout(buf), redirect_stderr(buf):
                BunnyVideoDRM(referer=referer,m3u8_url=video_m3u8,name=name,path=TEMP_DIR).download()
            if not os.path.exists(temp_video):
                continue
            # Try audio qualities
            for aq in AUDIO_QUALITIES:
                audio_m3u8 = f"https://{QUATERNARY_PREFIX}.b-cdn.net/{vid}/audio/{aq}/audio.m3u8"
                try:
                    merge_with_ffmpeg(temp_video,audio_m3u8,temp_merged)
                    move_to_android(temp_merged,name)
                    return True
                except Exception:
                    continue
        except Exception:
            continue
    return False


def download_video(info: dict) -> dict:
    vid,name,referer = info['video_id'],info['name'],info['referer']
    headers={"User-Agent":"Mozilla/5.0","Referer":referer}
    prefixes=[PRIMARY_PREFIX,SECONDARY_PREFIX,TERTIARY_PREFIX]
    os.makedirs(TEMP_DIR, exist_ok=True)
    # Try prefix1-3
    for p in prefixes:
        # m3u8
        m3u8_url=f"https://{p}.b-cdn.net/{vid}/playlist.m3u8"
        try:
            buf=io.StringIO()
            with redirect_stdout(buf),redirect_stderr(buf):
                BunnyVideoDRM(referer=referer,m3u8_url=m3u8_url,name=name,path=TEMP_DIR).download()
            file=os.path.join(TEMP_DIR,f"{name}.mp4")
            if os.path.exists(file):move_to_android(file,name);return{"name":referer,"success":True}
        except:pass
        # mp4 fallback
        for q in MP4_QUALITIES:
            mp4_url=f"https://{p}.b-cdn.net/{vid}/{q}"
            try:
                resp=requests.get(mp4_url,headers=headers,stream=True,timeout=10);resp.raise_for_status()
                file=os.path.join(TEMP_DIR,f"{name}.mp4")
                with open(file,'wb') as f: 
                    for chunk in resp.iter_content(1024*1024):f.write(chunk)
                move_to_android(file,name);return{"name":referer,"success":True}
            except:continue
    # Try quaternary with explicit video+audio
    if download_quaternary(info):return{"name":referer,"success":True}
    return{"name":referer,"success":False}


def main():
    raw=input("Enter URLs (space/comma-separated):\n").strip()
    urls=[u for u in re.split(r"[\s,;]+",raw) if u]
    if not urls:print("No URLs provided.");return
    jobs=[build_video_info(u) for u in urls]
    res=[]
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures=[ex.submit(download_video,j) for j in jobs]
        for f in as_completed(futures):res.append(f.result())
    print("\n=== Results ===")
    for r in res:
        if r['success']:print(f"[OK] {r['name']}")
    fails=[r['name'] for r in res if not r['success']]
    if fails:print("\n=== Failed ===");[print(f"- {e}") for e in fails]

if __name__ == "__main__":main()

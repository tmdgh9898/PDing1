import os
import re
import requests
import io
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from b_cdn_drm_vod_dl import BunnyVideoDRM
from PIL import Image, ImageDraw, ImageFont

PRIMARY_PREFIX = "vz-f9765c3e-82b"
SECONDARY_PREFIX = "vz-bcc18906-38f"
TERTIARY_PREFIX = "vz-b3fe6a46-b2b"
QUATERNARY_PREFIX = "vz-40d00b68-e91"
QUINARY_PREFIX = "vz-6b30db03-fbb"

MP4_QUALITIES = ["play_720p.mp4", "play_480p.mp4", "play_360p.mp4", "play_240p.mp4"]
VIDEO_RESOLUTIONS = ["2160p", "1440p", "1080p", "720p", "480p", "360p"]
AUDIO_QUALITIES = ["256a", "192a", "128a", "96a"]

TEMP_DIR = os.path.join(os.getcwd(), "downloads")
ANDROID_DOWNLOAD_DIR = "/storage/emulated/0/Download"
INVALID_CHARS = r'[<>:"/\\|?*]'

def sanitize_filename(name: str) -> str:
    return re.sub(INVALID_CHARS, '_', name)

def fetch_title(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    resp.raise_for_status()
    m = re.search(r"<title[^>]*>(.*?)</title>", resp.text, re.IGNORECASE | re.DOTALL)
    if not m:
        raise ValueError("Page title not found")
    title = m.group(1).strip()
    if '|' in title:
        title = title.split('|', 1)[1].strip()
    elif '_' in title:
        parts = re.split(r'_\s*', title, 1)
        title = parts[1].strip() if len(parts) > 1 else title
    return title

def build_video_info(url: str) -> dict:
    m = re.search(r"v=([a-f0-9\-]+)", url)
    if not m:
        raise ValueError(f"video_id not found in URL: {url}")
    vid = m.group(1)
    name = sanitize_filename(fetch_title(url))
    return {"referer": url, "video_id": vid, "name": name}

def get_video_info(video_path: str) -> dict:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration:stream=codec_name,width,height",
        "-of", "json",
        video_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        import json
        info = json.loads(result.stdout)
        streams = info.get("streams", [])
        video_stream = next((s for s in streams if s.get("width")), None)
        audio_stream = next((s for s in streams if s.get("codec_name") and not s.get("width")), None)
        return {
            "duration": float(info["format"]["duration"]),
            "resolution": f"{video_stream['width']}x{video_stream['height']}" if video_stream else "N/A",
            "vcodec": video_stream["codec_name"] if video_stream else "N/A",
            "acodec": audio_stream["codec_name"] if audio_stream else "N/A",
        }
    except Exception as e:
        print(f"[Info Error] {e}")
        return {}

def get_video_info_str(video_path: str) -> str:
    info = get_video_info(video_path)
    if not info:
        return ""
    duration_sec = int(float(info.get("duration", 0)))
    h, rem = divmod(duration_sec, 3600)
    m, s = divmod(rem, 60)
    duration_str = f"{h:02d}:{m:02d}:{s:02d}"
    txt = (
        f"{info.get('resolution','')} | {duration_str} | "
        f"V:{info.get('vcodec','')} / A:{info.get('acodec','')}"
    )
    return txt

def create_thumbnail_grid_with_info(video_path: str, thumb_path: str, tile=4):
    info_str = get_video_info_str(video_path)
    # 1. 영상 길이, 16 프레임 추출용 타임스탬프
    info = get_video_info(video_path)
    duration = info.get("duration", 0)
    if not duration or duration < 1:
        print("[Thumbnail Error] 영상 길이 파악 실패")
        return False
    # 16개 구간 프레임 (0.5초~끝-0.5초 사이 균등)
    timestamps = [duration * (i + 1) / 17 for i in range(16)]
    frames = []
    for idx, ts in enumerate(timestamps):
        outpath = thumb_path + f".frame{idx+1:02d}.jpg"
        cmd = [
            "ffmpeg", "-ss", str(ts), "-i", video_path,
            "-frames:v", "1", "-q:v", "2", outpath, "-y"
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            frames.append(outpath)
        except Exception as e:
            print(f"[Frame Error] {e}")
            return False
    # 2. 4x4 타일 합치기 (Pillow)
    imgs = [Image.open(f) for f in frames]
    w, h = imgs[0].size
    grid = Image.new('RGB', (w*tile, h*tile))
    for i, img in enumerate(imgs):
        x, y = (i % tile) * w, (i // tile) * h
        grid.paste(img, (x, y))
        img.close()
        os.remove(frames[i])
    # 3. info 오버레이
    draw = ImageDraw.Draw(grid)
    font_path = "/system/fonts/DroidSansMono.ttf"
    font_size = int(h * 0.4)
    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception:
        font = ImageFont.load_default()
    box_h = font_size + 20
    W, H = grid.size
    draw.rectangle([(0, H - box_h), (W, H)], fill=(0, 0, 0, 230))
    w_txt, h_txt = draw.textsize(info_str, font=font)
    draw.text(((W - w_txt) / 2, H - box_h + 10), info_str, font=font, fill=(255, 255, 255, 255))
    grid.save(thumb_path, quality=92)
    return True

def move_to_android(src: str, name: str) -> None:
    os.makedirs(ANDROID_DOWNLOAD_DIR, exist_ok=True)
    dst = os.path.join(ANDROID_DOWNLOAD_DIR, f"{name}.mp4")
    shutil.move(src, dst)
    thumb_path = os.path.join(ANDROID_DOWNLOAD_DIR, f"{name}_thumb.jpg")
    create_thumbnail_grid_with_info(dst, thumb_path)
    info = get_video_info(dst)
    info_path = os.path.join(ANDROID_DOWNLOAD_DIR, f"{name}_info.txt")
    with open(info_path, "w") as f:
        for k, v in info.items():
            f.write(f"{k}: {v}\n")

# download_advanced, download_video, main 함수 등은 기존 그대로 사용!
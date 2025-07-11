import os
import re
import requests
import io
from contextlib import redirect_stdout, redirect_stderr
from b_cdn_drm_vod_dl import BunnyVideoDRM
from concurrent.futures import ThreadPoolExecutor, as_completed

# CDN prefixes
PRIMARY_PREFIX = "vz-f9765c3e-82b"
SECONDARY_PREFIX = "vz-bcc18906-38f"
TERTIARY_PREFIX = "vz-b3fe6a46-b2b"
# mp4 화질 옵션 목록
MP4_QUALITIES = [
    "play_720p.mp4",
    "play_480p.mp4",
    "play_360p.mp4",
    "play_240p.mp4"
]
DOWNLOAD_DIR = "./downloads"
INVALID_FILENAME_CHARS = r'[<>:"/\\|?*]'


def sanitize_filename(name: str) -> str:
    return re.sub(INVALID_FILENAME_CHARS, '_', name)


def fetch_title(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    match = re.search(r"<title[^>]*>(.*?)</title>", resp.text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    raise ValueError("페이지 제목을 찾을 수 없습니다.")


def build_video_info(entry: dict) -> dict:
    referer = entry["referer"]
    orig_name = entry["name"]
    match = re.search(r"v=([a-f0-9\-]+)", referer)
    if not match:
        raise ValueError(f"video_id not found in referer: {referer}")
    safe_name = sanitize_filename(orig_name)
    return {"orig_name": orig_name, "safe_name": safe_name, "referer": referer, "video_id": match.group(1)}


def download_video(video_info: dict) -> dict:
    vid = video_info['video_id']
    safe_name = video_info['safe_name']
    orig_name = video_info['orig_name']
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    output_path = os.path.join(DOWNLOAD_DIR, f"{safe_name}.mp4")

    # 시도 순서 구성: primary -> secondary -> tertiary prefixes
    attempts = []
    # primary
    attempts.append(("m3u8 primary", f"https://{PRIMARY_PREFIX}.b-cdn.net/{vid}/playlist.m3u8"))
    for q in MP4_QUALITIES:
        attempts.append((f"mp4 primary {q}", f"https://{PRIMARY_PREFIX}.b-cdn.net/{vid}/{q}"))
    # secondary
    attempts.append(("m3u8 secondary", f"https://{SECONDARY_PREFIX}.b-cdn.net/{vid}/playlist.m3u8"))
    for q in MP4_QUALITIES:
        attempts.append((f"mp4 secondary {q}", f"https://{SECONDARY_PREFIX}.b-cdn.net/{vid}/{q}"))
    # tertiary
    attempts.append(("m3u8 tertiary", f"https://{TERTIARY_PREFIX}.b-cdn.net/{vid}/playlist.m3u8"))
    for q in MP4_QUALITIES:
        attempts.append((f"mp4 tertiary {q}", f"https://{TERTIARY_PREFIX}.b-cdn.net/{vid}/{q}"))

    headers = {"User-Agent": "Mozilla/5.0", "Referer": video_info["referer"]}
    for method, url in attempts:
        try:
            if method.startswith("m3u8"):
                buf = io.StringIO()
                with redirect_stdout(buf), redirect_stderr(buf):
                    job = BunnyVideoDRM(
                        referer=video_info["referer"],
                        m3u8_url=url,
                        name=safe_name,
                        path=DOWNLOAD_DIR
                    )
                    job.download()
            else:
                resp = requests.get(url, headers=headers, stream=True, timeout=10)
                resp.raise_for_status()
                with open(output_path, 'wb') as f:
                    for chunk in resp.iter_content(1024*1024):
                        f.write(chunk)
            if os.path.exists(output_path):
                return {"name": orig_name, "success": True}
        except Exception:
            continue
    return {"name": orig_name, "success": False}


def main():
    raw = input("URL들을 공백/쉼표로 구분하여 입력하세요:\n")
    urls = [u for u in re.split(r"[\s,;]+", raw.strip()) if u]
    if not urls:
        print("URL이 없습니다.")
        return

    videos = []
    for u in urls:
        try:
            title = fetch_title(u)
            if '|' in title:
                title = title.split('|', 1)[1].strip()
            videos.append({"referer": u, "name": title})
        except Exception:
            name = input(f"{u} 제목 자동 추출 실패, 제목 입력: ")
            videos.append({"referer": u, "name": name})

    confirm = input("즉시 다운로드 시작? (y/n): ").strip().lower()
    if confirm not in ("y","yes","예"):
        print("취소됨.")
        return

    results = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(download_video, build_video_info(v)) for v in videos]
        for f in as_completed(futures):
            results.append(f.result())

    print("\n=== 다운로드 결과 ===")
    for r in results:
        if r['success']:
            print(f"[OK] {r['name']}")
    errors = [r['name'] for r in results if not r['success']]
    if errors:
        print("\n=== 에러 발생 항목 ===")
        for e in errors:
            print(f"- {e}")

if __name__ == "__main__":
    main()

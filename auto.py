import os import re import requests import io from contextlib import redirect_stdout, redirect_stderr from b_cdn_drm_vod_dl import BunnyVideoDRM from concurrent.futures import ThreadPoolExecutor, as_completed

CDN prefixes

PRIMARY_PREFIX = "vz-f9765c3e-82b" SECONDARY_PREFIX = "vz-bcc18906-38f" TERTIARY_PREFIX = "vz-b3fe6a46-b2b"

mp4 quality options

MP4_QUALITIES = [ "play_720p.mp4", "play_480p.mp4", "play_360p.mp4", "play_240p.mp4" ]

DOWNLOAD_DIR = os.path.expanduser("~/storage/downloads")  # directly save to Android Download folder INVALID_FILENAME_CHARS = r'[<>:"/\|?*]'

def sanitize_filename(name: str) -> str: """ Remove invalid filesystem characters. """ return re.sub(INVALID_FILENAME_CHARS, '_', name)

def fetch_title(url: str) -> str: headers = {"User-Agent": "Mozilla/5.0"} resp = requests.get(url, headers=headers, timeout=10) resp.raise_for_status() match = re.search(r"<title[^>]>(.?)</title>", resp.text, re.IGNORECASE | re.DOTALL) if match: title = match.group(1).strip() # remove prefix before '|' or '' if '|' in title: title = title.split('|', 1)[1].strip() elif '' in title: parts = re.split(r'_\s*', title, 1) title = parts[1].strip() if len(parts) > 1 else title return title raise ValueError("Page title not found")

def build_video_info(url: str) -> dict: # Extract video_id from URL match = re.search(r"v=([a-f0-9-]+)", url) if not match: raise ValueError(f"video_id not found in URL: {url}") video_id = match.group(1) name = sanitize_filename(fetch_title(url)) return {"video_id": video_id, "referer": url, "name": name}

def download_video(info: dict) -> dict: vid = info['video_id'] name = info['name'] os.makedirs(DOWNLOAD_DIR, exist_ok=True) output_path = os.path.join(DOWNLOAD_DIR, f"{name}.mp4")

# attempt list: primary, secondary, tertiary
prefixes = [PRIMARY_PREFIX, SECONDARY_PREFIX, TERTIARY_PREFIX]
headers = {"User-Agent": "Mozilla/5.0", "Referer": info['referer']}

for prefix in prefixes:
    # m3u8 attempt
    m3u8_url = f"https://{prefix}.b-cdn.net/{vid}/playlist.m3u8"
    try:
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(buf):
            job = BunnyVideoDRM(referer=info['referer'], m3u8_url=m3u8_url, name=name, path=DOWNLOAD_DIR)
            job.download()
        if os.path.exists(output_path):
            return {"name": info['referer'], "success": True}
    except Exception:
        pass
    # mp4 attempts
    for q in MP4_QUALITIES:
        mp4_url = f"https://{prefix}.b-cdn.net/{vid}/{q}"
        try:
            resp = requests.get(mp4_url, headers=headers, stream=True, timeout=10)
            resp.raise_for_status()
            with open(output_path, 'wb') as f:
                for chunk in resp.iter_content(1024*1024): f.write(chunk)
            return {"name": info['referer'], "success": True}
        except Exception:
            continue
return {"name": info['referer'], "success": False}

def main(): raw = input("Enter URLs separated by space or comma:\n").strip() urls = [u for u in re.split(r"[\s,;]+", raw) if u] if not urls: print("No URLs provided.") return

results = []
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(download_video, build_video_info(u)) for u in urls]
    for f in as_completed(futures):
        results.append(f.result())

print("\n=== Download Results ===")
for r in results:
    if r['success']:
        print(f"[OK] {r['name']}")
errors = [r['name'] for r in results if not r['success']]
if errors:
    print("\n=== Errors ===")
    for e in errors:
        print(f"- {e}")

if name == "main": main()


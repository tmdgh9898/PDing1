#!/usr/bin/env python3
import os
import requests
import subprocess
from urllib.parse import urljoin

# ——————————————————————————————————————————
# 설정
BASE_URL = "https://vz-40d00b68-e91.b-cdn.net/a0d368af-f751-442e-9d6a-cb28f96fa765/av1_2160p/"
TEMP_DIR = "segments"
OUT_FILE = "output.mp4"
NUM_SEGMENTS = 593   # 실제 세그먼트 개수에 맞게 변경
HEADERS = {"User-Agent":"Mozilla/5.0"}
# ——————————————————————————————————————————

os.makedirs(TEMP_DIR, exist_ok=True)

# 1) init 세그먼트 다운로드
init_url = urljoin(BASE_URL, "videoinit.mp4")
init_path = os.path.join(TEMP_DIR, "videoinit.mp4")
print("Downloading init:", init_url)
resp = requests.get(init_url, headers=HEADERS, timeout=10)
resp.raise_for_status()
with open(init_path, "wb") as f:
    f.write(resp.content)

# 2) media segments 다운로드
segment_paths = ["videoinit.mp4"]
for i in range(1, NUM_SEGMENTS+1):
    name = f"video{i}.m4s"
    url  = urljoin(BASE_URL, name)
    out  = os.path.join(TEMP_DIR, name)
    print(f"Downloading segment {i}:", url)
    try:
        r = requests.get(url, headers=HEADERS, timeout=10, stream=True)
        r.raise_for_status()
        with open(out, "wb") as f:
            for chunk in r.iter_content(1024*1024):
                f.write(chunk)
        segment_paths.append(name)
    except requests.HTTPError as e:
        print(f"  → segment {i} not found, stopping ({e})")
        break

# 3) concat 리스트 파일 생성
list_txt = os.path.join(TEMP_DIR, "list.txt")
with open(list_txt, "w") as f:
    for fn in segment_paths:
        f.write(f"file '{fn}'\n")

# 4) ffmpeg로 합치기
print("Merging into", OUT_FILE)
subprocess.run([
    "ffmpeg", "-f", "concat", "-safe", "0",
    "-i", list_txt,
    "-c", "copy",
    "-y", OUT_FILE
], check=True)

print("Done:", OUT_FILE)
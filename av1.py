#!/data/data/com.termux/files/usr/bin/env python3
import os
import sys
from b_cdn_drm_vod_dl import BunnyVideoDRM

def usage():
    print("Usage: download_drm.py <VIDEO_ID> <RESOLUTION>")
    print("Example: download_drm.py a0d368af-f751-442e-9d6a-cb28f96fa765 2160p")
    sys.exit(1)

if len(sys.argv) != 3:
    usage()

VIDEO_ID  = sys.argv[1]
RESOLUTION = sys.argv[2]  # ex: 1080p, 1440p, 2160p
CODEC     = "av1"         # vp9 영상이라면 "vp9" 로 바꿔 쓰세요.

# HLS 플레이리스트 URL
m3u8_url = f"https://vz-40d00b68-e91.b-cdn.net/{VIDEO_ID}/{CODEC}_{RESOLUTION}/video.m3u8"

# 출력 파일명 및 경로
output_name = f"{VIDEO_ID}_{CODEC}_{RESOLUTION}"
output_path = os.getcwd()  # 스크립트 실행 디렉터리에 저장

drm = BunnyVideoDRM(
    referer="https://vz-40d00b68-e91.b-cdn.net",
    m3u8_url=m3u8_url,
    name=output_name,
    path=output_path
)

drm.download()
print(f"\n✅ Done! 파일은 {output_path}/{output_name}.mp4 입니다.")
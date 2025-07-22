#!/data/data/com.termux/files/usr/bin/env python3
"""
av1.py

Termux에서 AV1 HLS 스트림(DRM 포함)의 다운로드, 라이선스 교환, 복호화, 병합까지 자동 수행하는 스크립트입니다.
사용 전 `b_cdn_drm_vod_dl.py` 모듈이 같은 디렉터리에 위치해야 합니다.
"""
import os
import sys
import requests
from b_cdn_drm_vod_dl import BunnyVideoDRM

def usage():
    print("Usage: av1.py <VIDEO_ID> <RESOLUTION>")
    print("Example: av1.py a0d368af-f751-442e-9d6a-cb28f96fa765 2160p")
    sys.exit(1)

if len(sys.argv) != 3:
    usage()

VIDEO_ID   = sys.argv[1]
RESOLUTION = sys.argv[2]  # ex: 1080p, 1440p, 2160p
CODEC      = "av1"       # AV1 전용 스크립트

# 고정 Prefix 설정
PREFIX = "vz-40d00b68-e91"
DOMAIN = f"https://{PREFIX}.b-cdn.net"

# HLS manifest URL (video.m3u8)
m3u8_url = f"{DOMAIN}/{VIDEO_ID}/{CODEC}_{RESOLUTION}/video.m3u8"

# 존재 여부 확인
try:
    head = requests.head(m3u8_url, timeout=5)
    if head.status_code != 200:
        print(f"[ERROR] Manifest not found: {m3u8_url} (status {head.status_code})")
        sys.exit(1)
except requests.RequestException as e:
    print(f"[ERROR] Network error when checking manifest: {e}")
    sys.exit(1)

print(f"[*] Found HLS manifest: {m3u8_url}")

# 출력 파일명 및 경로
output_name = f"{VIDEO_ID}_{CODEC}_{RESOLUTION}"
output_path = os.getcwd()

# BunnyVideoDRM으로 다운로드 + 복호화 + 병합
drm = BunnyVideoDRM(
    referer=DOMAIN,
    m3u8_url=m3u8_url,
    name=output_name,
    path=output_path
)

drm.download()
print(f"\n✅ 완료! 파일 위치: {output_path}/{output_name}.mp4")
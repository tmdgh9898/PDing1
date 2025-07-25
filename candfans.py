#!/usr/bin/env python3
import json
import re
import cloudscraper
import subprocess
import sys

def fetch_timeline(comment_id: str) -> dict:
    """
    cloudscraper로 get-timeline API 호출
    """
    url = f"https://candfans.jp/api/contents/get-timeline/{comment_id}"
    scraper = cloudscraper.create_scraper()
    headers = {
        "Referer": f"https://candfans.jp/posts/comment/show/{comment_id}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }
    resp = scraper.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()

def extract_title_and_link(data: dict) -> tuple:
    """
    JSON에서 title과 m3u8 링크를 추출하여 반환
    """
    post = data.get("data", {}).get("post", {})
    title = post.get("title") or ""
    blob = json.dumps(data)
    match = re.search(r'https://video\.candfans\.jp/user/\d+/post/\d+/[0-9a-fA-F\-]+\.m3u8', blob)
    if match:
        return title, match.group(0)
    user_id = post.get("user_id")
    post_id = post.get("post_id")
    if not (user_id and post_id):
        raise ValueError("user_id 또는 post_id가 없습니다.")
    # post_attachments
    for att in post.get("post_attachments", []):
        dp = att.get("default_path")
        if dp:
            return title, f"https://video.candfans.jp/user/{user_id}/post/{post_id}/{dp}"
    sample = post.get("sample_file")
    if sample:
        return title, f"https://video.candfans.jp{sample}"
    for att in post.get("attachments", []):
        uuid = att.get("uuid")
        if uuid:
            return title, f"https://video.candfans.jp/user/{user_id}/post/{post_id}/{uuid}.m3u8"
    for key in ("default_path", "video_key"):
        val = post.get(key)
        if val:
            return title, f"https://video.candfans.jp/user/{user_id}/post/{post_id}/{val}.m3u8"
    raise ValueError("m3u8 생성용 키를 찾을 수 없습니다.")

def parse_comment_id(arg: str) -> str:
    """URL 또는 ID 문자열에서 숫자 comment_id 추출"""
    if arg.isdigit():
        return arg
    m = re.search(r"/([0-9]+)(?:$|/)", arg)
    if m:
        return m.group(1)
    m = re.search(r"([0-9]+)", arg)
    if m:
        return m.group(1)
    raise ValueError(f"유효한 comment_id를 찾을 수 없습니다: {arg}")

def main():
    # URL 또는 ID 입력
    url_input = input("Enter comment URL or ID: ").strip()
    if not url_input:
        print("No input provided.")
        sys.exit(1)
    try:
        cid = parse_comment_id(url_input)
    except Exception as e:
        print(f"[ERROR] ID 파싱 실패: {e}")
        sys.exit(1)
    try:
        data = fetch_timeline(cid)
    except Exception as e:
        print(f"[ERROR] API 호출 실패: {e}")
        sys.exit(1)
    try:
        title, link = extract_title_and_link(data)
    except Exception as e:
        print(f"[ERROR] 링크 생성 실패: {e}")
        sys.exit(1)
    # 링크 복사
    print(f"Link: {link}")
    try:
        subprocess.run(["termux-clipboard-set", link], check=True)
        print("Link copied to clipboard.")
    except Exception as e:
        print(f"Failed to copy link: {e}")
    # 제목 복사
    print(f"Title: {title}")
    try:
        subprocess.run(["termux-clipboard-set", title], check=True)
        print("Title copied to clipboard.")
    except Exception as e:
        print(f"Failed to copy title: {e}")

if __name__ == "__main__":
    main()

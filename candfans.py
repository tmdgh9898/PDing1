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
    match = re.search(
        r'https://video\.candfans\.jp/user/\d+/post/\d+/[0-9a-fA-F\-]+\.m3u8', blob
    )
    if match:
        return title, match.group(0)

    user_id = post.get("user_id")
    post_id = post.get("post_id")
    if not (user_id and post_id):
        raise ValueError("user_id 또는 post_id가 없습니다.")
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
    raw = input("Enter comment URLs or IDs (separated by space): ")
    args = raw.strip().split()
    if not args:
        print("No input provided.")
        sys.exit(1)
    last_title = None
    last_link = None
    for arg in args:
        try:
            cid = parse_comment_id(arg)
        except Exception as e:
            print(f"[ERROR] ID 파싱 실패 '{arg}': {e}")
            continue
        try:
            data = fetch_timeline(cid)
        except Exception as e:
            print(f"[{cid}] API 호출 실패: {e}")
            continue
        try:
            title, link = extract_title_and_link(data)
        except Exception as e:
            print(f"[{cid}] 링크 생성 실패: {e}")
            continue
        print(f"Link: {link}")
        print(f"Title: {title}\n")
        last_title = title
        last_link = link
    if last_link:
        try:
            subprocess.run(["termux-clipboard-set", last_link], check=True)
            print(f"Last link copied to clipboard: {last_link}")
        except Exception as e:
            print(f"Failed to copy link: {e}")
    if last_title:
        try:
            subprocess.run(["termux-clipboard-set", last_title], check=True)
            print(f"Last title copied to clipboard: {last_title}")
        except Exception as e:
            print(f"Failed to copy title: {e}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import json
import re
import cloudscraper
import subprocess

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

def extract_m3u8_link(data: dict) -> str:
    """
    1) JSON 내부에 전체 URL이 있으면 바로 리턴
    2) post_attachments[].default_path 사용
    3) sample_file 사용
    4) 기본 attachments, default_path, video_key 순으로 조합
    """
    blob = json.dumps(data)
    match = re.search(r'https://video\\.candfans\\.jp/user/\\d+/post/\\d+/[0-9a-fA-F\\-]+\\.m3u8', blob)
    if match:
        return match.group(0)

    post = data.get("data", {}).get("post", {})
    user_id = post.get("user_id")
    post_id = post.get("post_id")
    if not (user_id and post_id):
        raise ValueError("user_id 또는 post_id가 없습니다.")

    for att in post.get("post_attachments", []):
        dp = att.get("default_path")
        if dp:
            return f"https://video.candfans.jp/user/{user_id}/post/{post_id}/{dp}"

    sample = post.get("sample_file")
    if sample:
        return f"https://video.candfans.jp{sample}"

    for att in post.get("attachments", []):
        uuid = att.get("uuid")
        if uuid:
            return f"https://video.candfans.jp/user/{user_id}/post/{post_id}/{uuid}.m3u8"

    for key in ("default_path", "video_key"):
        val = post.get(key)
        if val:
            return f"https://video.candfans.jp/user/{user_id}/post/{post_id}/{val}.m3u8"

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
    # 사용자 입력 받기
    try:
        raw = input("Enter comment IDs or URLs (separated by space): ")
    except EOFError:
        return
    args = raw.strip().split()
    if not args:
        print("No input provided.")
        return

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
            link = extract_m3u8_link(data)
            print(link)
            last_link = link
        except Exception as e:
            print(f"[{cid}] 링크 생성 실패: {e}")

    if last_link:
        try:
            subprocess.run(["termux-clipboard-set", last_link], check=True)
            print(f"\nCopied to clipboard: {last_link}")
        except Exception as e:
            print(f"Failed to copy to clipboard: {e}")

if __name__ == "__main__":
    main()

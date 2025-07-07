import os
import subprocess

class BunnyVideoDRM:
    def __init__(self, referer, m3u8_url, name, path):
        self.referer = referer
        self.m3u8_url = m3u8_url
        self.name = name
        self.path = path

    def download(self):
        os.makedirs(self.path, exist_ok=True)
        output_path = os.path.join(self.path, f"{self.name}.mp4")

        cmd = [
            "yt-dlp",
            "-o", output_path,
            "--referer", self.referer,
            "--hls-use-mpegts",
            self.m3u8_url
        ]

        print(f"[INFO] Running yt-dlp command:")
        print(" ".join(cmd))

        try:
            subprocess.run(cmd, check=True)
            print(f"[SUCCESS] Download completed: {output_path}")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] yt-dlp failed: {e}")


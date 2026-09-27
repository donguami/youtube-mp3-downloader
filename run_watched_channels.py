import os
import sys
import json
import subprocess
from utils import setup_utf8_encoding

setup_utf8_encoding()

WATCHED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watched_channels.json")

def main():
    if not os.path.exists(WATCHED_FILE):
        print(f"[-] 감시 채널 목록 파일이 존재하지 않습니다: {WATCHED_FILE}")
        return

    try:
        with open(WATCHED_FILE, "r", encoding="utf-8") as f:
            channels = json.load(f)
    except Exception as e:
        print(f"[-] watched_channels.json 읽기 실패: {e}")
        return

    print(f"[+] 총 {len(channels)}개 채널 감시 체크 시작...", flush=True)

    for idx, item in enumerate(channels, 1):
        name = item.get("name", f"채널_{idx}")
        target = item.get("target")
        quality = item.get("quality", "128k")
        cnt = item.get("cnt", 1)

        if not target:
            continue

        print(f"\n[+] ({idx}/{len(channels)}) 감시 채널 체크 중: {name} ({target})", flush=True)

        cmd = [
            sys.executable, "download_channel.py",
            "-t", "channel",
            "-g", target,
            "-q", str(quality),
            "-c", str(cnt),
            "-tg"
        ]

        try:
            subprocess.run(cmd, check=False)
        except Exception as e:
            print(f"[-] {name} 처리 중 예외 발생: {e}", flush=True)

    print("\n[+] 모든 감시 채널 체크 완료!", flush=True)

if __name__ == "__main__":
    main()

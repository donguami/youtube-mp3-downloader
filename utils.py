import os
import sys
import json
import time
import subprocess
from datetime import datetime

# UTF-8 출력 재설정 (Windows 콘솔 호환성)
def setup_utf8_encoding():
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

# 파이썬 패키지 동적 설치 및 임포트 헬퍼
def install_and_import(package):
    import importlib
    try:
        importlib.import_module(package)
    except ImportError:
        print(f"[{package}] 패키지를 설치 중입니다...", flush=True)
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# yt-dlp 최신 버전 자동 점검 및 업데이트 헬퍼
UPDATE_CHECK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "update_check.json")

def check_and_update_ytdlp(force=False):
    """
    yt-dlp 엔진 및 실행 파일의 최신 업데이트를 자동으로 확인하고 업데이트합니다.
    (기본 24시간 주기로 체크하여 실행 속도 지연을 방지합니다.)
    """
    now = time.time()
    last_check = 0

    if os.path.exists(UPDATE_CHECK_FILE):
        try:
            with open(UPDATE_CHECK_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                last_check = data.get("last_check", 0)
        except Exception:
            pass

    # 24시간(86400초)이 지나지 않았고 force 옵션이 없으면 건너뜀
    if not force and (now - last_check < 86400):
        return

    print("🔄 yt-dlp 엔진 최신 업데이트 확인 중...", flush=True)
    try:
        # 1. 파이썬 pip 패키지 업데이트
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # 2. 프로젝트 폴더 내 yt-dlp.exe 바이너리 업데이트
        script_dir = os.path.dirname(os.path.abspath(__file__))
        ytdlp_exe = os.path.join(script_dir, "yt-dlp.exe")
        if os.path.exists(ytdlp_exe):
            subprocess.run([ytdlp_exe, "-U"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # 체크 일시 업데이트 저장
        with open(UPDATE_CHECK_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_check": now, "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, f, indent=2)

        print("✅ yt-dlp 최신 버전 업데이트 점검 완료!", flush=True)
    except Exception as e:
        print(f"⚠️ yt-dlp 업데이트 점검 중 알림: {e}", flush=True)

# 재생시간(초) 기반 50MB 맞춤 최적 비트레이트(kbps) 계산기
def calculate_optimal_bitrate(duration_seconds, max_mb=45, user_quality='128'):
    try:
        req_bitrate = int(str(user_quality).lower().replace('k', ''))
    except ValueError:
        req_bitrate = 128

    if not duration_seconds or duration_seconds <= 0:
        return str(req_bitrate)

    target_kbps = (max_mb * 1024 * 8) / duration_seconds
    standard_bitrates = [320, 256, 192, 160, 128, 96, 64, 48, 32]

    selected_bitrate = 32
    for b in standard_bitrates:
        if b <= target_kbps and b <= req_bitrate:
            selected_bitrate = b
            break

    if selected_bitrate > target_kbps and target_kbps < 32:
        selected_bitrate = 32

    mins = int(duration_seconds // 60)
    secs = int(duration_seconds % 60)
    print(f"⏱️ 재생시간: {mins}분 {secs}초")
    print(f"📊 계산된 최대 허용 비트레이트: {target_kbps:.1f} kbps (목표 용량: {max_mb}MB 이하)")
    print(f"⚙️ 최종 적용 비트레이트: {selected_bitrate} kbps", flush=True)

    return str(selected_bitrate)

# 재생시간(초) ➔ 시:분:초 가독성 포맷 변환기
def format_duration(seconds):
    if not seconds or seconds <= 0:
        return "정보 없음"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}시간 {minutes}분 {secs}초"
    return f"{minutes}분 {secs}초"

# 히스토리 파일 읽기
def get_history_ids(history_file_path: str) -> set:
    history_ids = set()
    if os.path.exists(history_file_path):
        try:
            with open(history_file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        history_ids.add(line)
        except Exception:
            pass
    return history_ids

# 통합 로깅 헬퍼
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "download_history.log")

def log_event(status: str, message: str, metadata: dict = None):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    meta_str = ""
    if metadata:
        meta_parts = []
        if metadata.get("title"):
            meta_parts.append(f"제목: {metadata['title']}")
        if metadata.get("channel"):
            meta_parts.append(f"채널: {metadata['channel']}")
        if metadata.get("quality"):
            meta_parts.append(f"음질: {metadata['quality']}k")
        if metadata.get("duration"):
            meta_parts.append(f"재생시간: {metadata['duration']}초")
        meta_str = f" | ({', '.join(meta_parts)})"

    log_line = f"[{now_str}] [{status.upper()}] {message}{meta_str}\n"

    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception as e:
        print(f"[!] 로그 파일 기록 실패: {e}", flush=True)

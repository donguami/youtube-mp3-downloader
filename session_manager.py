import os
import sys
import json
import time
from datetime import datetime

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

class SessionManager:
    """
    세션 프리셋 및 세션별 개별 폴더/로그 관리 클래스
    """
    def __init__(self, base_download_dir: str = None):
        if not base_download_dir:
            base_download_dir = os.path.join(os.path.expanduser("~"), "Downloads", "YouTube_Downloads")
        self.base_download_dir = os.path.abspath(base_download_dir)
        self.sessions_dir = os.path.join(self.base_download_dir, "sessions")
        self.presets_file = os.path.join(self.sessions_dir, "session_presets.json")
        os.makedirs(self.sessions_dir, exist_ok=True)

    def load_all_presets(self) -> dict:
        """저장된 모든 세션 프리셋 조회 (다운로드 경로 및 소스 내 백업 세션 통합)"""
        presets = {}

        if os.path.exists(self.presets_file):
            try:
                with open(self.presets_file, "r", encoding="utf-8") as f:
                    presets.update(json.load(f))
            except Exception:
                pass

        script_dir = os.path.dirname(os.path.abspath(__file__))
        local_presets_file = os.path.join(script_dir, "sessions", "session_presets.json")
        if os.path.exists(local_presets_file):
            try:
                with open(local_presets_file, "r", encoding="utf-8") as f:
                    local_data = json.load(f)
                    for k, v in local_data.items():
                        if k not in presets:
                            presets[k] = v
            except Exception:
                pass

        return presets

    def save_preset(self, session_id: str, target_type: str, target: str, quality: str, cnt: int, download_path: str):
        """세션 설정을 재사용 가능하게 프리셋으로 저장"""
        presets = self.load_all_presets()
        presets[session_id] = {
            "session_id": session_id,
            "target_type": target_type,
            "target": target,
            "quality": quality,
            "cnt": cnt,
            "download_path": download_path,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(self.presets_file, "w", encoding="utf-8") as f:
            json.dump(presets, f, ensure_ascii=False, indent=2)

    def list_presets(self) -> list:
        presets = self.load_all_presets()
        return list(presets.values())


class DownloadSession:
    """
    세션명 기반 폴더 관리 및 세션 수행 정보 기록 클래스
    """
    def __init__(self, session_name: str = None, download_path: str = None):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_id = session_name if session_name else f"SESSION_{self.timestamp}"
        self.start_time = time.time()
        
        if not download_path:
            download_path = os.path.join(os.path.expanduser("~"), "Downloads", "YouTube_Downloads")
        
        self.base_download_dir = os.path.abspath(download_path)
        # 세션명 기준 전용 폴더 생성: [다운로드 경로] > [세션명]
        self.session_dir = os.path.join(self.base_download_dir, self.session_id)
        os.makedirs(self.session_dir, exist_ok=True)

        self.manager = SessionManager(self.base_download_dir)
        self.summary = {
            "session_id": self.session_id,
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": None,
            "duration_seconds": 0,
            "target_type": None,
            "target": None,
            "quality": None,
            "requested_cnt": 0,
            "newly_downloaded_cnt": 0,
            "session_dir": self.session_dir,
            "status": "RUNNING"
        }

    def start_session(self, target_type: str, target: str, quality: str, cnt: int, save_as_preset: bool = True):
        self.summary["target_type"] = target_type
        self.summary["target"] = target
        self.summary["quality"] = quality
        self.summary["requested_cnt"] = cnt

        if save_as_preset:
            self.manager.save_preset(self.session_id, target_type, target, quality, cnt, self.base_download_dir)

        print("\n" + "=" * 65)
        print(f"🚀 작업 세션 시작: [{self.session_id}]")
        print(f"📅 시작 일시        : {self.summary['start_time']}")
        print(f"📌 구분 (type)         : {target_type}")
        print(f"🔗 대상 (target)       : {target}")
        print(f"🎵 음질 (quality)      : {quality}")
        print(f"🔢 보장 신규 건수(cnt) : {cnt}개")
        print(f"📁 세션 폴더 위치     : {self.session_dir}")
        print("=" * 65 + "\n")

    def end_session(self, downloaded_cnt: int = 0, success: bool = True, message: str = None):
        end_time = time.time()
        self.summary["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.summary["duration_seconds"] = round(end_time - self.start_time, 2)
        self.summary["newly_downloaded_cnt"] = downloaded_cnt
        self.summary["status"] = "COMPLETED" if success else "FAILED"
        if message:
            self.summary["message"] = message

        # 세션 폴더 바로 아래 세션 정보 저장: [세션 폴더]\session_info.json
        info_file = os.path.join(self.session_dir, "session_info.json")
        with open(info_file, "w", encoding="utf-8") as f:
            json.dump(self.summary, f, ensure_ascii=False, indent=2)

        print("\n" + "=" * 65)
        print(f"🏁 작업 세션 종료: [{self.session_id}]")
        print(f"⏱️ 총 소요 시간     : {self.summary['duration_seconds']}초")
        print(f"✨ 이번 신규 다운로드: {downloaded_cnt}건")
        print(f"상태                : {'✅ 완료' if success else '❌ 실패'}")
        if message:
            print(f"ℹ️ 세션 메시지      : {message}")
        print(f"📄 세션 정보 위치   : {info_file}")
        print("=" * 65 + "\n")

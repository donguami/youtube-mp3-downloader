import os
import sys
import argparse
from session_manager import DownloadSession, SessionManager
from utils import setup_utf8_encoding, install_and_import, get_history_ids, calculate_optimal_bitrate, check_and_update_ytdlp
from telegram_sender import send_telegram_audio

setup_utf8_encoding()

COMMON_EXTRACTOR_ARGS = {
    'youtube': {
        'player_client': ['android', 'ios', 'mweb', 'web'],
        'skip': ['hls', 'dash']
    }
}

def process_download(target_type: str, target: str, quality: str = "128k", cnt: int = 1, download_path: str = None, session_name: str = None, send_telegram: bool = False):
    """
    세션명 기반 폴더 관리 + 신규 다운로드 건수(cnt) 보장 + 재생시간 기반 최적 음질 산출 + 텔레그램 전송 다운로드 처리 함수
    """
    check_and_update_ytdlp()
    install_and_import("yt_dlp")
    import yt_dlp

    script_dir = os.path.dirname(os.path.abspath(__file__))

    if not download_path:
        download_path = os.path.join(os.path.expanduser("~"), "Downloads", "YouTube_Downloads")

    download_path = os.path.abspath(download_path)

    session = DownloadSession(session_name=session_name, download_path=download_path)
    session.start_session(
        target_type=target_type,
        target=target,
        quality=quality,
        cnt=cnt,
        save_as_preset=True
    )

    session_dir = session.session_dir
    history_file = os.path.join(session_dir, f"{session.session_id}_history.txt")

    if target_type.lower() == "channel":
        if target.startswith("http"):
            download_url = target if "/videos" in target else f"{target.rstrip('/')}/videos"
            clean_target = target.split("@")[-1].replace("/videos", "").strip() if "@" in target else "Channel_Downloads"
        else:
            clean_target = target.replace("https://www.youtube.com/", "").replace("@", "").replace("/videos", "").strip()
            download_url = f"https://www.youtube.com/@{clean_target}/videos"
        channel_folder_name = clean_target
    else:
        download_url = target
        channel_folder_name = "%(uploader,channel,Single_Downloads)s"

    output_template = os.path.join(session_dir, channel_folder_name, "%(upload_date)s_%(title)s.%(ext)s")

    history_ids = get_history_ids(history_file)

    print("🔍 신규 다운로드 대상 탐색 중 (기존 다운로드 항목 자동 제외)...", flush=True)
    
    flat_meta_opts = {
        'extract_flat': True,
        'quiet': True,
        'ignoreerrors': True,
        'extractor_args': COMMON_EXTRACTOR_ARGS
    }

    new_urls_to_process = []

    try:
        with yt_dlp.YoutubeDL(flat_meta_opts) as ydl:
            meta = ydl.extract_info(download_url, download=False)
            if meta:
                entries = meta.get('entries', []) if 'entries' in meta else [meta]
                
                for entry in entries:
                    if not entry:
                        continue
                    v_id = entry.get('id')
                    v_url = entry.get('url') or entry.get('webpage_url') or f"https://www.youtube.com/watch?v={v_id}"
                    
                    history_key = f"youtube {v_id}"
                    if v_id and (history_key in history_ids or v_id in history_ids):
                        continue
                    
                    new_urls_to_process.append(v_url)
                    if len(new_urls_to_process) >= int(cnt):
                        break
    except Exception as e:
        print(f"⚠️ 채널 목록 탐색 중 알림: {e}", flush=True)

    new_count = len(new_urls_to_process)

    if new_count == 0:
        print("\n" + "!" * 65)
        print("⚠️ 해당 채널/재생목록에 더 이상 다운로드할 새로운 영상이 없습니다.")
        print("!" * 65)
        session.end_session(downloaded_cnt=0, success=True, message="더 이상 다운로드할 새로운 영상이 없음")
        return

    print(f"✅ 신규 다운로드 대상 목록 확보 완료: 총 {new_count}개 확정 (요청: {cnt}개)", flush=True)

    downloaded_items = []

    try:
        single_meta_opts = {
            'quiet': True,
            'skip_download': True,
            'ignoreerrors': True,
            'extractor_args': COMMON_EXTRACTOR_ARGS
        }

        for v_url in new_urls_to_process:
            v_duration = 0
            v_title = "Audio"
            v_channel = clean_target if target_type == "channel" else "YouTube"

            try:
                with yt_dlp.YoutubeDL(single_meta_opts) as ydl:
                    info = ydl.extract_info(v_url, download=False)
                    if info:
                        v_duration = info.get('duration', 0)
                        v_title = info.get('title', v_title)
                        v_channel = info.get('uploader') or info.get('channel') or v_channel
            except Exception as e:
                print(f"⚠️ 메타데이터 미리보기 알림 ({v_url}): {e}", flush=True)

            optimal_quality = calculate_optimal_bitrate(v_duration, max_mb=45, user_quality=quality)

            ydl_opts = {
                'format': 'bestaudio/best',
                'ffmpeg_location': script_dir,
                'outtmpl': output_template,
                'download_archive': history_file,
                'ignoreerrors': True,
                'writethumbnail': True,
                'postprocessors': [
                    {
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': optimal_quality,
                    },
                    {
                        'key': 'FFmpegMetadata',
                        'add_metadata': True,
                    },
                    {
                        'key': 'EmbedThumbnail',
                        'already_have_thumbnail': False,
                    }
                ],
                'extractor_args': COMMON_EXTRACTOR_ARGS,
                'quiet': False,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                download_info = ydl.extract_info(v_url, download=True)
                if download_info:
                    mp3_filename = ydl.prepare_filename(download_info)
                    mp3_filepath = os.path.splitext(mp3_filename)[0] + ".mp3"
                    if os.path.exists(mp3_filepath):
                        downloaded_items.append({
                            'filepath': mp3_filepath,
                            'metadata': {
                                'title': v_title,
                                'channel': v_channel,
                                'duration': v_duration,
                                'quality': optimal_quality
                            }
                        })

        msg = None
        downloaded_count = len(downloaded_items)
        if downloaded_count > 0:
            session.end_session(downloaded_cnt=downloaded_count, success=True, message=msg)
            if send_telegram:
                print("\n[+] 텔레그램으로 MP3 파일 전송을 시작합니다...", flush=True)
                for item in downloaded_items:
                    send_telegram_audio(item['filepath'], metadata=item['metadata'])
        else:
            session.end_session(downloaded_cnt=0, success=False, message="MP3 변환된 파일을 찾을 수 없습니다.")

    except Exception as e:
        session.end_session(downloaded_cnt=0, success=False, message=str(e))

if __name__ == "__main__":
    is_interactive = len(sys.argv) == 1

    try:
        parser = argparse.ArgumentParser(description="세션 중심 폴더 & 50MB 맞춤 비트레이트 파이썬 유튜브 MP3 변환기")
        parser.add_argument("-t", "--type", choices=["channel", "url"], help="구분: channel 또는 url")
        parser.add_argument("-g", "--target", help="대상: 채널명(@채널명) 또는 영상/재생목록 URL")
        parser.add_argument("-q", "--quality", default="128k", help="기본 목표 음질: 128k, 192k, 320k 등 (기본값: 128k)")
        parser.add_argument("-c", "--cnt", type=int, default=1, help="신규 다운로드 보장 건수 (기본값: 1)")
        parser.add_argument("-p", "--path", help="다운로드 저장 경로 (기본값: 내 PC Downloads/YouTube_Downloads)")
        parser.add_argument("-s", "--session", help="세션 이름 지정")
        parser.add_argument("-tg", "--telegram", action="store_true", help="다운로드 후 텔레그램으로 MP3 파일 전송")
        parser.add_argument("-u", "--update", action="store_true", help="yt-dlp 최신 업데이트 강제 체크 및 설치")
        parser.add_argument("-l", "--list-sessions", action="store_true", help="저장된 작업 세션 목록 조회")

        args, unknown = parser.parse_known_args()

        if args.update:
            check_and_update_ytdlp(force=True)
            if not args.type and not args.target and not args.list_sessions:
                sys.exit(0)

        default_download_path = args.path if args.path else os.path.join(os.path.expanduser("~"), "Downloads", "YouTube_Downloads")
        manager = SessionManager(default_download_path)

        if args.list_sessions:
            presets = manager.list_presets()
            print("\n" + "=" * 65)
            print(f"📋 저장된 작업 세션 목록 (경로: {manager.presets_file})")
            print("=" * 65)
            if not presets:
                print("저장된 작업 세션이 없습니다.")
            else:
                for idx, p in enumerate(presets, 1):
                    print(f"[{idx}] 세션명: {p['session_id']}")
                    print(f"    - 구분: {p['target_type']} | 대상: {p['target']} | 음질: {p['quality']} | 신규건수: {p['cnt']}개")
                    print(f"    - 저장경로: {p['download_path']}")
            print("=" * 65 + "\n")
        else:
            if not args.type and len(sys.argv) > 1 and sys.argv[1].startswith("-") is False:
                args.type = sys.argv[1]
                args.target = sys.argv[2] if len(sys.argv) > 2 else ""
                args.quality = sys.argv[3] if len(sys.argv) > 3 else "128k"
                args.cnt = int(sys.argv[4]) if len(sys.argv) > 4 else 1
                args.path = sys.argv[5] if len(sys.argv) > 5 else None

            if not args.type or not args.target:
                presets = manager.list_presets()

                print("=" * 65)
                print(" 🎵 파이썬 유튜브 작업 세션 다운로더 (v2.6 봇 감지 방지 고속 버전)")
                print("=" * 65)

                if presets:
                    print("📋 저장된 세션 선택 또는 새 세션 생성:")
                    for idx, p in enumerate(presets, 1):
                        print(f"  [{idx}] {p['session_id']} (구분:{p['target_type']} | 대상:{p['target']} | 음질:{p['quality']} | 보장건수:{p['cnt']}개)")
                    print(f"  [{len(presets) + 1}] ➕ 새 작업 세션 생성")

                    sel = input(f"\n선택할 세션 번호를 입력하세요 (1~{len(presets) + 1}) [기본값: {len(presets) + 1}]: ").strip()
                    
                    if sel.isdigit() and 1 <= int(sel) <= len(presets):
                        selected_preset = presets[int(sel) - 1]
                        args.session = selected_preset["session_id"]
                        args.type = selected_preset["target_type"]
                        args.target = selected_preset["target"]
                        args.quality = selected_preset["quality"]
                        args.cnt = selected_preset["cnt"]
                        args.path = selected_preset["download_path"]

                if not args.type or not args.target:
                    type_input = input("\n1. 구분 선택 (1: channel / 2: url) [기본값: 1]: ").strip()
                    args.type = "url" if type_input == "2" or type_input.lower() == "url" else "channel"
                    
                    if args.type == "channel":
                        args.target = input("2. 채널명 또는 핸들 입력 (예: @지식해적단): ").strip()
                    else:
                        args.target = input("2. 영상 또는 재생목록 URL 입력: ").strip()

                    qual_input = input("3. 목표 기본 음질 입력 (128k, 192k, 320k 등) [기본값: 128k]: ").strip()
                    args.quality = qual_input if qual_input else "128k"

                    cnt_input = input("4. 신규 다운로드 보장 건수 (1~여러건) [기본값: 1]: ").strip()
                    args.cnt = int(cnt_input) if cnt_input.isdigit() else 1

                    path_input = input(f"5. 다운로드 경로 입력 [기본값: {default_download_path}]: ").strip()
                    args.path = path_input if path_input else default_download_path

                    sess_input = input("6. 작업 세션 이름 입력 (엔터 누르면 자동 생성): ").strip()
                    if sess_input:
                        args.session = sess_input

                    tg_input = input("7. 텔레그램으로 MP3 파일 전송 여부 (y/N) [기본값: n]: ").strip().lower()
                    if tg_input == 'y':
                        args.telegram = True

            if args.type and args.target:
                process_download(
                    target_type=args.type,
                    target=args.target,
                    quality=args.quality,
                    cnt=args.cnt,
                    download_path=args.path,
                    session_name=args.session,
                    send_telegram=args.telegram
                )
            else:
                print("⚠️ 대상(target)이 입력되지 않았습니다.")

    except Exception as e:
        print(f"\n❌ 실행 중 오류가 발생했습니다: {e}")

    finally:
        if is_interactive:
            input("\n[안내] 엔터(Enter) 키를 누르면 창이 닫힙니다...")

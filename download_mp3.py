import os
import sys
import argparse
from utils import setup_utf8_encoding, install_and_import, calculate_optimal_bitrate, check_and_update_ytdlp, setup_cookies_file, get_extractor_args
from telegram_sender import send_telegram_audio

setup_utf8_encoding()

def download_mp3(youtube_url, output_dir=None, quality='128', send_telegram=False):
    check_and_update_ytdlp()
    install_and_import("yt_dlp")
    import yt_dlp

    script_dir = os.path.dirname(os.path.abspath(__file__))

    if output_dir is None:
        output_dir = os.path.join(os.path.expanduser("~"), "Downloads")

    os.makedirs(output_dir, exist_ok=True)
    print(f"\n[+] 유튜브 정보 확인 및 최적 음질 산출 중: {youtube_url}", flush=True)
    print(f"📁 저장 위치: {output_dir}", flush=True)

    duration = 0
    title = "Audio"
    channel = "YouTube"

    cookie_file = setup_cookies_file()
    extractor_args = get_extractor_args(cookie_file)

    try:
        meta_opts = {
            'quiet': True,
            'skip_download': True,
            'extractor_args': extractor_args
        }

        with yt_dlp.YoutubeDL(meta_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            if info:
                duration = info.get('duration', 0)
                title = info.get('title', title)
                channel = info.get('uploader') or info.get('channel') or channel
    except Exception as e:
        print(f"⚠️ 영상 정보 미리보기 알림: {e}", flush=True)

    optimal_quality = calculate_optimal_bitrate(duration, max_mb=45, user_quality=quality)

    ydl_opts = {
        'format': '18/ba/b/best',
        'ffmpeg_location': script_dir,
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'writethumbnail': True,
        'ignoreerrors': True,
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
        'extractor_args': extractor_args,
        'quiet': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            download_info = ydl.extract_info(youtube_url, download=True)
            if download_info:
                mp3_filename = ydl.prepare_filename(download_info)
                mp3_filepath = os.path.splitext(mp3_filename)[0] + ".mp3"

        print("\n✅ MP3 변환 및 다운로드가 완료되었습니다!", flush=True)

        if send_telegram and os.path.exists(mp3_filepath):
            print("\n[+] 텔레그램으로 메타데이터 포함 MP3 파일 전송 시작...", flush=True)
            meta = {
                "title": title,
                "channel": channel,
                "duration": duration,
                "quality": optimal_quality
            }
            send_telegram_audio(mp3_filepath, metadata=meta)

    except Exception as e:
        print(f"\n❌ 다운로드 중 오류 발생: {e}", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="유튜브 MP3 다운로더 (50MB 맞춤 비트레이트 & 텔레그램 메타데이터 연동)")
    parser.add_argument("url", nargs="?", help="변환할 유튜브 URL")
    parser.add_argument("-q", "--quality", default="128", help="기본 목표 음질 (기본값: 128)")
    parser.add_argument("-o", "--output", help="저장 위치")
    parser.add_argument("-tg", "--telegram", action="store_true", help="다운로드 후 텔레그램으로 메타데이터와 파일 전송")
    parser.add_argument("-u", "--update", action="store_true", help="yt-dlp 최신 업데이트 강제 체크 및 설치")

    args = parser.parse_args()

    if args.update:
        check_and_update_ytdlp(force=True)
        if not args.url:
            sys.exit(0)

    url = args.url
    if not url:
        url = input("변환할 유튜브 URL을 입력하세요: ").strip()

    if url:
        send_tg = args.telegram
        if not args.telegram and len(sys.argv) == 1:
            tg_input = input("다운로드 후 텔레그램으로 MP3 파일을 보내시겠습니까? (y/N): ").strip().lower()
            send_tg = tg_input == 'y'

        download_mp3(url, output_dir=args.output, quality=args.quality, send_telegram=send_tg)
    else:
        print("URL이 입력되지 않았습니다.")

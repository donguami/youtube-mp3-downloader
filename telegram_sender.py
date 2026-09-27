import os
import sys
import json
import urllib3
from utils import setup_utf8_encoding, install_and_import, format_duration, log_event

setup_utf8_encoding()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "telegram_config.json")
DEFAULT_TOKEN = "8103893912:AAGAxjAqYHhNb-zo9Jj3cMtrwJOcK3Fe-Cs"

def load_config():
    # 1. 환경 변수 (GitHub Secrets 호환)
    env_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    env_chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    config = {"bot_token": env_token or DEFAULT_TOKEN, "chat_id": env_chat_id or ""}

    # 2. 로컬 telegram_config.json 파일
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                file_cfg = json.load(f)
                if not env_token and file_cfg.get("bot_token"):
                    config["bot_token"] = file_cfg["bot_token"]
                if not env_chat_id and file_cfg.get("chat_id"):
                    config["chat_id"] = file_cfg["chat_id"]
        except Exception:
            pass
    return config

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[!] Telegram 설정 저장 실패: {e}", flush=True)

def get_chat_id(token=None, prompt_if_missing=True):
    install_and_import("requests")
    import requests

    config = load_config()
    token = token or config.get("bot_token") or DEFAULT_TOKEN
    chat_id = config.get("chat_id")

    if chat_id:
        return str(chat_id)

    print("\n[+] Telegram chat_id 탐색 중...", flush=True)
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    
    try:
        resp = requests.get(url, verify=False, timeout=10)
        data = resp.json()
        if data.get("ok"):
            updates = data.get("result", [])
            for update in reversed(updates):
                msg = update.get("message") or update.get("channel_post") or update.get("my_chat_member")
                if msg and "chat" in msg:
                    found_id = str(msg["chat"]["id"])
                    user_name = msg["chat"].get("first_name") or msg["chat"].get("username") or "User"
                    print(f"[+] Telegram 수신 대상 감지 완료: {user_name} (chat_id: {found_id})", flush=True)
                    config["chat_id"] = found_id
                    config["bot_token"] = token
                    save_config(config)
                    return found_id
    except Exception as e:
        print(f"[!] getUpdates 조회 중 오류: {e}", flush=True)

    if prompt_if_missing:
        print("\n" + "!" * 65, flush=True)
        print("[!] 텔레그램 수신 대상(chat_id)을 찾지 못했습니다.", flush=True)
        print("1. 텔레그램 앱에서 @uguinn10_yt_down_bot 검색 후 들어갑니다.", flush=True)
        print("2. /start 버튼을 누르거나 아무 메시지나 전송해주세요.", flush=True)
        print("!" * 65, flush=True)
        
        user_input = input("\n메시지 전송 후 엔터(Enter) 키를 누르거나, chat_id를 직접 입력하세요: ").strip()
        if user_input.lstrip("-").isdigit():
            config["chat_id"] = user_input
            config["bot_token"] = token
            save_config(config)
            return user_input
        else:
            return get_chat_id(token, prompt_if_missing=False)
            
    return None

def send_telegram_message(text, token=None, chat_id=None):
    install_and_import("requests")
    import requests

    config = load_config()
    token = token or config.get("bot_token") or DEFAULT_TOKEN
    chat_id = chat_id or config.get("chat_id")

    if not chat_id:
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(url, data={'chat_id': chat_id, 'text': text}, verify=False, timeout=15)
        ok = resp.json().get("ok", False)
        log_event("MESSAGE", f"텔레그램 메시지 발송 ({'성공' if ok else '실패'}): {text}")
        return ok
    except Exception as e:
        print(f"[!] 메시지 발송 실패: {e}", flush=True)
        log_event("ERROR", f"텔레그램 메시지 발송 예외: {e}")
        return False

def format_metadata_caption(file_path, metadata=None):
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    file_name = os.path.basename(file_path)

    if not metadata:
        metadata = {}

    title = metadata.get("title") or os.path.splitext(file_name)[0]
    channel = metadata.get("channel") or metadata.get("uploader") or "알 수 없음"
    duration_str = format_duration(metadata.get("duration", 0))
    quality = metadata.get("quality") or "128"

    caption = (
        f"🎵 제목: {title}\n"
        f"📺 채널: {channel}\n"
        f"⏱️ 재생시간: {duration_str}\n"
        f"⚙️ 적용음질: {quality} kbps\n"
        f"💾 파일용량: {file_size_mb:.2f} MB\n"
        f"✅ 결과: 성공적으로 변환 및 전송됨"
    )
    return caption

def send_telegram_audio(file_path, metadata=None, caption=None, token=None, chat_id=None):
    install_and_import("requests")
    import requests

    file_name = os.path.basename(file_path) if os.path.exists(file_path) else str(file_path)

    config = load_config()
    token = token or config.get("bot_token") or DEFAULT_TOKEN
    chat_id = chat_id or config.get("chat_id") or get_chat_id(token)

    if not chat_id:
        err_msg = "[-] Telegram chat_id가 설정되지 않아 전송할 수 없습니다."
        print(err_msg, flush=True)
        log_event("FAILED", f"Chat ID 미설정으로 전송 취소: {file_name}", metadata)
        return False

    if not os.path.exists(file_path):
        err_msg = f"❌ [전송 실패] 전송할 파일이 존재하지 않습니다: {file_name}"
        print(err_msg, flush=True)
        log_event("FAILED", f"파일 미존재: {file_name}", metadata)
        send_telegram_message(err_msg, token=token, chat_id=chat_id)
        return False

    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)

    if file_size_mb > 50.0:
        err_msg = f"❌ [전송 실패] 파일 용량({file_size_mb:.2f}MB)이 텔레그램 봇 업로드 제한(50MB)을 초과했습니다."
        print(err_msg, flush=True)
        log_event("FAILED", f"50MB 용량 초과 ({file_size_mb:.2f}MB): {file_name}", metadata)
        send_telegram_message(err_msg, token=token, chat_id=chat_id)
        return False

    final_caption = caption or format_metadata_caption(file_path, metadata)

    print(f"\n[+] 텔레그램으로 MP3 파일 및 메타데이터 전송 중 ({file_size_mb:.2f}MB)...", flush=True)

    url = f"https://api.telegram.org/bot{token}/sendAudio"
    data = {'chat_id': chat_id, 'caption': final_caption}

    try:
        with open(file_path, 'rb') as f:
            files = {'audio': (file_name, f, 'audio/mpeg')}
            resp = requests.post(url, data=data, files=files, verify=False, timeout=600)
            res_data = resp.json()

            if res_data.get("ok"):
                print(f"[+] 텔레그램 전송 성공! ({file_name})", flush=True)
                log_event("SUCCESS", f"텔레그램 전송 성공 ({file_name}, {file_size_mb:.2f}MB)", metadata)
                return True
            else:
                fail_reason = res_data.get("description", str(res_data))
                err_msg = f"❌ [전송 실패] 텔레그램 API 오류: {fail_reason}\n📄 파일명: {file_name}"
                print(err_msg, flush=True)
                log_event("FAILED", f"텔레그램 API 오류: {fail_reason} ({file_name})", metadata)
                send_telegram_message(err_msg, token=token, chat_id=chat_id)
                return False
    except Exception as e:
        err_msg = f"❌ [전송 실패] 업로드 중 예외 발생: {e}\n📄 파일명: {file_name}"
        print(err_msg, flush=True)
        log_event("FAILED", f"업로드 중 예외 발생: {e} ({file_name})", metadata)
        send_telegram_message(err_msg, token=token, chat_id=chat_id)
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
        send_telegram_audio(target_file)
    else:
        print("텔레그램 연동 테스트를 진행합니다.", flush=True)
        cid = get_chat_id()
        if cid:
            print(f"현재 등록된 Chat ID: {cid}", flush=True)

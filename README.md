# 🎵 유튜브 MP3 변환기 v2.5 (GitHub Actions 클라우드 자동 감시 지원)

`E:\projects\mp3_downloader`에 위치한 유튜브 MP3 자동 다운로더 및 텔레그램 발송 시스템입니다.

---

## 🤖 GitHub Actions 클라우드 자동 감시 설정 (PC 꺼두어도 작동!)

GitHub 클라우드 서버에서 매일 지정된 시간에 자동으로 채널을 감시하여 새 영상 MP3를 텔레그램으로 전송합니다.

### 📌 1단계: GitHub Secrets 등록
GitHub 저장소의 **Settings ➔ Secrets and variables ➔ Actions** 메뉴에서 다음 2개의 Secret을 추가합니다:
- **`TELEGRAM_BOT_TOKEN`**: `8103893912:AAGAxjAqYHhNb-zo9Jj3cMtrwJOcK3Fe-Cs`
- **`TELEGRAM_CHAT_ID`**: `8530929852`

### 📌 2단계: 감시 채널 설정 (`watched_channels.json`)
[watched_channels.json](file:///E:/projects/mp3_downloader/watched_channels.json) 파일에 자동 감시할 유튜브 채널을 등록합니다:
```json
[
  {
    "name": "지식해적단",
    "target": "@지식해적단",
    "quality": "128k",
    "cnt": 1
  }
]
```

### 📌 3단계: 자동 동작 방식
- 매일 **오전 9시 / 오후 9시 (하루 2회)** GitHub 서버가 자동 실행됩니다.
- 신규 업로드 영상이 감지되면 MP3로 변환 후 텔레그램 대화방으로 즉시 발송합니다.
- 다운로드 히스토리가 Git에 자동 커밋되어 **중복 다운로드가 100% 방지**됩니다.

---

## 📁 디렉토리 구조

```text
E:\projects\mp3_downloader\
├── .github/workflows/monitor.yml     <-- [GitHub Actions 자동화 워크플로우]
├── watched_channels.json              <-- [자동 감시 대상 채널 목록]
├── run_watched_channels.py            <-- [감시 목록 일괄 순회 스크립트]
├── download_channel.py                <-- [채널/세션 다운로더]
├── download_mp3.py                    <-- [단일 URL 전용 다운로더]
├── telegram_sender.py                 <-- [텔레그램 전송 모듈 (환경변수/Secrets 지원)]
├── utils.py                           <-- [공통 모듈]
├── telegram_config.json               <-- [로컬 텔레그램 설정]
└── download_history.log               <-- [통합 실행 및 전송 로그]
```

---

## 🚀 로컬 사용법 및 명령어 예시

### 1. 감시 채널 목록 일괄 수동 실행
```bash
python run_watched_channels.py
```

### 2. 개별 명령어 실행 (`-tg` 옵션)
```bash
# 단일 영상 다운로드 및 텔레그램 전송
python download_mp3.py "https://www.youtube.com/watch?v=XXXXXX" -tg

# yt-dlp 최신 버전 업데이트 강제 체크
python download_mp3.py -u
```

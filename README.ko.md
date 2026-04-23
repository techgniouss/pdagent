# Pocket Desk Agent

<p align="center">
  <a href="https://pypi.org/project/pocket-desk-agent/"><img src="https://img.shields.io/pypi/v/pocket-desk-agent.svg?style=for-the-badge&color=3776AB" alt="PyPI" /></a>
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Gemini-2.0_Flash-4285F4?style=for-the-badge&logo=google-gemini&logoColor=white" alt="Gemini" />
  <img src="https://img.shields.io/badge/Windows-지원-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows" />
  <img src="https://img.shields.io/badge/라이선스-MIT-yellow.svg?style=for-the-badge" alt="라이선스" />
</p>

<p align="center"><strong>PC를 주머니 속에 — 원격 제어, AI 자동화, 개발 도구 — 모두 Telegram으로.</strong></p>

<p align="center">
  <a href="docs/COMMANDS.md">명령어</a> •
  <a href="docs/LOCAL_DEVELOPMENT.md">개발</a> •
  <a href="CONTRIBUTING.md">기여</a> •
  <a href="SECURITY.md">보안</a>
</p>

<p align="center">
  <a href="README.md">English</a> •
  <a href="README.zh-CN.md">中文</a> •
  <a href="README.ru.md">Русский</a> •
  <a href="README.es.md">Español</a> •
  <a href="README.de.md">Deutsch</a> •
  <a href="README.fr.md">Français</a> •
  <a href="README.ja.md">日本語</a> •
  <a href="README.pt-BR.md">Português</a> •
  <a href="README.ko.md"><strong>한국어</strong></a> •
  <a href="README.tr.md">Türkçe</a> •
  <a href="README.uk.md">Українська</a>
</p>

**Pocket Desk Agent**는 어떤 기기에서든 Windows PC를 완전히 원격 제어할 수 있는 자체 호스팅 Telegram 봇입니다. 완전히 로컬 머신에서 실행되며, 클라우드 릴레이나 구독이 필요 없습니다. Telegram 메시지 릴레이와 선택적 Gemini API 외에는 네트워크를 벗어나는 데이터가 없습니다.

AI 설정 없이 즉시 사용 가능한 기능:
- **파일 탐색 및 읽기** — 승인된 디렉토리 내에서
- **데스크톱 제어** — 스크린샷, 키보드 단축키, 클립보드, 창 전환, 절전, 종료
- **UI 자동화** — OCR 클릭(Tesseract)과 요소 감지(OpenCV)
- **Claude Desktop과 VS Code 원격 제어** — 키보드를 건드리지 않고
- **매크로 녹화** — 다단계 워크플로우를 단일 명령으로 재생
- **작업 예약** — 재시작 후에도 유지
- **Android APK 빌드 및 전달** — React Native 프로젝트에서 Telegram으로

**Google Gemini 2.0 Flash** 자격 증명 추가 시 해제되는 기능:
- **대화형 AI 채팅** — 멀티턴 기억과 이미지 분석
- **에이전트 컴퓨터 제어** — Gemini가 파일 탐색, 스크린샷, 클릭, 입력, 자연어로 PC 자동화 수행. 파괴적 작업에는 인간 확인 필요
- **프롬프트 향상** `/enhance` 명령어

---

## 주요 기능

아래 모든 기능은 AI 설정 없이 작동합니다:

- **파일 시스템 탐색기**: 승인된 경로 내에서 스마트폰으로 PC 파일 탐색, 읽기, 검색.
- **데스크톱 제어**: 스크린샷, 키보드 단축키, 클립보드, 창 관리, 배터리 상태, 절전/종료.
- **비전 및 UI 자동화**: Tesseract OCR 클릭, OpenCV 요소 감지.
- **매크로 녹화**: 다단계 시퀀스 녹화 후 단일 명령으로 재생.
- **Claude Desktop 연동**: 원격 제어 — 프롬프트 전송, 모델 전환, 워크스페이스 관리.
- **VS Code / Antigravity 연동**: 폴더 열기, AI 모델 전환, Antigravity 확장 제어.
- **작업 스케줄러**: 지정된 시간에 자동화 또는 Claude 프롬프트 실행. 재시작 후에도 유지.
- **빌드 자동화**: React Native Android 빌드 트리거 및 Telegram으로 APK 수신.
- **자동 업데이트**: 봇이 업데이트를 확인하고 적용 가능.
- **경량**: 유휴 시 RAM ~55-70 MB, CPU <0.5%. 무거운 의존성은 필요할 때만 로드.

**선택 사항 — Google Gemini 자격 증명 필요:**

- **AI 채팅 및 컴퓨터 제어**: Gemini 2.0 Flash로 멀티턴 대화, 이미지 분석, 도구 호출. 파괴적 작업은 Telegram 인라인 버튼으로 명시적 확인 필요.
- **프롬프트 향상**: `/enhance`로 Gemini가 프롬프트를 재작성하고 개선.

---

## 작동 방식

Pocket Desk Agent는 Windows PC의 로컬 프로세스로 실행되며 Long-Polling으로 **아웃바운드** 연결합니다. 포트 포워딩, 라우터 설정, 동적 DNS가 필요 없습니다.

```
내 전화 → Telegram 서버 → (아웃바운드 폴링) → Pocket Desk Agent (로컬) → PC 동작 → 응답
```

**주요 내부 컴포넌트:**

| 컴포넌트 | 역할 |
| :--- | :--- |
| `python-telegram-bot` | 비동기 Telegram 클라이언트 |
| `GeminiClient` | Gemini API 세션 및 대화 기록 관리 |
| `FileManager` | 샌드박스 파일 I/O — 경로 검증 |
| `AuthManager` | Antigravity, Gemini CLI, API 키용 멀티 프로바이더 OAuth |
| `SchedulerRegistry` | 디스크에 작업 영속화, 60초마다 확인 |
| `RateLimiter` | 명령어당 사용자별 토큰 버킷 속도 제한기 |

---

## 플랫폼 호환성

| 기능 | Windows | macOS / Linux |
| :--- | :---: | :---: |
| 파일 시스템 | ✅ | ✅ |
| AI 채팅 (Gemini) | ✅ | ✅ |
| 작업 예약 | ✅ | ✅ |
| 스크린샷 | ✅ | ✅ |
| 키보드 단축키 | ✅ | ⚠️ 부분 지원 |
| 클립보드 | ✅ | ⚠️ 부분 지원 |
| UI 자동화 (OCR) | ✅ | ❌ |
| 창 관리 | ✅ | ❌ |
| Claude Desktop 연동 | ✅ | ❌ |
| VS Code 연동 | ✅ | ❌ |
| APK 빌드 | ✅ | ❌ |
| 로그인 후 자동 시작 | ✅ | ❌ |

---

## 시작하기 전에

### 1. Telegram 봇 생성

1. Telegram을 열고 **[@BotFather](https://t.me/BotFather)**에 메시지 전송
2. `/newbot` 전송 후 안내에 따라 진행
3. **봇 토큰** 복사 — 이것이 `TELEGRAM_BOT_TOKEN`

### 2. Telegram 사용자 ID 획득

1. Telegram에서 **[@userinfobot](https://t.me/userinfobot)**에 메시지 전송
2. 숫자 ID가 응답으로 옴 — 이것이 `AUTHORIZED_USER_IDS`

### 3. (선택) Google / Gemini 자격 증명

AI 채팅, 이미지 분석, `/enhance` 명령어에만 필요합니다.

**옵션 A — OAuth (권장):** 내장 OAuth 지원, 별도 GCP 프로젝트 불필요. 설정 시 **Antigravity OAuth** 또는 **Gemini CLI OAuth** 선택.

**옵션 B — API 키:**
1. [Google AI Studio](https://aistudio.google.com/app/apikey) 접속
2. API 키 생성 — 이것이 `GOOGLE_API_KEY`

---

## 빠른 시작 및 설치

### 시스템 요구 사항

- **Python 3.11+**
- **Windows 10 이상** — UI 자동화 기능에 필요
- **Tesseract OCR** — `/findtext`, `/smartclick`용. `pdagent setup`으로 설치
- **Visual C++ 재배포 가능 패키지** — 보통 이미 설치되어 있음

### 옵션 A: PyPI에서 설치 (권장)

```bash
pip install pocket-desk-agent
pdagent
```

첫 실행 시 `pdagent`가 대화형 설정 마법사를 시작합니다.

```bash
pdagent start        # 백그라운드 데몬으로 실행
pdagent configure    # 설정 마법사 다시 실행
pdagent setup        # 시스템 의존성 확인 및 설치
```

### 옵션 B: 로컬 개발자 모드

```bash
git clone https://github.com/techgniouss/pocket-desk-agent.git
cd pocket-desk-agent
pip install -e ".[dev]"
pdagent
```

---

## 봇 실행

| 명령어 | 설명 |
| :--- | :--- |
| `pdagent` | 포어그라운드에서 실행 |
| `pdagent start` | 백그라운드 데몬으로 시작 |
| `pdagent stop` | 데몬 중지 |
| `pdagent restart` | 데몬 재시작 |
| `pdagent status` | 데몬 상태 확인 |
| `pdagent configure` | 설정 마법사 |
| `pdagent setup` | Check and install system dependencies (for example Tesseract OCR) |
| `pdagent startup <enable\|disable\|status\|configure>` | Manage automatic startup after Windows login |
| `pdagent auth` | Gemini 자격 증명 관리 |
| `pdagent version` | 설치된 버전 |

---

## 보안

자세한 보안 정보는 **[SECURITY.md](SECURITY.md)**를 참조하세요.

---

## 문제 해결

**봇이 시작되지만 메시지에 응답하지 않음**
- `AUTHORIZED_USER_IDS`에 Telegram ID가 있는지 확인
- 작업 디렉토리의 `bot.log` 에서 오류 확인
- `/status`로 Gemini 연결 확인

**`/findtext` 또는 `/smartclick`이 오류 반환**
- Tesseract OCR이 설치되지 않았거나 PATH에 없음
- `pdagent setup` 실행 또는 수동 설치: `winget install UB-Mannheim.TesseractOCR`

**Gemini 인증 실패**
- `pdagent auth` 실행 후 "로그인" 선택, 또는 Telegram에서 `/login` 사용
- OAuth: 포트 `51121`이 방화벽에 차단되지 않았는지 확인

---

**파일 작업이 "Access denied" 또는 "Path not allowed"로 실패함**
- 요청된 경로가 `APPROVED_DIRECTORIES` 범위를 벗어났습니다.
- `pdagent configure`를 실행하고 **2) Approved Directories**를 선택한 다음, 기존 목록을 변경하지 않고 **A** 옵션을 사용하여 단일 경로를 추가하십시오.
- 또는 구성을 직접 편집하십시오: `APPROVED_DIRECTORIES="C:\Users\사용자이름\Documents,C:\projects"` (쉼표로 구분된 절대 경로).
- 참고: `CLAUDE_DEFAULT_REPO_PATH`는 `APPROVED_DIRECTORIES`에 나열되지 않더라도 런타임에 **항상** 샌드박스에 추가됩니다.

**예약된 작업이 실행되지 않음**
- 예약된 시간이 되었을 때 봇이 실행 중이어야 합니다. 봇이 중지된 경우 작업이 호출되지 않습니다.
- `/listschedules`를 실행하여 작업이 대기 중인지와 시간 형식(24시간제 `HH:MM`)이 올바른지 확인하십시오.
- 스케줄러 오류는 `LOG_LEVEL=DEBUG` 출력을 확인하십시오.

## 기여

개발 설정, 코딩 표준, 새 명령어 추가 방법은 [CONTRIBUTING.md](CONTRIBUTING.md)를 참조하세요.

---

## 라이선스

MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE)를 참조하세요.

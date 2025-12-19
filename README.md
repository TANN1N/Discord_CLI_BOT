# Discord CLI Bot

터미널 환경에서 실시간으로 디스코드 메시지를 확인하고, 명령어를 통해 상호작용할 수 있는 CLI(Command-Line Interface) 기반 디스코드 봇입니다.

## 주요 기능

-   CLI를 통한 서버 및 채널 간 이동
-   실시간으로 새로운 메시지 수신 및 다른 채널의 활동 알림
-   현재 채널의 최근 메시지 조회
-   텍스트 메시지 및 파일 전송
-   텍스트 메시지의 수정 및 삭제
-   여러 줄 메시지 입력 지원
-   파일 기반 로깅 시스템을 통한 실행 기록 관리

## 아키텍처

이 프로젝트는 **MVC-S (Model-View-Controller-Service)** 패턴과 **TUI(Text-based User Interface)**, **이벤트 기반(Event-Driven)** 구조를 채택하여 각 컴포넌트의 역할을 명확히 분리하고 결합도를 낮췄습니다.

-   **Model (`models/app_state.py`)**: 애플리케이션의 상태(현재 서버/채널, 메시지 목록 등)를 관리하는 데이터 클래스입니다.
-   **View (`views/tui_view.py`)**: 사용자에게 보여지는 TUI 화면을 렌더링하고, 사용자 입력을 받아 Controller에 전달합니다. `prompt_toolkit`을 사용하여 TUI 환경을 구성합니다.
    - **`states`**: TUI 환경을 구성하는 데 필요한 상태를 state pattern으로 분리했습니다.
-   **Controller (`controllers/command_controller.py`)**: `/help`, `/setguild` 등과 같은 사용자 명령어를 해석하고, 이에 맞는 비즈니스 로직을 Service에 요청하는 역할을 합니다.
-   **Service (`services/bot_service.py`)**: Discord API와 직접 통신하며 봇의 핵심 비즈니스 로직(메시지 전송, 채널 목록 조회 등)을 수행합니다.
-   **Core System (`core/`)**:
    -   **`event_manager.py`**: 컴포넌트 간의 통신을 담당하는 이벤트 발행/구독 시스템입니다.
    -   **`logger.py`**: 파일 기반 로깅을 설정하고 관리합니다. 시스템의 모든 동작과 오류는 `logs/` 디렉터리에 타임스탬프 형식의 파일로 기록됩니다.

### 프로젝트 구조

```
discord_cli_bot/
├── main.py                     # 애플리케이션 초기화 및 실행
├── .env                        # 환경 변수 (봇 토큰, 로그 레벨) 설정
├── logs/                       # 로그 파일 저장 디렉터리
├── models/
│   └── app_state.py            # (M) 애플리케이션 상태 모델
├── views/
│   └── tui_view.py             # (V) TUI 사용자 인터페이스
│   └── states/                 # TUI 구성에 필요한 state classs
├── controllers/
│   └── command_controller.py   # (C) 사용자 명령어 처리
├── services/
│   └── bot_service.py          # (S) 비즈니스 로직 및 Discord API 연동
├── core/
│   ├── event_manager.py        # 이벤트 발행/구독 시스템
│   ├── event_types.py          # 이벤트 타입 정의
│   └── logger.py               # 로깅 시스템 설정
└── cogs/
    └── chatbridge.py           # Discord 이벤트(on_ready, on_message)를 내부 이벤트 시스템으로 연결
```

## 설치 및 실행

### 1. 필수 라이브러리 설치
먼저, 프로젝트에 필요한 모든 라이브러리를 `requirements.txt` 파일을 사용하여 한 번에 설치합니다.

```bash
pip install -r requirements.txt
```

-   **`discord.py`**: Discord API와 상호작용하는 비동기 라이브러리
-   **`python-dotenv`**: `.env` 파일에서 환경 변수를 로드
-   **`prompt_toolkit`**: 향상된 CLI/TUI 환경을 제공
-   **`aiohttp`**: `discord.py`가 내부적으로 사용하는 비동기 HTTP 클라이언트. 또한 파일 다운로드에 사용됩니다. 
-   **`aiofiles`**: 비동기적으로 파일을 읽고 쓸 때 사용됩니다. 

### 2. 환경 변수 설정 (`.env` 파일)

프로젝트 루트 디렉터리에 `.env` 파일을 생성하고, 아래 내용을 추가하세요.

```dotenv
# Discord Developer Portal에서 발급받은 봇 토큰
DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN_HERE

# 로그 레벨 설정 (DEBUG, INFO, WARNING, ERROR, CRITICAL) - 선택 사항, 기본값: INFO
LOG_LEVEL=INFO
```

> **주의**: 봇이 서버에 참여해 있고, 채널을 보고 메시지를 읽고 쓸 수 있는 권한을 가지고 있는지 확인하세요.

### 3. 봇 실행

```bash
python main.py
```

봇이 실행되면, CLI 환경에서 서버와 채널을 순서대로 선택하라는 안내가 나옵니다. 설정이 완료되면 프롬프트가 활성화되어 메시지를 보내거나 명령어를 사용할 수 있습니다. 모든 실행 기록은 `logs/` 폴더에 저장됩니다.

## 주요 명령어

-   `/help` (`/h`): 사용 가능한 모든 명령어 목록을 봅니다.
-   `/listguilds` (`/lg`): 봇이 참여 중인 서버 목록을 봅니다.
-   `/setguild <index|id|name>` (`/sg`): 현재 서버를 변경합니다.
-   `/listchannels` (`/lc`): 현재 서버의 채널 목록을 봅니다.
-   `/setchannel <index|id|name>` (`/sc`): 현재 채널을 변경합니다.
-   `/read [count]` (`/r`): 현재 채널의 최근 메시지를 지정된 수만큼 읽어옵니다. (기본값: 20)
-   `/self_messages [count]` (`/sm`): 현재 채널에서 자신의 최근 메시지를 지정된 수만큼 읽어옵니다. (기본값: 50) 
-   `/delete <index>` (`/d`): 자신의 최근 메시지를 삭제합니다. (기본 인덱스: 0)
-   `/edit <index>` (`/e`): 자신의 최근 메시지를 수정합니다. (기본 인덱스: 0)
-   `/multiline` (`/ml`): 여러 줄의 메시지를 입력하는 모드로 전환합니다.
-   `/attach <path> [caption]` (`/a`): 파일을 첨부하여 전송합니다.
-   `/files` (`/f`): 현재 채널의 최근 파일 목록을 표시합니다. (기본 50개 메시지 스캔)
-   `/download` (`/dl`): `/files`를 통해 캐시된 파일 목록에서 인덱스를 사용하여 파일을 다운로드 합니다.
-   `/clear` (`/cls`): 터미널 화면을 지웁니다.
-   `/quit`: 봇을 종료합니다.
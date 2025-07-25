# Discord CLI Bot
A terminal-based Discord bot that displays real-time messages and allows message sending through command-line interface.

## 주요 기능

- CLI를 통한 서버 및 채널 간 이동
- 실시간으로 새로운 메시지 수신 및 알림
- 현재 채널의 최근 메시지 조회
- 텍스트 메시지 및 파일 전송
- 여러 줄 메시지 입력 지원

### 추가될 기능

- 파일 다운로드
- 로그 출력 및 저장
- CLI -> TUI 전환

## 아키텍처

이 프로젝트는 MVC-S (Model-View-Controller-Service) 패턴과 이벤트 기반(Event-Driven, Pub-Sub) 구조를 채택하여 각 컴포넌트의 역할을 명확히 분리하고 결합도를 낮췄습니다.

각 컴포넌트의 재사용성을 높이고 대체할 수 있게 함으로써 CLI에서 TUI로 전환하거나 유지보수하기 쉽게 설계했습니다.

- Model (models/app_state.py): 애플리케이션의 상태(현재 서버/채널, 메시지 목록 등)을 관리하는 데이터 클래스입니다.
- View (views/cli_view.py): 사용자에게 보여지는 CLI 화면을 렌더링하고, 사용자 입력을 바아 Controller에 전달합니다. 추후 tui_view.py 등으로 변경할 수 있습니다.
- Controller (controllers/command_controller.py): `/help`, `/setguild` 등의 사용자 명령어를 해석하고, 이에 맞는 비즈니스 로직을 Service에 요청합니다.
- Service (services/bot_service.py): Discord API와 직접 통신하며 봇의 핵심 비즈니스 로직을 수행합니다. 
- Event Ststem (core/): EventManager를 통해 컴포넌트 간의 통신을 중개합니다. 이벤트를 발행하고 구독하는 Publish-Subscribe 패턴을 채용하여 각 컴포넌트가 직접적인 참조 없이 상호작용 할 수 있게 합니다. 

### 프로젝트 파일 구조

봇은 다음과 같은 디렉토리 구조를 가지고 있습니다.

```
discord_cli_bot/
├── main.py               # 봇의 메인 실행 파일 및 CLI 루프
├── models/               # (M) 애플리케이션 상태 모델
│   ├── app_state.py
├── views/                # (V) 사용자 인터페이스
│   ├── cli_view.py
├── controllers/          # (C) 사용자 명령어 처리
│   ├── cli_view.py
├── services/             # (S) 비즈니스 로직 및 Discord API 상호작용
│   └── bot_service.py
├── core/                 # (S) 비즈니스 로직 및 Discord API 상호작용
│   └── event_manager.py  # 이벤트 발행/구독 시스템
│   └── event_types.py   # 이벤트 타입 정의
├── cogs/                 # 봇의 기능(Cog)들을 모아두는 디렉토리
     └── chatbridge.py     # Discord 이벤트(on_ready, on_message)를 내부 이벤트 시스템에 연결
```

-----

## 프로젝트 설정 및 실행 가이드

이 봇은 Discord API를 사용하여 CLI (Command Line Interface) 환경에서 Discord와 상호작용할 수 있게 해줍니다. 봇을 실행하기 위해 필요한 모듈 설치 및 환경 설정 방법을 안내합니다.

-----

### 1\. 필수 Python 모듈 설치

```bash
pip install discord.py python-dotenv prompt_toolkit aiohttp
```

  * **`discord.py`**: Discord API와 상호작용 하는 비동기 Python 라이브러리입니다.
  * **`python-dotenv`**: `.env` 파일에 저장된 환경 변수를 안전하게 로드하는 데 필요합니다.
  * **`prompt_toolkit`**: 고급 CLI 기능(예: 명령줄 편집)을 제공하는 데 사용됩니다.
  * **`aiohtttp`**: 비동기 HTTP 요청을 처리하며, 특히 파일 다운로드에 사용됩니다.

-----

### 2\. Discord 봇 토큰 설정 (`.env` 파일)

봇이 Discord에 로그인하려면 **봇 토큰**이 필요합니다. 이 토큰은 **매우** 중요하며 **절대** 외부에 노출되지 않도록 `.env` 파일에 저장하여 관리하는 것이 가장 안전합니다.

1.  **`.env` 파일 생성**: 프로젝트의 루트 디렉토리에 `.env` 파일을 생성하세요.

2.  **봇 토큰 추가**: 생성한 `.env` 파일에 다음 형식으로 Discord 봇 토큰을 추가합니다. `YOUR_DISCORD_BOT_TOKEN_HERE` 부분을 실제 봇 토큰으로 교체하세요.

    ```dotenv
    DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN_HERE
    ```

      * **봇 토큰 얻는 방법**:
        1.  [Discord Developer Portal](https://discord.com/developers/applications)에 접속하여 애플리케이션을 선택하거나 새로 만듭니다.
        2.  왼쪽 메뉴에서 **Bot** 탭을 클릭합니다.
        3.  **Add Bot** 버튼을 클릭하여 봇을 생성합니다.
        4.  **TOKEN** 섹션에서 **Reset Token**을 클릭하고 토큰을 복사합니다. 이 토큰은 **반드시** 외부에 유출되지 않도록 주의해야 합니다.

3. **대상 서버에 봇 초대**: 생성한 디스코드 봇을 사용하고자 하는 Discord 서버에 초대해야 합니다.

    - 봇 초대 링크 생성: [Discord Developer Portal](https://discord.com/developers/applications)의 Bot 탭에서 OAuth2 탭으로 이동합니다. SCOPES에서 `bot`을 선택하고, 필요한 BOT PERMISSIONS (예: Send Messages, Read Message History, View Channels 등)를 선택한 후 생성된 URL을 통해 봇을 서버에 초대합니다.

    - **주의**: 봇이 서버에 참여해 있고, 채널을 보고 메시지를 읽고 쓸 수 있는 권한을 가지고 있는지 확인하세요. 

-----

### 3\. 봇 실행 방법

모든 설정이 완료되었다면, 터미널 또는 명령 프롬프트에서 `main.py` 파일을 실행하여 봇을 시작할 수 있습니다.

```bash
python main.py
```

봇이 성공적으로 연결되면, 서버와 채널을 선택하라는 초기 설정 메시지가 나타나고, 이후 CLI를 통해 Discord와 상호작용할 수 있게 됩니다.

### 4\. 명령어 목록

 -   `/help` (`/h`): 사용 가능한 모든 명령어 목록을 봅니다.
 -   `/listguilds` (`/lg`): 봇이 참여 중인 서버 목록을 봅니다.
 -   `/setguild <index|id|name>` (`/sg`): 현재 서버를 변경합니다.
 -   `/listchannels` (`/lc`): 현재 서버의 채널 목록을 봅니다.
 -   `/setchannel <index|id|name>` (`/sc`): 현재 채널을 변경합니다.
 -   `/read [count]` (`/r`): 현재 채널의 최근 메시지를 지정된 수만큼 읽어옵니다. (기본값: 20)
 -   `/multiline` (`/ml`): 여러 줄의 메시지를 입력하는 모드로 전환합니다.
 -   `/attach <path> [caption]` (`/a`): 파일을 첨부하여 전송합니다.
 -   `/clear` (`/cls`): 터미널 화면을 지웁니다.
 -   `/quit`: 봇을 종료합니다.

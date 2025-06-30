# Discord CLI Bot
A terminal-based Discord bot that displays real-time messages and allows message sending through command-line interface.

## 프로젝트 설정 및 실행 가이드

이 봇은 Discord API를 사용하여 CLI (Command Line Interface) 환경에서 Discord와 상호작용할 수 있게 해줍니다. 봇을 실행하기 위해 필요한 모듈 설치 및 환경 설정 방법을 안내합니다.

### 1\. 프로젝트 파일 구조

봇은 다음과 같은 디렉토리 구조를 가지고 있습니다.

```
your_bot_project/
├── .env                  # Discord 봇 토큰 저장
├── main.py               # 봇의 메인 실행 파일 및 CLI 루프
├── cogs/                 # 봇의 기능(Cog)들을 모아두는 디렉토리
│   └── chatbridge.py     # Discord 메시지 및 채널 관리 기능
└── cli/                  # CLI 명령어 처리 로직을 모아두는 디렉토리
    └── cli_handler.py    # CLI 명령어 파싱 및 실행 핸들러
```

-----

### 2\. 필수 Python 모듈 설치

프로젝트에 필요한 모든 라이브러리는 `pip`를 통해 설치할 수 있습니다. 터미널 또는 명령 프롬프트에서 다음 명령어를 실행하세요.

```bash
pip install discord.py python-dotenv prompt_toolkit
```

  * **`discord.py`**: Discord API와 상호작용하는 데 사용되는 비동기 Python 라이브러리입니다.
  * **`python-dotenv`**: `.env` 파일에 저장된 환경 변수를 안전하게 로드하는 데 필요합니다.
  * **`prompt_toolkit`**: 고급 CLI 기능(예: 명령줄 편집, 자동 완성)을 제공하는 데 사용됩니다.

-----

### 3\. Discord 봇 토큰 설정 (`.env` 파일)

봇이 Discord에 로그인하려면 **봇 토큰**이 필요합니다. 이 토큰은 **매우** 중요하며 **절대** 외부에 노출되지 않도록 `.env` 파일에 저장하여 관리하는 것이 가장 안전합니다.

1.  **`.env` 파일 생성**: 프로젝트의 루트 디렉토리(예: `main.py` 파일이 있는 곳)에 `.env`라는 이름의 파일을 생성하세요.

2.  **봇 토큰 추가**: 생성한 `.env` 파일에 다음 형식으로 Discord 봇 토큰을 추가합니다. `YOUR_DISCORD_BOT_TOKEN_HERE` 부분을 실제 봇 토큰으로 교체해야 합니다.

    ```dotenv
    DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN_HERE
    ```

      * **봇 토큰 얻는 방법**:
        1.  [Discord Developer Portal](https://discord.com/developers/applications)에 접속하여 애플리케이션을 선택하거나 새로 만듭니다.
        2.  왼쪽 메뉴에서 **Bot** 탭을 클릭합니다.
        3.  **Add Bot** 버튼을 클릭하여 봇을 생성합니다.
        4.  **TOKEN** 섹션에서 **Reset Token**을 클릭하고 토큰을 복사합니다. 이 토큰은 **반드시** 외부에 유출되지 않도록 주의해야 합니다.

3. **대상 서버에 봇 초대**: 생성한 디스코드 봇을 사용하고자 하는 Discord 서버에 초대해야 합니다.

    - 봇 초대 링크 생성: [Discord Developer Portal](https://discord.com/developers/applications)의 Bot 탭에서 OAuth2 탭으로 이동합니다. SCOPES에서 bot을 선택하고, 필요한 BOT PERMISSIONS (예: Send Messages, Read Message History, View Channels 등)를 선택한 후 생성된 URL을 통해 봇을 서버에 초대합니다.

    - 만약 봇이 서버에 초대되어 있지 않거나, 봇이 읽을 수 있는 텍스트 채널이 없는 경우 프로그램이 제대로 동작하지 않습니다

-----

### 4\. 봇 실행 방법

모든 설정이 완료되었다면, 터미널 또는 명령 프롬프트에서 `main.py` 파일을 실행하여 봇을 시작할 수 있습니다.

```bash
python main.py
```

봇이 성공적으로 연결되면, 서버와 채널을 선택하라는 초기 설정 메시지가 나타나고, 이후 CLI를 통해 Discord와 상호작용할 수 있게 됩니다.

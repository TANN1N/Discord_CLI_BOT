import os
import asyncio
from typing import Callable

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

from models.app_state import AppState
from core.event_manager import EventManager
from core.event_types import EventType
from controllers.command_controller import CommandController
from models import app_state

class CLIView:
    """
    콘솔 UI를 관리하는 View 클래스.
    AppState의 데이터를 기반으로 화면을 렌더링하고, 사용자 입력을 Controller에 전달하며,
    EventManager로부터 UI 업데이트 이벤트를 수신하여 처리합니다.
    """
    def __init__(self, controller: CommandController, app_state: AppState, event_manager: EventManager):
        self.controller = controller
        self.app_state = app_state
        self.event_manager = event_manager
        self.session = PromptSession()
        self.is_bot_ready = asyncio.Event()
        self.is_running = True

    def register_event_listeners(self):
        """UI와 관련된 모든 이벤트를 구독합니다."""
        self.event_manager.subscribe(EventType.SHOW_TEXT, self.handle_show_text)
        self.event_manager.subscribe(EventType.ERROR, self.handle_error)
        self.event_manager.subscribe(EventType.CLEAR_DISPLAY, self.handle_clear_display)
        self.event_manager.subscribe(EventType.BOT_READY, self.handle_bot_ready)
        self.event_manager.subscribe(EventType.GUILDS_UPDATED, self.handle_guilds_updated)
        self.event_manager.subscribe(EventType.GUILD_SELECTED, self.handle_guild_selected)
        self.event_manager.subscribe(EventType.AVAILABLE_CHANNELS_UPDATED, self.handle_available_channels_updated)
        self.event_manager.subscribe(EventType.CHANNEL_SELECTED, self.handle_channel_selected)
        self.event_manager.subscribe(EventType.MESSAGES_UPDATED, self.handle_messages_updated)
        self.event_manager.subscribe(EventType.NEW_INCOMING_MESSAGE, self.handle_new_incoming_message)
        self.event_manager.subscribe(EventType.REQUEST_MULTILINE_INPUT, self.handle_request_multiline_input)
        self.event_manager.subscribe(EventType.REQUEST_FILE_INPUT, self.handle_request_file_input)

    async def run_cli(self):
        """메인 CLI 루프를 실행합니다."""
        await self.is_bot_ready.wait()

        # 초기 설정 (서버 및 채널 선택)
        if not await self._initial_setup():
            print("초기 설정에 실패하여 프로그램을 종료합니다.")
            await self.controller._quit("")
            return

        print("\n[정보] 명령어 도움말은 '/help'를 입력해 주세요.")
        
        with patch_stdout():
            while self.is_running:
                try:
                    guild_name = self.app_state.current_guild.name if self.app_state.current_guild else "No Guild"
                    channel_name = f"#{self.app_state.current_channel.name}" if self.app_state.current_channel else "No Channel"
                    prompt_text = f"[{guild_name} | {channel_name}]> "
                    user_input = await self.session.prompt_async(prompt_text)

                    if not user_input.strip():
                        continue

                    if user_input.startswith('/'):
                        parts = user_input.split(' ', 1)
                        command = parts[0].lower()
                        arg = parts[1] if len(parts) > 1 else ""
                        if await self.controller.handle_command(command, arg):
                            self.is_running = False # 종료 명령 시 루프 중단
                    else:
                        # 일반 메시지는 컨트롤러를 거치지 않고 바로 서비스로 전송 요청
                        await self.controller.bot_service.send_message(user_input)

                except (EOFError, KeyboardInterrupt):
                    print("\n[정보] 종료하려면 '/quit'을 입력하세요.")
                except Exception as e:
                    print(f"[CLI 오류] 예외 발생: {e}")

    async def _initial_setup(self) -> bool:
        """봇 시작 시 서버와 채널을 설정하는 과정을 처리합니다."""
        print("\n--- 초기 설정: 서버 선택 ---")
        await self.controller._list_guilds("")
        
        while True:
            guild_input = await self.session.prompt_async("서버 인덱스, ID 또는 이름을 입력하세요: ")
            if await self.controller.bot_service.select_guild(guild_input.strip()):
                break
            print("[실패] 다시 시도해 주세요.")

        print("\n--- 초기 설정: 채널 선택 ---")

        while True:
            channel_input = await self.session.prompt_async("채널 인덱스, ID 또는 이름을 입력하세요: ")
            if await self.controller.bot_service.select_channel(channel_input.strip()):
                await self.controller.bot_service.fetch_recent_messages()
                return True
            print("[실패] 다시 시도해 주세요.")
        return False

    # --- Event Handlers ---

    async def handle_show_text(self, text: str):
        print(text)

    async def handle_error(self, error_message: str):
        print(f"\n{error_message}\n")

    async def handle_clear_display(self, *args):
        os.system('cls' if os.name == 'nt' else 'clear')
        print("[정보] 화면이 지워졌습니다.")

    async def handle_bot_ready(self, *args):
        self.is_bot_ready.set()

    async def handle_guilds_updated(self, *args):
        print("\n--- 서버 목록 ---")
        if not self.app_state.all_guilds:
            print("  참여 중인 서버가 없습니다.")
            return
        for idx, guild in enumerate(self.app_state.all_guilds):
            print(f"  [{idx + 1}] {guild.name} (ID: {guild.id})")
        print("------------------\n")

    async def handle_guild_selected(self, guild_name: str):
        print(f"\n[성공] 서버가 설정되었습니다: {guild_name}")

    async def handle_available_channels_updated(self, *args):
        """사용 가능한 채널 목록을 출력합니다."""
        print(f"\n--- 채널 목록 (서버: {self.app_state.current_guild.name}) ---")
        channels = self.app_state.available_channels
        if not channels:
            print("  사용 가능한 텍스트 채널이 없습니다.")
        else:
            for idx, channel in enumerate(channels):
                current_indicator = " (현재 선택됨)" if self.app_state.current_channel and self.app_state.current_channel.id == channel.id else ""
                print(f"  [{idx + 1}] #{channel.name} (ID: {channel.id}){current_indicator}")
        print("-------------------------------------------\n")

    async def handle_channel_selected(self, channel_name: str):
        print(f"\n[성공] 채널이 설정되었습니다: #{channel_name}\n")

    async def handle_messages_updated(self, *args):
        print(f"\n--- 최근 메시지 (채널: #{self.app_state.current_channel.name}) ---")
        if not self.app_state.recent_messages:
            print("  메시지가 없습니다.")
        else:
            for msg in self.app_state.recent_messages:
                print(msg)
        print("----------------------------------------\n")

    async def handle_new_incoming_message(self, message):
        # 현재 채널의 메시지인 경우, 일반적인 포맷으로 출력
        if self.app_state.current_channel and message.channel.id == self.app_state.current_channel.id:
            formatted_message = await self.controller.bot_service.format_message_for_cli(message)
            print(f"\n{formatted_message}")
        # 다른 채널의 메시지인 경우, 어디서 온 메시지인지 표시하여 알려줌
        else:
            notification = f"\n[새 메시지 @{message.guild.name}/#{message.channel.name}]\n"
            print(notification)

    async def handle_request_multiline_input(self, on_complete: Callable):
        print("\n--- 여러 줄 메시지 입력 모드 ---")
        print("  입력을 마치려면 새로운 줄에 '@END'를 입력하고 Enter를 누르세요.")
        print("----------------------------")
        lines = []
        while True:
            line = await self.session.prompt_async(">> ")
            if line.strip().upper() == "@END":
                break
            lines.append(line)
        
        full_message = "\n".join(lines)
        print("\n--- 여러 줄 메시지 입력 모드 종료 ---\n")
        await on_complete(full_message)

    async def handle_request_file_input(self, on_complete: Callable, initial_arg: str):
        print("\n--- 파일 첨부 ---")
        file_path = ""
        caption = None

        # 인자 분석
        if initial_arg:
            parts = initial_arg.split(' ', 1)
            file_path = parts[0].strip('\'""')
            if len(parts) > 1:
                caption = parts[1]
        
        # 파일 경로가 없으면 입력받기
        while not file_path or not os.path.exists(file_path):
            if file_path: # 경로가 있었는데 못찾은 경우
                print(f"[오류] 파일을 찾을 수 없습니다: {file_path}")
            file_path_input = await self.session.prompt_async("첨부할 파일의 전체 경로를 입력하세요: ")
            file_path = file_path_input.strip('\'""')

        # 캡션이 없으면 입력받기 (선택 사항)
        if not caption:
            caption_input = await self.session.prompt_async("첨부할 메시지(캡션)를 입력하세요 (선택사항): ")
            if caption_input.strip():
                caption = caption_input
        
        print(f"[정보] 파일 전송 시도: '{file_path}'")
        await on_complete(file_path, caption)

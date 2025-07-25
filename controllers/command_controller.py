import os
import asyncio
import logging
from typing import Callable

from services.bot_service import DiscordBotService 
from models.app_state import AppState
from core.event_manager import EventManager
from core.event_types import EventType

logger = logging.getLogger(__name__)


class CommandController:
    """
    커맨드 라인 인터페이스(CLI)에서의 유저 입력을 핸들링합니다. 
    MVC 패턴에서 Controller에 해당합니다. 
    명령어를 입력 받고 인자를 받으며 해당 내용을 통해 BotService에게 작업을 요청하고 몇가지 메시지를 출력합니다. 
    그러나 직접적으로 BotService의 메서드를 호출하거나 View(CLIManager) 대신 메시지를 출력하는 것은 지양하며 Event-Driven 방식을 통해 각 클래스와 통신합니다. 
    """
    def __init__(self, bot_service: DiscordBotService, app_state: AppState, event_manager: EventManager):
        self.bot_service = bot_service
        self.app_state = app_state
        self.event_manager = event_manager
        # 명령어와 해당 핸들러 메서드를 매핑합니다.
        self.commands = {
            '/help': self._help,
            '/h': self._help,
            '/listguilds': self._list_guilds,
            '/lg': self._list_guilds,
            '/setguild': self._set_guild,
            '/sg': self._set_guild,
            '/listchannels': self._list_channels,
            '/lc': self._list_channels,
            '/setchannel': self._set_channel,
            '/sc': self._set_channel,
            '/read': self._read,
            '/r': self._read,
            '/multiline': self._multiline_input,
            '/ml': self._multiline_input,
            '/attach': self._attach_file,
            '/a': self._attach_file,
            '/clear': self._clear,
            '/cls': self._clear,
            '/quit': self._quit,
        }

    async def handle_command(self, command: str, arg: str) -> bool:
        """CLI 명령어를 처리하고, 봇 종료가 필요한 경우 True를 반환합니다."""
        handler = self.commands.get(command)
        if handler:
            logger.info("Executing command: %s with arg: '%s'", command, arg)
            # 모든 핸들러는 bool 값을 반환하도록 통일했습니다.
            return await handler(arg)
        else:
            logger.warning("Unknown command received: %s", command)
            error_message = f"[오류] 알 수 없는 명령어입니다: {command}\n"
            error_message += "명령어 도움말을 보려면 '/help'를 입력해 주세요.\n"
            await self.event_manager.publish(EventType.ERROR, error_message) # Error Event pub
            return False

    async def _help(self, arg: str) -> bool:
        """명령어 도움말을 표시합니다."""
        help_text = ("\n--- 사용 가능한 명령어 ---\n")
        
        for cmd_key, func in self.commands.items():
            if len(cmd_key) > 3: # 단축 명령어는 제외하고 긴 명령어만 도움말에 표시
                doc = func.__doc__.strip() if func.__doc__ else "설명 없음."
                help_text += f"{cmd_key:<15} - {doc}\n"
        help_text += ("--------------------------\n")
        await self.event_manager.publish(EventType.SHOW_TEXT, help_text) # Show text Event pub
        return False

    async def _list_guilds(self, arg: str) -> bool:
        """봇이 참여하고 있는 서버 목록을 표시하도록 요청합니다."""
        await self.bot_service.get_all_guilds_info()
        return False

    async def _set_guild(self, arg: str) -> bool:
        """서버 인덱스, ID 또는 이름을 사용하여 현재 서버의 설정을 요청합니다."""
        if not arg:
            await self.event_manager.publish(EventType.ERROR, "[오류] 서버 인덱스, ID 또는 이름을 입력해 주세요. 예: /setguild 1") # Error Event pub
            return False
        
        if not await self.bot_service.select_guild(arg):
            await self.event_manager.publish(EventType.ERROR, "[오류] 유효하지 않은 서버 인덱스, ID 또는 이름입니다.") # Error Event pub
        return False

    async def _list_channels(self, arg: str) -> bool:
        """현재 선택된 서버의 채널 목록을 표시합니다."""
        if self.app_state.current_guild:
            await self.event_manager.publish(EventType.AVAILABLE_CHANNELS_UPDATED)
        else:
            await self.event_manager.publish(EventType.ERROR, "[오류] 채널 목록을 보려면 먼저 서버를 선택해 주세요. '/setguild' 사용.")
        return False

    async def _set_channel(self, arg: str) -> bool:
        """채널 인덱스, ID 또는 이름을 사용하여 현재 채널을 설정합니다."""
        if not arg:
            await self.event_manager.publish(EventType.ERROR, "[오류] 채널 인덱스, ID 또는 이름을 입력해 주세요. 예: /setchannel 1\n /setchannel 123456789012345678\n /setchannel 일반")

        if await self.bot_service.select_channel(arg):
            await self.bot_service.fetch_recent_messages()
        else:
            await self.event_manager.publish(EventType.ERROR, "[오류] 유효하지 않은 채널 인덱스, ID 또는 이름입니다.")
        return False

    async def _read(self, arg: str) -> bool:
        """현재 채널의 최근 메시지를 지정된 개수(기본값 20)만큼 불러옵니다."""
        count = 20
        if arg:
            try:
                count = int(arg)
                if not (1 <= count <= 100):
                    await self.event_manager.publish(EventType.ERROR, "[오류] 읽을 메시지 개수는 1에서 100 사이여야 합니다.")
                    return False
            except ValueError:
                await self.event_manager.publish(EventType.ERROR, "[오류] 읽을 메시지 개수는 숫자여야 합니다.")
                return False
        await self.bot_service.fetch_recent_messages(count)
        
        # fetch_recent_messages에서 이벤트를 발행하므로 View에서 어떻게 처리할지 결정하도록 위임함
        # if messages:
        #     self.event_manager.publish(EventType.SHOW_TEXT, f"\n[최근 {count}개 메시지] (채널: #{self.app_state.current_channel.name})")
        #     for msg_line in messages:
        #         self.event_manager.publish(EventType.SHOW_TEXT, msg_line)
        # elif self.app_state.current_channel: 
        #     self.event_manager.publish(EventType.SHOW_TEXT, "[정보] 불러올 메시지가 없거나 오류가 발생했습니다. 권한을 확인해 주세요.")
        # else: 
        #     self.event_manager.publish(EventType.ERROR, "[오류] 먼저 채널을 선택해 주세요. '/setchannel' 사용.")
        return False

    async def _clear(self, arg: str) -> bool:
        """터미널 화면을 지웁니다."""
        # 터미널 화면의 관리는 View에게 맡기도록 함
        # os.system('cls' if os.name == 'nt' else 'clear')
        # self.event_manager.publish(EventType.SHOW_TEXT, "[정보] 화면이 지워졌습니다.")
        await self.event_manager.publish(EventType.CLEAR_DISPLAY)
        return False

    async def _multiline_input(self, arg: str) -> bool:
        """여러 줄 메시지 입력 모드로 전환합니다. 입력을 마치려면 새로운 줄에 @END를 입력하세요."""
        # self.event_manager.publish(EventType.SHOW_TEXT, "\n--- 여러 줄 메시지 입력 모드 ---")
        # self.event_manager.publish(EventType.SHOW_TEXT, "  입력을 마치려면 새로운 줄에 '@END'를 입력하고 Enter를 누르세요.")
        # self.event_manager.publish(EventType.SHOW_TEXT, "----------------------------")
        # lines = []
        # while True:
        #     # asyncio.to_thread를 사용하여 blocking input을 비동기적으로 처리합니다.
        #     line = await asyncio.to_thread(input, ">> ")
        #     if line.strip().upper() == "@END": 
        #         break
        #     lines.append(line)
        
        # full_message = "\n".join(lines)
        # if full_message.strip(): 
        #     await self.bot_service.send_message(full_message)
        # else:
        #     print("[정보] 입력된 내용이 없어 메시지를 전송하지 않았습니다.")
        # print("\n--- 여러 줄 메시지 입력 모드 종료 ---\n")

        async def on_complete(text: str):
            if text.strip():
                await self.bot_service.send_message(text)
        await self.event_manager.publish(EventType.REQUEST_MULTILINE_INPUT, on_complete)
        return False

    async def _attach_file(self, arg: str) -> bool:
        """지정된 파일을 현재 채널에 첨부합니다. (예: /a C:/path/file.png '캡션')"""
        # multiline input과 마찬가지로 View에게 구현을 위임함.
        # if not arg:
        #     print("[오류] 첨부할 파일 경로를 입력하세요. 사용법: /attach <파일경로> [선택적 메시지]")
        #     return False

        # 첫 번째 공백을 기준으로 파일 경로와 메시지를 분리합니다.
        # parts = arg.split(' ', 1)
        # file_path = parts[0]
        # message_content = parts[1] if len(parts) > 1 else None

        # # 파일 경로에 따옴표가 있을 경우 제거합니다.
        # file_path = file_path.strip('\'"')

        # if not os.path.exists(file_path):
        #     print(f"[오류] 지정된 파일 경로를 찾을 수 없습니다: '{file_path}'")
        #     return False

        # await self.bot_service.send_file(file_path, message_content)
        # print(f"[정보] 파일 전송 시도: '{file_path}'")
        
        async def on_complete(file_path: str, caption: str | None):
            await self.bot_service.send_file(file_path, caption)
        await self.event_manager.publish(EventType.REQUEST_FILE_INPUT, on_complete, arg)
        return False

    async def _quit(self, arg: str) -> bool:
        """봇을 종료합니다."""
        await self.event_manager.publish(EventType.SHOW_TEXT, "[정보] 봇을 종료합니다...")
        await self.bot_service.bot.close()
        return True
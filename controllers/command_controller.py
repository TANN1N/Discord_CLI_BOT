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
    View로부터 받은 유저 입력을 핸들링합니다. 
    MVC 패턴에서 Controller에 해당합니다. 
    명령어를 입력 받고 인자를 받으며 해당 내용을 통해 Service에게 작업을 요청하고 몇가지 메시지를 출력합니다. 
    그러나 직접적으로 Service의 메서드를 호출하거나 View 대신 메시지를 출력하는 것은 지양하며 Event-Driven 방식을 통해 각 클래스와 통신합니다. 
    """
    def __init__(self, bot_service: DiscordBotService, app_state: AppState, event_manager: EventManager):
        self.bot_service = bot_service
        self.app_state = app_state
        self.event_manager = event_manager
        # 명령어와 해당 핸들러 메서드를 매핑합니다.
        self.commands = {
            '/help': self._help, '/h': self._help,
            '/listguilds': self._list_guilds, '/lg': self._list_guilds,
            '/setguild': self._set_guild, '/sg': self._set_guild,
            '/listchannels': self._list_channels, '/lc': self._list_channels,
            '/setchannel': self._set_channel, '/sc': self._set_channel,
            '/read': self._read, '/r': self._read,
            '/self_messages': self._get_self_messages, '/sm': self._get_self_messages,
            '/delete': self._delete_self_message, '/d': self._delete_self_message,
            '/multiline': self._multiline_input, '/ml': self._multiline_input,
            '/attach': self._attach_file, '/a': self._attach_file,
            '/files': self._list_files, '/f': self._list_files,
            '/download': self._download_file, '/dl': self._download_file,
            '/clear': self._clear, '/cls': self._clear,
            '/quit': self._quit, '/q': self._quit,
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
            error_message = f"알 수 없는 명령어입니다: {command}\n"
            error_message += "명령어 도움말을 보려면 '/help'를 입력해 주세요.\n"
            await self.event_manager.publish(EventType.ERROR, error_message)
            return False

    async def _help(self, arg: str) -> bool:
        """명령어 도움말을 표시합니다."""
        help_text = ("\n--- 사용 가능한 명령어 ---\n")
        
        for cmd_key, func in self.commands.items():
            if len(cmd_key) > 4: # 단축 명령어는 제외하고 긴 명령어만 도움말에 표시
                doc = func.__doc__.strip() if func.__doc__ else "설명 없음."
                help_text += f"{cmd_key:<15} - {doc}\n"
        help_text += ("--------------------------")
        await self.event_manager.publish(EventType.UI_TEXT_SHOW_REQUEST, help_text)
        return False

    async def _list_guilds(self, arg: str) -> bool:
        """봇이 참여하고 있는 서버 목록을 표시하도록 요청합니다."""
        await self.bot_service.get_all_guilds_info()
        return False

    async def _set_guild(self, arg: str) -> bool:
        """서버 인덱스, ID 또는 이름을 사용하여 현재 서버의 설정을 요청합니다."""
        if not arg:
            await self.event_manager.publish(EventType.ERROR, "서버 인덱스, ID 또는 이름을 입력해 주세요. 예: /setguild 1")
            return False
        
        await self.event_manager.publish(EventType.GUILD_SELECT_REQUEST, arg)
        return False

    async def _list_channels(self, arg: str) -> bool:
        """현재 선택된 서버의 채널 목록을 표시합니다."""
        if self.app_state.current_guild:
            await self.event_manager.publish(EventType.CHANNELS_UPDATED)
        else:
            await self.event_manager.publish(EventType.ERROR, "채널 목록을 보려면 먼저 서버를 선택해 주세요. '/setguild' 사용.")
        return False

    async def _set_channel(self, arg: str) -> bool:
        """채널 인덱스, ID 또는 이름을 사용하여 현재 채널을 설정합니다."""
        if not arg:
            await self.event_manager.publish(EventType.ERROR, "채널 인덱스, ID 또는 이름을 입력해 주세요. 예: /setchannel 1\n /setchannel 123456789012345678\n /setchannel 일반")

        await self.event_manager.publish(EventType.CHANNEL_SELECT_REQUEST, arg)
        return False

    # TODO Continue refactor 
    async def _read(self, arg: str) -> bool:
        """현재 채널의 최근 메시지를 지정된 개수(기본값 20)만큼 불러옵니다."""
        limit = 20
        if arg:
            try:
                limit = int(arg)
                if not (1 <= limit <= 100):
                    await self.event_manager.publish(EventType.ERROR, "읽을 메시지 개수는 1에서 100 사이여야 합니다.")
                    return False
            except ValueError:
                await self.event_manager.publish(EventType.ERROR, "읽을 메시지 개수는 숫자여야 합니다.")
                return False
        await self.bot_service.fetch_recent_messages(limit)
        return False

    async def _get_self_messages(self, arg: str) -> bool:
        """현재 채널에서 자신의 최근 메시지를 지정된 개수(기본값 50) 만큼 불러옵니다."""
        limit = 50
        if arg:
            try:
                limit = int(arg)
                if not (1 <= limit <= 100):
                    await self.event_manager.publish(EventType.ERROR, "읽을 메시지 개수는 1에서 100 사이여야 합니다.")
                    return False
            except ValueError:
                await self.event_manager.publish(EventType.ERROR, "읽을 메시지 개수는 숫자여야 합니다.")
                return False
        await self.bot_service.fetch_recent_self_messages(limit)
        return False

    async def _delete_self_message(self, arg: str) -> bool:
        """선택된 자신의 메시지를 삭제합니다."""
        index = 0
        if arg:
            try:
                index = int(arg) - 1
                if not (0 <= index <= len(self.app_state.recent_self_messages)):
                    await self.event_manager.publish(EventType.ERROR, "삭제할 메시지의 인덱스는 캐시된 메시지 범위 안에 있어야 합니다.")
                    return False
            except ValueError:
                await self.event_manager.publish(EventType.ERROR, "삭제할 메시지의 인덱스는 숫자여야 합니다.")
                return False
        await self.event_manager.publish(EventType.MESSAGE_DELETE_REQUEST, index)
        return False

    async def _clear(self, arg: str) -> bool:
        """터미널 화면을 지웁니다."""
        await self.event_manager.publish(EventType.UI_DISPLAY_CLEAR_REQUEST)
        return False

    async def _multiline_input(self, arg: str) -> bool:
        """여러 줄 메시지 입력 모드로 전환합니다. 입력을 마치려면 새로운 줄에 @END를 입력하세요."""
        async def on_complete(text: str):
            if text.strip():
                await self.bot_service.send_message(text)
        await self.event_manager.publish(EventType.UI_MULTILINE_INPUT_REQUEST, on_complete)
        return False

    async def _attach_file(self, arg: str) -> bool:
        """지정된 파일을 현재 채널에 첨부합니다. (예: /a C:/path/file.png '캡션')"""
        async def on_complete(file_path: str, caption: str | None):
            await self.bot_service.send_file(file_path, caption)
        await self.event_manager.publish(EventType.UI_FILE_INPUT_REQUEST, on_complete, arg)
        return False

    async def _list_files(self, arg: str) -> bool:
        """현재 채널의 최근 파일 목록을 표시합니다. (기본 50개 메시지 스캔)"""
        if not self.app_state.current_channel:
            await self.event_manager.publish(EventType.ERROR, "먼저 채널을 선택해 주세요. '/setchannel' 사용.")
            return False
        
        limit = 50
        if arg:
            try:
                limit = int(arg)
                if not (1 <= limit <= 200):
                    await self.event_manager.publish(EventType.ERROR, "스캔할 메시지 개수는 1에서 200 사이여야 합니다.")
                    return False
            except ValueError:
                await self.event_manager.publish(EventType.ERROR, "스캔할 메시지 개수는 숫자여야 합니다.")
                return False
        
        await self.event_manager.publish(EventType.UI_TEXT_SHOW_REQUEST, f"[정보] 최근 {limit}개 메시지에서 파일을 검색합니다...")
        await self.event_manager.publish(EventType.FILES_LIST_FETCH_REQUEST, limit)
        return False

    async def _download_file(self, arg: str) -> bool:
        """인덱스를 사용하여 캐시된 파일 목록에서 파일을 다운로드합니다."""
        if not self.app_state.file_cache:
            await self.event_manager.publish(EventType.ERROR, "파일 목록이 비어있습니다. 먼저 '/files'를 실행해 주세요.")
            return False
        
        index = 0
        if arg:
            try:
                index = int(arg) - 1
                if not (1 <= index <= len(self.app_state.file_cache)):
                    await self.event_manager.publish(EventType.ERROR, f"유효하지 않은 인덱스입니다. 1에서 {len(self.app_state.file_cache)} 사이의 숫자를 입력해 주세요.")
                    return False
            except ValueError:
                await self.event_manager.publish(EventType.ERROR, "파일 인덱스는 숫자여야 합니다.")
                return False

        await self.event_manager.publish(EventType.FILE_DOWNLOAD_REQUEST, index)
        return False

    async def _quit(self, arg: str) -> bool:
        """봇을 종료합니다."""
        await self.event_manager.publish(EventType.UI_TEXT_SHOW_REQUEST, "[정보] 봇을 종료합니다...")
        await self.bot_service.bot.close()
        return True
import os
import asyncio
import logging
import aiohttp

import discord
from discord.ext import commands
from datetime import timedelta

from models.app_state import AppState
from core.event_manager import EventManager
from core.event_types import EventType

logger = logging.getLogger(__name__)


class DiscordBotService:
    def __init__(self, bot: commands.Bot, app_state: AppState, event_manager: EventManager):
        self.bot = bot
        self.app_state = app_state
        self.event_manager = event_manager
        self._cached_channels: list[discord.TextChannel] = []

    async def get_all_guilds_info(self) -> bool:
        """봇이 참여 중인 모든 길드의 정보 (인덱스, 이름, ID)를 반환합니다."""
        if not self.bot.is_ready():
            await self.event_manager.publish(EventType.ERROR, "[오류] 봇이 Discord에 연결될 때까지 기다려 주세요.") # Error Event pub
            return False
        # Discord Bot 객체의 guilds 속성에서 직접 정보를 가져옵니다.
        self.app_state.all_guilds = list(self.bot.guilds)
        await self.event_manager.publish(EventType.GUILDS_UPDATED) # Guilds updated Event pub
        return True

    async def select_guild(self, value: str) -> bool:
        """주어진 인덱스, ID 또는 이름으로 현재 길드를 설정합니다."""
        guild_found = None
        
        # 1. 인덱스로 시도
        try:
            idx = int(value)
            if 1 <= idx <= len(self.bot.guilds):
                guild_found = self.bot.guilds[idx - 1]
        except ValueError:
            pass # 숫자가 아니면 다음 시도
        
        # 2. ID로 시도
        if not guild_found:
            try:
                guild_id = int(value)
                guild_found = self.bot.get_guild(guild_id)
            except ValueError:
                pass # 유효한 ID가 아니면 다음 시도
        
        # 3. 이름으로 시도
        if not guild_found:
            lowered_value = value.lower()
            for guild in self.bot.guilds:
                if guild.name.lower() == lowered_value:
                    guild_found = guild
                    break
        
        if guild_found:
            self.app_state.current_guild = guild_found
            self.app_state.current_channel = None # 길드 변경 시 채널 초기화
            # 현재 길드의 텍스트 채널 목록을 캐싱합니다.
            self.app_state.available_channels = [ch for ch in guild_found.channels if isinstance(ch, discord.TextChannel)]
            await self.event_manager.publish(EventType.GUILD_SELECTED, guild_found.name) # Guild selected Event pub
            await self.event_manager.publish(EventType.AVAILABLE_CHANNELS_UPDATED) # Available channels updated Event pub
            return True
        return False

    async def select_channel(self, value: str) -> bool:
        """주어진 인덱스, ID 또는 이름으로 현재 채널을 설정합니다."""
        if not self.app_state.current_guild:
            await self.event_manager.publish(EventType.ERROR, "[오류] 채널을 설정하려면 먼저 서버를 선택해 주세요.") # Error Event pub
            return False

        channel_found = None
        # 1. 인덱스로 시도 (캐싱된 목록 사용)
        try:
            idx = int(value)
            if 1 <= idx <= len(self.app_state.available_channels):
                channel_found = self.app_state.available_channels[idx - 1]
        except ValueError:
            pass
        
        # 2. ID로 시도
        if not channel_found:
            try:
                channel_id = int(value)
                # 현재 길드 내에서 채널을 찾습니다.
                channel_found = self.app_state.current_guild.get_channel(channel_id) 
            except ValueError:
                pass
        
        # 3. 이름으로 시도
        if not channel_found and isinstance(value, str):
            lowered_value = value.lower()
            for ch in self.app_state.available_channels:
                if ch.name.lower() == lowered_value:
                    channel_found = ch
                    break
        
        if channel_found and isinstance(channel_found, discord.TextChannel):
            self.app_state.current_channel = channel_found
            await self.event_manager.publish(EventType.CHANNEL_SELECTED, channel_found.name) # Channel selected Event pub
            return True
        return False

    async def fetch_recent_messages(self, count: int = 20) -> bool:
        """
        현재 채널의 최근 메시지를 가져와 CLI 출력 형식으로 변환해 recent_messages에 업데이트 합니다.
        성공 여부를 반환합니다. 
        """
        if not self.app_state.current_channel:
            await self.event_manager.publish(EventType.ERROR, "[오류] 먼저 채널을 선택해 주세요.") # Error Event pub
            return False
        
        cli_messages = []
        try:
            # 채널 히스토리를 비동기적으로 가져옵니다.
            async for msg in self.app_state.current_channel.history(limit=count):
                cli_messages.append(await self.format_message_for_cli(msg))
        except discord.errors.Forbidden:
            logger.warning(
                "Failed to fetch messages from channel %s due to Forbidden error.",
                self.app_state.current_channel.name
            )
            await self.event_manager.publish(EventType.ERROR, "[오류] 채널 메시지 읽기 권한이 없습니다. 봇 역할 권한을 확인해 주세요.")
        except Exception as e:
            logger.exception(
                "An unexpected error occurred while fetching messages from channel %s.",
                self.app_state.current_channel.name
            )
            await self.event_manager.publish(EventType.ERROR, f"[오류] 메시지 가져오기 실패: {e}")
        
        self.app_state.recent_messages = list(reversed(cli_messages))
        await self.event_manager.publish(EventType.MESSAGES_UPDATED) # Messages updated Event pub
        return True

    async def send_message(self, content: str) -> bool:
        """현재 채널에 메시지를 전송하고 성공 여부를 반환합니다."""
        if not self.app_state.current_channel:
            await self.event_manager.publish(EventType.ERROR, "[오류] 메시지를 보낼 채널이 선택되지 않았습니다. 채널을 설정해 주세요.") # Error Event pub
            return False
        
        try:
            message = await self.app_state.current_channel.send(content)
            logger.info("Message sent to #%s: %s", self.app_state.current_channel.name, content)
            await self.event_manager.publish(EventType.MESSAGE_SENT_SUCCESS, message) # Message sent success Event pub
            return True
        except discord.errors.Forbidden:
            logger.warning(
                "Failed to send message to channel %s due to Forbidden error.",
                self.app_state.current_channel.name
            )
            await self.event_manager.publish(EventType.ERROR, "[오류] 채널에 메시지를 보낼 권한이 없습니다. 봇 역할 권한을 확인해 주세요.")
        except Exception as e:
            logger.exception(
                "An unexpected error occurred while sending message to channel %s.",
                self.app_state.current_channel.name
            )
            await self.event_manager.publish(EventType.ERROR, f"[오류] 메시지 전송 실패: {e}")
        return False

    async def send_file(self, file_path: str, content: str | None = None) -> bool:
        """지정된 파일을 현재 채널에 전송하고 성공 여부를 반환합니다."""
        if not self.app_state.current_channel:
            await self.event_manager.publish(EventType.ERROR, "[오류] 파일을 보낼 채널이 선택되지 않았습니다. 채널을 설정해 주세요.") # Error Event pub
            return False
        
        if not os.path.exists(file_path):
            logger.error("File not found at path: %s", file_path)
            await self.event_manager.publish(EventType.ERROR, f"[오류] 파일을 찾을 수 없습니다: '{file_path}'") # Error Event pub
            return False
            
        try:
            logger.info("Attempting to send file %s to #%s", file_path, self.app_state.current_channel.name)
            discord_file = discord.File(file_path)
            message = await self.app_state.current_channel.send(content=content, file=discord_file)
            await self.event_manager.publish(EventType.FILE_SENT_SUCCESS, message) # File sent success Event pub
            logger.info("Successfully sent file %s", file_path)
        except discord.errors.Forbidden:
            logger.warning(
                "Failed to send file to channel %s due to Forbidden error.",
                self.app_state.current_channel.name
            )
            await self.event_manager.publish(EventType.ERROR, "[오류] 채널에 파일을 첨부할 권한이 없습니다. 봇 역할 권한을 확인해 주세요.")
        except Exception as e:
            logger.exception(
                "An unexpected error occurred while sending file to channel %s.",
                self.app_state.current_channel.name
            )
            await self.event_manager.publish(EventType.ERROR, f"[오류] 파일 전송 실패: {e}")
        return False

    async def format_message_for_cli(self, message: discord.Message) -> str:
        """Discord 메시지 객체를 CLI에 표시할 단일 문자열로 포맷팅합니다."""
        timestamp = (message.created_at + timedelta(hours=9)).strftime("%m/%d %H:%M:%S")
        
        content = message.content
        for member in message.mentions:
            display_name = member.display_name
            content = content.replace(f"<@{member.id}>", f"@{display_name}")
            content = content.replace(f"<@!{member.id}>", f"@{display_name}")
        for role in message.role_mentions:
            content = content.replace(f"<@&{role.id}>", f"@{role.name}")
        for channel in message.channel_mentions:
            content = content.replace(f"<#{channel.id}>", f"#{channel.name}")
        
        author_display = message.author.display_name
        
        file_attachments = []
        if message.attachments:
            for attachment in message.attachments:
                file_attachments.append(f"📁 {attachment.filename}")
        
        if file_attachments:
            processed_content = f"{author_display}: {content}\n[첨부 파일: {', '.join(file_attachments)}]"
        else:
            processed_content = f"{author_display}: {content}"
            
        return f"[{timestamp}] {processed_content}"
    
    # 해당 함수들은 MVC, Pub-Sub 아키텍쳐로 전환하면서 더이상 사용하지 않기를 권고합니다.
    # @property
    # def current_guild(self) -> discord.Guild | None:
    #     """현재 선택된 Discord 길드 객체를 반환합니다."""
    #     return self.app_state.current_guild

    # @property
    # def current_channel(self) -> discord.TextChannel | None:
    #     """현재 선택된 Discord 텍스트 채널 객체를 반환합니다."""
    #     return self.app_state.current_channel
    
    # async def get_channels_in_current_guild_info(self) -> list[tuple[int, str, int]]:
    #     """현재 설정된 길드의 텍스트 채널 정보 (인덱스, 이름, ID)를 반환합니다."""
    #     if not self.app_state.available_channels:
    #         print("[오류] 채널 목록을 보려면 먼저 서버를 선택해 주세요.")
    #         return []
    #     # 캐싱된 채널 목록을 사용합니다.
    #     return [(idx + 1, ch.name, ch.id) for idx, ch in enumerate(self.app_state.available_channels)]
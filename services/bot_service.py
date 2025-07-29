import os
import asyncio
import logging
import aiohttp
import aiofiles

import discord
from discord.ext import commands
from datetime import timedelta

from models.app_state import AppState
from core.event_manager import EventManager
from core.event_types import EventType

logger = logging.getLogger(__name__)

DOWNLOADS_DIR = "downloads"

class DiscordBotService:
    def __init__(self, bot: commands.Bot, app_state: AppState, event_manager: EventManager):
        self.bot = bot
        self.app_state = app_state
        self.event_manager = event_manager
        self._cached_channels: list[discord.TextChannel] = []
        logger.debug("Registering file-related event listeners...")
        self.event_manager.subscribe(EventType.FILES_LIST_REQUESTED, self.fetch_recent_files)
        self.event_manager.subscribe(EventType.FILE_DOWNLOAD_REQUESTED, self.download_file_by_index)
        logger.info("DiscordBotService initialized.")

    async def get_all_guilds_info(self) -> bool:
        """봇이 참여 중인 모든 길드의 정보 (인덱스, 이름, ID)를 반환합니다."""
        if not self.bot.is_ready():
            await self.event_manager.publish(EventType.ERROR, "[오류] 봇이 Discord에 연결될 때까지 기다려 주세요.")
            return False
        
        self.app_state.all_guilds = list(self.bot.guilds)
        logger.info("Found %d guilds.", len(self.app_state.all_guilds))
        await self.event_manager.publish(EventType.GUILDS_UPDATED)
        return True

    async def select_guild(self, value: str) -> bool:
        """주어진 인덱스, ID 또는 이름으로 현재 길드를 설정합니다."""
        guild_found = None
        
        # 1. 인덱스로 시도
        try:
            idx = int(value)
            if 1 <= idx <= len(self.bot.guilds):
                guild_found = self.bot.guilds[idx - 1]
                logger.debug("Found guild by index: %s", guild_found.name)
        except ValueError:
            pass # 숫자가 아니면 다음 시도
        
        # 2. ID로 시도
        if not guild_found:
            try:
                guild_id = int(value)
                guild_found = self.bot.get_guild(guild_id)
                if guild_found:
                    logger.debug("Found guild by ID: %s", guild_found.name)
            except ValueError:
                pass # 유효한 ID가 아니면 다음 시도
        
        # 3. 이름으로 시도
        if not guild_found:
            lowered_value = value.lower()
            for guild in self.bot.guilds:
                if guild.name.lower() == lowered_value:
                    guild_found = guild
                    logger.debug("Found guild by name: %s", guild_found.name)
                    break
        
        if guild_found:
            logger.info("Successfully selected guild: %s (ID: %s)", guild_found.name, guild_found.id)
            self.app_state.current_guild = guild_found
            self.app_state.current_channel = None # 길드 변경 시 채널 초기화
            self.app_state.file_cache.clear() # 길드 변경 시 파일 캐시 초기화
            # 현재 길드의 텍스트 채널 목록을 캐싱합니다.
            self.app_state.available_channels = [ch for ch in guild_found.channels if isinstance(ch, discord.TextChannel)]
            logger.info("Cached %d text channels for guild '%s'.", len(self.app_state.available_channels), guild_found.name)
            
            await self.event_manager.publish(EventType.GUILD_SELECTED, guild_found.name)
            await self.event_manager.publish(EventType.AVAILABLE_CHANNELS_UPDATED)
            return True
        
        logger.warning("Could not find guild with value: '%s'", value)
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
                logger.debug("Found channel by index: #%s", channel_found.name)
        except ValueError:
            pass
        
        # 2. ID로 시도
        if not channel_found:
            try:
                channel_id = int(value)
                channel_found = self.app_state.current_guild.get_channel(channel_id)
                if channel_found:
                    logger.debug("Found channel by ID: #%s", channel_found.name)
            except ValueError:
                pass
        
        # 3. 이름으로 시도
        if not channel_found and isinstance(value, str):
            lowered_value = value.lower()
            for ch in self.app_state.available_channels:
                if ch.name.lower() == lowered_value:
                    channel_found = ch
                    logger.debug("Found channel by name: #%s", ch.name)
                    break
        
        if channel_found and isinstance(channel_found, discord.TextChannel):
            logger.info("Successfully selected channel: #%s (ID: %s)", channel_found.name, channel_found.id)
            self.app_state.current_channel = channel_found
            self.app_state.file_cache.clear() # 채널 변경 시 파일 캐시 초기화
            await self.event_manager.publish(EventType.CHANNEL_SELECTED, channel_found.name) # Channel selected Event pub
            return True
            
        logger.warning("Could not find channel with value: '%s' in guild '%s'", value, self.app_state.current_guild.name)
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
            async for msg in self.app_state.current_channel.history(limit=count):
                cli_messages.append(await self.format_message_for_cli(msg))
            logger.info("Successfully fetched %d messages.", len(cli_messages))
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
        await self.event_manager.publish(EventType.MESSAGES_UPDATED)
        return True

    async def fetch_recent_files(self, limit: int = 50) -> bool:
        """현재 채널의 최근 파일들을 가져와 file_cache에 캐싱하고 성공 여부를 반환합니다."""
        logger.info("Fetching recent files from last %d messages in #%s.", limit, self.app_state.current_channel.name if self.app_state.current_channel else "None")
        if not self.app_state.current_channel:
            logger.warning("[오류] 먼저 채널을 선택해 주세요.")
            await self.event_manager.publish(EventType.ERROR, "[오류] 먼저 채널을 선택해 주세요.") # Error Event pub
            return False
        
        files = []
        try:
            async for msg in self.app_state.current_channel.history(limit=limit):
                if msg.attachments:
                    files.extend(msg.attachments)
            
            self.app_state.file_cache = files # 최신 파일이 위로 오도록
            await self.event_manager.publish(EventType.FILES_LIST_UPDATED)
            return True

        except discord.errors.Forbidden:
            logger.warning("Forbidden to read history in channel #%s", self.app_state.current_channel.name)
            await self.event_manager.publish(EventType.ERROR, "[오류] 채널 히스토리 읽기 권한이 없습니다.")
        except Exception as e:
            logger.exception("Error fetching files from channel #%s", self.app_state.current_channel.name)
            await self.event_manager.publish(EventType.ERROR, f"[오류] 파일 목록 가져오기 실패: {e}")
        
        return False

    async def download_file_by_index(self, index: int):
        """인덱스를 사용하여 file_cache에서 파일을 다운로드합니다."""
        logger.info("Request to download file at index %d.", index)
        try:
            attachment = self.app_state.file_cache[index - 1]
            
            if not os.path.exists(DOWNLOADS_DIR):
                logger.info("Downloads directory does not exist. Creating it at '%s'.", DOWNLOADS_DIR)
                os.makedirs(DOWNLOADS_DIR)
            
            file_path = os.path.join(DOWNLOADS_DIR, attachment.filename)
            
            logger.info("Starting download for '%s' from URL: %s", attachment.filename, attachment.url)
            await self.event_manager.publish(EventType.SHOW_TEXT, f"[정보] '{attachment.filename}' 다운로드 시작...")

            async with aiohttp.ClientSession() as session:
                async with session.get(attachment.url) as resp:
                    if resp.status == 200:
                        async with aiofiles.open(file_path, mode='wb') as f:
                            await f.write(await resp.read())
                        logger.info("File downloaded successfully to '%s'", os.path.abspath(file_path))
                        await self.event_manager.publish(EventType.FILE_DOWNLOAD_COMPLETE, file_path)
                    else:
                        logger.error("Error downloading file '%s': status %d", attachment.filename, resp.status)
                        await self.event_manager.publish(EventType.ERROR, f"[오류] '{attachment.filename}' 다운로드 실패 (HTTP 상태: {resp.status})")

        except IndexError:
            logger.error("Invalid file index %d requested. Cache size is %d.", index, len(self.app_state.file_cache))
            await self.event_manager.publish(EventType.ERROR, "[오류] 잘못된 파일 인덱스입니다.")
        except Exception as e:
            logger.exception("An unexpected error occurred during file download for index %d.", index)
            await self.event_manager.publish(EventType.ERROR, f"[오류] 파일 다운로드 중 예외 발생: {e}")

    async def send_message(self, content: str) -> bool:
        """현재 채널에 메시지를 전송하고 성공 여부를 반환합니다."""
        if not self.app_state.current_channel:
            logger.error("Cannot send message, no channel is selected.")
            await self.event_manager.publish(EventType.ERROR, "[오류] 메시지를 보낼 채널이 선택되지 않았습니다. 채널을 설정해 주세요.") # Error Event pub
            return False
        
        try:
            message = await self.app_state.current_channel.send(content)
            await self.event_manager.publish(EventType.MESSAGE_SENT_SUCCESS, message)
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
            logger.error("Cannot send file, no channel is selected.")
            await self.event_manager.publish(EventType.ERROR, "[오류] 파일을 보낼 채널이 선택되지 않았습니다. 채널을 설정해 주세요.") # Error Event pub
            return False
        
        if not os.path.exists(file_path):
            logger.error("File not found at path: %s", file_path)
            await self.event_manager.publish(EventType.ERROR, f"[오류] 파일을 찾을 수 없습니다: '{file_path}'") # Error Event pub
            return False
            
        try:
            logger.info("Attempting to send file '%s' to #%s", file_path, self.app_state.current_channel.name)
            discord_file = discord.File(file_path)
            message = await self.app_state.current_channel.send(content=content, file=discord_file)
            await self.event_manager.publish(EventType.FILE_SENT_SUCCESS, message) # File sent success Event pub
            logger.info("Successfully sent file '%s'", file_path)
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
            separator = "\n" if content else ""
            processed_content = f"{author_display}: {content}{separator}[Attachment(s): {', '.join(file_attachments)}]"
        else:
            processed_content = f"{author_display}: {content}"
            
        return f"[{timestamp}] {processed_content}"

    async def format_message_for_tui(self, message: discord.Message) -> list:
        """Discord 메시지 객체를 TUI에 표시할 서식 있는 텍스트 튜플 리스트로 포맷팅합니다."""
        timestamp = (message.created_at + timedelta(hours=9)).strftime("%m/%d %H:%M:%S")
        
        content = message.content
        # 멘션 처리 (CLI와 동일)
        for member in message.mentions:
            display_name = member.display_name
            content = content.replace(f"<@{member.id}>", f"@{display_name}")
            content = content.replace(f"<@!{member.id}>", f"@{display_name}")
        for role in message.role_mentions:
            content = content.replace(f"<@&{role.id}>", f"@{role.name}")
        for channel in message.channel_mentions:
            content = content.replace(f"<#{channel.id}>", f"#{channel.name}")
        
        author_display = message.author.display_name
        
        # TUI용 포맷팅된 리스트 생성
        formatted_list = [
            ('class:timestamp', f'[{timestamp}] '),
            ('class:author', f'{author_display}'),
            ('', ': '),
            ('', content)
        ]
        
        # 첨부 파일 처리
        if message.attachments:
            attachment_texts = [f"📁 {att.filename}" for att in message.attachments]
            separator = "\n" if content else ""
            attachment_str = f"{separator}[Attachment(s): {', '.join(attachment_texts)}]";
            formatted_list.append(('class:attachment', attachment_str))
            
        return formatted_list
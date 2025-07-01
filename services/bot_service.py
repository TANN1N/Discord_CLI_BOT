import discord
from discord.ext import commands
from datetime import timedelta
import os
import asyncio

class DiscordBotService:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._current_guild: discord.Guild | None = None
        self._current_channel: discord.TextChannel | None = None
        # 현재 길드의 채널 목록을 캐싱하여 반복적인 API 호출을 줄입니다.
        self._cached_channels: list[discord.TextChannel] = []

    @property
    def current_guild(self) -> discord.Guild | None:
        """현재 선택된 Discord 길드 객체를 반환합니다."""
        return self._current_guild

    @property
    def current_channel(self) -> discord.TextChannel | None:
        """현재 선택된 Discord 텍스트 채널 객체를 반환합니다."""
        return self._current_channel

    async def get_all_guilds_info(self) -> list[tuple[int, str, int]]:
        """봇이 참여 중인 모든 길드의 정보 (인덱스, 이름, ID)를 반환합니다."""
        if not self.bot.is_ready():
            print("[오류] 봇이 Discord에 연결될 때까지 기다려 주세요.")
            return []
        # Discord Bot 객체의 guilds 속성에서 직접 정보를 가져옵니다.
        return [(idx + 1, guild.name, guild.id) for idx, guild in enumerate(self.bot.guilds)]

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
            for g in self.bot.guilds:
                if g.name.lower() == lowered_value:
                    guild_found = g
                    break
        
        if guild_found:
            self._current_guild = guild_found
            self._current_channel = None # 길드 변경 시 채널 초기화
            # 현재 길드의 텍스트 채널 목록을 캐싱합니다.
            self._cached_channels = [ch for ch in self._current_guild.channels if isinstance(ch, discord.TextChannel)]
            return True
        return False

    async def get_channels_in_current_guild_info(self) -> list[tuple[int, str, int]]:
        """현재 설정된 길드의 텍스트 채널 정보 (인덱스, 이름, ID)를 반환합니다."""
        if not self._current_guild:
            print("[오류] 채널 목록을 보려면 먼저 서버를 선택해 주세요.")
            return []
        # 캐싱된 채널 목록을 사용합니다.
        return [(idx + 1, ch.name, ch.id) for idx, ch in enumerate(self._cached_channels)]

    async def select_channel(self, value: str) -> bool:
        """주어진 인덱스, ID 또는 이름으로 현재 채널을 설정합니다."""
        if not self._current_guild:
            print("[오류] 채널을 설정하려면 먼저 서버를 선택해 주세요.")
            return False

        channel_found = None
        # 1. 인덱스로 시도 (캐싱된 목록 사용)
        try:
            idx = int(value)
            if 1 <= idx <= len(self._cached_channels):
                channel_found = self._cached_channels[idx - 1]
        except ValueError:
            pass
        
        # 2. ID로 시도
        if not channel_found:
            try:
                channel_id = int(value)
                # 현재 길드 내에서 채널을 찾습니다.
                channel_found = self._current_guild.get_channel(channel_id) 
            except ValueError:
                pass
        
        # 3. 이름으로 시도
        if not channel_found and isinstance(value, str):
            lowered_value = value.lower()
            for ch in self._cached_channels:
                if ch.name.lower() == lowered_value:
                    channel_found = ch
                    break
        
        if channel_found and isinstance(channel_found, discord.TextChannel):
            self._current_channel = channel_found
            return True
        return False

    async def fetch_recent_messages(self, count: int = 20) -> list[str]:
        """현재 채널의 최근 메시지를 가져와 CLI 출력 형식으로 반환합니다."""
        if not self._current_channel:
            print("[오류] 먼저 채널을 선택해 주세요.")
            return []
            
        cli_messages = []
        try:
            # 채널 히스토리를 비동기적으로 가져옵니다.
            async for msg in self._current_channel.history(limit=count):
                timestamp = (msg.created_at + timedelta(hours=9)).strftime("%m/%d %H:%M:%S")
                processed_content = await self._process_message_mentions(msg)
                cli_messages.append(f"[{timestamp}] {msg.author.display_name}: {processed_content}")
        except discord.errors.Forbidden:
            print("[오류] 채널 메시지 읽기 권한이 없습니다. 봇 역할 권한을 확인해 주세요.")
        except Exception as e:
            print(f"[오류] 메시지 가져오기 실패: {e}")
        
        # 가장 오래된 메시지부터 출력되도록 순서를 뒤집습니다.
        return list(reversed(cli_messages))

    async def send_message(self, content: str) -> bool:
        """현재 채널에 메시지를 전송하고 성공 여부를 반환합니다."""
        if not self._current_channel:
            print("[오류] 메시지를 보낼 채널이 선택되지 않았습니다. 채널을 설정해 주세요.")
            return False
        
        try:
            message = await self.current_channel.send(content)
            timestamp = (message.created_at + timedelta(hours=9)).strftime("%m/%d %H:%M:%S")
            print(f"[{timestamp}] 나 ({self.bot.user.display_name}): {message.content}")
            return True
        except discord.errors.Forbidden:
            print("[오류] 채널에 메시지를 보낼 권한이 없습니다. 봇 역할 권한을 확인해 주세요.")
        except Exception as e:
            print(f"[오류] 메시지 전송 실패: {e}")
        return False

    async def send_file(self, file_path: str, content: str | None = None) -> bool:
        """지정된 파일을 현재 채널에 전송하고 성공 여부를 반환합니다."""
        if not self._current_channel:
            print("[오류] 파일을 보낼 채널이 선택되지 않았습니다. 채널을 설정해 주세요.")
            return False
        
        if not os.path.exists(file_path):
            print(f"[오류] 파일을 찾을 수 없습니다: '{file_path}'")
            return False
            
        try:
            discord_file = discord.File(file_path)
            message = await self._current_channel.send(content=content, file=discord_file)
            
            timestamp = (message.created_at + timedelta(hours=9)).strftime("%m/%d %H:%M:%S")
            print(f"[{timestamp}] 나 ({self.bot.user.display_name}): (파일 첨부) {os.path.basename(file_path)}")
            if content:
                print(f"  └ 메시지: {content}")
            return True
        except discord.errors.Forbidden:
            print("[오류] 채널에 파일을 첨부할 권한이 없습니다. 봇 역할 권한을 확인해 주세요.")
        except Exception as e:
            print(f"[오류] 파일 전송 실패: {e}")
        return False

    async def _process_message_mentions(self, message: discord.Message) -> str:
        """메시지 내용을 파싱하여 멘션(사용자, 역할, 채널)을 이름으로 변환합니다."""
        content = message.content
        for member in message.mentions:
            display_name = member.display_name
            content = content.replace(f"<@{member.id}>", f"@{display_name}")
            content = content.replace(f"<@!{member.id}>", f"@{display_name}")
        for role in message.role_mentions:
            content = content.replace(f"<@&{role.id}>", f"@{role.name}")
        for channel in message.channel_mentions:
            content = content.replace(f"<#{channel.id}>", f"#{channel.name}")
        return content
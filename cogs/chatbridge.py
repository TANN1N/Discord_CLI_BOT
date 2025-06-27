import discord
from discord.ext import commands
from datetime import timedelta
import asyncio
import os

class ChatBridge(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild = None
        self.channel = None
        self.channel_list = []

    @commands.Cog.listener()
    async def on_ready(self):
        # 봇이 Discord에 연결될 때 이 메시지가 출력됩니다.
        print(f"ChatBridge Cog: 봇 ({self.bot.user.name}) 준비 완료.")
        # 이 시점에서 self.bot.guilds 등에 접근할 수 있어야 합니다.

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user: # 봇 자신이 보낸 메시지는 무시
            return

        timestamp = (message.created_at + timedelta(hours=9)).strftime("%m/%d %H:%M:%S")

        processed_content = await self.process_message_mentions(message)

        if message.channel == self.channel: # 현재 설정된 채널의 메시지
            # 이전과 동일하게 출력
            print(f"[{timestamp}] {message.author.display_name}: {message.content}")
        else: # 봇이 주시하는 채널이 아닌 다른 채널의 메시지
            # 서버 이름과 채널 이름을 추가하여 출력
            guild_name = message.guild.name if message.guild else "DM"
            channel_name = message.channel.name if isinstance(message.channel, discord.TextChannel) else "DM"
            
            print(f"[알림] 메시지 도착! [[{guild_name} #{channel_name}] {message.author.display_name}")


    async def list_guilds(self):
        # 봇이 연결된 길드(서버) 목록을 반환
        # bot.guilds는 봇이 준비된 후에야 채워집니다.
        return [(idx + 1, guild.name, guild.id) for idx, guild in enumerate(self.bot.guilds)]

    async def set_guild_by_index(self, idx):
        guilds = self.bot.guilds
        if 1 <= idx <= len(guilds):
            self.guild = guilds[idx - 1]
            self.channel = None # 서버 변경 시 채널 초기화
            self.channel_list = self.guild.text_channels
            return True
        return False

    async def list_channels(self):
        if not self.guild:
            print("[오류] 채널 목록을 보려면 먼저 서버를 선택하세요.")
            return []
        # 현재 서버의 텍스트 채널 목록만 가져오기
        self.channel_list = [ch for ch in self.guild.channels if isinstance(ch, discord.TextChannel)]
        return [(idx + 1, ch.name, ch.id) for idx, ch in enumerate(self.channel_list)]

    async def set_channel_by_index_or_id_or_name(self, value):
        if not self.guild:
            print("[오류] 채널을 설정하려면 먼저 서버를 선택하세요.")
            return False

        # 1. 인덱스로 시도
        try:
            idx = int(value)
            if 1 <= idx <= len(self.channel_list):
                self.channel = self.channel_list[idx - 1]
                return True
        except ValueError:
            pass # 숫자가 아니면 다음 단계로 진행

        # 2. ID로 시도 (숫자이지만 인덱스가 아닌 경우)
        try:
            channel_id = int(value)
            channel = self.bot.get_channel(channel_id)
            if channel and channel.guild == self.guild and isinstance(channel, discord.TextChannel):
                self.channel = channel
                return True
        except ValueError:
            pass # 유효한 ID가 아니면 다음 단계로 진행
        
        # 3. 이름으로 시도
        if isinstance(value, str):
            lowered_value = value.lower()
            for ch in self.channel_list:
                if ch.name.lower() == lowered_value and isinstance(ch, discord.TextChannel):
                    self.channel = ch
                    return True
        
        return False # 모든 시도 실패

    async def process_message_mentions(self, message: discord.Message) -> str:
        # 메시지 내용을 파싱하여 멘션(사용자, 역할, 채널)을 이름으로 변환
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

    async def fetch_recent_messages_cli(self, count=20):
        if not self.channel:
            print("[오류] 먼저 채널을 선택하세요.")
            return # 아무것도 반환하지 않음
            
        messages = []
        try:
            async for msg in self.channel.history(limit=count):
                messages.append(msg)
        except discord.errors.Forbidden:
            print("[오류] 채널 메시지 읽기 권한이 없습니다. 봇 역할 권한을 확인하세요.")
            return
        except Exception as e:
            print(f"[오류] 메시지 가져오기 실패: {e}")
            return
        
        print(f"[최근 {count}개 메시지] (채널: #{self.channel.name})")
        if not messages:
            print("[정보] 불러올 메시지가 없습니다.")
        # 가장 오래된 메시지부터 출력하도록 순서 뒤집기
        for msg in reversed(messages): 
            timestamp = (msg.created_at + timedelta(hours=9)).strftime("%m/%d %H:%M:%S")
            processed_content = await self.process_message_mentions(msg)
            print(f"[{timestamp}] {msg.author.display_name}: {processed_content}")

    async def send_message(self, content):
        if not self.channel:
            print("[오류] 메시지를 보낼 채널이 선택되지 않았습니다. '/setchannel'을 사용하세요.")
            return None
        
        try:
            message = await self.channel.send(content)
            timestamp = (message.created_at + timedelta(hours=9)).strftime("%m/%d %H:%M:%S")
            print(f"[{timestamp}] {message.author.display_name}: {message.content}") # 본인 메시지임을 표시
            return message
        except discord.errors.Forbidden:
            print("[오류] 채널에 메시지를 보낼 권한이 없습니다. 봇 역할 권한을 확인하세요.")
            return None
        except Exception as e:
            print(f"[오류] 메시지 전송 실패: {e}")
            return None

    async def send_file(self, file_path: str, content: str | None):
        """
        지정된 파일과 함께 메시지를 현재 채널에 전송합니다.
        """
        if not self.channel:
            print("[오류] 파일을 보낼 채널이 선택되지 않았습니다. '/setchannel'을 사용하세요.")
            return None
        
        if not os.path.exists(file_path):
            print(f"[오류] 파일을 찾을 수 없습니다: '{file_path}'")
            return None
            
        try:
            # discord.File 객체 생성
            # file_path는 전송할 파일의 경로
            # filename 인자는 디스코드에 표시될 파일 이름 (선택 사항, 없으면 file_path의 파일 이름 사용)
            discord_file = discord.File(file_path)
            
            # 파일과 함께 메시지 전송
            # content 인자는 파일과 함께 보낼 텍스트 메시지 (선택 사항)
            message = await self.channel.send(content=content, file=discord_file)
            
            timestamp = (message.created_at + timedelta(hours=9)).strftime("%m/%d %H:%M:%S")
            # 파일이 전송되었음을 표시
            print(f"[{timestamp}] 나 ({self.bot.user.display_name}): (파일 첨부) {file_path.split(os.sep)[-1]}")
            if content:
                print(f"  └ 메시지: {content}") # 파일과 함께 보낸 메시지가 있다면 출력
            
            return message
        except discord.errors.Forbidden:
            print("[오류] 채널에 파일을 첨부할 권한이 없습니다. 봇 역할 권한을 확인하세요.")
            return None
        except Exception as e:
            print(f"[오류] 파일 전송 실패: {e}")
            return None

async def setup(bot):
    await bot.add_cog(ChatBridge(bot))
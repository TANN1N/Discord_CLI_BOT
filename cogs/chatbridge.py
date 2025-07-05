import discord
from discord.ext import commands
from datetime import timedelta

from services.bot_service import DiscordBotService 
from models.app_state import AppState
from core.event_manager import EventManager
from core.event_types import EventType

class ChatBridge(commands.Cog):
    def __init__(self, bot: commands.Bot, event_manager: EventManager):
        self.bot = bot
        self.event_manager = event_manager
    
    @commands.Cog.listener()
    async def on_ready(self):
        """봇이 Discord에 연결될 때 호출됩니다."""
        await self.event_manager.publish(EventType.BOT_READY, self.bot.user) # Bot ready Event pub
        # 이 시점에서 bot_service가 Discord Bot 객체를 통해 데이터에 접근할 준비가 됩니다.
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """새로운 메시지가 도착할 때 호출됩니다."""
        # 봇 자신이 보낸 메시지는 무시합니다.
        if message.author == self.bot.user: 
            return
        
        await self.event_manager.publish(EventType.NEW_INCOMING_MESSAGE, message)
        
        # 메시지를 가공하는 것은 View가 결정하도록 함
        # 메시지 멘션 처리는 BotService의 유틸리티 메서드를 활용합니다.
        # processed_content = await self.bot_service._process_message_mentions(message) 
        
        # # 현재 설정된 채널과 비교하여 메시지를 출력합니다.
        # if message.channel == self.app_state.current_channel: 
        #     self.event_manager.publish("NEW_MESSAGE_RECEIVED", f"[{timestamp}] {message.author.display_name}: {processed_content}")
        # else: 
        #     # 봇이 주시하는 채널이 아닌 다른 채널의 메시지
        #     guild_name = message.guild.name if message.guild else "DM"
        #     channel_name = message.channel.name if isinstance(message.channel, discord.TextChannel) else "DM"
        #     self.event_manager.publish("DISCORD_MESSAGE_RECEIVED", message) # Discord message received Event pub

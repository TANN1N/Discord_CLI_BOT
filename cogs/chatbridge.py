import discord
import logging
from discord.ext import commands

from core.event_manager import EventManager
from core.event_types import EventType

logger = logging.getLogger(__name__)

class ChatBridge(commands.Cog):
    def __init__(self, bot: commands.Bot, event_manager: EventManager):
        self.bot = bot
        self.event_manager = event_manager
    
    @commands.Cog.listener()
    async def on_ready(self):
        """봇이 Discord에 연결될 때 호출됩니다."""
        logger.info("Bot is ready and connected to Discord as %s (ID: %s)", self.bot.user, self.bot.user.id)
        await self.event_manager.publish(EventType.BOT_STATUS_READY, self.bot.user)
        # 이 시점에서 bot_service가 Discord Bot 객체를 통해 데이터에 접근할 준비가 됩니다.
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """새로운 메시지가 도착할 때 호출됩니다."""

        await self.event_manager.publish(EventType.MESSAGE_RECEIVED, message)

        if message.author != self.bot.user:
            logger.debug(
                "New message received in #%s from %s: %s",
                message.channel.name,
                message.author.name,
                message.content
            )

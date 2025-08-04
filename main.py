import os
import asyncio
import logging

from discord.ext import commands
from discord import Intents
from dotenv import load_dotenv

# Core
from core.event_manager import EventManager
from core.event_types import EventType
from core.logger import setup_logging

# Models
from models.app_state import AppState

# Controllers
from controllers.command_controller import CommandController

# Views
from views.tui_view import TUIView

# Services
from services.bot_service import DiscordBotService

# Cogs
from cogs.chatbridge import ChatBridge

logger = logging.getLogger(__name__)


async def main():
    # 0. Initialize Logging
    load_dotenv()
    setup_logging()
    logger.info("Application starting...")

    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        # Log the error before raising it
        logger.critical("DISCORD_TOKEN environment variable is not set.")
        raise RuntimeError("DISCORD_TOKEN environment variable is not set.")

    # 1. Initialize Core Components
    logger.info("Initializing core components...")
    app_state = AppState()
    event_manager = EventManager()

    # 2. Setup Discord Bot
    logger.info("Setting up Discord bot...")
    intents = Intents.default()
    intents.message_content = True
    intents.members = True
    bot = commands.Bot(command_prefix="!", intents=intents)

    # 3. Initialize Services, Controllers, and Views with Dependency Injection
    logger.info("Initializing MVC components...")
    bot_service = DiscordBotService(bot, app_state, event_manager)
    command_controller = CommandController(app_state, event_manager)
    tui_view = TUIView(command_controller, app_state, event_manager)

    # 4. Register Event Listeners for the View
    logger.info("Registering view event listeners...")
    tui_view.register_event_listeners()

    # 5. Setup Cogs
    logger.info("Setting up Cogs...")
    chat_bridge_cog = ChatBridge(bot, event_manager)
    await bot.add_cog(chat_bridge_cog)
    logger.info("Cogs added successfully.")

    # 6. Define Bot Lifecycle Events
    @bot.event
    async def on_ready():
        logger.info("Bot is ready. Logged in as %s (ID: %s)", bot.user.name, bot.user.id)
        await event_manager.publish(EventType.SHOW_TEXT, f"\n--- 봇 연결 성공! ---")
        await event_manager.publish(EventType.SHOW_TEXT, f"로그인 완료: {bot.user.name} (ID: {bot.user.id})")
        await event_manager.publish(EventType.BOT_READY) # Notify view that the bot is ready

    @bot.event
    async def on_connect():
        logger.debug("Connecting to discord...")
        await event_manager.publish(EventType.SHOW_TEXT, "Discord에 연결 중...")

    @bot.event
    async def on_disconnect():
        logger.debug("Connection lost")
        await event_manager.publish(EventType.SHOW_TEXT, "Discord에서 연결 끊김.")

    @bot.event
    async def on_resumed():
        logger.debug("Connection resumed")
        await event_manager.publish(EventType.SHOW_TEXT, "Discord 연결 재개됨.")

    # 7. Start Bot and CLI concurrently
    try:
        # Start the bot in the background
        bot_task = asyncio.create_task(bot.start(TOKEN))
        # Start the TUI in the foreground
        tui_task = asyncio.create_task(tui_view.run_tui())

        await asyncio.wait([bot_task, tui_task], return_when="FIRST_COMPLETED")

    except KeyboardInterrupt:
        await event_manager.publish(EventType.SHOW_TEXT, "\n사용자에 의해 봇 시작이 중단되었습니다.")
    except Exception as e:
        await event_manager.publish(EventType.ERROR, f"\nFATAL ERROR: 봇 시작 중 오류가 발생했습니다: {e}")
    finally:
        if bot and not bot.is_closed():
            await bot.close()
            await event_manager.publish(EventType.SHOW_TEXT, "봇이 성공적으로 종료되었습니다.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n사용자에 의해 봇이 완전히 종료되었습니다.")
    except Exception as e:
        print(f"\n처리되지 않은 치명적인 예외가 발생했습니다: {e}")
        # 현 시점에서 로거가 동작하지 않을 확률이 높지만 일단 시도는 해봄.
        logging.critical("처리되지 않은 치명적인 예외 발생", exc_info=True)

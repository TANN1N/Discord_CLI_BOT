import os
import asyncio

from discord.ext import commands
from discord import Intents
from dotenv import load_dotenv

from services.bot_service import DiscordBotService
from cogs.chatbridge import ChatBridge
from cli.cli_manager import CLIManager 

async def main():
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN 환경 변수가 설정되지 않았습니다.")

    intents = Intents.default()
    intents.message_content = True
    intents.members = True         

    bot = commands.Bot(command_prefix="!", intents=intents)
    
    bot_service = DiscordBotService(bot)

    chat_bridge_cog = ChatBridge(bot, bot_service) 
    await bot.add_cog(chat_bridge_cog)

    # CLIManager 인스턴스를 생성하고 서비스 객체를 주입합니다.
    cli_manager = CLIManager(bot_service)

    @bot.event
    async def on_ready():
        print(f"\n--- 봇 연결 성공! ---")
        print(f"로그인 완료: {bot.user.name} (ID: {bot.user.id})")
        # 봇이 준비되면 CLI 루프를 별도의 비동기 태스크로 시작합니다.
        asyncio.create_task(cli_manager.run_cli())

    @bot.event
    async def on_connect():
        print("Discord에 연결 중...")

    @bot.event
    async def on_disconnect():
        print("Discord에서 연결 끊김.")

    @bot.event
    async def on_resumed():
        print("Discord 연결 재개됨.")

    try:
        await bot.start(TOKEN)
    except KeyboardInterrupt:
        print("\n사용자에 의해 봇 시작이 중단되었습니다.")
    except Exception as e:
        print(f"\nFATAL ERROR: 봇 시작 중 오류가 발생했습니다: {e}")
    finally:
        if not bot.is_closed():
            await bot.close()
            print("봇이 성공적으로 종료되었습니다.")


if __name__ == "__main__":
    print("Discord CLI 봇 실행 시작...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n사용자에 의해 봇이 완전히 종료되었습니다.")
    except Exception as e:
        print(f"\n처리되지 않은 치명적인 예외가 발생했습니다: {e}")
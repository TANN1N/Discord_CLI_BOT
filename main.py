import os
import asyncio
from discord.ext import commands
from discord import Intents
from dotenv import load_dotenv

from cogs.chatbridge import ChatBridge
from cli.cli_handler import CLIHandler

async def main():
    load_dotenv()
    TOKEN = str(os.getenv("DISCORD_TOKEN"))

    intents = Intents.default()
    intents.message_content = True
    intents.members = True

    bot = commands.Bot(command_prefix="!", intents=intents)

    chat_bridge_cog = ChatBridge(bot)
    await bot.add_cog(chat_bridge_cog)

    @bot.event
    async def on_ready():
        print(f"\n--- 봇 연결 성공! ---")
        print(f"로그인 완료: {bot.user.name} (ID: {bot.user.id})")
        print("--------------------")
        # 봇이 준비된 후 CLI 루프 시작
        asyncio.create_task(cli_loop(chat_bridge_cog))

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
        print("\n봇이 종료됩니다.")
    except Exception as e:
        print(f"\nFATAL ERROR: 봇 시작 중 치명적인 오류 발생: {e}")

async def cli_loop(chat_bridge_cog: ChatBridge):
    """
    터미널에서 사용자 입력을 받아 봇 기능을 호출하는 비동기 루프
    """
    await asyncio.sleep(1) # 봇 on_ready가 완전히 처리될 시간을 줍니다.
    cli_handler = CLIHandler(chat_bridge_cog) # CLIHandler 인스턴스 생성

    # --- 초기 설정 시작 ---
    print("\n--- 초기 봇 설정 ---")

    # 1. 길드 선택
    selected_guild = False
    while not selected_guild:
        guilds = await cli_handler._list_guilds("") # 길드 목록 표시
        if not guilds:
            print("[오류] 봇이 참여하고 있는 서버가 없습니다. 서버에 봇을 초대해주세요.")
            await chat_bridge_cog.bot.close()
            return # 봇 종료

        guild_input = await asyncio.to_thread(input, "서버 인덱스를 입력하세요: ")
        selected_guild = await cli_handler._set_guild(guild_input.strip())
        if not selected_guild:
            print("[안내] 다시 시도해주세요.")

    # 2. 채널 선택
    selected_channel = False
    while not selected_channel:
        channels = await cli_handler._list_channels("") # 채널 목록 표시
        if not channels:
            print("[오류] 선택된 서버에 텍스트 채널이 없습니다. 다른 서버를 선택하거나 채널을 생성해주세요.")
            await chat_bridge_cog.bot.close()
            return # 봇 종료

        channel_input = await asyncio.to_thread(input, "채널 인덱스, ID 또는 이름을 입력하세요: ")
        selected_channel = await cli_handler._set_channel(channel_input.strip())
        if not selected_channel:
            print("[안내] 다시 시도해주세요.")

    print("-------------------\n")
    print("명령어 도움말을 보려면 '/help'를 입력하세요.")
    # --- 초기 설정 끝 ---

    while True:
        try:
            user_input = await asyncio.to_thread(input, "> ")

            if user_input.startswith('/'):
                parts = user_input.split(' ', 1)
                command = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""

                should_quit = await cli_handler.handle_command(command, arg)
                if should_quit:
                    break
            else:
                if user_input.strip():
                    await chat_bridge_cog.send_message(user_input)

        except EOFError:
            print("\nEOF 감지: 봇을 종료합니다.")
            await chat_bridge_cog.bot.close()
            break
        except Exception as e:
            print(f"[CLI 오류] 예외 발생: {e}")

if __name__ == "__main__":
    print("봇 실행 및 CLI 인터페이스 시작.")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n사용자에 의해 봇이 종료되었습니다.")
    except Exception as e:
        print(f"\n최종 처리되지 않은 예외: {e}")
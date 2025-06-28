from imaplib import Commands
import os
import asyncio
from discord.ext import commands
from discord import Intents
from dotenv import load_dotenv

from cogs.chatbridge import ChatBridge
from cli.cli_handler import CLIHandler

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.patch_stdout import patch_stdout

COMMANDS = [
    "/help", "/clear", "/quit",
    "/listguilds", "setguild",
    "/listchannels", "/setchannel",
    "/read", "/multiline", "/attach"
]

command_completer = WordCompleter(COMMANDS, ignore_case=True)

async def prompt_cli_loop(chat_bridge_cog: ChatBridge):
    session = PromptSession(completer=command_completer)
    cli_handler = CLIHandler(chat_bridge_cog)

    if not await select_guild(cli_handler):
        await chat_bridge_cog.bot.close()
        return

    if not await select_channel(cli_handler):
        await chat_bridge_cog.bot.close()
        return

    print("-----------------------------")
    print("명령어 도움말은 '/help'를 입력하세요.")
    with patch_stdout():
        while True:
            try:
                user_input = await session.prompt_async("> ")
                if not user_input.strip():
                    continue
                if user_input.startswith('/'):
                    parts = user_input.split(' ', 1)
                    command = parts[0].lower()
                    arg = parts[1] if len(parts) > 1 else ""
                    if await cli_handler.handle_command(command, arg):
                        break
                elif user_input.strip():
                    await chat_bridge_cog.send_message(user_input)
            except (EOFError, KeyboardInterrupt):
                print("\n봇을 종료합니다.")
                await chat_bridge_cog.bot.close()
                break
            except Exception as e:
                print(f"[CLI 오류] 예외 발생: {e}")

async def select_guild(cli_handler):
    print("\n--- 초기 봇 설정: 서버 선택 ---")
    while True:
        guilds = await cli_handler._list_guilds("")
        if not guilds:
            print("[오류] 봇이 참여 중인 서버가 없습니다.")
            return False
        guild_input = await asyncio.to_thread(input, "서버 인덱스를 입력하세요: ")
        if await cli_handler._set_guild(guild_input.strip()):
            print("[성공] 서버가 설정되었습니다.")
            return True
        print("[실패] 다시 시도해주세요.")

async def select_channel(cli_handler):
    print("\n--- 초기 봇 설정: 채널 선택 ---")
    while True:
        channels = await cli_handler._list_channels("")
        if not channels:
            print("[오류] 선택한 서버에 텍스트 채널이 없습니다.")
            return False
        channel_input = await asyncio.to_thread(input, "채널 인덱스, ID 또는 이름을 입력하세요: ")
        if await cli_handler._set_channel(channel_input.strip()):
            print("[성공] 채널이 설정되었습니다.")
            return True
        print("[실패] 다시 시도해주세요.")

async def main():
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN이 설정되지 않았습니다.")

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
        asyncio.create_task(prompt_cli_loop(chat_bridge_cog))

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
        print(f"\nFATAL ERROR: 봇 시작 중 오류: {e}")

if __name__ == "__main__":
    print("봇 실행 및 고급 CLI 시작.")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n사용자에 의해 봇이 종료되었습니다.")
    except Exception as e:
        print(f"\n최종 처리되지 않은 예외: {e}")
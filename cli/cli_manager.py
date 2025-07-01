import asyncio
import os

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter, NestedCompleter, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.patch_stdout import patch_stdout

from services.bot_service import DiscordBotService
from cli.cli_handler import CLIHandler

class CLIManager:
    def __init__(self, bot_service: DiscordBotService):
        self.bot_service = bot_service
        self.cli_handler = CLIHandler(bot_service)
        self.session = PromptSession()

    async def _select_guild_cli(self) -> bool:
        """초기 봇 설정: 서버를 선택합니다."""
        print("\n--- 초기 봇 설정: 서버 선택 ---")
        while True:
            await self.cli_handler._list_guilds("") 
            if not self.bot_service.bot.guilds:
                print("[오류] 봇이 참여 중인 서버가 없습니다. 봇을 서버에 초대해 주세요.")
                return False

            guild_input = await asyncio.to_thread(input, "서버 인덱스, ID 또는 이름을 입력하세요: ")
            if await self.bot_service.select_guild(guild_input.strip()):
                print(f"[성공] 서버가 설정되었습니다: {self.bot_service.current_guild.name}")
                return True
            print("[실패] 다시 시도해 주세요.")

    async def _select_channel_cli(self) -> bool:
        """초기 봇 설정: 채널을 선택합니다."""
        print("\n--- 초기 봇 설정: 채널 선택 ---")
        while True:
            await self.cli_handler._list_channels("")
            if not await self.bot_service.get_channels_in_current_guild_info():
                print("[오류] 선택한 서버에 텍스트 채널이 없습니다.")
                return False

            channel_input = await asyncio.to_thread(input, "채널 인덱스, ID 또는 이름을 입력하세요: ")
            if await self.bot_service.select_channel(channel_input.strip()):
                print(f"[성공] 채널이 설정되었습니다: #{self.bot_service.current_channel.name}")
                print("\n[정보] 채널 입장: 최근 메시지를 불러오는 중...")
                messages = await self.bot_service.fetch_recent_messages()
                if messages:
                    for msg_line in messages:
                        print(msg_line)
                    print(f"[정보] 총 {len(messages)}개의 메시지를 불러왔습니다.")
                else:
                    print("[정보] 이 채널에는 아직 메시지가 없거나 불러올 수 없습니다.")
                return True
            print("[실패] 다시 시도해 주세요.")

    async def run_cli(self):
        """CLI 루프를 실행합니다."""
        if not await self._select_guild_cli():
            print("서버 설정에 실패하여 봇을 종료합니다.")
            await self.bot_service.bot.close()
            return

        if not await self._select_channel_cli():
            print("채널 설정에 실패하여 봇을 종료합니다.")
            await self.bot_service.bot.close()
            return

        print("-----------------------------")
        print("명령어 도움말은 '/help'를 입력해 주세요.")
        
        with patch_stdout(): 
            while True:
                try:
                    user_input = await self.session.prompt_async("> ")

                    if not user_input.strip():
                        continue
                    
                    if user_input.startswith('/'):
                        parts = user_input.split(' ', 1)
                        command = parts[0].lower()
                        arg = parts[1] if len(parts) > 1 else ""
                        if await self.cli_handler.handle_command(command, arg): 
                            break
                    else: 
                        await self.bot_service.send_message(user_input) 
                except (EOFError, KeyboardInterrupt):
                    print("\n봇을 종료합니다.")
                    await self.bot_service.bot.close()
                    break
                except Exception as e:
                    print(f"[CLI 오류] 예외 발생: {e}")
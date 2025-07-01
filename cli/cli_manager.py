# your_bot_project/cli/cli_manager.py
import asyncio
import os

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter, NestedCompleter, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.patch_stdout import patch_stdout

from services.bot_service import DiscordBotService
from cli.cli_handler import CLIHandler

class GuildDynamicCompleter(Completer):
    """현재 봇이 접근 가능한 길드 이름을 동적으로 자동 완성합니다."""
    def __init__(self, bot_service: DiscordBotService):
        self.bot_service = bot_service

    def get_completions(self, document: Document, complete_event):
        word_before_cursor = document.get_word_before_cursor(pattern=True)
        
        guild_names = []
        if self.bot_service.bot.is_ready(): # 봇이 준비된 상태인지 확인
            for guild in self.bot_service.bot.guilds:
                guild_names.append(guild.name)

        for guild_name in guild_names:
            if guild_name.lower().startswith(word_before_cursor.lower()):
                yield Completion(
                    guild_name,
                    start_position=-len(word_before_cursor),
                    display=f"🌍 {guild_name}",
                    display_meta="서버 이름"
                )

class ChannelDynamicCompleter(Completer):
    """현재 선택된 길드의 채널 이름을 동적으로 자동 완성합니다."""
    def __init__(self, bot_service: DiscordBotService):
        self.bot_service = bot_service

    def get_completions(self, document: Document, complete_event):
        word_before_cursor = document.get_word_before_cursor(pattern=True)
        
        channel_names = []
        if self.bot_service.current_guild: # 현재 길드가 선택된 상태인지 확인
            # DiscordBotService의 캐싱된 채널 목록을 사용합니다.
            for channel in self.bot_service._cached_channels: 
                channel_names.append(channel.name)

        for channel_name in channel_names:
            if channel_name.lower().startswith(word_before_cursor.lower()):
                yield Completion(
                    channel_name,
                    start_position=-len(word_before_cursor),
                    display=f"#{channel_name}",
                    display_meta="채널 이름"
                )

# --- CLIManager 클래스: CLI의 모든 동작을 관리 ---
class CLIManager:
    def __init__(self, bot_service: DiscordBotService):
        self.bot_service = bot_service
        self.cli_handler = CLIHandler(bot_service) # CLIHandler 인스턴스 생성 및 서비스 주입

        # Dynamic Completer 인스턴스 생성 및 서비스 주입
        self.guild_completer = GuildDynamicCompleter(self.bot_service)
        self.channel_completer = ChannelDynamicCompleter(self.bot_service)

        # NestedCompleter를 사용하여 명령어 구조를 정의합니다.
        self.main_completer = NestedCompleter.from_nested_dict({
            '/help': None, '/h': None,
            '/clear': None, '/cls': None,
            '/quit': None,
            '/listguilds': None, '/lg': None,
            '/setguild': {
                '': self.guild_completer # 'setguild' 다음에는 길드 자동 완성
            },
            '/sg': {
                '': self.guild_completer
            },
            '/listchannels': None, '/lc': None,
            '/setchannel': {
                '': self.channel_completer # 'setchannel' 다음에는 채널 자동 완성
            },
            '/sc': {
                '': self.channel_completer
            },
            '/read': None, '/r': None,
            '/multiline': None, '/ml': None,
            '/attach': None, '/a': None, 
        })
        
        self.session = PromptSession(completer=self.main_completer)

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
                    user_input = await self.session.prompt_async(
                        "> ",
                        pre_run=self._update_dynamic_completers_on_pre_run
                    )
                    
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

    def _update_dynamic_completers_on_pre_run(self):
        # 이 함수는 현재의 DynamicCompleter 구현에서는 직접적인 데이터 업데이트 로직이 필요 없습니다.
        # 데이터 업데이트는 select_guild() 같은 BotService 메서드 호출 시점에 이루어집니다.
        pass
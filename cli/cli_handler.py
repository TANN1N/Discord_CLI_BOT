import os
import asyncio

from services.bot_service import DiscordBotService 

class CLIHandler:
    def __init__(self, bot_service: DiscordBotService):
        self.bot_service = bot_service
        # 명령어와 해당 핸들러 메서드를 매핑합니다.
        self.commands = {
            '/help': self._help,
            '/h': self._help, # 단축 명령어
            '/listguilds': self._list_guilds,
            '/lg': self._list_guilds,
            '/setguild': self._set_guild,
            '/sg': self._set_guild,
            '/listchannels': self._list_channels,
            '/lc': self._list_channels,
            '/setchannel': self._set_channel,
            '/sc': self._set_channel,
            '/read': self._read,
            '/r': self._read,
            '/multiline': self._multiline_input,
            '/ml': self._multiline_input,
            '/attach': self._attach_file,
            '/a': self._attach_file,
            '/clear': self._clear,
            '/cls': self._clear,
            '/quit': self._quit,
        }

    async def handle_command(self, command: str, arg: str) -> bool:
        """
        CLI 명령어를 처리하고, 봇 종료가 필요한 경우 True를 반환합니다.
        그 외의 경우 False를 반환합니다.
        """
        handler = self.commands.get(command)
        if handler:
            # 모든 핸들러는 bool 값을 반환하도록 통일했습니다.
            return await handler(arg)
        else:
            print(f"[오류] 알 수 없는 명령어입니다: {command}")
            print("명령어 도움말을 보려면 '/help'를 입력해 주세요.")
            return False

    async def _help(self, arg: str) -> bool:
        """명령어 도움말을 표시합니다."""
        print("\n--- 사용 가능한 명령어 ---")
        # 긴 이름의 명령어만 출력하여 가독성을 높입니다.
        displayed_commands = sorted([cmd for cmd in self.commands if len(cmd) > 3 and not cmd.startswith('/')]) # 예: '/help'는 제외하고 'help'만 표시
        
        for cmd_key, handler_func in self.commands.items():
            if not cmd_key.startswith('/'): # /help를 통해 보여줄 명령어는 / 접두사가 붙어있는 것만
                continue
            
            if len(cmd_key) > 3: # 단축 명령어는 제외하고 긴 명령어만 도움말에 표시
                doc = handler_func.__doc__.strip() if handler_func.__doc__ else "설명 없음."
                print(f"{cmd_key:<15} - {doc}")
        print("--------------------------\n")
        return False

    async def _list_guilds(self, arg: str) -> bool:
        """봇이 참여하고 있는 서버 목록을 표시합니다."""
        guilds = await self.bot_service.get_all_guilds_info()
        if guilds:
            print("\n--- 서버 목록 ---")
            for idx, name, _id in guilds:
                # 현재 선택된 길드를 표시합니다.
                current_indicator = " (현재 선택됨)" if self.bot_service.current_guild and self.bot_service.current_guild.id == _id else ""
                print(f"  [{idx}] {name} (ID: {_id}){current_indicator}")
            print("-----------------\n")
        else:
            print("[정보] 참여하고 있는 서버가 없습니다.")
        return False

    async def _set_guild(self, arg: str) -> bool:
        """서버 인덱스, ID 또는 이름을 사용하여 현재 서버를 설정합니다."""
        if not arg:
            print("[오류] 서버 인덱스, ID 또는 이름을 입력해 주세요. 예: /setguild 1")
            return False
        
        if await self.bot_service.select_guild(arg):
            print(f"[성공] 서버가 '{self.bot_service.current_guild.name}'(으)로 설정되었습니다.")
            return False
        else:
            print("[오류] 유효하지 않은 서버 인덱스, ID 또는 이름입니다.")
            return False

    async def _list_channels(self, arg: str) -> bool:
        """현재 선택된 서버의 채널 목록을 표시합니다."""
        if not self.bot_service.current_guild:
            print("[오류] 채널 목록을 보려면 먼저 서버를 선택해 주세요. '/setguild' 사용.")
            return False
            
        channels = await self.bot_service.get_channels_in_current_guild_info()
        if channels:
            print(f"\n--- 채널 목록 (서버: {self.bot_service.current_guild.name}) ---")
            for idx, name, _id in channels:
                # 현재 선택된 채널을 표시합니다.
                current_indicator = " (현재 선택됨)" if self.bot_service.current_channel and self.bot_service.current_channel.id == _id else ""
                print(f"  [{idx}] #{name} (ID: {_id}){current_indicator}")
            print("-------------------------------------------\n")
        else:
            print(f"[정보] '{self.bot_service.current_guild.name}' 서버에 텍스트 채널이 없거나, 권한이 없습니다.")
        return False

    async def _set_channel(self, arg: str) -> bool:
        """채널 인덱스, ID 또는 이름을 사용하여 현재 채널을 설정합니다."""
        if not arg:
            print("[오류] 채널 인덱스, ID 또는 이름을 입력해 주세요. 예: /setchannel 1 또는 /setchannel 123456789012345678 또는 /setchannel 일반")
            return False

        if await self.bot_service.select_channel(arg):
            print(f"[성공] 채널이 '#{self.bot_service.current_channel.name}'(으)로 설정되었습니다.")
            await self._read("") # 채널 설정 후 최근 메시지를 자동으로 읽어옵니다.
            return False
        else:
            print("[오류] 유효하지 않은 채널 인덱스, ID 또는 이름입니다.")
            return False

    async def _read(self, arg: str) -> bool:
        """현재 채널의 최근 메시지를 지정된 개수(기본값 20)만큼 불러옵니다."""
        count = 20
        if arg:
            try:
                count = int(arg)
                if not (1 <= count <= 100):
                    print("[오류] 읽을 메시지 개수는 1에서 100 사이여야 합니다.")
                    return False
            except ValueError:
                print("[오류] 읽을 메시지 개수는 숫자여야 합니다.")
                return False
        
        messages = await self.bot_service.fetch_recent_messages(count)
        if messages:
            print(f"\n[최근 {count}개 메시지] (채널: #{self.bot_service.current_channel.name})")
            for msg_line in messages:
                print(msg_line)
        elif self.bot_service.current_channel: 
            print("[정보] 불러올 메시지가 없거나 오류가 발생했습니다. 권한을 확인해 주세요.")
        else: 
            print("[오류] 먼저 채널을 선택해 주세요. '/setchannel' 사용.")
        return False

    async def _clear(self, arg: str) -> bool:
        """터미널 화면을 지웁니다."""
        os.system('cls' if os.name == 'nt' else 'clear')
        print("[정보] 화면이 지워졌습니다.")
        return False

    async def _multiline_input(self, arg: str) -> bool:
        """여러 줄 메시지 입력 모드로 전환합니다. 입력을 마치려면 새로운 줄에 @END를 입력하세요."""
        print("\n--- 여러 줄 메시지 입력 모드 ---")
        print("  입력을 마치려면 새로운 줄에 '@END'를 입력하고 Enter를 누르세요.")
        print("----------------------------")

        lines = []
        while True:
            # asyncio.to_thread를 사용하여 blocking input을 비동기적으로 처리합니다.
            line = await asyncio.to_thread(input, ">> ")
            if line.strip().upper() == "@END": 
                break
            lines.append(line)
        
        full_message = "\n".join(lines)
        if full_message.strip(): 
            await self.bot_service.send_message(full_message)
        else:
            print("[정보] 입력된 내용이 없어 메시지를 전송하지 않았습니다.")
        print("\n--- 여러 줄 메시지 입력 모드 종료 ---\n")
        return False

    async def _attach_file(self, arg: str) -> bool:
        """지정된 파일을 현재 채널에 첨부합니다. (예: /a C:/path/file.png '캡션')"""
        if not arg:
            print("[오류] 첨부할 파일 경로를 입력하세요. 사용법: /attach <파일경로> [선택적 메시지]")
            return False

        # 첫 번째 공백을 기준으로 파일 경로와 메시지를 분리합니다.
        parts = arg.split(' ', 1)
        file_path = parts[0]
        message_content = parts[1] if len(parts) > 1 else None

        # 파일 경로에 따옴표가 있을 경우 제거합니다.
        file_path = file_path.strip('\'"')

        if not os.path.exists(file_path):
            print(f"[오류] 지정된 파일 경로를 찾을 수 없습니다: '{file_path}'")
            return False

        await self.bot_service.send_file(file_path, message_content)
        print(f"[정보] 파일 전송 시도: '{file_path}'")
        return False

    async def _quit(self, arg: str) -> bool:
        """봇을 종료합니다."""
        print("[정보] 봇을 종료합니다...")
        # 봇 객체를 직접 닫도록 bot_service를 통해 접근합니다.
        await self.bot_service.bot.close()
        return True # 종료 신호를 반환합니다.
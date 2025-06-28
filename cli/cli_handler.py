import os
import asyncio
from cogs.chatbridge import ChatBridge

class CLIHandler:
    def __init__(self, chat_bridge_cog: ChatBridge):
        self.chat_bridge_cog = chat_bridge_cog
        self.commands = {
            '/help': self._help,
            '/h': self._help,
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
        handler = self.commands.get(command)
        if handler:
            return await handler(arg)
        else:
            print(f"[오류] 알 수 없는 명령어입니다: {command}")
            print("명령어 도움말을 보려면 '/help'를 입력하세요.")
            return False

    async def _help(self, arg: str):
        """명령어 도움말을 표시합니다."""
        print("사용 가능한 명령어:")
        for cmd, handler in self.commands.items():
            if len(cmd) <= 3:
                continue
            doc = handler.__doc__.strip() if handler.__doc__  else ""
            print(f"{cmd:<15} - {doc}")
        return False

    async def _list_guilds(self, arg: str):
        """봇이 참여하고 있는 서버 목록을 표시합니다."""
        guilds = await self.chat_bridge_cog.list_guilds()
        if guilds:
            print("\n--- 서버 목록 ---")
            for idx, name, _id in guilds:
                print(f"  [{idx}] {name} (ID: {_id})")
            print("-----------------\n")
        else:
            print("[정보] 참여하고 있는 서버가 없습니다.")
        return guilds

    async def _set_guild(self, arg: str) -> bool:
        """서버 인덱스를 사용하여 현재 서버를 설정합니다."""
        if not arg:
            print("[오류] 서버 인덱스를 입력해주세요. 예: /setguild 1")
            return False
        try:
            idx = int(arg)
            if await self.chat_bridge_cog.set_guild_by_index(idx):
                print(f"[성공] 서버가 '{self.chat_bridge_cog.guild.name}'(으)로 설정되었습니다.")
                return True
            else:
                print("[오류] 유효하지 않은 서버 인덱스입니다.")
                return False
        except ValueError:
            print("[오류] 서버 인덱스는 숫자여야 합니다.")
            return False

    async def _list_channels(self, arg: str):
        """현재 선택된 서버의 채널 목록을 표시합니다."""
        channels = await self.chat_bridge_cog.list_channels()
        if channels:
            print(f"\n--- 채널 목록 (서버: {self.chat_bridge_cog.guild.name}) ---")
            for idx, name, _id in channels:
                print(f"  [{idx}] #{name} (ID: {_id})")
            print("-------------------------------------------\n")
        else:
            if self.chat_bridge_cog.guild:
                print(f"[정보] '{self.chat_bridge_cog.guild.name}' 서버에 텍스트 채널이 없습니다.")
            else:
                print("[오류] 채널 목록을 보려면 먼저 서버를 선택하세요. '/setguild' 사용.")
        return channels

    async def _set_channel(self, arg: str) -> bool:
        """채널 인덱스, ID 또는 이름을 사용하여 현재 채널을 설정합니다."""
        if not arg:
            print("[오류] 채널 인덱스, ID 또는 이름을 입력해주세요. 예: /setchannel 1 또는 /setchannel 123456789012345678 또는 /setchannel 일반")
            return False
        if await self.chat_bridge_cog.set_channel_by_index_or_id_or_name(arg):
            print(f"[성공] 채널이 '#{self.chat_bridge_cog.channel.name}'(으)로 설정되었습니다.")
            await self._read("")
            return True
        else:
            print("[오류] 유효하지 않은 채널 인덱스, ID 또는 이름입니다.")
            return False

    async def _read(self, arg: str):
        """현재 채널의 최근 메시지를 지정된 개수(기본값 20)만큼 불러옵니다."""
        count = 20
        if arg:
            try:
                count = int(arg)
                if not (1 <= count <= 100):
                    print("[오류] 읽을 메시지 개수는 1에서 100 사이여야 합니다.")
                    return
            except ValueError:
                print("[오류] 읽을 메시지 개수는 숫자여야 합니다.")
                return
        await self.chat_bridge_cog.fetch_recent_messages_cli(count)

    async def _clear(self, arg: str):
        """터미널 화면을 지웁니다."""
        os.system('cls' if os.name == 'nt' else 'clear')
        print("[정보] 화면이 지워졌습니다.")

    async def _multiline_input(self, chat_bridge_cog: ChatBridge):
        """여러 줄 메시지 입력 모드로 전환합니다. 입력을 마치려면 새로운 줄에 @END를 입력하세요."""
        print("\n--- 여러 줄 메시지 입력 모드 ---")
        print("  입력을 마치려면 새로운 줄에 '@END'를 입력하고 Enter를 누르세요.")
        print("----------------------------")

        lines = []
        while True:
            # asyncio.to_thread를 사용하여 blocking input을 비동기적으로 처리
            line = await asyncio.to_thread(input, ">> ")
            if line.strip().upper() == "@END": # 대소문자 구분 없이 @END 인식
                break
            lines.append(line)
        
        full_message = "\n".join(lines)
        if full_message.strip(): # 비어있지 않은 메시지만 전송
            await self.chat_bridge_cog.send_message(full_message)
        else:
            print("[정보] 입력된 내용이 없어 메시지를 전송하지 않았습니다.")
        print("\n--- 여러 줄 메시지 입력 모드 종료 ---\n")

    async def _attach_file(self, arg: str):
        """지정된 파일을 현재 채널에 첨부합니다. (예: /a C:/path/file.png '캡션')"""
        if not arg:
            print("[오류] 첨부할 파일 경로를 입력하세요. 사용법: /attach <파일경로> [선택적 메시지]")
            return

        # 첫 번째 공백을 기준으로 파일 경로와 메시지 분리
        # 파일 경로에 공백이 포함될 수 있으므로, 경로를 먼저 추출
        parts = arg.split(' ', 1)
        file_path = parts[0]
        message_content = parts[1] if len(parts) > 1 else None # 메시지 없으면 None

        # 파일 경로에 따옴표가 있을 경우 제거 (사용자가 편의상 붙였을 수 있음)
        file_path = file_path.strip('\'"')

        if not os.path.exists(file_path):
            print(f"[오류] 지정된 파일 경로를 찾을 수 없습니다: '{file_path}'")
            return

        await self.chat_bridge_cog.send_file(file_path, message_content)
        print(f"[정보] 파일 전송 시도: '{file_path}'")

    async def _quit(self, arg: str):
        """봇을 종료합니다."""
        print("[정보] 봇을 종료합니다...")
        await self.chat_bridge_cog.bot.close()
        return True

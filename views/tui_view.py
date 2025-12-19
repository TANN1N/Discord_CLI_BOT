import asyncio
import logging
import discord
from datetime import timedelta
from typing import Callable, List

from prompt_toolkit import PromptSession
from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings, merge_key_bindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import TextArea

from models import AppState
from core import EventManager, EventType
from controllers import CommandController

from .states import InputState, NormalState, MultilineState, FileInputState, EditState

logger = logging.getLogger(__name__)

class TUIView:
    def __init__(self, controller: CommandController, app_state: AppState, event_manager: EventManager):
        self.controller = controller
        self.app_state = app_state
        self.event_manager = event_manager
        self.is_running = True
        self.app = None
        
        self.current_state: InputState = NormalState(self)
        
        # 초기 설정을 위한 컴포넌트
        self.session = PromptSession()
        self.is_bot_ready = asyncio.Event()

        # TUI 컴포넌트
        self.message_window = TextArea(
            scrollbar=True,
            wrap_lines=True
        )

        self.input_field = TextArea(
            multiline=False,
            wrap_lines=False,
            prompt=self._get_prompt_text
        )
        self.input_buffer = self.input_field.buffer
        self.input_field.buffer.accept_handler = self._accept_input_wrapper

        self.root_container = HSplit([
            self.message_window,
            Window(height=1, char='-'),
            self.input_field
        ])
        
        self.layout = Layout(self.root_container, focused_element=self.input_field)

        self.style = Style.from_dict({
            'timestamp': '#888888',
            'author': 'bold #00aa00',
            'attachment': 'italic #0000ff',
            'error': 'bg:#ff0000 #ffffff',
            'info': '#0088ff',
            'prompt.multiline': 'bg:#00aaff #ffffff',
        })

        self.global_bindings = KeyBindings()
        self.global_bindings.add('c-c')(self._handle_exit)
        self.global_bindings.add('c-d')(self._handle_exit)
        self.global_bindings.add('tab')(self._focus_next)

    def _get_merged_key_bindings(self):
        state_bindings = self.current_state.get_key_bindings()
        return merge_key_bindings([self.global_bindings, state_bindings])

    async def transition_to(self, new_state: InputState):
        if self.current_state:
            await self.current_state.on_exit()
        
        self.current_state = new_state
        await self.current_state.on_enter()
        
        if self.app:
            self.app.key_bindings = self._get_merged_key_bindings()

    def _focus_next(self, _):
        """레이아웃의 다음 위젯으로 포커스를 이동시킵니다."""
        self.layout.focus_next()

    def _get_prompt_text(self):
        return self.current_state.get_prompt_text()

    def _accept_input_wrapper(self, buffer: Buffer) -> bool:
        user_input = buffer.text.strip()
        asyncio.create_task(self.current_state.on_accept(user_input))

        buffer.text = ""
        return True

    async def _process_input_async(self, user_input: str):
        try:
            if user_input.startswith('/'):
                parts = user_input.split(' ', 1)
                command = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""
                if await self.controller.handle_command(command, arg):
                    self.is_running = False
                    if self.app: self.app.exit()
            else:
                await self.event_manager.publish(EventType.MESSAGE_SEND_REQUEST, user_input)
        except Exception as e:
            logger.exception("Error processing user input: %s", user_input)
            await self.handle_error(f"Input processing error: {e}")

    def _handle_exit(self, _):
        self.is_running = False
        if self.app: self.app.exit()

    def register_event_listeners(self):
        logger.debug("Registering TUI event listeners...")
        self.event_manager.subscribe(EventType.BOT_STATUS_READY, self.handle_bot_ready)
        self.event_manager.subscribe(EventType.ERROR, self.handle_error)
        self.event_manager.subscribe(EventType.UI_TEXT_SHOW_REQUEST, self.handle_show_text)
        self.event_manager.subscribe(EventType.UI_DISPLAY_CLEAR_REQUEST, self.handle_clear_display)
        self.event_manager.subscribe(EventType.MESSAGE_RECEIVED, self.handle_new_incoming_message)
        self.event_manager.subscribe(EventType.GUILDS_UPDATED, self.handle_guilds_updated)
        self.event_manager.subscribe(EventType.GUILD_SELECTED, self.handle_guild_selected)
        self.event_manager.subscribe(EventType.CHANNELS_UPDATED, self.handle_available_channels_updated)
        self.event_manager.subscribe(EventType.CHANNEL_SELECTED, self.handle_channel_selected)
        self.event_manager.subscribe(EventType.MESSAGES_RECENT_UPDATED, self.handle_messages_updated)
        self.event_manager.subscribe(EventType.MESSAGES_SELF_UPDATED, self.handle_self_messages_updated)
        self.event_manager.subscribe(EventType.MESSAGE_DELETE_COMPLETED, self.handle_delete_message_complete)
        self.event_manager.subscribe(EventType.UI_EDIT_INPUT_REQUEST, self._handle_edit_message)
        self.event_manager.subscribe(EventType.MESSAGE_EDIT_COMPLETED, self._handle_edit_message_complete)
        self.event_manager.subscribe(EventType.UI_MULTILINE_INPUT_REQUEST, self.handle_request_multiline_input)
        self.event_manager.subscribe(EventType.UI_FILE_INPUT_REQUEST, self.handle_request_file_input)
        self.event_manager.subscribe(EventType.FILES_LIST_UPDATED, self.handle_files_list_updated)
        self.event_manager.subscribe(EventType.FILE_DOWNLOAD_COMPLETED, self.handle_file_download_complete)
        logger.info("TUI event listeners registered.")

    async def run_tui(self):
        # 1. 봇 준비 대기
        print("Waiting for bot to be ready...")
        await self.is_bot_ready.wait()
        print("Bot is ready. Starting initial setup.")

        # 2. 초기 설정 (CLI 방식)
        if not await self._initial_setup():
            logger.error("Initial setup failed. Exiting application.")
            print("초기 설정에 실패하여 프로그램을 종료합니다.")
            return

        # 3. TUI 애플리케이션 실행
        self._add_message_to_log([('class:info', "[정보] 명령어 도움말은 '/help'를 입력해 주세요.")])
        self.app = Application(
            layout=self.layout,
            key_bindings=self._get_merged_key_bindings(),
            style=self.style,
            full_screen=True,
            mouse_support=True
        )
        logger.info("TUI main loop starting.")
        await self.app.run_async()
        logger.info("TUI main loop finished.")

    async def _initial_setup(self) -> bool:
        logger.debug("Starting initial setup process.")
        logger.debug("--- Initial Setup: Select Guild ---")
        print("\n--- 초기 설정: 서버 선택 ---")
        await self.controller._list_guilds("")
        
        while True:
            guild_input = await self.session.prompt_async("서버 인덱스, ID 또는 이름을 입력하세요: ")
            guild_input = guild_input.strip()
            
            if not guild_input:
                print("[실패] 서버 인덱스, ID 또는 이름을 입력하세요.")
                continue
            
            logger.debug("User entereing guild: '%s'", guild_input)
            await self.event_manager.publish(EventType.GUILD_SELECT_REQUEST, guild_input)
            await asyncio.sleep(0) # 이벤트 핸들러가 app_state를 업데이트할 시간을 줌
            
            if self.app_state.current_guild:
                logger.info("Guild '%s' selected successfully.", self.app_state.current_guild.name)
                break
            logger.warning("Failed to select guild with input: '%s'. Retrying", guild_input)
            print("[실패] 다시 시도해 주세요.")

        logger.debug("--- Initial Setup: Select Channel ---")
        print("\n--- 초기 설정: 채널 선택 ---")
        while True:
            channel_input = await self.session.prompt_async("채널 인덱스, ID 또는 이름을 입력하세요: ")
            channel_input = channel_input.strip()
            
            if not channel_input:
                print("[실패] 채널 인덱스, ID 또는 이름을 입력하세요.")
                continue
            
            logger.debug("User entereing channel: '%s'", channel_input)
            await self.event_manager.publish(EventType.CHANNEL_SELECT_REQUEST, channel_input)
            await asyncio.sleep(0) # 이벤트 핸들러가 app_state를 업데이트할 시간
            
            if self.app_state.current_channel:
                logger.info("Channel '%s' selected successfully.", self.app_state.current_channel.name)
                return True
            logger.warning("Failed to select channel with input: '%s'. Retrying.", channel_input)
            print("[실패] 다시 시도해 주세요.")
        return False

    def _add_message_to_log(self, message_parts: List[tuple]):
        buffer = self.message_window.buffer
        buffer.cursor_position = len(buffer.text)
        plain_text = "".join(part[1] for part in message_parts) + "\n"
        buffer.insert_text(plain_text)
        buffer.cursor_position = len(buffer.text)

    def _display_info(self, text: str, style: str = ''):
        if self.app and self.app.is_running:
            self._add_message_to_log([(style, text)])
        else:
            print(text)

    def format_message(self, message: discord.Message) -> list:
        """Discord 메시지 객체를 TUI에 표시할 서식 있는 텍스트 튜플 리스트로 포맷팅합니다."""
        timestamp = (message.created_at + timedelta(hours=9)).strftime("%m/%d %H:%M:%S")
        
        content = message.content or ""
        # --- Content & Mentions
        for member in message.mentions:
            display_name = member.display_name
            content = content.replace(f"<@{member.id}>", f"@{display_name}")
            content = content.replace(f"<@!{member.id}>", f"@{display_name}")
        for role in message.role_mentions:
            content = content.replace(f"<@&{role.id}>", f"@{role.name}")
        for channel in message.channel_mentions:
            content = content.replace(f"<#{channel.id}>", f"#{channel.name}")
        
        author_display = message.author.display_name
        
        # TUI용 포맷팅된 리스트 생성
        formatted_list = [
            ('class:timestamp', f'[{timestamp}] '),
            ('class:author', f'{author_display}'),
            ('', ': ')
        ]
        if content:
            formatted_list.append(('',content))
        
        # --- Attachments ---
        if message.attachments:
            attachment_texts = [f"📁 {att.filename}" for att in message.attachments]
            separator = "\n" if content else ""
            attachment_str = f"{separator}[Attachment(s): {', '.join(attachment_texts)}]";
            formatted_list.append(('class:attachment', attachment_str))
        
        # --- Embeds ---
        if message.embeds:
            for embed in message.embeds:
                # Title
                if embed.title:
                    formatted_list.append(('class:embed_title', f"\n📌 {embed.title}"))
                
                # Description
                if embed.description:
                    formatted_list.append(('class:embed_desc', f"\n{embed.description}"))

                # Fields
                for field in embed.fields:
                    formatted_list.append(('class:embed_field', f"\n-{field.name}: {field.value}"))
                
                # Footer
                if embed.footer and embed.footer.text:
                    formatted_list.append(('class:embed_footer', f"\n*{embed.footer.text}*"))
        
        return formatted_list

    # --- Event Handlers ---

    async def handle_unsupported_feature(self, *args):
        """TUI 모드에서 아직 지원되지 않는 기능에 대한 핸들러입니다."""
        await self.handle_error("This feature is not yet implemented in TUI mode.")

    async def handle_show_text(self, text: str):
        logger.debug("Handling SHOW_TEXT event.")
        self._display_info(text, 'class:info')

    async def handle_error(self, error_message: str):
        logger.debug("Handling ERROR event.")
        self._display_info(f"[ERROR] {error_message}", 'class:error')

    async def handle_clear_display(self, *args):
        logger.debug("Handling CLEAR_DISPLAY event.")
        if self.message_window:
            self.message_window.buffer.reset()
        self._add_message_to_log([('class:info', "[정보] 화면의 모든 메시지가 지워졌습니다.")])

    async def handle_bot_ready(self, *args):
        logger.info("Handling BOT_READY event. TUI is now unblocked.")
        self.is_bot_ready.set()

    async def handle_guilds_updated(self, *args):
        logger.debug("Handling GUILDS_UPDATED event.")
        text = "\n--- 서버 목록 ---\n"
        if not self.app_state.all_guilds:
            text += "  참여 중인 서버가 없습니다."
        else:
            for idx, guild in enumerate(self.app_state.all_guilds):
                text += f"  [{idx + 1}] {guild.name} (ID: {guild.id})\n"
        text += "------------------"
        self._display_info(text)

    async def handle_guild_selected(self, guild_name: str):
        logger.debug("Handling GUILD_SELECTED event for guild: %s", guild_name)
        self._display_info(f"\n[성공] 서버가 설정되었습니다: {guild_name}")

    async def handle_available_channels_updated(self, *args):
        text = f"\n--- 채널 목록 (서버: {self.app_state.current_guild.name}) ---\n"
        channels = self.app_state.available_channels
        if not channels:
            text += "  사용 가능한 텍스트 채널이 없습니다."
        else:
            for idx, channel in enumerate(channels):
                current_indicator = " (현재 선택됨)" if self.app_state.current_channel and self.app_state.current_channel.id == channel.id else ""
                text += f"  [{idx + 1}] #{channel.name} (ID: {channel.id}){current_indicator}\n"
        text += "-------------------------------------------"
        self._display_info(text)

    async def handle_channel_selected(self, channel_name: str):
        logger.debug("Handling CHANNEL_SELECTED event.")
        self._display_info(f"\n[성공] 채널이 설정되었습니다: #{channel_name}")

    async def handle_messages_updated(self, *args):
        logger.debug("Handling MESSAGES_UPDATED event for channel: %s", self.app_state.current_channel.name)
        self._add_message_to_log([('class:info', f"--- 최근 메시지 (채널: #{self.app_state.current_channel.name}) ---")])
        for msg in self.app_state.recent_messages:
            formatted_msg = self.format_message(msg)
            self._add_message_to_log(formatted_msg)

    async def handle_new_incoming_message(self, message):
        logger.debug("Handling NEW_INCOMING_MESSAGE event from channel #%s", message.channel.name)
        if self.app_state.current_channel and message.channel.id == self.app_state.current_channel.id:
            formatted_message = self.format_message(message)
            self._add_message_to_log(formatted_message)
        else:
            notification = [('class:info', f"[새 메시지 @{message.guild.name}/#{message.channel.name}]")]
            self._add_message_to_log(notification)
            self._add_message_to_log([('class:info', "----------------------------------------")])

    async def handle_self_messages_updated(self, *args):
        """캐시된 자신의 메시지 목록을 TUI에 표시합니다."""
        logger.debug("Handling SELF_MESSAGES_UPDATED event.")
        self._add_message_to_log([('class:info', f"--- 최근 메시지 목록 (채널: #{self.app_state.current_channel.name}) ---")])
        if not self.app_state.recent_self_messages:
            self._add_message_to_log([('', "  최근 메시지에서 찾은 자신의 메시지가 없습니다.")])
        else:
            for idx, msg in enumerate(self.app_state.recent_self_messages):
                # 메시지의 내용이 너무 길 수 있으므로 최대 20자까지만 표시하도록 함
                self._add_message_to_log([('', f"  [{idx + 1}] {msg.content[:20]}")])
            self._add_message_to_log([('class:info', "--------------------------------------------------")])
            self._add_message_to_log([('', "편집하기 위해서는 '/edit <인덱스>'를 삭제하기 위해서는 '/delete <인덱스>'를 입력하세요.")])

    async def handle_delete_message_complete(self, m_id: int):
        logger.debug("Handling DELETE_MESSAGE_COMPLETE event.")
        self._display_info(f"\n[Success] delete message id: {m_id}")

    def _handle_edit_message_complete(self, m_id: int):
        logger.debug("Handling MESSAGE_EDIT_COMPLETED event.")
        self._display_info(f"\n[Success] edit message id: {m_id}")

    async def _handle_edit_message(self, on_complete: Callable, message_to_edit: str):
        """메시지 수정 상태에 진입합니다."""
        logger.debug("Handling UI_EDIT_INPUT_REQUEST event.")
        await self.transition_to(EditState(self, on_complete, message_to_edit))

    async def handle_request_file_input(self, on_complete: Callable, initial_arg: str):
        """파일 첨부 상태에 진입합니다."""
        logger.debug("Handling UI_FILE_INPUT_REQUEST event.")
        await self.transition_to(FileInputState(self, on_complete, initial_arg))

    async def handle_request_multiline_input(self, on_complete: Callable):
        """다중 라인 입력 상태에 진입합니다."""
        logger.debug("Handling UI_MULTILINE_INPUT_REQUEST event.")
        await self.transition_to(MultilineState(self, on_complete))

    async def handle_files_list_updated(self, *args):
        """캐시된 파일 목록을 TUI에 표시합니다."""
        logger.debug("Handling FILES_LIST_UPDATED event.")
        self._add_message_to_log([('class:info', f"--- 최근 파일 목록 (채널: #{self.app_state.current_channel.name}) ---")])
        if not self.app_state.file_cache:
            self._add_message_to_log([('', "  최근 메시지에서 찾은 파일이 없습니다.")])
        else:
            for idx, attachment in enumerate(self.app_state.file_cache):
                size_kb = attachment.size / 1024
                size_str = f"{size_kb / 1024:.2f} MB" if size_kb > 1024 else f"{size_kb:.2f} KB"
                self._add_message_to_log([('', f"  [{idx + 1}] {attachment.filename} ({size_str})")])
            self._add_message_to_log([('class:info', "--------------------------------------------------")])
            self._add_message_to_log([('', "다운로드하려면 '/download <인덱스>'를 입력하세요.")])

    async def handle_file_download_complete(self, file_path: str):
        """파일 다운로드 완료 메시지를 TUI에 표시합니다."""
        logger.info("Handling FILE_DOWNLOAD_COMPLETE event for path: %s", file_path)
        self._add_message_to_log([('class:info', f"\n[성공] 파일이 성공적으로 다운로드 되었습니다. -> 저장 경로: {file_path}")])

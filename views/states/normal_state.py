from typing import Any
from core import EventType
from .states import InputState
from prompt_toolkit.key_binding import KeyBindings

class NormalState(InputState):
    async def on_enter(self):
        self.logger.debug("Entered Normal State")
    
    async def on_exit(self):
        pass
    
    async def on_accept(self, text: str):
        if not text: return
        
        try:
            if text.startswith('/'):
                parts = text.split(' ', 1)
                command = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""
                if await self.view.controller.handle_command(command, arg):
                    self.view.is_running = False
                    if self.view.app: self.view.app.exit()
            else:
                await self.view.event_manager.publish(EventType.MESSAGE_SEND_REQUEST, text)
        except Exception as e:
            # TODO: Logging 시에 유저의 입력이 기록 되는 것은 보안상 좋지 않음
            self.logger.exception("Error processing user input: %s", text)
            await self.view.handle_error(f"Input processing error: {e}")
    
    def get_prompt_text(self) -> str:
        app_state = self.view.app_state
        guild_name = app_state.current_guild.name if app_state.current_guild else "No Guild"
        channel_name = f"#{app_state.current_channel.name}" if app_state.current_channel else "No Channel"
        return f"[{guild_name} | {channel_name}]> "
    
    def get_key_bindings(self) -> KeyBindings:
        self.key_bindings = KeyBindings()
        self.key_bindings.add('c-c')(self.view._handle_exit)
        self.key_bindings.add('c-d')(self.view._handle_exit)
        self.key_bindings.add('tab')(self.view._focus_next)
        return self.key_bindings
from typing import Any
from core import EventType
from .abstract_tui_state import AbstractTUIState
from .normal_state import NormalState
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import AnyContainer
import asyncio

class MultilineState(AbstractTUIState):
    def __init__(self, view, on_complete):
        super().__init__(view)
        self.on_complete = on_complete
        self.lines = []

    async def on_enter(self):
        self.logger.debug("Entered Multiline State")
        self.view._add_message_to_log([('class:info', "\n--- 여러 줄 메시지 입력 모드 (종료: @END) ---\n")])

    async def on_exit(self):
        self.view._add_message_to_log([('class:info', "[정보] 다중 라인 입력 모드 종료")])

    async def on_accept(self, text: str):
        if text.strip().upper() == '@END':
            full_message = "\n".join(self.lines)
            await self._submit_message(full_message)
        else:
            self.lines.append(text)

    def get_layout_container(self) -> AnyContainer:
        return super().get_layout_container()

    def get_prompt_text(self):
        return [('class:prompt.multiline', 'ML MODE (@END to finish) > ')]

    def get_key_bindings(self) -> KeyBindings:
        kb = KeyBindings()
        
        @kb.add('escape', 'enter')
        def _(event):
            current_text = self.view.input_buffer.text
            if current_text:
                self.lines.append(current_text)
            
            full_message = "\n".join(self.lines)
            
            asyncio.create_task(self._submit_message(full_message))
            
            self.view.input_buffer.text = ""
        
        return kb
    
    async def _submit_message(self, message):
        await self.on_complete(message)
        await self.view.transition_to(NormalState(self.view))
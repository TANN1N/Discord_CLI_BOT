from typing import Any, Callable
from core import EventType
from .abstract_tui_state import AbstractTUIState
from .normal_state import NormalState
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import AnyContainer

class EditState(AbstractTUIState):
    def __init__(self, view, on_complete: Callable, message_to_edit: str):
        super().__init__(view)
        self.on_complete = on_complete
        self.message_to_edit = message_to_edit

    async def on_enter(self):
        self.logger.debug("Entered Edit State")
        info_text = "\n--- 메시지 편집 모드 ---\n" \
                    "  메시지를 편집하세요. 취소하려면 아무것도 입력하지 않고 Enter를 누르세요.\n" \
                    "--------------------------\n"
        self.view._add_message_to_log([('class:info', info_text)])
        self.view.input_buffer.text = self.message_to_edit
        self.view.input_buffer.cursor_position = len(self.message_to_edit)

    async def on_exit(self):
        self.view._add_message_to_log([('class:info', "[정보] 메시지 편집 모드 종료")])

    async def on_accept(self, text: str):
        await self.on_complete(text)
        await self.view.transition_to(NormalState(self.view))
    
    def get_prompt_text(self):
        return [('class:info', 'EDIT MODE > ')]
    
    def get_key_bindings(self) -> KeyBindings:
        return super().get_key_bindings()
    
    def get_layout_container(self) -> AnyContainer:
        return super().get_layout_container()
from typing import Any
from core import EventType
from .states import InputState
from .normal_state import NormalState
from prompt_toolkit.key_binding import KeyBindings

class MultilineState(InputState):
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
            await self.on_complete(full_message)
            # 작업 완료 후 일반 상태로 복귀
            await self.view.transition_to(NormalState(self.view))
        else:
            self.lines.append(text)

    def get_prompt_text(self):
        return [('class:prompt.multiline', 'ML MODE (@END to finish) > ')]
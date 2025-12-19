from typing import Any
from core import EventType
from .states import InputState
from .normal_state import NormalState
from prompt_toolkit.key_binding import KeyBindings

class FileInputState(InputState):
    def __init__(self, view, on_complete, initial_path=None):
        super().__init__(view)
        self.on_complete = on_complete
        self.file_path = initial_path
        self.caption = None

    async def on_enter(self):
        self.logger.debug("Entered Fileinput State")
        self.view._add_message_to_log([('class:info', "\n--- 파일 첨부 모드 ---\n")])

    async def on_exit(self):
        pass

    async def on_accept(self, text: str):
        # 1단계: 파일 경로 입력
        if self.file_path is None:
            if not text: # 취소
                self.view._add_message_to_log([('class:info', "취소됨")])
                await self.view.transition_to(NormalState(self.view))
                return
            self.file_path = text.strip()
            # UI 갱신을 위해 강제 리프레시 필요할 수 있음 (prompt 변경됨)
            return

        # 2단계: 캡션 입력
        self.caption = text
        await self.on_complete(self.file_path, self.caption)
        await self.view.transition_to(NormalState(self.view))

    def get_prompt_text(self):
        if self.file_path is None:
            return [('class:prompt.multiline', 'File Path > ')]
        else:
            return [('class:prompt.multiline', 'Caption (optional) > ')]
    
    def get_key_bindings(self) -> KeyBindings:
        return super().get_key_bindings()
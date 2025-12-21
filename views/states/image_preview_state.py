import climage
from prompt_toolkit.layout.containers import Window, AnyContainer
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout import WindowAlign
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.key_binding import KeyBindings
import asyncio
from .abstract_tui_state import AbstractTUIState
from .normal_state import NormalState

class ImagePreviewState(AbstractTUIState):
    def __init__(self, view, file_path: str):
        super().__init__(view)
        self.file_path = file_path
        self.ansi_art = None

    async def on_enter(self):
        try:
            self.ansi_art = climage.convert(self.file_path, is_unicode=True, width=80)
        except Exception as e:
            self.logger.exception(f"Image convert failed: {e}")
            self.ansi_art = f"[ERROR] 이미지 변환 실패: {e}"

    async def on_exit(self):
        pass # 특별한 정리 작업 없음

    async def on_accept(self, text: str):
        pass # 이 모드에서는 입력창이 없거나 사용되지 않음

    def get_layout_container(self) -> AnyContainer:
        # 화면 전체를 꽉 채우는 Window 생성
        return Window(
            content=FormattedTextControl(text=ANSI(self.ansi_art if self.ansi_art else "Loading...")),
            align=WindowAlign("CENTER"), # 가운데 정렬
            wrap_lines=False # 아트가 깨지지 않도록 줄바꿈 방지
        )

    def get_key_bindings(self) -> KeyBindings:
        kb = KeyBindings()

        # 'q', 'esc', 'enter', 'space' 등 일반적인 종료 키 바인딩
        @kb.add('q')
        @kb.add('escape')
        @kb.add('enter')
        @kb.add('space')
        def _(event):
            # NormalState로 복귀
            asyncio.create_task(self.view.transition_to(NormalState(self.view)))
            
        return kb

    def get_prompt_text(self):
        return [] # 프롬프트 없음
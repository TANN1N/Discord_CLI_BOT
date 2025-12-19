from abc import ABC, abstractclassmethod, abstractmethod
import logging
import asyncio
from prompt_toolkit.key_binding import KeyBindings

class InputState(ABC):
    def __init__(self, view):
        self.view = view
        self.logger = logging.getLogger(self.__class__.__name__)
    @abstractmethod
    async def on_enter(self):
        """상태 진입 시 실행(예: 안내 메시지 출력, 키 바인딩 변경, 로깅 등)"""
        pass
    
    @abstractmethod
    async def on_exit(self):
        """상태 퇴장 시 실행(예: 로깅, 임시 버퍼 초기화 등)"""
        pass
    
    @abstractmethod
    async def on_accept(self, text: str):
        """사용자가 엔터를 쳤을 때의 동작"""
        pass
    
    @abstractmethod
    async def get_prompt_text(self) -> str:
        """현재 상태에 맞는 프롬프트 텍스트 반환"""
        pass
    
    @abstractmethod
    def get_key_bindings(self) -> KeyBindings:
        """(선택)해당 상태 전용 키 바인딩 반환"""
        return KeyBindings()

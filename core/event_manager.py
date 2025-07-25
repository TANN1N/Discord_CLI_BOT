import asyncio
from typing import Callable
from collections import defaultdict
from .event_types import EventType

class EventManager:
    """간단한 Pub-Sub 패턴을 구현한 이벤트 관리자입니다."""
    def __init__(self):
        self._listeners = defaultdict(list)
    
    def subscribe(self, event_type: EventType, callback: Callable):
        """이벤트가 발생했을 때 호출된 콜백 함수를 등록합니다."""
        self._listeners[event_type].append(callback)
    
    async def publish(self, event_type: EventType, *args, **kwargs):
        """특정 유형의 이벤트를 모든 구독자에게 발행합니다."""
        if event_type in self._listeners:
            for callback in self._listeners[event_type]:
                if asyncio.iscoroutinefunction(callback):
                    await callback(*args, **kwargs)
                else:
                    callback(*args, **kwargs)

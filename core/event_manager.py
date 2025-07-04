from collections import defaultdict

class EventManager:
    """간단한 Pub-Sub 패턴을 구현한 이벤트 관리자입니다."""
    def __init__(self):
        self._listeners = defaultdict(list)
    
    def subscribe(self, event_type: str, callback: function): # type hint function 괜찮은지 확인할 것
        """이벤트가 발생했을 때 호출된 콜백 함수를 등록합니다."""
        self._listeners[event_type].append(callback) # dict를 사용하는 것으로 여러개의 콜백 함수가 존재할 수 있도록 함
    
    def publish(self, event_type: str, *args, **kwargs):
        for callback in self._listeners[event_type]:
            callback(*args, **kwargs)
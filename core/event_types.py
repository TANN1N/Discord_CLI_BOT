from enum import Enum, auto


class EventType(Enum):
    """
    발행할 수 있는 이벤트 타입을 enum으로 명시적으로 지정함으로써 오타로 인한 오류를 방지.
    IDE의 자동완성 기능을 사용할 수 있도록 함.
    """
    
    # General Events
    ERROR = auto()
    SHOW_TEXT = auto()
    CLEAR_DISPLAY = auto()
    
    # UI Interaction Events
    REQUEST_MULTILINE_INPUT = auto()
    REQUEST_FILE_INPUT = auto()
    
    # Bot Status Events
    BOT_READY = auto()
    
    # Guild/Server Events
    GUILDS_UPDATED = auto()
    GUILD_SELECTED = auto()
    
    # Channel Events
    AVAILABLE_CHANNELS_UPDATED = auto()
    CHANNEL_SELECTED = auto()
    
    # Message Events
    MESSAGES_UPDATED = auto()
    SELF_MESSAGES_UPDATED = auto()
    # TODO: Add and implement 2 event below
    DELETE_MESSAGE_COMPLETE = auto()
    # EDIT_MESSAGE_REQUESTED = auto
    MESSAGE_SENT_SUCCESS = auto()
    FILE_SENT_SUCCESS = auto()
    
    # File Download Events
    FILES_LIST_REQUESTED = auto()
    FILES_LIST_UPDATED = auto()
    FILE_DOWNLOAD_REQUESTED = auto()
    FILE_DOWNLOAD_COMPLETE = auto()
    
    NEW_INCOMING_MESSAGE = auto()

from enum import Enum, auto


class EventType(Enum):
    """
    사용되는 이벤트 타입을 enum으로 명시적으로 지정함.
    (객체 중심 명명 규칙: OBJECT_ACTION_STATUS 적용)
    """
    
    # --- General & UI Events ---
    ERROR = auto()
    
    UI_TEXT_SHOW_REQUEST = auto()
    UI_DISPLAY_CLEAR_REQUEST = auto()
    UI_MULTILINE_INPUT_REQUEST = auto()
    UI_FILE_INPUT_REQUEST = auto()
    
    # --- Bot Status Events ---
    BOT_STATUS_READY = auto()
    
    # --- Guild/Server Events ---
    GUILDS_UPDATED = auto()
    GUILD_SELECT_REQUEST = auto()
    GUILD_SELECTED = auto()
    
    # --- Channel Events ---
    CHANNELS_UPDATED = auto()
    CHANNEL_SELECT_REQUEST = auto()
    CHANNEL_SELECTED = auto()
    
    # --- Message Events ---
    MESSAGE_RECEIVED = auto()
    
    MESSAGES_RECENT_FETCH_REQUEST = auto()
    MESSAGES_RECENT_UPDATED = auto()
    
    MESSAGES_SELF_FETCH_REQUEST = auto()
    MESSAGES_SELF_UPDATED = auto()
    
    MESSAGE_DELETE_REQUEST = auto()
    MESSAGE_DELETE_COMPLETED = auto()
    
    # TODO Add Edit message feature
    # REQUEST_EDIT_MESSAGE = auto()
    # EDIT_MESSAGE_COMPLETE = auto()
    
    MESSAGE_SEND_REQUEST = auto()
    MESSAGE_SEND_COMPLETED = auto()
    
    # --- File Events ---
    FILE_SEND_REQUEST = auto()
    FILE_SEND_COMPLETED = auto()
    
    FILES_LIST_FETCH_REQUEST = auto()
    FILES_LIST_UPDATED = auto()
    
    FILE_DOWNLOAD_REQUEST = auto()
    FILE_DOWNLOAD_COMPLETED = auto()

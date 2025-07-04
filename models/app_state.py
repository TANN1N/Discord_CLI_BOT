from dataclasses import dataclass, field
import discord

@dataclass
class AppState:
    """애플리케이션의 모든 상태를 관리하는 데이터 클래스입니다."""
    in_bot_ready: bool = False
    current_guild: discord.Guild | None = None
    current_channel: discord.TextChannel | None = None
    all_guilds: list[discord.Guild] = field(default_factory=list)
    available_channels: list[discord.TextChannel] = field(default_factory=list)
    recent_messages: list[str] = field(default_factory=list)
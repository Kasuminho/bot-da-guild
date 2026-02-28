from dataclasses import dataclass


@dataclass(frozen=True)
class TenantContext:
    guild_id: int
    channel_id: int | None
    actor_user_id: int

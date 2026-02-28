from __future__ import annotations

from typing import Literal, cast

from services.guild_config_service import GuildConfigService

LootMode = Literal["legacy", "dkp"]
VALID_LOOT_MODES: set[str] = {"legacy", "dkp"}


class LootModeService:
    """Guild loot mode manager.

    Important:
    - Legacy flow remains implemented in legacy cogs (`forum_announce`, `forum_delivery`, `item_requests`).
    - DKP mode is optional and only enabled when guild config explicitly switches to `dkp`.
    """

    def __init__(self, config_service: GuildConfigService):
        self.config_service = config_service

    def get_mode(self, guild_id: int) -> LootMode:
        cfg = self.config_service.get_config(guild_id)
        mode = str(cfg.get("loot_mode", "legacy")).strip().lower()
        if mode not in VALID_LOOT_MODES:
            return "legacy"
        return cast(LootMode, mode)

    def set_mode(self, guild_id: int, actor_user_id: int, mode: str) -> LootMode:
        normalized = mode.strip().lower()
        if normalized not in VALID_LOOT_MODES:
            raise ValueError("Invalid loot mode")

        self.config_service.set_config(guild_id, actor_user_id, "loot_mode", normalized)
        return cast(LootMode, normalized)

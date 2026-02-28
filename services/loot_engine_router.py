from __future__ import annotations

from engines.dkp_engine import DKPEngine
from engines.legacy_engine import LegacyEngine
from services.guild_config_service import GuildConfigService


class LootEngineRouter:
    def __init__(self, config_service: GuildConfigService, legacy_engine: LegacyEngine, dkp_engine: DKPEngine):
        self.config_service = config_service
        self.legacy_engine = legacy_engine
        self.dkp_engine = dkp_engine

    def get_engine(self, guild_id: int):
        cfg = self.config_service.get_config(guild_id)
        mode = str(cfg.get("loot_mode", "legacy")).lower()
        if mode == "dkp":
            return self.dkp_engine
        return self.legacy_engine

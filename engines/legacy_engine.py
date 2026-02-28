from __future__ import annotations

from core.context import TenantContext
from engines.loot_engine import LootEngine


class LegacyEngine(LootEngine):
    def assign_loot(self, ctx: TenantContext, item: str, participants: list[int], **kwargs):
        return {"mode": "legacy", "item": item, "participants": participants}

    def get_state(self, ctx: TenantContext):
        return {"mode": "legacy"}

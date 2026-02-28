from __future__ import annotations

from core.context import TenantContext
from engines.loot_engine import LootEngine
from services.dkp_service import DKPService


class DKPEngine(LootEngine):
    def __init__(self, dkp_service: DKPService):
        self.dkp_service = dkp_service

    def assign_loot(self, ctx: TenantContext, item: str, participants: list[int], **kwargs):
        cost = int(kwargs.get("cost", 0))
        winner_id = int(kwargs.get("winner_id", participants[0] if participants else 0))
        if winner_id and cost > 0:
            self.dkp_service.remove_points(ctx, winner_id, cost, f"Loot won: {item}")
        return {"mode": "dkp", "item": item, "winner_id": winner_id, "cost": cost}

    def get_state(self, ctx: TenantContext):
        return {"mode": "dkp"}

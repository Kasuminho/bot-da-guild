from __future__ import annotations

from abc import ABC, abstractmethod

from core.context import TenantContext


class LootEngine(ABC):
    @abstractmethod
    def assign_loot(self, ctx: TenantContext, item: str, participants: list[int], **kwargs):
        raise NotImplementedError

    @abstractmethod
    def get_state(self, ctx: TenantContext):
        raise NotImplementedError

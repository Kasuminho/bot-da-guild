from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol


class SaaSRepoProtocol(Protocol):
    def get_guild(self, guild_id: int) -> tuple[Any, ...] | None: ...

    def get_plan(self, plan_id: str) -> tuple[Any, ...] | None: ...


@dataclass(frozen=True)
class PlanInfo:
    plan_id: str
    subscription_status: str
    subscription_expires_at: int | None
    is_active: bool
    features: dict[str, Any]


class FeatureService:
    """Resolves plan features and entitlement checks per guild."""

    def __init__(self, saas_repo: SaaSRepoProtocol):
        self.saas_repo = saas_repo

    def get_plan(self, guild_id: int) -> PlanInfo:
        guild_row = self.saas_repo.get_guild(guild_id)
        if not guild_row:
            return PlanInfo(
                plan_id="free",
                subscription_status="free",
                subscription_expires_at=None,
                is_active=True,
                features={},
            )

        _, _, plan_id, status, expires_at, is_active, _ = guild_row
        resolved_plan_id = str(plan_id or "free")
        plan_row = self.saas_repo.get_plan(resolved_plan_id)
        features = dict(plan_row[4]) if plan_row and isinstance(plan_row[4], dict) else {}

        return PlanInfo(
            plan_id=resolved_plan_id,
            subscription_status=str(status),
            subscription_expires_at=int(expires_at) if expires_at is not None else None,
            is_active=bool(is_active),
            features=features,
        )

    def can_use_feature(self, guild_id: int, feature_key: str) -> bool:
        plan = self.get_plan(guild_id)

        if not plan.is_active:
            return False

        if plan.subscription_status in {"past_due", "canceled"}:
            if plan.subscription_expires_at is not None:
                now_epoch = int(datetime.now(tz=timezone.utc).timestamp())
                if now_epoch > plan.subscription_expires_at:
                    return False

        return bool(plan.features.get(feature_key, False))

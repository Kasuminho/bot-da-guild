from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol


class SaaSRepoProtocol(Protocol):
    def upsert_guild(self, guild_id: int, name: str) -> None: ...

    def get_guild(self, guild_id: int) -> tuple[Any, ...] | None: ...

    def set_plan(self, guild_id: int, plan_id: str) -> None: ...

    def set_subscription_status(self, guild_id: int, status: str) -> None: ...

    def set_subscription_expiry(self, guild_id: int, expiry_epoch: int) -> None: ...


class AuditRepoProtocol(Protocol):
    def log(
        self,
        guild_id: int,
        actor_user_id: int,
        action: str,
        entity_type: str,
        entity_id: str | None,
        details: dict,
    ) -> None: ...


class SaaSService:
    def __init__(self, saas_repo: SaaSRepoProtocol, audit_repo: AuditRepoProtocol):
        self.saas_repo = saas_repo
        self.audit_repo = audit_repo

    def ensure_guild(self, guild_id: int, guild_name: str) -> None:
        self.saas_repo.upsert_guild(guild_id, guild_name)

    def view_plan(self, guild_id: int) -> dict[str, Any]:
        guild = self.saas_repo.get_guild(guild_id)
        if not guild:
            return {"plan_id": "free", "status": "free", "expires_at": None}

        _, _, plan_id, status, expires_at, _, _ = guild
        return {"plan_id": plan_id or "free", "status": status, "expires_at": expires_at}

    def set_plan(self, guild_id: int, actor_id: int, plan_id: str) -> None:
        self.saas_repo.set_plan(guild_id, plan_id)
        self.audit_repo.log(guild_id, actor_id, "saas.plan.set", "guild", str(guild_id), {"plan_id": plan_id})

    def set_subscription_status(self, guild_id: int, actor_id: int, status: str) -> None:
        self.saas_repo.set_subscription_status(guild_id, status)
        self.audit_repo.log(guild_id, actor_id, "saas.subscription.status", "guild", str(guild_id), {"status": status})

    def set_subscription_expiry(self, guild_id: int, actor_id: int, iso_date: str) -> None:
        normalized = iso_date.replace("Z", "+00:00")
        expiry_dt = datetime.fromisoformat(normalized)
        if expiry_dt.tzinfo is None:
            expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)

        expiry_epoch = int(expiry_dt.timestamp())
        self.saas_repo.set_subscription_expiry(guild_id, expiry_epoch)
        self.audit_repo.log(
            guild_id,
            actor_id,
            "saas.subscription.expiry",
            "guild",
            str(guild_id),
            {"expiry": expiry_dt.isoformat()},
        )

from __future__ import annotations

from typing import Protocol

from core.context import TenantContext


class DKPRepoProtocol(Protocol):
    def add_transaction(
        self,
        guild_id: int,
        user_id: int,
        amount: int,
        reason: str,
        created_by_user_id: int,
        event_id: str | None = None,
    ) -> None: ...

    def get_balance(self, guild_id: int, user_id: int) -> int: ...

    def get_leaderboard(self, guild_id: int, limit: int): ...

    def get_history(self, guild_id: int, user_id: int, limit: int): ...

    def list_user_balances(self, guild_id: int): ...

    def clear_guild(self, guild_id: int, actor_id: int) -> None: ...


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


class DKPService:
    def __init__(self, dkp_repo: DKPRepoProtocol, audit_repo: AuditRepoProtocol):
        self.dkp_repo = dkp_repo
        self.audit_repo = audit_repo

    def add_points(self, ctx: TenantContext, user_id: int, amount: int, reason: str) -> None:
        normalized = abs(amount)
        self.dkp_repo.add_transaction(ctx.guild_id, user_id, normalized, reason, ctx.actor_user_id)
        self.audit_repo.log(
            ctx.guild_id,
            ctx.actor_user_id,
            "dkp.add",
            "user",
            str(user_id),
            {"amount": normalized, "reason": reason},
        )

    def remove_points(self, ctx: TenantContext, user_id: int, amount: int, reason: str) -> None:
        normalized = -abs(amount)
        self.dkp_repo.add_transaction(ctx.guild_id, user_id, normalized, reason, ctx.actor_user_id)
        self.audit_repo.log(
            ctx.guild_id,
            ctx.actor_user_id,
            "dkp.remove",
            "user",
            str(user_id),
            {"amount": abs(amount), "reason": reason},
        )

    def get_balance(self, ctx: TenantContext, user_id: int) -> int:
        return self.dkp_repo.get_balance(ctx.guild_id, user_id)

    def get_leaderboard(self, ctx: TenantContext, limit: int = 10):
        return self.dkp_repo.get_leaderboard(ctx.guild_id, limit)

    def get_history(self, ctx: TenantContext, user_id: int, limit: int = 20):
        return self.dkp_repo.get_history(ctx.guild_id, user_id, limit)

    def apply_decay(self, ctx: TenantContext, percent: int) -> None:
        balances = self.dkp_repo.list_user_balances(ctx.guild_id)
        for user_id, balance in balances:
            if balance <= 0:
                continue

            reduction = int((balance * percent) / 100)
            if reduction <= 0:
                continue

            self.dkp_repo.add_transaction(
                ctx.guild_id,
                user_id,
                -reduction,
                f"Decay {percent}%",
                ctx.actor_user_id,
                event_id=f"decay_{percent}",
            )

        self.audit_repo.log(
            ctx.guild_id,
            ctx.actor_user_id,
            "dkp.decay",
            "guild",
            str(ctx.guild_id),
            {"percent": percent},
        )

    def reset(self, ctx: TenantContext) -> None:
        self.dkp_repo.clear_guild(ctx.guild_id, ctx.actor_user_id)
        self.audit_repo.log(ctx.guild_id, ctx.actor_user_id, "dkp.reset", "guild", str(ctx.guild_id), {})

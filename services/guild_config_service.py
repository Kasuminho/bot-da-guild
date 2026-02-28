from __future__ import annotations

from typing import Any, Protocol


class ConfigRepoProtocol(Protocol):
    def get(self, guild_id: int) -> dict[str, Any]: ...

    def set(self, guild_id: int, key: str, value: Any) -> None: ...


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


class GuildConfigService:
    def __init__(self, config_repo: ConfigRepoProtocol, audit_repo: AuditRepoProtocol):
        self.config_repo = config_repo
        self.audit_repo = audit_repo

    def get_config(self, guild_id: int) -> dict[str, Any]:
        return self.config_repo.get(guild_id)

    def set_config(self, guild_id: int, actor_user_id: int, key: str, value: Any) -> None:
        self.config_repo.set(guild_id, key, value)
        self.audit_repo.log(
            guild_id=guild_id,
            actor_user_id=actor_user_id,
            action="config.set",
            entity_type="guild_config",
            entity_id=key,
            details={"key": key, "value": value},
        )

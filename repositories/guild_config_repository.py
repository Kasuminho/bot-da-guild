from __future__ import annotations

import json
import time
from typing import Any

import db


class GuildConfigRepository:
    """JSON-backed guild config accessor."""

    def get(self, guild_id: int) -> dict[str, Any]:
        row = db.execute(
            "SELECT config_json FROM guilds WHERE guild_id = %s",
            (guild_id,),
            fetchone=True,
        )
        if not row or row[0] is None:
            return {}

        payload = row[0]
        if isinstance(payload, dict):
            return payload
        if isinstance(payload, str):
            return json.loads(payload)

        return dict(payload)

    def set(self, guild_id: int, key: str, value: Any) -> None:
        current = self.get(guild_id)
        current[key] = value
        db.execute(
            "UPDATE guilds SET config_json = %s, updated_at = %s WHERE guild_id = %s",
            (json.dumps(current), int(time.time()), guild_id),
        )

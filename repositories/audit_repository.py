from __future__ import annotations

import json

import db


class AuditRepository:
    def log(self, guild_id: int, actor_user_id: int, action: str, entity_type: str, entity_id: str | None, details: dict):
        db.execute(
            """
            INSERT INTO audit_logs (guild_id, actor_user_id, action, entity_type, entity_id, details_json, created_at)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, EXTRACT(EPOCH FROM NOW())::BIGINT)
            """,
            (guild_id, actor_user_id, action, entity_type, entity_id, json.dumps(details)),
        )

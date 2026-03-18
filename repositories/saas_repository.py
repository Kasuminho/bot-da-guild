from __future__ import annotations

import time
from typing import Any

import db


class SaaSRepository:
    def upsert_guild(self, guild_id: int, name: str) -> None:
        now_epoch = int(time.time())
        db.execute(
            """
            INSERT INTO guilds (guild_id, name, subscription_status, is_active, created_at, updated_at)
            VALUES (%s, %s, 'free', TRUE, %s, %s)
            ON CONFLICT(guild_id)
            DO UPDATE SET name = EXCLUDED.name, updated_at = EXCLUDED.updated_at
            """,
            (guild_id, name, now_epoch, now_epoch),
        )

    def get_guild(self, guild_id: int) -> tuple[Any, ...] | None:
        return db.execute("SELECT guild_id, name, plan_id, subscription_status, subscription_expires_at, is_active, config_json FROM guilds WHERE guild_id = %s", (guild_id,), fetchone=True)

    def set_plan(self, guild_id: int, plan_id: str) -> None:
        db.execute(
            "UPDATE guilds SET plan_id = %s, updated_at = %s WHERE guild_id = %s",
            (plan_id, int(time.time()), guild_id),
        )

    def set_subscription_status(self, guild_id: int, status: str) -> None:
        db.execute(
            "UPDATE guilds SET subscription_status = %s, updated_at = %s WHERE guild_id = %s",
            (status, int(time.time()), guild_id),
        )

    def set_subscription_expiry(self, guild_id: int, expiry_epoch: int) -> None:
        db.execute(
            "UPDATE guilds SET subscription_expires_at = %s, updated_at = %s WHERE guild_id = %s",
            (expiry_epoch, int(time.time()), guild_id),
        )

    def get_plan(self, plan_id: str) -> tuple[Any, ...] | None:
        return db.execute(
            "SELECT plan_id, name, price_cents, currency, features_json, is_public FROM plans WHERE plan_id = %s",
            (plan_id,),
            fetchone=True,
        )

    def list_plans(self) -> list[tuple[Any, ...]]:
        return db.execute(
            "SELECT plan_id, name, price_cents, currency, features_json FROM plans ORDER BY price_cents ASC",
            fetchall=True,
        ) or []

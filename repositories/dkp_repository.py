from __future__ import annotations

import db


class DKPRepository:
    def add_transaction(self, guild_id: int, user_id: int, amount: int, reason: str, created_by_user_id: int, event_id: str | None = None):
        db.execute(
            """
            INSERT INTO dkp_transactions (guild_id, user_id, amount, reason, created_by_user_id, event_id, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, EXTRACT(EPOCH FROM NOW())::BIGINT)
            """,
            (guild_id, user_id, amount, reason, created_by_user_id, event_id),
        )

    def get_balance(self, guild_id: int, user_id: int) -> int:
        row = db.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM dkp_transactions WHERE guild_id = %s AND user_id = %s",
            (guild_id, user_id),
            fetchone=True,
        )
        return int(row[0] if row else 0)

    def get_leaderboard(self, guild_id: int, limit: int) -> list[tuple[int, int]]:
        return db.execute(
            """
            SELECT user_id, COALESCE(SUM(amount), 0) AS balance
            FROM dkp_transactions
            WHERE guild_id = %s
            GROUP BY user_id
            ORDER BY balance DESC, user_id ASC
            LIMIT %s
            """,
            (guild_id, limit),
            fetchall=True,
        ) or []

    def get_history(self, guild_id: int, user_id: int, limit: int):
        return db.execute(
            """
            SELECT amount, reason, created_by_user_id, created_at
            FROM dkp_transactions
            WHERE guild_id = %s AND user_id = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            (guild_id, user_id, limit),
            fetchall=True,
        ) or []

    def list_user_balances(self, guild_id: int):
        return db.execute(
            "SELECT user_id, COALESCE(SUM(amount), 0) FROM dkp_transactions WHERE guild_id = %s GROUP BY user_id",
            (guild_id,),
            fetchall=True,
        ) or []

    def clear_guild(self, guild_id: int, actor_id: int):
        balances = self.list_user_balances(guild_id)
        for user_id, balance in balances:
            if balance:
                self.add_transaction(guild_id, user_id, -int(balance), "DKP reset", actor_id, event_id="dkp_reset")

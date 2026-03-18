import json
import os
import re
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Optional

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DEFAULT_GUILD_ID = int(os.getenv("DEFAULT_GUILD_ID", "0") or "0")
SQLITE_PATH = os.getenv("SQLITE_PATH", "").strip()
ROOT = Path(__file__).resolve().parent
DEFAULT_SQLITE_PATH = ROOT / "database.db"

if DATABASE_URL and not DATABASE_URL.startswith(("postgres://", "postgresql://", "sqlite:///")):
    raise RuntimeError(
        "DATABASE_URL inválido. Use postgres://, postgresql://, sqlite:///caminho/ou/deixe vazio para SQLite local."
    )

IS_POSTGRES = DATABASE_URL.startswith(("postgres://", "postgresql://"))
IS_SQLITE = not IS_POSTGRES

if IS_SQLITE:
    sqlite_target = SQLITE_PATH or str(DEFAULT_SQLITE_PATH)
    if DATABASE_URL.startswith("sqlite:///"):
        sqlite_target = DATABASE_URL.removeprefix("sqlite:///")
    conn = sqlite3.connect(sqlite_target)
    conn.execute("PRAGMA foreign_keys = ON")
else:
    import psycopg2

    conn = psycopg2.connect(DATABASE_URL)

if IS_POSTGRES:
    conn.autocommit = False

POSTGRES_SCHEMA_PATH = ROOT / "sql" / "schema.sql"
SQLITE_SCHEMA_PATH = ROOT / "sql" / "schema_sqlite.sql"
SCHEMA_PATH = POSTGRES_SCHEMA_PATH if IS_POSTGRES else SQLITE_SCHEMA_PATH

SQLITE_EPOCH_PATTERN = re.compile(r"EXTRACT\(EPOCH FROM NOW\(\)\)::BIGINT", re.IGNORECASE)
SQLITE_JSON_CAST_PATTERN = re.compile(r"::jsonb", re.IGNORECASE)


@contextmanager
def get_cursor():
    cur = conn.cursor()
    try:
        yield cur
    finally:
        cur.close()


@contextmanager
def transaction():
    try:
        yield
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def adapt_query(query: str) -> str:
    if not IS_SQLITE:
        return query

    normalized = SQLITE_EPOCH_PATTERN.sub("CAST(strftime('%s', 'now') AS INTEGER)", query)
    normalized = SQLITE_JSON_CAST_PATTERN.sub("", normalized)
    return normalized.replace("%s", "?")


def execute(
    query: str,
    params: Optional[Iterable[Any]] = None,
    fetchone: bool = False,
    fetchall: bool = False,
):
    with transaction():
        with get_cursor() as cur:
            cur.execute(adapt_query(query), tuple(params or ()))
            if fetchone:
                return cur.fetchone()
            if fetchall:
                return cur.fetchall()
    return None


def ensure_schema():
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with transaction():
        with get_cursor() as cur:
            cur.executescript(schema_sql) if IS_SQLITE else cur.execute(schema_sql)


def column_exists(table: str, column: str) -> bool:
    if IS_SQLITE:
        rows = execute(f"PRAGMA table_info({table})", fetchall=True) or []
        return any(row[1] == column for row in rows)

    row = execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
        LIMIT 1
        """,
        (table, column),
        fetchone=True,
    )
    return row is not None


TENANT_TABLES = [
    "players",
    "one_time_reminders",
    "boss_rotations",
    "boss_participation",
    "forum_posts",
    "drops",
    "daily_announcements",
    "player_levels",
    "parties",
    "forum_items",
    "item_requests",
    "item_request_logs",
]


def ensure_tenant_column(table: str):
    if column_exists(table, "guild_id"):
        return
    execute(f"ALTER TABLE {table} ADD COLUMN guild_id BIGINT")


ensure_schema()


def run_bootstrap_migrations():
    if DEFAULT_GUILD_ID <= 0:
        return

    for table in TENANT_TABLES:
        ensure_tenant_column(table)
        execute("UPDATE {} SET guild_id = %s WHERE guild_id IS NULL".format(table), (DEFAULT_GUILD_ID,))

    execute("CREATE INDEX IF NOT EXISTS idx_players_guild_discord ON players(guild_id, discord_id)")
    execute("CREATE INDEX IF NOT EXISTS idx_item_requests_guild_thread ON item_requests(guild_id, thread_id)")
    execute("CREATE INDEX IF NOT EXISTS idx_drops_guild_discord ON drops(guild_id, discord_id)")

    free_features = json.dumps(
        {
            "dkp_enabled": False,
            "dkp_decay": False,
            "audit_logs": True,
            "advanced_reports": False,
        }
    )
    pro_features = json.dumps(
        {
            "dkp_enabled": True,
            "dkp_decay": True,
            "audit_logs": True,
            "advanced_reports": False,
        }
    )
    elite_features = json.dumps(
        {
            "dkp_enabled": True,
            "dkp_decay": True,
            "audit_logs": True,
            "advanced_reports": True,
        }
    )

    execute(
        """
        INSERT INTO plans (plan_id, name, price_cents, currency, features_json, is_public)
        VALUES
        ('free', 'Free', 0, 'USD', %s, TRUE),
        ('pro', 'Pro', 999, 'USD', %s, TRUE),
        ('elite', 'Elite', 2499, 'USD', %s, TRUE)
        ON CONFLICT(plan_id) DO NOTHING
        """,
        (free_features, pro_features, elite_features),
    )

    now_epoch = int(time.time())
    execute(
        """
        INSERT INTO guilds (guild_id, name, created_at, updated_at, plan_id, subscription_status, is_active, config_json)
        VALUES (%s, %s, %s, %s, COALESCE(NULLIF(%s, ''), 'pro'), 'active', TRUE, %s)
        ON CONFLICT(guild_id) DO NOTHING
        """,
        (
            DEFAULT_GUILD_ID,
            f"Guild {DEFAULT_GUILD_ID}",
            now_epoch,
            now_epoch,
            os.getenv("SAAS_DEFAULT_PLAN", "pro"),
            json.dumps({"loot_mode": "legacy"}),
        ),
    )


run_bootstrap_migrations()


def add_player(discord_id, nickname, language, channel_id):
    execute(
        """
        INSERT INTO players (discord_id, nickname_ingame, language, channel_id)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT(discord_id)
        DO UPDATE SET
            nickname_ingame = EXCLUDED.nickname_ingame,
            language = EXCLUDED.language,
            channel_id = EXCLUDED.channel_id
        """,
        (discord_id, nickname, language, channel_id),
    )


def update_channel(discord_id, channel_id):
    execute("UPDATE players SET channel_id=%s WHERE discord_id=%s", (channel_id, discord_id))


def get_all_players():
    return execute("SELECT * FROM players", fetchall=True) or []


def get_player_language(discord_id: int):
    row = execute(
        """
        SELECT language
        FROM players
        WHERE discord_id = %s
        """,
        (discord_id,),
        fetchone=True,
    )
    return row[0] if row else None


def add_reminder(tipo, nome, channel_id, timestamp):
    execute(
        """
        INSERT INTO one_time_reminders (tipo, nome, channel_id, timestamp)
        VALUES (%s, %s, %s, %s)
        """,
        (tipo, nome, channel_id, timestamp),
    )


def get_active_reminders():
    return execute(
        """
        SELECT id, tipo, nome, channel_id, timestamp, sent, warned_4h, warned_1h,
               warned_30m, warned_now, warned_daily_day
        FROM one_time_reminders
        WHERE sent = FALSE
        """,
        fetchall=True,
    ) or []


ALLOWED_REMINDER_WARN_FIELDS = {"warned_4h", "warned_1h", "warned_30m", "warned_now"}


def mark_warned(reminder_id, field):
    if field not in ALLOWED_REMINDER_WARN_FIELDS:
        raise ValueError(f"Campo inválido para reminder: {field}")

    execute(f'UPDATE one_time_reminders SET "{field}"=TRUE WHERE id=%s', (reminder_id,))


def set_warned_daily_day(reminder_id: int, day_key: int):
    execute(
        "UPDATE one_time_reminders SET warned_daily_day = %s WHERE id = %s",
        (day_key, reminder_id),
    )


def mark_reminder_sent(reminder_id):
    execute("UPDATE one_time_reminders SET sent=TRUE WHERE id=%s", (reminder_id,))


def get_pending_reminders(now):
    return execute(
        "SELECT * FROM one_time_reminders WHERE sent=FALSE AND timestamp<=%s",
        (now,),
        fetchall=True,
    ) or []


def mark_as_sent(reminder_id):
    execute("UPDATE one_time_reminders SET sent=TRUE WHERE id=%s", (reminder_id,))


def upsert_player_channel_with_language(discord_id, language, channel_id):
    execute(
        """
        INSERT INTO players (discord_id, nickname_ingame, language, channel_id)
        VALUES (%s, NULL, %s, %s)
        ON CONFLICT(discord_id)
        DO UPDATE SET channel_id = EXCLUDED.channel_id, language = EXCLUDED.language
        """,
        (discord_id, language, channel_id),
    )


def add_forum_post(thread_id, close_time):
    execute(
        """
        INSERT INTO forum_posts (thread_id, close_time)
        VALUES (%s, %s)
        ON CONFLICT(thread_id) DO NOTHING
        """,
        (thread_id, close_time),
    )


def get_open_forum_posts(now):
    return execute(
        "SELECT id, thread_id FROM forum_posts WHERE closed = FALSE AND close_time <= %s",
        (now,),
        fetchall=True,
    ) or []


def mark_forum_post_closed(post_id):
    execute("UPDATE forum_posts SET closed = TRUE WHERE id = %s", (post_id,))


def get_forum_post_by_thread(thread_id):
    return execute(
        "SELECT id, close_time, closed, delivered FROM forum_posts WHERE thread_id = %s",
        (thread_id,),
        fetchone=True,
    )


def mark_forum_post_delivered(post_id):
    execute("UPDATE forum_posts SET delivered = TRUE WHERE id = %s", (post_id,))


def add_drop(discord_id, nickname, item, thread_id, staff_id):
    execute(
        """
        INSERT INTO drops (discord_id, nickname_ingame, item, thread_id, staff_id, delivered_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (discord_id, nickname, item, thread_id, staff_id, int(time.time())),
    )


def get_last_drop(discord_id):
    row = execute(
        "SELECT delivered_at FROM drops WHERE discord_id = %s ORDER BY delivered_at DESC LIMIT 1",
        (discord_id,),
        fetchone=True,
    )
    return row[0] if row else None


def upsert_daily_announcement(channel_id, text_pt, text_en, image_pt_path, image_en_path):
    execute(
        """
        INSERT INTO daily_announcements (channel_id, text_pt, text_en, image_pt_path, image_en_path, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT(channel_id)
        DO UPDATE SET
            text_pt = EXCLUDED.text_pt,
            text_en = EXCLUDED.text_en,
            image_pt_path = EXCLUDED.image_pt_path,
            image_en_path = EXCLUDED.image_en_path,
            active = TRUE
        """,
        (channel_id, text_pt, text_en, image_pt_path, image_en_path, int(time.time())),
    )


def disable_daily_announcement(channel_id):
    execute("UPDATE daily_announcements SET active = FALSE WHERE channel_id = %s", (channel_id,))


def add_daily_announcement(text_pt, text_en, img_pt, img_en):
    execute(
        """
        INSERT INTO daily_announcements
        (channel_id, text_pt, text_en, image_pt_path, image_en_path, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (None, text_pt, text_en, img_pt, img_en, int(time.time())),
    )


def get_active_daily_announcements():
    return execute(
        """
        SELECT id, text_pt, text_en, image_pt_path, image_en_path
        FROM daily_announcements
        WHERE active = TRUE
        ORDER BY created_at ASC
        LIMIT 4
        """,
        fetchall=True,
    ) or []


def deactivate_daily_announcement(announcement_id):
    execute("UPDATE daily_announcements SET active = FALSE WHERE id = %s", (announcement_id,))


def get_future_reminders():
    now = int(time.time())
    return execute(
        """
        SELECT id, tipo, nome, channel_id, timestamp
        FROM one_time_reminders
        WHERE sent = FALSE AND timestamp > %s
        ORDER BY timestamp ASC
        """,
        (now,),
        fetchall=True,
    ) or []


def get_reminder_by_id(reminder_id):
    return execute(
        "SELECT tipo, nome, channel_id, timestamp FROM one_time_reminders WHERE id = %s",
        (reminder_id,),
        fetchone=True,
    )


def get_players_stuck_3_days():
    return execute(
        """
        SELECT player_id, player_name
        FROM player_levels
        GROUP BY player_id, player_name
        HAVING COUNT(DISTINCT level) = 1 AND COUNT(*) >= 3
        """,
        fetchall=True,
    ) or []


def add_player_level(player_id, player_name, level, days_ago=0):
    if days_ago > 3:
        raise ValueError("Máximo de 3 dias retroativos")

    day = int((datetime.utcnow() - timedelta(days=days_ago)).strftime("%Y%m%d"))
    now = int(time.time())

    execute(
        """
        INSERT INTO player_levels (player_id, player_name, level, day, created_at)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (player_id, day) DO NOTHING
        """,
        (player_id, player_name, level, day, now),
    )


def cleanup_old_players():
    limit_day = int((datetime.utcnow() - timedelta(days=4)).strftime("%Y%m%d"))
    execute(
        """
        DELETE FROM player_levels
        WHERE player_id NOT IN (
            SELECT DISTINCT player_id
            FROM player_levels
            WHERE day >= %s
        )
        """,
        (limit_day,),
    )


def get_player_drops(player_id: int):
    return execute(
        """
        SELECT item, delivered_at, staff_id
        FROM drops
        WHERE discord_id = %s
        ORDER BY delivered_at DESC
        LIMIT 10
        """,
        (player_id,),
        fetchall=True,
    ) or []


def add_forum_item(kind, category, item_pt, item_en, type_pt, type_en, image1_path, image2_path):
    now = int(time.time())
    with transaction():
        with get_cursor() as cur:
            cur.execute(
                adapt_query(
                    """
                    INSERT INTO forum_items (
                        kind, category, item_pt, item_en, type_pt, type_en, image1_path, image2_path, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """
                ),
                (kind, category, item_pt, item_en, type_pt, type_en, image1_path, image2_path, now),
            )
            return cur.fetchone()[0]


def get_forum_item(item_id: int):
    return execute(
        """
        SELECT id, kind, category, item_pt, item_en, type_pt, type_en, image1_path, image2_path
        FROM forum_items
        WHERE id = %s AND active = TRUE
        """,
        (item_id,),
        fetchone=True,
    )


def get_forum_items_by_kind(kind: str):
    return execute(
        "SELECT id, item_pt, item_en FROM forum_items WHERE kind = %s AND active = TRUE ORDER BY item_pt ASC",
        (kind,),
        fetchall=True,
    ) or []


def get_all_forum_items():
    return execute("SELECT id, item_pt, item_en FROM forum_items ORDER BY id", fetchall=True) or []


def get_forum_items_for_select():
    return execute(
        "SELECT id, kind, item_pt, item_en FROM forum_items WHERE active = TRUE ORDER BY kind, item_pt ASC",
        fetchall=True,
    ) or []


def get_forum_item_category_by_name(item_name: str):
    row = execute(
        """
        SELECT category
        FROM forum_items
        WHERE active = TRUE AND (LOWER(item_pt) = LOWER(%s) OR LOWER(item_en) = LOWER(%s))
        LIMIT 1
        """,
        (item_name, item_name),
        fetchone=True,
    )
    return row[0] if row else None


def add_rotation(rotation_type: str, day: int):
    with transaction():
        with get_cursor() as cur:
            cur.execute(
                adapt_query(
                    """
                    INSERT INTO boss_rotations (rotation_type, day, created_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT(rotation_type, day) DO NOTHING
                    """
                ),
                (rotation_type, day, int(time.time())),
            )
            cur.execute(adapt_query("SELECT id FROM boss_rotations WHERE rotation_type = %s AND day = %s"), (rotation_type, day))
            return cur.fetchone()[0]


def get_last_rotation_day():
    row = execute("SELECT MAX(day) FROM boss_rotations", fetchone=True)
    return row[0] if row and row[0] else None


def get_rotations_since(since_day: int):
    return execute(
        "SELECT id, day, rotation_type FROM boss_rotations WHERE day >= %s ORDER BY day DESC",
        (since_day,),
        fetchall=True,
    ) or []


def has_participation(rotation_id: int, discord_id: int) -> bool:
    return (
        execute(
            "SELECT 1 FROM boss_participation WHERE rotation_id = %s AND discord_id = %s LIMIT 1",
            (rotation_id, discord_id),
            fetchone=True,
        )
        is not None
    )


def get_or_create_rotation(rotation_type: str, day: int) -> int:
    return add_rotation(rotation_type, day)


def add_participation(rotation_id: int, discord_id: int) -> bool:
    with transaction():
        with get_cursor() as cur:
            cur.execute(
                adapt_query(
                    """
                    INSERT INTO boss_participation (rotation_id, discord_id, present)
                    VALUES (%s, %s, TRUE)
                    ON CONFLICT(rotation_id, discord_id) DO NOTHING
                    """
                ),
                (rotation_id, discord_id),
            )
            return cur.rowcount > 0


def get_participation_stats(discord_id: int, start_day: str, end_day: str):
    total_rotations = execute(
        "SELECT COUNT(*) FROM boss_rotations WHERE day BETWEEN %s AND %s",
        (start_day, end_day),
        fetchone=True,
    )[0]
    presences = execute(
        """
        SELECT COUNT(*)
        FROM boss_participation bp
        JOIN boss_rotations br ON br.id = bp.rotation_id
        WHERE bp.discord_id = %s AND br.day BETWEEN %s AND %s
        """,
        (discord_id, start_day, end_day),
        fetchone=True,
    )[0]
    t4_absences = execute(
        """
        SELECT COUNT(*)
        FROM boss_rotations br
        WHERE br.rotation_type = 'T4'
          AND br.day BETWEEN %s AND %s
          AND br.id NOT IN (
              SELECT rotation_id FROM boss_participation WHERE discord_id = %s
          )
        """,
        (start_day, end_day, discord_id),
        fetchone=True,
    )[0]
    return {"total_rotations": total_rotations, "presences": presences, "t4_absences": t4_absences}


def get_rotation_history(discord_id: int, start_day: int, end_day: int):
    rows = execute(
        """
        SELECT br.day, br.rotation_type,
               CASE WHEN bp.id IS NOT NULL THEN 1 ELSE 0 END AS present
        FROM boss_rotations br
        LEFT JOIN boss_participation bp ON bp.rotation_id = br.id AND bp.discord_id = %s
        WHERE br.day BETWEEN %s AND %s
        ORDER BY br.day ASC
        """,
        (discord_id, start_day, end_day),
        fetchall=True,
    ) or []
    return [{"day": row[0], "type": row[1], "present": bool(row[2])} for row in rows]


def add_item_request(discord_id, player_name, item_name, quantity, thread_id, thread_channel_id):
    now = int(time.time())
    with transaction():
        with get_cursor() as cur:
            cur.execute(
                adapt_query("SELECT id FROM item_requests WHERE discord_id = %s AND item_name = %s"),
                (discord_id, item_name),
            )
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    adapt_query(
                        """
                        UPDATE item_requests
                        SET total_quantity = %s, remaining_quantity = %s, last_update = %s,
                            warned_3d = FALSE, warned_4d = FALSE
                        WHERE id = %s
                        """
                    ),
                    (quantity, quantity, now, existing[0]),
                )
                return

            cur.execute(
                adapt_query("SELECT COALESCE(MAX(rank_position), 0) FROM item_requests WHERE item_name = %s"),
                (item_name,),
            )
            rank = cur.fetchone()[0] + 1
            cur.execute(
                adapt_query(
                    """
                    INSERT INTO item_requests (
                        discord_id, player_name, item_name, total_quantity, remaining_quantity,
                        rank_position, thread_id, thread_channel_id, created_at, last_update
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                ),
                (discord_id, player_name, item_name, quantity, quantity, rank, thread_id, thread_channel_id, now, now),
            )


def get_item_requests_by_player(discord_id: int):
    rows = execute("SELECT item_name FROM item_requests WHERE discord_id = %s", (discord_id,), fetchall=True) or []
    return [row[0] for row in rows]


def update_item_request_by_thread(thread_id):
    now = int(time.time())
    with transaction():
        with get_cursor() as cur:
            cur.execute(
                adapt_query("UPDATE item_requests SET last_update = %s, warned_3d = FALSE, warned_4d = FALSE WHERE thread_id = %s"),
                (now, thread_id),
            )
            return cur.rowcount > 0


def deliver_item_by_thread(thread_id, item_key, quantity):
    now = int(time.time())
    with transaction():
        with get_cursor() as cur:
            cur.execute(
                adapt_query("SELECT id, item_name, remaining_quantity, rank_position FROM item_requests WHERE thread_id = %s AND item_name = %s"),
                (thread_id, item_key),
            )
            row = cur.fetchone()
            if not row:
                return False

            request_id, item_name, remaining, rank = row
            new_remaining = remaining - quantity

            if new_remaining > 0:
                cur.execute(adapt_query("UPDATE item_requests SET remaining_quantity = %s WHERE id = %s"), (new_remaining, request_id))
            else:
                cur.execute(adapt_query("DELETE FROM item_requests WHERE id = %s"), (request_id,))
                cur.execute(
                    adapt_query("UPDATE item_requests SET rank_position = rank_position - 1 WHERE item_name = %s AND rank_position > %s"),
                    (item_name, rank),
                )

            cur.execute(
                adapt_query("INSERT INTO item_request_logs (request_id, action, info, thread_id, created_at) VALUES (%s, 'delivered', %s, %s, %s)"),
                (request_id, f"qty={quantity}", thread_id, now),
            )
            return True


def get_all_item_requests_for_check():
    return execute(
        """
        SELECT id, discord_id, player_name, item_name, rank_position, thread_id,
               thread_channel_id, last_update, warned_3d, warned_4d
        FROM item_requests
        ORDER BY item_name, rank_position ASC
        """,
        fetchall=True,
    ) or []


ALLOWED_REQUEST_WARN_FIELDS = {"warned_3d", "warned_4d"}


def mark_request_warned(request_id, field):
    if field not in ALLOWED_REQUEST_WARN_FIELDS:
        raise ValueError(f"Campo inválido para item request: {field}")

    execute(f'UPDATE item_requests SET "{field}" = TRUE WHERE id = %s', (request_id,))


def drop_request_rank(request_id):
    now = int(time.time())
    with transaction():
        with get_cursor() as cur:
            cur.execute(adapt_query("SELECT item_name, rank_position FROM item_requests WHERE id = %s"), (request_id,))
            row = cur.fetchone()
            if not row:
                return
            item_name, rank = row

            cur.execute(adapt_query("SELECT id FROM item_requests WHERE item_name = %s AND rank_position = %s"), (item_name, rank + 1))
            below = cur.fetchone()
            if not below:
                return
            below_id = below[0]

            cur.execute(
                adapt_query("UPDATE item_requests SET rank_position = %s, last_update = %s, warned_3d = FALSE, warned_4d = FALSE WHERE id = %s"),
                (rank, now, below_id),
            )
            cur.execute(
                adapt_query("UPDATE item_requests SET rank_position = %s, last_update = %s, warned_3d = FALSE, warned_4d = FALSE WHERE id = %s"),
                (rank + 1, now, request_id),
            )


def get_daily_item_summary():
    return execute(
        "SELECT item_name, rank_position, player_name, remaining_quantity, thread_id FROM item_requests ORDER BY item_name, rank_position ASC",
        fetchall=True,
    ) or []


def get_item_request_by_thread(thread_id):
    return execute(
        "SELECT id, discord_id, player_name, item_name, rank_position, thread_id, last_update FROM item_requests WHERE thread_id = %s",
        (thread_id,),
        fetchone=True,
    )


def get_request_by_thread(thread_id: int, item_name: str):
    return execute(
        "SELECT id, discord_id, item_name, rank_position FROM item_requests WHERE thread_id = %s and item_name = %s",
        (thread_id, item_name),
        fetchone=True,
    )


def get_active_request_items_by_thread(thread_id: int):
    rows = execute(
        "SELECT item_name FROM item_requests WHERE thread_id = %s ORDER BY rank_position ASC",
        (thread_id,),
        fetchall=True,
    ) or []
    return [row[0] for row in rows]


def delete_request(request_id: int):
    execute("DELETE FROM item_requests WHERE id = %s", (request_id,))


def reorder_item_ranks(item_name: str):
    with transaction():
        with get_cursor() as cur:
            cur.execute(adapt_query("SELECT id FROM item_requests WHERE item_name = %s ORDER BY rank_position ASC"), (item_name,))
            rows = cur.fetchall()
            for index, (req_id,) in enumerate(rows, start=1):
                cur.execute(adapt_query("UPDATE item_requests SET rank_position = %s WHERE id = %s"), (index, req_id))


def fix_last_update(request_id: int, ts: int):
    execute("UPDATE item_requests SET last_update = %s WHERE id = %s", (ts, request_id))


def get_player_timezone(discord_id: int):
    row = execute("SELECT timezone FROM players WHERE discord_id = %s", (discord_id,), fetchone=True)
    return row[0] if row else None


def set_player_timezone(discord_id: int, timezone: str):
    execute("UPDATE players SET timezone = %s WHERE discord_id = %s", (timezone, discord_id))


def add_party(message_id, channel_id, creator_id, reason_pt, reason_en, start_ts, end_ts):
    execute(
        """
        INSERT INTO parties (message_id, channel_id, creator_id, reason_pt, reason_en, start_ts, end_ts)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (message_id, channel_id, creator_id, reason_pt, reason_en, start_ts, end_ts),
    )


def get_party_by_message(message_id: int):
    return execute("SELECT * FROM parties WHERE message_id = %s", (message_id,), fetchone=True)


def get_parties_by_creator(creator_id: int):
    return execute("SELECT message_id, channel_id FROM parties WHERE creator_id = %s", (creator_id,), fetchone=True)


def get_all_parties():
    return execute("SELECT message_id, channel_id FROM parties", fetchall=True) or []


def delete_party(message_id: int):
    execute("DELETE FROM parties WHERE message_id = %s", (message_id,))


def clear_parties():
    execute("DELETE FROM parties")


def cleanup_boss_participation_duplicates():
    with transaction():
        with get_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM boss_participation")
            before = cur.fetchone()[0]
            cur.execute(
                """
                DELETE FROM boss_participation
                WHERE id NOT IN (
                    SELECT MIN(id)
                    FROM boss_participation
                    GROUP BY rotation_id, discord_id
                )
                """
            )
            cur.execute("SELECT COUNT(*) FROM boss_participation")
            after = cur.fetchone()[0]
            return before, after

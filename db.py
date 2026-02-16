import sqlite3
import time
from datetime import datetime, timedelta

conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_id INTEGER UNIQUE,
    nickname_ingame TEXT,
    language TEXT,
    channel_id INTEGER
)
"""
)

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS one_time_reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL,
    nome TEXT NOT NULL,
    channel_id INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    sent INTEGER DEFAULT 0,
    warned_4h INTEGER DEFAULT 0,
    warned_1h INTEGER DEFAULT 0,
    warned_30m INTEGER DEFAULT 0,
    warned_now INTEGER DEFAULT 0,
    warned_daily_day INTEGER
)
"""
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS boss_rotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rotation_type TEXT NOT NULL, -- T3 | T4
    day INTEGER NOT NULL,        -- YYYYMMDD
    created_at INTEGER NOT NULL,
    UNIQUE(rotation_type, day)
)
    """
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS boss_participation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rotation_id INTEGER NOT NULL,
    discord_id INTEGER NOT NULL,
    present INTEGER NOT NULL, -- 1 = presente, 0 = falta
    FOREIGN KEY(rotation_id) REFERENCES boss_rotations(id)
)
    """
)

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS forum_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id INTEGER UNIQUE,
    close_time INTEGER,
    closed INTEGER DEFAULT 0,
    delivered INTEGER DEFAULT 0
)
"""
)

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS drops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_id INTEGER,
    nickname_ingame TEXT,
    item TEXT,
    thread_id INTEGER,
    staff_id INTEGER,
    delivered_at INTEGER
)
"""
)

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS daily_announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text_pt TEXT NOT NULL,
    text_en TEXT NOT NULL,
    image_pt_path TEXT NOT NULL,
    image_en_path TEXT NOT NULL,
    active INTEGER DEFAULT 1,
    created_at INTEGER NOT NULL
)
"""
)

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS player_levels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    player_name TEXT NOT NULL,
    level INTEGER NOT NULL,
    day INTEGER NOT NULL, -- YYYYMMDD
    created_at INTEGER NOT NULL
)
"""
)

cursor.execute(
    """
CREATE UNIQUE INDEX IF NOT EXISTS idx_player_day
ON player_levels(player_id, day)
"""
)

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS parties (
    message_id INTEGER PRIMARY KEY,
    channel_id INTEGER NOT NULL,
    creator_id INTEGER NOT NULL,
    reason_pt TEXT NOT NULL,
    reason_en TEXT NOT NULL,
    start_ts INTEGER NOT NULL,
    end_ts INTEGER NOT NULL
)
"""
)

cursor.execute(
    """
CREATE TABLE IF NOT EXISTS forum_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    kind TEXT NOT NULL,        -- equipment | skill
    category TEXT NOT NULL,    -- PvE | PvP

    item_pt TEXT NOT NULL,
    item_en TEXT NOT NULL,

    type_pt TEXT NOT NULL,
    type_en TEXT NOT NULL,

    image1_path TEXT NOT NULL,
    image2_path TEXT NOT NULL,

    active INTEGER DEFAULT 1,
    created_at INTEGER NOT NULL
)
"""
)

cursor.execute(
    """
 CREATE TABLE IF NOT EXISTS item_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    discord_id INTEGER NOT NULL,
    player_name TEXT NOT NULL,

    item_name TEXT NOT NULL,

    total_quantity INTEGER NOT NULL,
    remaining_quantity INTEGER NOT NULL,

    rank_position INTEGER NOT NULL,

    thread_id INTEGER NOT NULL,
    thread_channel_id INTEGER NOT NULL,

    created_at INTEGER NOT NULL,
    last_update INTEGER NOT NULL,

    warned_3d INTEGER DEFAULT 0,
    warned_4d INTEGER DEFAULT 0
)
    """
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS item_request_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL,
    action TEXT NOT NULL, -- created | updated | delivered | rank_down
    info TEXT,
    thread_id INTEGER,
    created_at INTEGER NOT NULL
)
    """
)

conn.commit()

def _ensure_one_time_reminders_columns():
    cursor.execute("PRAGMA table_info(one_time_reminders)")
    columns = {row[1] for row in cursor.fetchall()}

    if "warned_4h" not in columns:
        cursor.execute(
            "ALTER TABLE one_time_reminders ADD COLUMN warned_4h INTEGER DEFAULT 0"
        )

    if "warned_daily_day" not in columns:
        cursor.execute(
            "ALTER TABLE one_time_reminders ADD COLUMN warned_daily_day INTEGER"
        )

    conn.commit()


_ensure_one_time_reminders_columns()


def add_player(discord_id, nickname, language, channel_id):
    cursor.execute(
        """
        INSERT OR REPLACE INTO players
        (discord_id, nickname_ingame, language, channel_id)
        VALUES (?, ?, ?, ?)
    """,
        (discord_id, nickname, language, channel_id),
    )
    conn.commit()


def update_channel(discord_id, channel_id):
    cursor.execute(
        "UPDATE players SET channel_id=? WHERE discord_id=?", (channel_id, discord_id)
    )
    conn.commit()


def get_all_players():
    cursor.execute("SELECT * FROM players")
    return cursor.fetchall()


def get_player_language(discord_id: int):
    cursor.execute(
        """
        SELECT language
        FROM players
        WHERE discord_id = ?
        """,
        (discord_id,),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def add_reminder(tipo, nome, channel_id, timestamp):
    cursor.execute(
        """
        INSERT INTO one_time_reminders (tipo, nome, channel_id, timestamp)
        VALUES (?, ?, ?, ?)
    """,
        (tipo, nome, channel_id, timestamp),
    )
    conn.commit()


def get_active_reminders():
    cursor.execute(
        """
        SELECT
            id,
            tipo,
            nome,
            channel_id,
            timestamp,
            sent,
            warned_4h,
            warned_1h,
            warned_30m,
            warned_now,
            warned_daily_day
        FROM one_time_reminders
        WHERE sent = 0
    """
    )
    return cursor.fetchall()


def mark_warned(reminder_id, field):
    cursor.execute(
        f"UPDATE one_time_reminders SET {field}=1 WHERE id=?", (reminder_id,)
    )
    conn.commit()




def set_warned_daily_day(reminder_id: int, day_key: int):
    cursor.execute(
        "UPDATE one_time_reminders SET warned_daily_day = ? WHERE id = ?",
        (day_key, reminder_id),
    )
    conn.commit()

def mark_reminder_sent(reminder_id):
    cursor.execute("UPDATE one_time_reminders SET sent=1 WHERE id=?", (reminder_id,))
    conn.commit()


def get_pending_reminders(now):
    cursor.execute(
        "SELECT * FROM one_time_reminders WHERE sent=0 AND timestamp<=?", (now,)
    )
    return cursor.fetchall()


def mark_as_sent(reminder_id):
    cursor.execute("UPDATE one_time_reminders SET sent=1 WHERE id=?", (reminder_id,))
    conn.commit()


def upsert_player_channel_with_language(discord_id, language, channel_id):
    cursor.execute(
        """
        INSERT INTO players (discord_id, nickname_ingame, language, channel_id)
        VALUES (?, NULL, ?, ?)
        ON CONFLICT(discord_id)
        DO UPDATE SET
            channel_id = excluded.channel_id,
            language = excluded.language
    """,
        (discord_id, language, channel_id),
    )
    conn.commit()


# =========================
# FORUM POSTS
# =========================


def add_forum_post(thread_id, close_time):
    cursor.execute(
        """
    INSERT OR IGNORE INTO forum_posts (thread_id, close_time)
    VALUES (?, ?)
    """,
        (thread_id, close_time),
    )

    conn.commit()


def get_open_forum_posts(now):
    cursor.execute(
        """
    SELECT id, thread_id
    FROM forum_posts
    WHERE closed = 0 AND close_time <= ?
    """,
        (now,),
    )

    rows = cursor.fetchall()
    return rows


def mark_forum_post_closed(post_id):
    cursor.execute(
        """
    UPDATE forum_posts
    SET closed = 1
    WHERE id = ?
    """,
        (post_id,),
    )

    conn.commit()


def get_forum_post_by_thread(thread_id):
    cursor.execute(
        """
    SELECT id, close_time, closed, delivered
    FROM forum_posts
    WHERE thread_id = ?
    """,
        (thread_id,),
    )

    row = cursor.fetchone()
    return row


def mark_forum_post_delivered(post_id):
    cursor.execute(
        """
    UPDATE forum_posts
    SET delivered = 1
    WHERE id = ?
    """,
        (post_id,),
    )

    conn.commit()


# =========================
# DROPS
# =========================


def add_drop(discord_id, nickname, item, thread_id, staff_id):
    cursor.execute(
        """
    INSERT INTO drops (
        discord_id,
        nickname_ingame,
        item,
        thread_id,
        staff_id,
        delivered_at
    ) VALUES (?, ?, ?, ?, ?, ?)
    """,
        (discord_id, nickname, item, thread_id, staff_id, int(time.time())),
    )

    conn.commit()


def get_last_drop(discord_id):
    cursor.execute(
        """
    SELECT delivered_at
    FROM drops
    WHERE discord_id = ?
    ORDER BY delivered_at DESC
    LIMIT 1
    """,
        (discord_id,),
    )

    row = cursor.fetchone()

    return row[0] if row else None


# =========================
# DAILY ANNOUNCEMENTS
# =========================


def upsert_daily_announcement(
    channel_id, text_pt, text_en, image_pt_path, image_en_path
):
    cursor.execute(
        """
        INSERT INTO daily_announcements (
            channel_id, text_pt, text_en, image_pt_path, image_en_path
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(channel_id)
        DO UPDATE SET
            text_pt = excluded.text_pt,
            text_en = excluded.text_en,
            image_pt_path = excluded.image_pt_path,
            image_en_path = excluded.image_en_path,
            active = 1
        """,
        (channel_id, text_pt, text_en, image_pt_path, image_en_path),
    )
    conn.commit()


def disable_daily_announcement(channel_id):
    cursor.execute(
        """
        UPDATE daily_announcements
        SET active = 0
        WHERE channel_id = ?
        """,
        (channel_id,),
    )
    conn.commit()


def add_daily_announcement(text_pt, text_en, img_pt, img_en):
    cursor.execute(
        """
        INSERT INTO daily_announcements
        (text_pt, text_en, image_pt_path, image_en_path, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (text_pt, text_en, img_pt, img_en, int(time.time())),
    )
    conn.commit()


def get_active_daily_announcements():
    cursor.execute(
        """
        SELECT id, text_pt, text_en, image_pt_path, image_en_path
        FROM daily_announcements
        WHERE active = 1
        ORDER BY created_at ASC
        LIMIT 4
        """
    )
    return cursor.fetchall()


def deactivate_daily_announcement(announcement_id):
    cursor.execute(
        "UPDATE daily_announcements SET active = 0 WHERE id = ?", (announcement_id,)
    )
    conn.commit()


def get_future_reminders():
    now = int(time.time())
    cursor.execute(
        """
        SELECT id, tipo, nome, channel_id, timestamp
        FROM one_time_reminders
        WHERE sent = 0
          AND timestamp > ?
        ORDER BY timestamp ASC
        """,
        (now,),
    )
    return cursor.fetchall()


def get_reminder_by_id(reminder_id):
    cursor.execute(
        """
        SELECT tipo, nome, channel_id, timestamp
        FROM one_time_reminders
        WHERE id = ?
        """,
        (reminder_id,),
    )
    return cursor.fetchone()


def get_players_stuck_3_days():
    cursor.execute(
        """
        SELECT player_id, player_name
        FROM player_levels
        GROUP BY player_id
        HAVING COUNT(DISTINCT level) = 1
           AND COUNT(*) >= 3
        """
    )
    return cursor.fetchall()


def add_player_level(player_id, player_name, level, days_ago=0):
    if days_ago > 3:
        raise ValueError("Máximo de 3 dias retroativos")

    day = int((datetime.utcnow() - timedelta(days=days_ago)).strftime("%Y%m%d"))
    now = int(time.time())

    cursor.execute(
        """
        INSERT OR IGNORE INTO player_levels
        (player_id, player_name, level, day, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (player_id, player_name, level, day, now),
    )
    conn.commit()


def cleanup_old_players():
    limit_day = int((datetime.utcnow() - timedelta(days=4)).strftime("%Y%m%d"))
    cursor.execute(
        """
        DELETE FROM player_levels
        WHERE player_id NOT IN (
            SELECT DISTINCT player_id
            FROM player_levels
            WHERE day >= ?
        )
        """,
        (limit_day,),
    )
    conn.commit()


def get_player_drops(player_id: int):
    cursor.execute(
        """
        SELECT
            item,
            delivered_at,
            staff_id
        FROM drops
        WHERE discord_id = ?
        ORDER BY delivered_at DESC
        LIMIT 10
    """,
        (player_id,),
    )
    return cursor.fetchall()


def add_forum_item(
    kind,
    category,
    item_pt,
    item_en,
    type_pt,
    type_en,
    image1_path,
    image2_path,
):
    cursor.execute(
        """
        INSERT INTO forum_items (
            kind, category,
            item_pt, item_en,
            type_pt, type_en,
            image1_path, image2_path,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            kind,
            category,
            item_pt,
            item_en,
            type_pt,
            type_en,
            image1_path,
            image2_path,
            int(time.time()),
        ),
    )
    conn.commit()
    return cursor.lastrowid


def get_forum_item(item_id: int):
    cursor.execute(
        """
        SELECT
            id,
            kind,
            category,
            item_pt,
            item_en,
            type_pt,
            type_en,
            image1_path,
            image2_path
        FROM forum_items
        WHERE id = ? AND active = 1
        """,
        (item_id,),
    )
    return cursor.fetchone()


def get_forum_items_by_kind(kind: str):
    cursor.execute(
        """
        SELECT id, item_pt, item_en
        FROM forum_items
        WHERE kind = ? AND active = 1
        ORDER BY item_pt ASC
        """,
        (kind,),
    )
    return cursor.fetchall()


def get_all_forum_items():
    """
    Retorna uma lista de todos os itens do fórum no formato:
    [(id, nome_pt, nome_en), ...]
    """
    cursor = conn.cursor()
    cursor.execute("SELECT id, item_pt, item_en FROM forum_items ORDER BY id")
    return cursor.fetchall()


def get_forum_items_for_select():
    """
    Retorna todos os itens ativos do fórum,
    usados no fluxo de anúncio.
    Retorno:
    (id, kind, item_pt, item_en)
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, kind, item_pt, item_en
        FROM forum_items
        WHERE active = 1
        ORDER BY kind, item_pt ASC
    """)
    return cursor.fetchall()


def get_forum_item_category_by_name(item_name: str):
    cursor.execute(
        """
        SELECT category
        FROM forum_items
        WHERE active = 1
          AND (LOWER(item_pt) = LOWER(?) OR LOWER(item_en) = LOWER(?))
        LIMIT 1
        """,
        (item_name, item_name),
    )
    row = cursor.fetchone()
    return row[0] if row else None

# =========================
# BOSS ROTATIONS (FINAL)
# =========================

def add_rotation(rotation_type: str, day: int):
    cursor.execute(
        """
        INSERT OR IGNORE INTO boss_rotations
        (rotation_type, day, created_at)
        VALUES (?, ?, ?)
        """,
        (rotation_type, day, int(time.time())),
    )
    conn.commit()

    cursor.execute(
        """
        SELECT id
        FROM boss_rotations
        WHERE rotation_type = ? AND day = ?
        """,
        (rotation_type, day),
    )
    return cursor.fetchone()[0]


def get_last_rotation_day():
    cursor.execute("SELECT MAX(day) FROM boss_rotations")
    row = cursor.fetchone()
    return row[0] if row and row[0] else None


def get_rotations_since(since_day: int):
    cursor.execute(
        """
        SELECT id, day, rotation_type
        FROM boss_rotations
        WHERE day >= ?
        ORDER BY day DESC
        """,
        (since_day,),
    )
    return cursor.fetchall()


def has_participation(rotation_id: int, discord_id: int) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM boss_participation
        WHERE rotation_id = ?
          AND discord_id = ?
        LIMIT 1
        """,
        (rotation_id, discord_id),
    )
    return cursor.fetchone() is not None


def get_or_create_rotation(rotation_type: str, day: int) -> int:
    cursor.execute(
        """
        INSERT OR IGNORE INTO boss_rotations (rotation_type, day, created_at)
        VALUES (?, ?, ?)
        """,
        (rotation_type, day, int(time.time())),
    )
    conn.commit()

    cursor.execute(
        """
        SELECT id
        FROM boss_rotations
        WHERE rotation_type = ? AND day = ?
        """,
        (rotation_type, day),
    )
    return cursor.fetchone()[0]


def add_participation(rotation_id: int, discord_id: int) -> bool:
    cursor.execute(
        """
        INSERT OR IGNORE INTO boss_participation
        (rotation_id, discord_id, present)
        VALUES (?, ?, 1)
        """,
        (rotation_id, discord_id),
    )
    conn.commit()
    return cursor.rowcount > 0

def get_participation_stats(discord_id: int, start_day: str, end_day: str):
    """
    Retorna estatísticas de participação do jogador no período informado.

    Regras:
    - total_rotations: total de rotações T3 + T4 no período
    - presences: quantas ele participou
    - t4_absences: quantas rotações T4 ele faltou
    """

    # Total de rotações no período
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM boss_rotations
        WHERE day BETWEEN ? AND ?
        """,
        (start_day, end_day),
    )
    total_rotations = cursor.fetchone()[0]

    # Presenças do jogador
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM boss_participation bp
        JOIN boss_rotations br ON br.id = bp.rotation_id
        WHERE bp.discord_id = ?
          AND br.day BETWEEN ? AND ?
        """,
        (discord_id, start_day, end_day),
    )
    presences = cursor.fetchone()[0]

    # Faltas em T4
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM boss_rotations br
        WHERE br.rotation_type = 'T4'
          AND br.day BETWEEN ? AND ?
          AND br.id NOT IN (
              SELECT rotation_id
              FROM boss_participation
              WHERE discord_id = ?
          )
        """,
        (start_day, end_day, discord_id),
    )
    t4_absences = cursor.fetchone()[0]

    return {
        "total_rotations": total_rotations,
        "presences": presences,
        "t4_absences": t4_absences,
    }
    
def get_rotation_history(discord_id: int, start_day: int, end_day: int):
    """
    Retorna todas as rotações no período, marcando se o jogador esteve presente.
    """

    cursor.execute(
        """
        SELECT
            br.day,
            br.rotation_type,
            CASE
                WHEN bp.id IS NOT NULL THEN 1
                ELSE 0
            END AS present
        FROM boss_rotations br
        LEFT JOIN boss_participation bp
            ON bp.rotation_id = br.id
           AND bp.discord_id = ?
        WHERE br.day BETWEEN ? AND ?
        ORDER BY br.day ASC
        """,
        (discord_id, start_day, end_day),
    )

    rows = cursor.fetchall()

    return [
        {
            "day": row[0],
            "type": row[1],
            "present": bool(row[2]),
        }
        for row in rows
    ]



#Funções do rankeamento

def add_item_request(discord_id, player_name, item_name, quantity, thread_id, thread_channel_id):
    now = int(time.time())

    cursor.execute(
        "SELECT id FROM item_requests WHERE discord_id = ? AND item_name = ?",
        (discord_id, item_name),
    )
    existing = cursor.fetchone()

    if existing:
        cursor.execute(
            """
            UPDATE item_requests
            SET total_quantity = ?,
                remaining_quantity = ?,
                last_update = ?,
                warned_3d = 0,
                warned_4d = 0
            WHERE id = ?
            """,
            (quantity, quantity, now, existing[0]),
        )
        conn.commit()
        return

    cursor.execute(
        "SELECT COALESCE(MAX(rank_position), 0) FROM item_requests WHERE item_name = ?",
        (item_name,),
    )
    rank = cursor.fetchone()[0] + 1

    cursor.execute(
        """
        INSERT INTO item_requests (
            discord_id, player_name, item_name,
            total_quantity, remaining_quantity,
            rank_position, thread_id, thread_channel_id,
            created_at, last_update
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (discord_id, player_name, item_name, quantity, quantity,
         rank, thread_id, thread_channel_id, now, now),
    )
    conn.commit()


def get_item_requests_by_player(discord_id: int):
    cursor.execute(
        """
        SELECT item_name
        FROM item_requests
        WHERE discord_id = ?
        """,
        (discord_id,),
    )
    return [row[0] for row in cursor.fetchall()]



def update_item_request_by_thread(thread_id):
    now = int(time.time())
    cursor.execute(
        """
        UPDATE item_requests
        SET last_update = ?, warned_3d = 0, warned_4d = 0
        WHERE thread_id = ?
        """,
        (now, thread_id),
    )
    conn.commit()
    return cursor.rowcount > 0



def deliver_item_by_thread(thread_id, item_key, quantity):
    now = int(time.time())

    cursor.execute(
        """
        SELECT
            id,
            item_name,
            remaining_quantity,
            rank_position
        FROM item_requests
        WHERE thread_id = ? AND item_name = ?
        """,
        (thread_id,item_key,),
    )

    row = cursor.fetchone()
    if not row:
        return False

    request_id, item_name, remaining, rank = row
    new_remaining = remaining - quantity

    if new_remaining > 0:
        cursor.execute(
            """
            UPDATE item_requests
            SET remaining_quantity = ?
            WHERE id = ?
            """,
            (new_remaining, request_id),
        )
    else:
        cursor.execute(
            "DELETE FROM item_requests WHERE id = ?", (request_id,)
        )

        cursor.execute(
            """
            UPDATE item_requests
            SET rank_position = rank_position - 1
            WHERE item_name = ?
              AND rank_position > ?
            """,
            (item_name, rank),
        )

    cursor.execute(
        """
        INSERT INTO item_request_logs
        (request_id, action, info, thread_id, created_at)
        VALUES (?, 'delivered', ?, ?, ?)
        """,
        (request_id, f"qty={quantity}", thread_id, now),
    )

    conn.commit()
    return True


def get_all_item_requests_for_check():
    cursor.execute(
        """
        SELECT
            id,
            discord_id,
            player_name,
            item_name,
            rank_position,
            thread_id,
            thread_channel_id,
            last_update,
            warned_3d,
            warned_4d
        FROM item_requests
        ORDER BY item_name, rank_position ASC
        """
    )
    return cursor.fetchall()


def mark_request_warned(request_id, field):
    cursor.execute(
        f"UPDATE item_requests SET {field} = 1 WHERE id = ?",
        (request_id,),
    )
    conn.commit()


def drop_request_rank(request_id):
    now = int(time.time())

    cursor.execute(
        "SELECT item_name, rank_position FROM item_requests WHERE id = ?",
        (request_id,),
    )
    row = cursor.fetchone()
    if not row:
        return

    item_name, rank = row

    cursor.execute(
        "SELECT id FROM item_requests WHERE item_name = ? AND rank_position = ?",
        (item_name, rank + 1),
    )
    below = cursor.fetchone()
    if not below:
        return

    below_id = below[0]

    # QUEM SOBE
    cursor.execute(
        """
        UPDATE item_requests
        SET rank_position = ?, last_update = ?, warned_3d = 0, warned_4d = 0
        WHERE id = ?
        """,
        (rank, now, below_id),
    )

    # QUEM CAI
    cursor.execute(
        """
        UPDATE item_requests
        SET rank_position = ?, last_update = ?, warned_3d = 0, warned_4d = 0
        WHERE id = ?
        """,
        (rank + 1, now, request_id),
    )

    conn.commit()



def get_daily_item_summary():
    cursor.execute(
        """
        SELECT
            item_name,
            rank_position,
            player_name,
            remaining_quantity,
            thread_id
        FROM item_requests
        ORDER BY item_name, rank_position ASC
        """
    )
    return cursor.fetchall()

def get_item_request_by_thread(thread_id):
    cursor.execute(
        """
        SELECT
            id,
            discord_id,
            player_name,
            item_name,
            rank_position,
            thread_id,
            last_update
        FROM item_requests
        WHERE thread_id = ?
        """,
        (thread_id,),
    )
    return cursor.fetchone()


def get_request_by_thread(thread_id: int, item_name: str):
    cursor.execute(
        """
        SELECT id, discord_id, item_name, rank_position
        FROM item_requests
        WHERE thread_id = ? and item_name = ?
        """,
        (thread_id,item_name)
    )
    return cursor.fetchone()


def get_active_request_items_by_thread(thread_id: int):
    cursor.execute(
        """
        SELECT item_name
        FROM item_requests
        WHERE thread_id = ?
        ORDER BY rank_position ASC
        """,
        (thread_id,),
    )
    return [row[0] for row in cursor.fetchall()]

def delete_request(request_id: int):
    cursor.execute(
        "DELETE FROM item_requests WHERE id = ?",
        (request_id,)
    )
    conn.commit()

def reorder_item_ranks(item_name: str):
    cursor.execute(
        """
        SELECT id
        FROM item_requests
        WHERE item_name = ?
        ORDER BY rank_position ASC
        """,
        (item_name,)
    )

    rows = cursor.fetchall()

    for index, (req_id,) in enumerate(rows, start=1):
        cursor.execute(
            "UPDATE item_requests SET rank_position = ? WHERE id = ?",
            (index, req_id)
        )

    conn.commit()

def fix_last_update(request_id: int, ts: int):
    cursor.execute(
        "UPDATE item_requests SET last_update = ? WHERE id = ?",
        (ts, request_id)
    )
    conn.commit()

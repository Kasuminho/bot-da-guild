CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_id INTEGER UNIQUE,
    nickname_ingame TEXT,
    language TEXT,
    channel_id INTEGER,
    timezone TEXT
);

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
);

CREATE TABLE IF NOT EXISTS boss_rotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rotation_type TEXT NOT NULL,
    day INTEGER NOT NULL,
    created_at INTEGER NOT NULL,
    UNIQUE(rotation_type, day)
);

CREATE TABLE IF NOT EXISTS boss_participation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rotation_id INTEGER NOT NULL REFERENCES boss_rotations(id),
    discord_id INTEGER NOT NULL,
    present INTEGER NOT NULL,
    UNIQUE(rotation_id, discord_id)
);

CREATE TABLE IF NOT EXISTS forum_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id INTEGER UNIQUE,
    close_time INTEGER,
    closed INTEGER DEFAULT 0,
    delivered INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS drops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_id INTEGER,
    nickname_ingame TEXT,
    item TEXT,
    thread_id INTEGER,
    staff_id INTEGER,
    delivered_at INTEGER
);

CREATE TABLE IF NOT EXISTS daily_announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER UNIQUE,
    text_pt TEXT NOT NULL,
    text_en TEXT NOT NULL,
    image_pt_path TEXT NOT NULL,
    image_en_path TEXT NOT NULL,
    active INTEGER DEFAULT 1,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS player_levels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    player_name TEXT NOT NULL,
    level INTEGER NOT NULL,
    day INTEGER NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_player_day ON player_levels(player_id, day);

CREATE TABLE IF NOT EXISTS parties (
    message_id INTEGER PRIMARY KEY,
    channel_id INTEGER NOT NULL,
    creator_id INTEGER NOT NULL,
    reason_pt TEXT NOT NULL,
    reason_en TEXT NOT NULL,
    start_ts INTEGER NOT NULL,
    end_ts INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS forum_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    category TEXT NOT NULL,
    item_pt TEXT NOT NULL,
    item_en TEXT NOT NULL,
    type_pt TEXT NOT NULL,
    type_en TEXT NOT NULL,
    image1_path TEXT NOT NULL,
    image2_path TEXT NOT NULL,
    active INTEGER DEFAULT 1,
    created_at INTEGER NOT NULL
);

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
);

CREATE TABLE IF NOT EXISTS item_request_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    info TEXT,
    thread_id INTEGER,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_players_discord_id ON players(discord_id);
CREATE INDEX IF NOT EXISTS idx_forum_posts_thread_id ON forum_posts(thread_id);
CREATE INDEX IF NOT EXISTS idx_drops_discord_id ON drops(discord_id);
CREATE INDEX IF NOT EXISTS idx_drops_thread_id ON drops(thread_id);
CREATE INDEX IF NOT EXISTS idx_item_requests_thread_id ON item_requests(thread_id);
CREATE INDEX IF NOT EXISTS idx_item_requests_item_rank ON item_requests(item_name, rank_position);
CREATE INDEX IF NOT EXISTS idx_item_requests_discord_id ON item_requests(discord_id);
CREATE INDEX IF NOT EXISTS idx_boss_participation_rotation_discord ON boss_participation(rotation_id, discord_id);
CREATE INDEX IF NOT EXISTS idx_boss_rotations_day ON boss_rotations(day);

CREATE TABLE IF NOT EXISTS plans (
    plan_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    price_cents INTEGER NOT NULL,
    currency TEXT NOT NULL,
    features_json TEXT NOT NULL,
    is_public INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS guilds (
    guild_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    plan_id TEXT REFERENCES plans(plan_id),
    subscription_status TEXT NOT NULL DEFAULT 'free',
    subscription_expires_at INTEGER,
    is_active INTEGER NOT NULL DEFAULT 1,
    config_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    actor_user_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    details_json TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS dkp_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_by_user_id INTEGER NOT NULL,
    event_id TEXT,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS dkp_bids (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    item_name TEXT NOT NULL,
    min_bid INTEGER NOT NULL,
    ends_at INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    winner_user_id INTEGER,
    winning_bid INTEGER,
    created_by_user_id INTEGER NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS dkp_bid_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bid_id INTEGER NOT NULL REFERENCES dkp_bids(id),
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_guild_created_at ON audit_logs(guild_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_dkp_transactions_guild_user ON dkp_transactions(guild_id, user_id);
CREATE INDEX IF NOT EXISTS idx_dkp_bids_guild_channel_status ON dkp_bids(guild_id, channel_id, status);

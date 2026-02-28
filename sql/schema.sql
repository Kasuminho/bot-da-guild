CREATE TABLE IF NOT EXISTS players (
    id BIGSERIAL PRIMARY KEY,
    discord_id BIGINT UNIQUE,
    nickname_ingame TEXT,
    language TEXT,
    channel_id BIGINT,
    timezone TEXT
);

CREATE TABLE IF NOT EXISTS one_time_reminders (
    id BIGSERIAL PRIMARY KEY,
    tipo TEXT NOT NULL,
    nome TEXT NOT NULL,
    channel_id BIGINT NOT NULL,
    timestamp BIGINT NOT NULL,
    sent BOOLEAN DEFAULT FALSE,
    warned_4h BOOLEAN DEFAULT FALSE,
    warned_1h BOOLEAN DEFAULT FALSE,
    warned_30m BOOLEAN DEFAULT FALSE,
    warned_now BOOLEAN DEFAULT FALSE,
    warned_daily_day INTEGER
);

CREATE TABLE IF NOT EXISTS boss_rotations (
    id BIGSERIAL PRIMARY KEY,
    rotation_type TEXT NOT NULL,
    day INTEGER NOT NULL,
    created_at BIGINT NOT NULL,
    UNIQUE(rotation_type, day)
);

CREATE TABLE IF NOT EXISTS boss_participation (
    id BIGSERIAL PRIMARY KEY,
    rotation_id BIGINT NOT NULL REFERENCES boss_rotations(id),
    discord_id BIGINT NOT NULL,
    present BOOLEAN NOT NULL,
    UNIQUE(rotation_id, discord_id)
);

CREATE TABLE IF NOT EXISTS forum_posts (
    id BIGSERIAL PRIMARY KEY,
    thread_id BIGINT UNIQUE,
    close_time BIGINT,
    closed BOOLEAN DEFAULT FALSE,
    delivered BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS drops (
    id BIGSERIAL PRIMARY KEY,
    discord_id BIGINT,
    nickname_ingame TEXT,
    item TEXT,
    thread_id BIGINT,
    staff_id BIGINT,
    delivered_at BIGINT
);

CREATE TABLE IF NOT EXISTS daily_announcements (
    id BIGSERIAL PRIMARY KEY,
    channel_id BIGINT UNIQUE,
    text_pt TEXT NOT NULL,
    text_en TEXT NOT NULL,
    image_pt_path TEXT NOT NULL,
    image_en_path TEXT NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS player_levels (
    id BIGSERIAL PRIMARY KEY,
    player_id BIGINT NOT NULL,
    player_name TEXT NOT NULL,
    level INTEGER NOT NULL,
    day INTEGER NOT NULL,
    created_at BIGINT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_player_day ON player_levels(player_id, day);

CREATE TABLE IF NOT EXISTS parties (
    message_id BIGINT PRIMARY KEY,
    channel_id BIGINT NOT NULL,
    creator_id BIGINT NOT NULL,
    reason_pt TEXT NOT NULL,
    reason_en TEXT NOT NULL,
    start_ts BIGINT NOT NULL,
    end_ts BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS forum_items (
    id BIGSERIAL PRIMARY KEY,
    kind TEXT NOT NULL,
    category TEXT NOT NULL,
    item_pt TEXT NOT NULL,
    item_en TEXT NOT NULL,
    type_pt TEXT NOT NULL,
    type_en TEXT NOT NULL,
    image1_path TEXT NOT NULL,
    image2_path TEXT NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS item_requests (
    id BIGSERIAL PRIMARY KEY,
    discord_id BIGINT NOT NULL,
    player_name TEXT NOT NULL,
    item_name TEXT NOT NULL,
    total_quantity INTEGER NOT NULL,
    remaining_quantity INTEGER NOT NULL,
    rank_position INTEGER NOT NULL,
    thread_id BIGINT NOT NULL,
    thread_channel_id BIGINT NOT NULL,
    created_at BIGINT NOT NULL,
    last_update BIGINT NOT NULL,
    warned_3d BOOLEAN DEFAULT FALSE,
    warned_4d BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS item_request_logs (
    id BIGSERIAL PRIMARY KEY,
    request_id BIGINT NOT NULL,
    action TEXT NOT NULL,
    info TEXT,
    thread_id BIGINT,
    created_at BIGINT NOT NULL
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
    features_json JSONB NOT NULL,
    is_public BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS guilds (
    guild_id BIGINT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    plan_id TEXT REFERENCES plans(plan_id),
    subscription_status TEXT NOT NULL DEFAULT 'free',
    subscription_expires_at BIGINT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    config_json JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    actor_user_id BIGINT NOT NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    details_json JSONB NOT NULL,
    created_at BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS dkp_transactions (
    id BIGSERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    amount INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_by_user_id BIGINT NOT NULL,
    event_id TEXT,
    created_at BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS dkp_bids (
    id BIGSERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    item_name TEXT NOT NULL,
    min_bid INTEGER NOT NULL,
    ends_at BIGINT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    winner_user_id BIGINT,
    winning_bid INTEGER,
    created_by_user_id BIGINT NOT NULL,
    created_at BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS dkp_bid_entries (
    id BIGSERIAL PRIMARY KEY,
    bid_id BIGINT NOT NULL REFERENCES dkp_bids(id),
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    amount INTEGER NOT NULL,
    created_at BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_guild_created_at ON audit_logs(guild_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_dkp_transactions_guild_user ON dkp_transactions(guild_id, user_id);
CREATE INDEX IF NOT EXISTS idx_dkp_bids_guild_channel_status ON dkp_bids(guild_id, channel_id, status);

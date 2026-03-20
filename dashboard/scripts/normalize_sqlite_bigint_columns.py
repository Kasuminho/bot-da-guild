from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "sql" / "schema_sqlite.sql"

BIGINT_COLUMNS = {
    "players": {"discord_id", "channel_id"},
    "one_time_reminders": {"channel_id"},
    "boss_participation": {"discord_id"},
    "forum_posts": {"thread_id"},
    "drops": {"discord_id", "thread_id", "staff_id"},
    "daily_announcements": {"channel_id"},
    "parties": {"message_id", "channel_id", "creator_id"},
    "item_requests": {"discord_id", "thread_id", "thread_channel_id"},
    "item_request_logs": {"thread_id"},
    "guilds": {"guild_id"},
    "audit_logs": {"guild_id", "actor_user_id"},
    "dkp_transactions": {"guild_id", "user_id", "created_by_user_id"},
    "dkp_bids": {"guild_id", "channel_id", "winner_user_id", "created_by_user_id"},
    "dkp_bid_entries": {"guild_id", "user_id"},
}


def parse_table_statements() -> dict[str, str]:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    statements: dict[str, str] = {}

    for chunk in schema_sql.split(";"):
        statement = chunk.strip()
        if not statement.startswith("CREATE TABLE IF NOT EXISTS "):
            continue
        prefix = "CREATE TABLE IF NOT EXISTS "
        table_name = statement[len(prefix):].split("(", 1)[0].strip()
        statements[table_name] = f"{statement};"

    return statements


def get_column_types(connection: sqlite3.Connection, table: str) -> dict[str, str]:
    rows = connection.execute(f'PRAGMA table_info("{table}")').fetchall()
    return {row[1]: (row[2] or "").upper() for row in rows}


def rebuild_table(
    connection: sqlite3.Connection,
    table: str,
    create_statement: str,
) -> None:
    legacy_table = f"{table}__legacy_bigint"
    connection.execute(f'ALTER TABLE "{table}" RENAME TO "{legacy_table}"')
    connection.execute(create_statement)

    legacy_columns = [row[1] for row in connection.execute(f'PRAGMA table_info("{legacy_table}")').fetchall()]
    current_columns = [row[1] for row in connection.execute(f'PRAGMA table_info("{table}")').fetchall()]
    shared_columns = [column for column in current_columns if column in legacy_columns]

    quoted_columns = ", ".join(f'"{column}"' for column in shared_columns)
    connection.execute(
        f'INSERT INTO "{table}" ({quoted_columns}) SELECT {quoted_columns} FROM "{legacy_table}"'
    )
    connection.execute(f'DROP TABLE "{legacy_table}"')


def normalize_database(database_path: Path) -> list[str]:
    create_statements = parse_table_statements()
    migrated_tables: list[str] = []

    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = OFF")

        for table, bigint_columns in BIGINT_COLUMNS.items():
            table_exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
                (table,),
            ).fetchone()
            if not table_exists:
                continue

            column_types = get_column_types(connection, table)
            if not column_types:
                continue

            needs_rebuild = any(
                column in column_types and column_types[column] != "BIGINT"
                for column in bigint_columns
            )
            if not needs_rebuild:
                continue

            rebuild_table(connection, table, create_statements[table])
            migrated_tables.append(table)

        if migrated_tables:
            connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        connection.execute("PRAGMA foreign_keys = ON")

    return migrated_tables


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normaliza colunas SQLite que armazenam IDs do Discord para BIGINT.",
    )
    parser.add_argument("database_path", help="Caminho para o arquivo SQLite a ser ajustado.")
    args = parser.parse_args()

    migrated_tables = normalize_database(Path(args.database_path).resolve())
    if migrated_tables:
        print(
            "Normalized SQLite BIGINT columns in: "
            + ", ".join(migrated_tables)
        )
    else:
        print("SQLite BIGINT columns already normalized.")


if __name__ == "__main__":
    main()

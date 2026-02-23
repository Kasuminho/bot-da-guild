import argparse
import os
import sqlite3
import sys
import time
import traceback
from pathlib import Path

import psycopg2
from psycopg2 import sql

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "sql" / "schema.sql"

BOOLEAN_COLUMNS = {
    "one_time_reminders": {"sent", "warned_4h", "warned_1h", "warned_30m", "warned_now"},
    "boss_participation": {"present"},
    "forum_posts": {"closed", "delivered"},
    "daily_announcements": {"active"},
    "forum_items": {"active"},
    "item_requests": {"warned_3d", "warned_4d"},
}


def table_names(sqlite_conn):
    cur = sqlite_conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    return [r[0] for r in cur.fetchall()]


def table_columns(sqlite_conn, table):
    cur = sqlite_conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]


def normalize_value(table, column, value):
    if value == "":
        return None
    if column in BOOLEAN_COLUMNS.get(table, set()):
        return bool(value) if value is not None else None
    return value


def execute_schema(pg_conn):
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with pg_conn.cursor() as cur:
        cur.execute(schema_sql)
    pg_conn.commit()


def truncate_table(pg_conn, table):
    with pg_conn.cursor() as cur:
        cur.execute(sql.SQL("TRUNCATE TABLE {} RESTART IDENTITY CASCADE").format(sql.Identifier(table)))
    pg_conn.commit()


def build_upsert(table, columns):
    col_identifiers = [sql.Identifier(c) for c in columns]
    placeholders = sql.SQL(", ").join(sql.Placeholder() * len(columns))

    conflict_map = {
        "players": ["discord_id"],
        "boss_rotations": ["rotation_type", "day"],
        "boss_participation": ["rotation_id", "discord_id"],
        "forum_posts": ["thread_id"],
        "player_levels": ["player_id", "day"],
    }

    conflict_cols = [c for c in conflict_map.get(table, []) if c in columns]
    if not conflict_cols:
        return sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
            sql.Identifier(table), sql.SQL(", ").join(col_identifiers), placeholders
        )

    update_cols = [c for c in columns if c not in conflict_cols and c != "id"]
    if not update_cols:
        return sql.SQL(
            "INSERT INTO {} ({}) VALUES ({}) ON CONFLICT ({}) DO NOTHING"
        ).format(
            sql.Identifier(table),
            sql.SQL(", ").join(col_identifiers),
            placeholders,
            sql.SQL(", ").join(sql.Identifier(c) for c in conflict_cols),
        )

    set_clause = sql.SQL(", ").join(
        sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(c), sql.Identifier(c)) for c in update_cols
    )

    return sql.SQL(
        "INSERT INTO {} ({}) VALUES ({}) ON CONFLICT ({}) DO UPDATE SET {}"
    ).format(
        sql.Identifier(table),
        sql.SQL(", ").join(col_identifiers),
        placeholders,
        sql.SQL(", ").join(sql.Identifier(c) for c in conflict_cols),
        set_clause,
    )


def migrate_table(sqlite_conn, pg_conn, table, mode):
    cols = table_columns(sqlite_conn, table)
    select_cols = ", ".join(cols)

    sqlite_cur = sqlite_conn.cursor()
    sqlite_cur.execute(f"SELECT {select_cols} FROM {table}")
    rows = sqlite_cur.fetchall()

    if mode == "truncate-first":
        truncate_table(pg_conn, table)

    start = time.time()
    inserted = 0

    try:
        with pg_conn.cursor() as pg_cur:
            stmt = build_upsert(table, cols) if mode == "upsert" else sql.SQL(
                "INSERT INTO {} ({}) VALUES ({})"
            ).format(
                sql.Identifier(table),
                sql.SQL(", ").join(sql.Identifier(c) for c in cols),
                sql.SQL(", ").join(sql.Placeholder() * len(cols)),
            )

            for row in rows:
                normalized = [normalize_value(table, c, v) for c, v in zip(cols, row)]
                pg_cur.execute(stmt, normalized)
                inserted += 1
        pg_conn.commit()
    except Exception:
        pg_conn.rollback()
        print(f"[ERRO] tabela={table}")
        traceback.print_exc()
        return len(rows), inserted, time.time() - start, False

    return len(rows), inserted, time.time() - start, True


def count_pg_table(pg_conn, table):
    with pg_conn.cursor() as cur:
        cur.execute(sql.SQL("SELECT COUNT(*) FROM {}" ).format(sql.Identifier(table)))
        return cur.fetchone()[0]


def adjust_sequence(pg_conn, table):
    with pg_conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = %s AND column_name = 'id'",
            (table,),
        )
        if not cur.fetchone():
            return
        cur.execute(
            sql.SQL(
                "SELECT setval(pg_get_serial_sequence(%s, 'id'), COALESCE((SELECT MAX(id) FROM {}), 1), true)"
            ).format(sql.Identifier(table)),
            (table,),
        )


def main():
    parser = argparse.ArgumentParser(description="Migra dados de SQLite para PostgreSQL")
    parser.add_argument("--truncate-first", action="store_true", help="Limpa tabelas de destino antes da carga")
    parser.add_argument("--upsert", action="store_true", help="Faz UPSERT nas tabelas com chave conhecida")
    args = parser.parse_args()

    if args.truncate_first and args.upsert:
        print("Escolha apenas um modo: --truncate-first OU --upsert")
        sys.exit(1)

    mode = "upsert" if args.upsert else "truncate-first"

    sqlite_path = os.getenv("SQLITE_PATH", str(ROOT / "database.db"))
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("DATABASE_URL não definido.")
        sys.exit(1)

    sqlite_conn = sqlite3.connect(sqlite_path)
    pg_conn = psycopg2.connect(database_url)
    pg_conn.autocommit = False

    try:
        execute_schema(pg_conn)
        tables = table_names(sqlite_conn)
        print(f"Modo de migração: {mode}")

        summary = []
        for table in tables:
            print(f"\n[TABELA] {table}")
            sqlite_count, inserted, elapsed, ok = migrate_table(sqlite_conn, pg_conn, table, mode)
            print(f"SQLite: {sqlite_count} | Inseridos: {inserted} | Tempo: {elapsed:.2f}s")
            summary.append((table, sqlite_count, ok))

        for table in tables:
            adjust_sequence(pg_conn, table)
        pg_conn.commit()

        print("\n[VALIDAÇÃO] Contagem SQLite vs PostgreSQL")
        for table, sqlite_count, ok in summary:
            pg_count = count_pg_table(pg_conn, table)
            status = "OK" if sqlite_count == pg_count else "DIVERGENTE"
            if not ok:
                status = "FALHOU"
            print(f"- {table}: sqlite={sqlite_count} postgres={pg_count} [{status}]")

    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    main()

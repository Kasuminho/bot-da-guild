import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path

import psycopg2
import sqlite3
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
SQLITE_SCHEMA_PATH = ROOT / "sql" / "schema_sqlite.sql"


def table_names(sqlite_conn):
    cur = sqlite_conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    return [row[0] for row in cur.fetchall()]


def table_columns(sqlite_conn, table):
    cur = sqlite_conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]


def execute_schema(sqlite_conn):
    sqlite_conn.executescript(SQLITE_SCHEMA_PATH.read_text(encoding="utf-8"))
    sqlite_conn.commit()


def truncate_table(sqlite_conn, table):
    sqlite_conn.execute(f'DELETE FROM "{table}"')
    sqlite_conn.commit()


def normalize_value(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return value


def migrate_table(pg_conn, sqlite_conn, table, mode):
    columns = table_columns(sqlite_conn, table)
    if mode == "truncate-first":
        truncate_table(sqlite_conn, table)

    with pg_conn.cursor() as pg_cur:
        pg_cur.execute(f'SELECT {", ".join(columns)} FROM {table}')
        rows = pg_cur.fetchall()

    placeholders = ", ".join("?" for _ in columns)
    insert_sql = f'INSERT INTO {table} ({", ".join(columns)}) VALUES ({placeholders})'

    start = time.time()
    inserted = 0
    try:
        with sqlite_conn:
            cur = sqlite_conn.cursor()
            for row in rows:
                cur.execute(insert_sql, [normalize_value(value) for value in row])
                inserted += 1
    except Exception:
        print(f"[ERRO] tabela={table}")
        traceback.print_exc()
        return len(rows), inserted, time.time() - start, False

    return len(rows), inserted, time.time() - start, True


def count_table(conn, table, sqlite_mode):
    cur = conn.cursor()
    cur.execute(f'SELECT COUNT(*) FROM {table}')
    return cur.fetchone()[0]


def main():
    load_dotenv(ROOT / ".env")

    parser = argparse.ArgumentParser(description="Migra dados de PostgreSQL para SQLite")
    parser.add_argument("--truncate-first", action="store_true", help="Limpa tabelas de destino antes da carga")
    args = parser.parse_args()

    mode = "truncate-first" if args.truncate_first else "append"

    database_url = os.getenv("DATABASE_URL", "").strip()
    sqlite_path = os.getenv("SQLITE_PATH", str(ROOT / "database.db"))

    if not database_url.startswith(("postgres://", "postgresql://")):
        print("DATABASE_URL deve apontar para PostgreSQL para exportar os dados.")
        sys.exit(1)

    pg_conn = psycopg2.connect(database_url)
    sqlite_conn = sqlite3.connect(sqlite_path)

    try:
        execute_schema(sqlite_conn)
        tables = table_names(sqlite_conn)
        print(f"Modo de migração: {mode}")
        print(f"SQLite destino: {sqlite_path}")

        summary = []
        for table in tables:
            print(f"\n[TABELA] {table}")
            pg_count, inserted, elapsed, ok = migrate_table(pg_conn, sqlite_conn, table, mode)
            print(f"Postgres: {pg_count} | Inseridos: {inserted} | Tempo: {elapsed:.2f}s")
            summary.append((table, pg_count, ok))

        print("\n[VALIDAÇÃO] Contagem PostgreSQL vs SQLite")
        for table, pg_count, ok in summary:
            sqlite_count = count_table(sqlite_conn, table, sqlite_mode=True)
            status = "OK" if pg_count == sqlite_count else "DIVERGENTE"
            if not ok:
                status = "FALHOU"
            print(f"- {table}: postgres={pg_count} sqlite={sqlite_count} [{status}]")
    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    main()

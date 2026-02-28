"""One-shot migration for multi-tenant + SaaS foundations.

Usage:
    DEFAULT_GUILD_ID=123 DATABASE_URL=... python scripts/migrate_to_multi_tenant.py
"""

import os

import db


def main():
    if int(os.getenv("DEFAULT_GUILD_ID", "0") or "0") <= 0:
        raise RuntimeError("DEFAULT_GUILD_ID must be set for safe backfill.")

    db.run_bootstrap_migrations()
    print("Migration completed.")


if __name__ == "__main__":
    main()

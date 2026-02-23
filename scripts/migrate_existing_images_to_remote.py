"""Migra caminhos locais de imagens para storage remoto (ex.: Google Drive).

Uso:
  python scripts/migrate_existing_images_to_remote.py --dry-run
  python scripts/migrate_existing_images_to_remote.py
"""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import db
from utils.image_storage import get_image_storage_provider, is_remote_url, upload_image


ROOT_DIR = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Só mostra o que faria")
    return parser.parse_args()


def normalize_local_path(raw_path: str) -> Path:
    p = Path(raw_path)
    if p.is_absolute():
        return p
    return ROOT_DIR / p


def migrate_forum_items(dry_run: bool) -> tuple[int, int, int]:
    rows = db.execute(
        """
        SELECT id, image1_path, image2_path
        FROM forum_items
        WHERE active = TRUE
        ORDER BY id ASC
        """,
        fetchall=True,
    ) or []

    migrated = 0
    skipped = 0
    failed = 0

    for item_id, image1_path, image2_path in rows:
        if is_remote_url(image1_path) and is_remote_url(image2_path):
            skipped += 1
            continue

        local1 = normalize_local_path(image1_path)
        local2 = normalize_local_path(image2_path)
        if not local1.exists() or not local2.exists():
            print(f"[forum_items:{item_id}] SKIP (arquivo não encontrado): {local1} | {local2}")
            failed += 1
            continue

        if dry_run:
            print(f"[forum_items:{item_id}] DRY-RUN upload -> {local1.name}, {local2.name}")
            migrated += 1
            continue

        try:
            ts = int(time.time())
            remote1 = upload_image(str(local1), f"forum_items_{item_id}_{ts}_1.png")
            remote2 = upload_image(str(local2), f"forum_items_{item_id}_{ts}_2.png")
            db.execute(
                "UPDATE forum_items SET image1_path = %s, image2_path = %s WHERE id = %s",
                (remote1, remote2, item_id),
            )
            migrated += 1
            print(f"[forum_items:{item_id}] OK")
        except Exception as exc:
            failed += 1
            print(f"[forum_items:{item_id}] FAIL: {exc}")

    return migrated, skipped, failed


def main() -> None:
    args = parse_args()
    provider = get_image_storage_provider()
    if provider == "local":
        raise RuntimeError(
            "IMAGE_STORAGE_PROVIDER=local. Configure provider remoto (ex.: google_drive) antes de migrar."
        )

    print(f"Provider atual: {provider}")
    migrated, skipped, failed = migrate_forum_items(dry_run=args.dry_run)
    print("\nResumo:")
    print(f"- Migrados: {migrated}")
    print(f"- Ignorados (já remotos): {skipped}")
    print(f"- Falhas: {failed}")


if __name__ == "__main__":
    main()

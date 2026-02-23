"""Migra caminhos locais de imagens para storage remoto (ex.: Google Drive).

Cobertura atual:
- forum_items.image1_path / image2_path
- daily_announcements.image_pt_path / image_en_path

Uso:
  python scripts/migrate_existing_images_to_remote.py --dry-run
  python scripts/migrate_existing_images_to_remote.py
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import db
from utils.image_storage import get_image_storage_provider, is_remote_url, upload_image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Só mostra o que faria")
    return parser.parse_args()


def normalize_local_path(raw_path: str) -> Path:
    p = Path(raw_path)
    if p.is_absolute():
        return p
    return ROOT_DIR / p


def _migrate_pair(
    *,
    dry_run: bool,
    label: str,
    row_id: int,
    path_a: str,
    path_b: str,
    upload_name_a: str,
    upload_name_b: str,
    update_sql: str,
) -> tuple[bool, bool]:
    """Retorna (processed, failed). processed=True inclui migrado/skip dry-run."""

    if is_remote_url(path_a) and is_remote_url(path_b):
        print(f"[{label}:{row_id}] SKIP (já remoto)")
        return True, False

    local_a = normalize_local_path(path_a)
    local_b = normalize_local_path(path_b)
    if not local_a.exists() or not local_b.exists():
        print(f"[{label}:{row_id}] FAIL (arquivo não encontrado): {local_a} | {local_b}")
        return False, True

    if dry_run:
        print(f"[{label}:{row_id}] DRY-RUN upload -> {local_a.name}, {local_b.name}")
        return True, False

    remote_a = upload_image(str(local_a), upload_name_a)
    remote_b = upload_image(str(local_b), upload_name_b)
    db.execute(update_sql, (remote_a, remote_b, row_id))
    print(f"[{label}:{row_id}] OK")
    return True, False


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

    migrated_or_skipped = 0
    failed = 0
    skipped_already_remote = 0

    for item_id, image1_path, image2_path in rows:
        if is_remote_url(image1_path) and is_remote_url(image2_path):
            skipped_already_remote += 1

        ts = int(time.time())
        processed, is_failed = _migrate_pair(
            dry_run=dry_run,
            label="forum_items",
            row_id=item_id,
            path_a=image1_path,
            path_b=image2_path,
            upload_name_a=f"forum_items_{item_id}_{ts}_1.png",
            upload_name_b=f"forum_items_{item_id}_{ts}_2.png",
            update_sql="UPDATE forum_items SET image1_path = %s, image2_path = %s WHERE id = %s",
        )
        migrated_or_skipped += int(processed)
        failed += int(is_failed)

    return migrated_or_skipped, skipped_already_remote, failed


def migrate_daily_announcements(dry_run: bool) -> tuple[int, int, int]:
    rows = db.execute(
        """
        SELECT id, image_pt_path, image_en_path
        FROM daily_announcements
        WHERE active = TRUE
        ORDER BY id ASC
        """,
        fetchall=True,
    ) or []

    migrated_or_skipped = 0
    failed = 0
    skipped_already_remote = 0

    for ann_id, image_pt_path, image_en_path in rows:
        if is_remote_url(image_pt_path) and is_remote_url(image_en_path):
            skipped_already_remote += 1

        ts = int(time.time())
        processed, is_failed = _migrate_pair(
            dry_run=dry_run,
            label="daily_announcements",
            row_id=ann_id,
            path_a=image_pt_path,
            path_b=image_en_path,
            upload_name_a=f"daily_announcements_{ann_id}_{ts}_pt.png",
            upload_name_b=f"daily_announcements_{ann_id}_{ts}_en.png",
            update_sql="UPDATE daily_announcements SET image_pt_path = %s, image_en_path = %s WHERE id = %s",
        )
        migrated_or_skipped += int(processed)
        failed += int(is_failed)

    return migrated_or_skipped, skipped_already_remote, failed


def main() -> None:
    args = parse_args()
    provider = get_image_storage_provider()
    if provider == "local":
        raise RuntimeError(
            "IMAGE_STORAGE_PROVIDER=local. Configure provider remoto (ex.: google_drive) antes de migrar."
        )

    print(f"Provider atual: {provider}")

    fi_total, fi_skipped, fi_failed = migrate_forum_items(dry_run=args.dry_run)
    da_total, da_skipped, da_failed = migrate_daily_announcements(dry_run=args.dry_run)

    print("\nResumo:")
    print(f"- forum_items processados: {fi_total} | já remotos: {fi_skipped} | falhas: {fi_failed}")
    print(f"- daily_announcements processados: {da_total} | já remotos: {da_skipped} | falhas: {da_failed}")


if __name__ == "__main__":
    main()

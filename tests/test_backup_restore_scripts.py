import json
import sqlite3
from pathlib import Path

from scripts.backup import run_backup
from scripts.restore import run_restore


def test_backup_creates_verified_sqlite_copy_and_manifest(tmp_path: Path) -> None:
    db_path = tmp_path / "affiliate.db"
    images_dir = tmp_path / "generated_images"
    backup_root = tmp_path / "backups"

    _create_database(db_path, "before-backup")
    images_dir.mkdir()
    (images_dir / "banner.txt").write_text("image-asset", encoding="utf-8")

    backup_dir = run_backup(db_path, images_dir, backup_root)

    manifest = json.loads((backup_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["database"]["integrity_check"] == "ok"
    assert (backup_dir / "affiliate.db").exists()
    assert (backup_dir / "generated_images.zip").exists()
    assert _read_messages(backup_dir / "affiliate.db") == ["before-backup"]


def test_restore_recovers_database_and_images_from_verified_backup(
    tmp_path: Path,
) -> None:
    source_db = tmp_path / "affiliate.db"
    source_images = tmp_path / "generated_images"
    backup_root = tmp_path / "backups"
    restore_root = tmp_path / "restore-target"
    restore_db = restore_root / "affiliate.db"
    restore_images = restore_root / "generated_images"

    _create_database(source_db, "golden")
    source_images.mkdir()
    (source_images / "banner.txt").write_text("golden-image", encoding="utf-8")
    backup_dir = run_backup(source_db, source_images, backup_root)

    restore_root.mkdir()
    _create_database(restore_db, "stale")
    restore_images.mkdir()
    (restore_images / "banner.txt").write_text("stale-image", encoding="utf-8")

    run_restore(backup_dir, restore_db, restore_images)

    assert _read_messages(restore_db) == ["golden"]
    assert (restore_images / "banner.txt").read_text(encoding="utf-8") == "golden-image"


def _create_database(db_path: Path, message: str) -> None:
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS messages (value TEXT NOT NULL)")
        connection.execute("DELETE FROM messages")
        connection.execute("INSERT INTO messages (value) VALUES (?)", (message,))
        connection.commit()


def _read_messages(db_path: Path) -> list[str]:
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            "SELECT value FROM messages ORDER BY rowid ASC"
        ).fetchall()
    return [str(row[0]) for row in rows]

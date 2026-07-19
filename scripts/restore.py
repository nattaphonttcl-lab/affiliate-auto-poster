from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import shutil
from pathlib import Path


def run_restore(backup_dir: Path, db_path: Path, images_dir: Path) -> None:
    manifest = _load_manifest(backup_dir)
    backup_db = backup_dir / db_path.name
    backup_images_zip = backup_dir / "generated_images.zip"

    if backup_db.exists():
        database_manifest = manifest.get("database")
        _verify_backup_file(backup_db, database_manifest, checksum_key="sha256")
        if _database_backup_mode(database_manifest) == "file_copy":
            _restore_plain_file(backup_db=backup_db, db_path=db_path)
        else:
            _restore_sqlite_database(backup_db=backup_db, db_path=db_path)

    if backup_images_zip.exists():
        _verify_backup_file(
            backup_images_zip, manifest.get("images"), checksum_key="sha256"
        )
        _restore_images_archive(
            backup_images_zip=backup_images_zip, images_dir=images_dir
        )


def _load_manifest(backup_dir: Path) -> dict[str, object]:
    manifest_path = backup_dir / "manifest.json"
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _verify_backup_file(
    backup_path: Path,
    manifest_entry: object,
    *,
    checksum_key: str,
) -> None:
    if not isinstance(manifest_entry, dict):
        return
    expected = manifest_entry.get(checksum_key)
    if not isinstance(expected, str) or not expected:
        return
    actual = _sha256(backup_path)
    if actual != expected:
        raise RuntimeError(f"Checksum verification failed for {backup_path.name}")


def _database_backup_mode(manifest_entry: object) -> str:
    if not isinstance(manifest_entry, dict):
        return "sqlite_backup"
    mode = manifest_entry.get("mode")
    return mode if isinstance(mode, str) else "sqlite_backup"


def _restore_plain_file(*, backup_db: Path, db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup_db, db_path)


def _restore_sqlite_database(*, backup_db: Path, db_path: Path) -> None:
    _validate_sqlite_database(backup_db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = db_path.with_suffix(f"{db_path.suffix}.restore.tmp")
    if temp_path.exists():
        temp_path.unlink()
    shutil.copy2(backup_db, temp_path)
    _validate_sqlite_database(temp_path)

    source = sqlite3.connect(temp_path)
    destination = sqlite3.connect(db_path)
    try:
        source.backup(destination)
        destination.commit()
    finally:
        destination.close()
        source.close()

    _validate_sqlite_database(db_path)
    try:
        temp_path.unlink(missing_ok=True)
    except PermissionError:
        pass


def _restore_images_archive(*, backup_images_zip: Path, images_dir: Path) -> None:
    staging_dir = images_dir.parent / f"{images_dir.name}.restore.tmp"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)
    shutil.unpack_archive(str(backup_images_zip), str(staging_dir), "zip")
    if images_dir.exists():
        shutil.rmtree(images_dir)
    shutil.move(str(staging_dir), str(images_dir))


def _validate_sqlite_database(db_path: Path) -> None:
    with sqlite3.connect(db_path) as connection:
        row = connection.execute("PRAGMA integrity_check").fetchone()
    result = str(row[0]) if row else "unknown"
    if result != "ok":
        raise RuntimeError(
            f"SQLite integrity check failed for {db_path.name}: {result}"
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore platform backup")
    parser.add_argument("backup_path")
    parser.add_argument("--db", default="affiliate.db")
    parser.add_argument("--images", default="generated_images")
    args = parser.parse_args()

    run_restore(Path(args.backup_path), Path(args.db), Path(args.images))
    print("Restore completed")


if __name__ == "__main__":
    main()

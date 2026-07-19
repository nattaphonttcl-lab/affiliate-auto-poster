from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


def run_backup(db_path: Path, images_dir: Path, backup_dir: Path) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    target = backup_dir / f"backup-{timestamp}"
    target.mkdir(parents=True, exist_ok=False)

    manifest: dict[str, object] = {
        "created_at": datetime.now(UTC).isoformat(),
        "database": None,
        "images": None,
    }

    if db_path.exists():
        backup_db_path = target / db_path.name
        metadata = _backup_database_file(db_path=db_path, backup_path=backup_db_path)
        manifest["database"] = metadata

    if images_dir.exists():
        archive_path = Path(
            shutil.make_archive(str(target / "generated_images"), "zip", images_dir)
        )
        manifest["images"] = {
            "filename": archive_path.name,
            "sha256": _sha256(archive_path),
        }

    (target / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    return target


def _backup_database_file(*, db_path: Path, backup_path: Path) -> dict[str, str]:
    if _is_sqlite_database(db_path):
        _backup_sqlite_database(db_path=db_path, backup_path=backup_path)
        return {
            "filename": backup_path.name,
            "mode": "sqlite_backup",
            "sha256": _sha256(backup_path),
            "integrity_check": _sqlite_integrity_check(backup_path),
        }

    shutil.copy2(db_path, backup_path)
    return {
        "filename": backup_path.name,
        "mode": "file_copy",
        "sha256": _sha256(backup_path),
        "integrity_check": "not_sqlite",
    }


def _backup_sqlite_database(*, db_path: Path, backup_path: Path) -> None:
    source = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    destination = sqlite3.connect(backup_path)
    try:
        source.backup(destination)
        destination.commit()
    finally:
        destination.close()
        source.close()

    integrity = _sqlite_integrity_check(backup_path)
    if integrity != "ok":
        raise RuntimeError(f"SQLite backup integrity check failed: {integrity}")


def _sqlite_integrity_check(db_path: Path) -> str:
    with sqlite3.connect(db_path) as connection:
        row = connection.execute("PRAGMA integrity_check").fetchone()
    return str(row[0]) if row else "unknown"


def _is_sqlite_database(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 16:
        return False
    with path.open("rb") as handle:
        header = handle.read(16)
    return header == b"SQLite format 3\x00"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create automatic platform backup")
    parser.add_argument("--db", default="affiliate.db")
    parser.add_argument("--images", default="generated_images")
    parser.add_argument("--out", default="backups")
    args = parser.parse_args()

    backup_path = run_backup(Path(args.db), Path(args.images), Path(args.out))
    print(f"Backup created at {backup_path}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import shutil
from datetime import UTC, datetime
from pathlib import Path


def run_backup(db_path: Path, images_dir: Path, backup_dir: Path) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    target = backup_dir / f"backup-{timestamp}"
    target.mkdir(parents=True, exist_ok=False)

    if db_path.exists():
        shutil.copy2(db_path, target / db_path.name)

    if images_dir.exists():
        shutil.make_archive(str(target / "generated_images"), "zip", images_dir)

    return target


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

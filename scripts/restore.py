from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def run_restore(backup_dir: Path, db_path: Path, images_dir: Path) -> None:
    backup_db = backup_dir / db_path.name
    backup_images_zip = backup_dir / "generated_images.zip"

    if backup_db.exists():
        shutil.copy2(backup_db, db_path)

    if backup_images_zip.exists():
        if images_dir.exists():
            shutil.rmtree(images_dir)
        images_dir.mkdir(parents=True, exist_ok=True)
        shutil.unpack_archive(str(backup_images_zip), str(images_dir), "zip")


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

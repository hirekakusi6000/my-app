"""DB とプロフィール画像のバックアップ。

使い方: python -m app.db.backup
  data/backups/20261107-031500/ に app.db と uploads/ を保存する。
  古いバックアップは、新しいものから APP_BACKUP_KEEP 個（既定 14）を残して削除する。

アプリを動かしたままでも安全に実行できる（SQLite のバックアップ機能を使うため、
書き込み中でも整合性の取れた写しになる）。毎日1回、cron やタスクスケジューラで実行する想定。
"""

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from app.core.config import get_settings
from app.core.time import JST

_NAME_FORMAT = "%Y%m%d-%H%M%S"


def create_backup(
    database_path: Path, upload_dir: Path, backup_dir: Path, *, now: datetime | None = None
) -> Path:
    """バックアップを1つ作り、その場所を返す。"""
    name = (now or datetime.now(JST)).strftime(_NAME_FORMAT)
    target = backup_dir / name
    target.mkdir(parents=True, exist_ok=False)

    source = sqlite3.connect(database_path)
    destination = sqlite3.connect(target / database_path.name)
    try:
        with destination:
            source.backup(destination)
    finally:
        destination.close()
        source.close()

    if upload_dir.exists():
        shutil.copytree(upload_dir, target / "uploads")
    return target


def prune_backups(backup_dir: Path, keep: int) -> list[Path]:
    """新しいものから keep 個を残し、古いバックアップを削除する。削除したものを返す。"""
    backups = sorted(
        (p for p in backup_dir.iterdir() if p.is_dir() and _is_backup_name(p.name)),
        key=lambda p: p.name,
        reverse=True,
    )
    removed = backups[keep:]
    for path in removed:
        shutil.rmtree(path)
    return removed


def _is_backup_name(name: str) -> bool:
    try:
        datetime.strptime(name, _NAME_FORMAT)
    except ValueError:
        return False
    return True


def main() -> None:
    settings = get_settings()
    target = create_backup(settings.database_path, settings.upload_dir, settings.backup_dir)
    removed = prune_backups(settings.backup_dir, settings.backup_keep)
    print(f"バックアップを作成しました: {target}")
    if removed:
        print(f"古いバックアップを削除しました: {len(removed)}個")


if __name__ == "__main__":
    main()

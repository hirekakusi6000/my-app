"""migrations/NNNN_*.sql を番号順に適用する。

適用済みのバージョンは PRAGMA user_version に記録する。
手動実行: python -m app.db.migrate
"""

import re
import sqlite3
from pathlib import Path

from app.core.config import get_settings
from app.db.connection import connect

_FILE_PATTERN = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")


def _discover(migrations_dir: Path) -> list[tuple[int, Path]]:
    found: list[tuple[int, Path]] = []
    for path in migrations_dir.glob("*.sql"):
        match = _FILE_PATTERN.match(path.name)
        if not match:
            raise ValueError(f"マイグレーションのファイル名が不正です: {path.name}")
        found.append((int(match.group(1)), path))
    found.sort()
    versions = [v for v, _ in found]
    if len(versions) != len(set(versions)):
        raise ValueError("マイグレーションの番号が重複しています")
    return found


def current_version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def migrate(conn: sqlite3.Connection, migrations_dir: Path) -> list[int]:
    """未適用のマイグレーションを適用し、適用したバージョンの一覧を返す。"""
    applied: list[int] = []
    version = current_version(conn)
    for number, path in _discover(migrations_dir):
        if number <= version:
            continue
        sql = path.read_text(encoding="utf-8")
        try:
            # 1ファイル＝1トランザクション。途中で失敗したらそのファイル全体を取り消す
            conn.executescript(f"BEGIN;\n{sql}\nPRAGMA user_version = {number};\nCOMMIT;")
        except sqlite3.Error:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        applied.append(number)
    return applied


def run(db_path: Path, migrations_dir: Path) -> list[int]:
    conn = connect(db_path)
    try:
        return migrate(conn, migrations_dir)
    finally:
        conn.close()


def main() -> None:
    settings = get_settings()
    applied = run(settings.database_path, settings.migrations_dir)
    if applied:
        print(f"適用しました: {', '.join(f'{v:04d}' for v in applied)}")
    else:
        print("適用するマイグレーションはありません")


if __name__ == "__main__":
    main()

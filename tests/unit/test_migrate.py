import sqlite3

import pytest

from app.db import migrate
from app.db.connection import connect

EXPECTED_TABLES = {
    "organizations",
    "users",
    "sessions",
    "positions",
    "job_types",
    "skills",
    "floors",
    "rooms",
    "furniture",
    "profiles",
    "user_skills",
    "presence",
    "troubles",
}


def _tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {row["name"] for row in rows}


def test_creates_all_tables_and_sets_version(db):
    assert _tables(db) == EXPECTED_TABLES
    assert migrate.current_version(db) == 1


def test_running_twice_applies_nothing(settings, db):
    assert migrate.run(settings.database_path, settings.migrations_dir) == []


def test_connection_enables_foreign_keys_and_wal(db):
    assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_failed_migration_is_rolled_back(tmp_path):
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "0001_ok.sql").write_text("CREATE TABLE a (id INTEGER);", encoding="utf-8")
    (migrations_dir / "0002_broken.sql").write_text(
        "CREATE TABLE b (id INTEGER);\nTHIS IS NOT SQL;", encoding="utf-8"
    )
    conn = connect(tmp_path / "test.db")
    try:
        with pytest.raises(sqlite3.Error):
            migrate.migrate(conn, migrations_dir)
        assert migrate.current_version(conn) == 1
        assert _tables(conn) == {"a"}
    finally:
        conn.close()


def test_rejects_invalid_file_name(tmp_path):
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    (migrations_dir / "init.sql").write_text("SELECT 1;", encoding="utf-8")
    conn = connect(tmp_path / "test.db")
    try:
        with pytest.raises(ValueError):
            migrate.migrate(conn, migrations_dir)
    finally:
        conn.close()

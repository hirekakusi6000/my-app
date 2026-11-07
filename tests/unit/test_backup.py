import sqlite3
from datetime import datetime, timedelta

import pytest

from app.db.backup import create_backup, prune_backups


@pytest.fixture
def source(tmp_path):
    db = tmp_path / "app.db"
    conn = sqlite3.connect(db)
    with conn:
        conn.execute("CREATE TABLE t (v TEXT)")
        conn.execute("INSERT INTO t VALUES ('hello')")
    conn.close()
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    (uploads / "a.png").write_bytes(b"png")
    return db, uploads


def test_create_backup_copies_database_and_uploads(tmp_path, source):
    db, uploads = source
    target = create_backup(db, uploads, tmp_path / "backups", now=datetime(2026, 11, 7, 3, 15))

    assert target.name == "20261107-031500"
    conn = sqlite3.connect(target / "app.db")
    assert conn.execute("SELECT v FROM t").fetchone() == ("hello",)
    conn.close()
    assert (target / "uploads" / "a.png").read_bytes() == b"png"


def test_backup_works_while_database_is_open(tmp_path, source):
    db, uploads = source
    writer = sqlite3.connect(db)
    writer.execute("PRAGMA journal_mode=WAL")
    with writer:
        writer.execute("INSERT INTO t VALUES ('during')")
    target = create_backup(db, uploads, tmp_path / "backups")
    writer.close()
    conn = sqlite3.connect(target / "app.db")
    assert conn.execute("SELECT COUNT(*) FROM t").fetchone() == (2,)
    conn.close()


def test_prune_keeps_newest_and_ignores_other_folders(tmp_path, source):
    db, uploads = source
    backups = tmp_path / "backups"
    start = datetime(2026, 11, 1, 3, 0)
    for day in range(5):
        create_backup(db, uploads, backups, now=start + timedelta(days=day))
    (backups / "my-notes").mkdir()  # バックアップ以外のフォルダは消さない

    removed = prune_backups(backups, keep=2)

    assert sorted(p.name for p in removed) == [
        "20261101-030000",
        "20261102-030000",
        "20261103-030000",
    ]
    assert sorted(p.name for p in backups.iterdir()) == [
        "20261104-030000",
        "20261105-030000",
        "my-notes",
    ]

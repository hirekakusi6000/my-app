"""0001_init.sql の制約が、設計どおりにデータを守ることを確認する。"""

import sqlite3

import pytest

NOW = "2026-11-06T00:00:00Z"


def _org(conn: sqlite3.Connection, name: str = "組織A") -> int:
    cur = conn.execute("INSERT INTO organizations (name, created_at) VALUES (?, ?)", (name, NOW))
    return cur.lastrowid


def _user(conn: sqlite3.Connection, org_id: int, email: str, role: str = "general") -> int:
    cur = conn.execute(
        "INSERT INTO users (organization_id, email, password_hash, role, created_at, updated_at)"
        " VALUES (?, ?, 'x', ?, ?, ?)",
        (org_id, email, role, NOW, NOW),
    )
    return cur.lastrowid


def _chair(conn: sqlite3.Connection, org_id: int) -> int:
    floor_id = conn.execute(
        "INSERT INTO floors (organization_id, name) VALUES (?, ?)", (org_id, "1F")
    ).lastrowid
    room_id = conn.execute(
        "INSERT INTO rooms (organization_id, floor_id, name, width, height)"
        " VALUES (?, ?, '執務室', 20, 10)",
        (org_id, floor_id),
    ).lastrowid
    return conn.execute(
        "INSERT INTO furniture (organization_id, room_id, type, x, y, width, height)"
        " VALUES (?, ?, 'chair', 1, 1, 1, 1)",
        (org_id, room_id),
    ).lastrowid


def _presence(conn, user_id, org_id, status, seat_id=None) -> None:
    conn.execute(
        "INSERT INTO presence (user_id, organization_id, status, seat_id, updated_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (user_id, org_id, status, seat_id, NOW),
    )


def test_email_is_unique_case_insensitive(db):
    org_id = _org(db)
    _user(db, org_id, "taro@example.com")
    with pytest.raises(sqlite3.IntegrityError):
        _user(db, _org(db, "組織B"), "TARO@example.com")


def test_same_seat_cannot_be_taken_twice(db):
    org_id = _org(db)
    seat_id = _chair(db, org_id)
    _presence(db, _user(db, org_id, "a@example.com"), org_id, "present", seat_id)
    with pytest.raises(sqlite3.IntegrityError):
        _presence(db, _user(db, org_id, "b@example.com"), org_id, "present", seat_id)


@pytest.mark.parametrize(
    ("status", "has_seat"),
    [("present", False), ("away", False), ("remote", True), ("not_working", True)],
)
def test_seat_must_match_status(db, status, has_seat):
    org_id = _org(db)
    seat_id = _chair(db, org_id) if has_seat else None
    with pytest.raises(sqlite3.IntegrityError):
        _presence(db, _user(db, org_id, "a@example.com"), org_id, status, seat_id)


def test_occupied_seat_cannot_be_deleted(db):
    org_id = _org(db)
    seat_id = _chair(db, org_id)
    _presence(db, _user(db, org_id, "a@example.com"), org_id, "present", seat_id)
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("DELETE FROM furniture WHERE id = ?", (seat_id,))


def test_deleting_user_removes_related_rows(db):
    org_id = _org(db)
    seat_id = _chair(db, org_id)
    user_id = _user(db, org_id, "a@example.com")
    _presence(db, user_id, org_id, "present", seat_id)
    db.execute(
        "INSERT INTO profiles (user_id, name, birth_date, updated_at)"
        " VALUES (?, '山田太郎', '1990-04-01', ?)",
        (user_id, NOW),
    )

    db.execute("DELETE FROM users WHERE id = ?", (user_id,))

    assert db.execute("SELECT COUNT(*) FROM presence").fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM profiles").fetchone()[0] == 0
    # 座席が空いたので、家具自体は削除できる
    db.execute("DELETE FROM furniture WHERE id = ?", (seat_id,))


def test_default_seat_is_cleared_when_chair_is_deleted(db):
    org_id = _org(db)
    seat_id = _chair(db, org_id)
    user_id = _user(db, org_id, "a@example.com")
    db.execute(
        "INSERT INTO profiles (user_id, name, birth_date, default_seat_id, updated_at)"
        " VALUES (?, '山田太郎', '1990-04-01', ?, ?)",
        (user_id, seat_id, NOW),
    )

    db.execute("DELETE FROM furniture WHERE id = ?", (seat_id,))

    row = db.execute("SELECT default_seat_id FROM profiles WHERE user_id = ?", (user_id,))
    assert row.fetchone()["default_seat_id"] is None


def test_birth_date_format_is_checked(db):
    user_id = _user(db, _org(db), "a@example.com")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO profiles (user_id, name, birth_date, updated_at)"
            " VALUES (?, '山田太郎', '1990/4/1', ?)",
            (user_id, NOW),
        )

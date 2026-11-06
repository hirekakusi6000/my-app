import sqlite3

from app.entities.user import User


class SessionRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create(self, *, token_hash: str, user_id: int, expires_at: str, now: str) -> None:
        self.conn.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at, created_at)"
            " VALUES (?, ?, ?, ?)",
            (token_hash, user_id, expires_at, now),
        )

    def find_user(self, token_hash: str, now: str) -> User | None:
        """有効期限内のセッションに対応するユーザーを返す。"""
        row = self.conn.execute(
            "SELECT u.id, u.organization_id, u.email, u.password_hash, u.role,"
            "       u.must_change_password, u.created_at, u.updated_at"
            " FROM sessions s JOIN users u ON u.id = s.user_id"
            " WHERE s.token_hash = ? AND s.expires_at > ?",
            (token_hash, now),
        ).fetchone()
        return User.from_row(row) if row else None

    def delete(self, token_hash: str) -> None:
        self.conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))

    def delete_others(self, *, user_id: int, keep_token_hash: str) -> None:
        self.conn.execute(
            "DELETE FROM sessions WHERE user_id = ? AND token_hash <> ?",
            (user_id, keep_token_hash),
        )

    def delete_expired(self, now: str) -> None:
        self.conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))

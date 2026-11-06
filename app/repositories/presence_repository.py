import sqlite3

from app.entities.profile import Presence


class PresenceRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create_initial(self, *, user_id: int, organization_id: int, now: str) -> None:
        """一般ユーザーの作成時に「未出勤」の状態を用意する。"""
        self.conn.execute(
            "INSERT INTO presence (user_id, organization_id, status, updated_at)"
            " VALUES (?, ?, 'not_working', ?)",
            (user_id, organization_id, now),
        )

    def get(self, user_id: int, organization_id: int) -> Presence | None:
        row = self.conn.execute(
            "SELECT status, seat_id, comment FROM presence"
            " WHERE user_id = ? AND organization_id = ?",
            (user_id, organization_id),
        ).fetchone()
        if row is None:
            return None
        return Presence(status=row["status"], seat_id=row["seat_id"], comment=row["comment"])

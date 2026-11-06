import sqlite3


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

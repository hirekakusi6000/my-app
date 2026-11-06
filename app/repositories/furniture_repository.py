import sqlite3


class FurnitureRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def is_seat(self, furniture_id: int, organization_id: int) -> bool:
        """自分の組織の椅子（＝座席）かどうか。"""
        row = self.conn.execute(
            "SELECT 1 FROM furniture WHERE id = ? AND organization_id = ? AND type = 'chair'",
            (furniture_id, organization_id),
        ).fetchone()
        return row is not None

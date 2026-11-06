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

    def release_seats(self, seat_ids: list[int], organization_id: int, now: str) -> None:
        """指定した座席に座っている人を「未出勤」に戻し、座席を空ける。"""
        self.conn.executemany(
            "UPDATE presence SET status = 'not_working', seat_id = NULL, updated_at = ?"
            " WHERE seat_id = ? AND organization_id = ?",
            [(now, seat_id, organization_id) for seat_id in seat_ids],
        )

    def release_seats_in_rooms(self, room_ids: list[int], organization_id: int, now: str) -> None:
        self.conn.executemany(
            "UPDATE presence SET status = 'not_working', seat_id = NULL, updated_at = ?"
            " WHERE organization_id = ?"
            "   AND seat_id IN (SELECT id FROM furniture WHERE room_id = ?)",
            [(now, organization_id, room_id) for room_id in room_ids],
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

import sqlite3

from app.entities.office import SeatInfo
from app.entities.presence import PresenceEntry, PresenceStatus
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

    def update(
        self,
        *,
        user_id: int,
        organization_id: int,
        status: PresenceStatus,
        seat_id: int | None,
        comment: str | None,
        now: str,
    ) -> None:
        """在席状態を更新する。座席が他の人と重なると sqlite3.IntegrityError になる。"""
        self.conn.execute(
            "UPDATE presence SET status = ?, seat_id = ?, comment = ?, updated_at = ?"
            " WHERE user_id = ? AND organization_id = ?",
            (status.value, seat_id, comment, now, user_id, organization_id),
        )

    def find_user_on_seat(self, seat_id: int, organization_id: int) -> int | None:
        row = self.conn.execute(
            "SELECT user_id FROM presence WHERE seat_id = ? AND organization_id = ?",
            (seat_id, organization_id),
        ).fetchone()
        return row["user_id"] if row else None

    def list_entries(self, organization_id: int, user_id: int | None = None) -> list[PresenceEntry]:
        """組織の一般ユーザーの勤務状況（プロフィール登録済みの人だけ）。"""
        rows = self.conn.execute(
            "SELECT pr.user_id, pr.status, pr.comment, pr.seat_id, pr.updated_at,"
            "       p.name, p.avatar_path,"
            "       f.label AS seat_label, r.id AS room_id, r.name AS room_name,"
            "       fl.id AS floor_id, fl.name AS floor_name"
            " FROM presence pr"
            " JOIN profiles p ON p.user_id = pr.user_id"
            " LEFT JOIN furniture f ON f.id = pr.seat_id"
            " LEFT JOIN rooms r ON r.id = f.room_id"
            " LEFT JOIN floors fl ON fl.id = r.floor_id"
            " WHERE pr.organization_id = ? AND (? IS NULL OR pr.user_id = ?)"
            " ORDER BY p.name, pr.user_id",
            (organization_id, user_id, user_id),
        ).fetchall()
        return [
            PresenceEntry(
                user_id=r["user_id"],
                name=r["name"],
                avatar_path=r["avatar_path"],
                status=PresenceStatus(r["status"]),
                comment=r["comment"],
                seat=(
                    SeatInfo(
                        seat_id=r["seat_id"],
                        label=r["seat_label"],
                        room_id=r["room_id"],
                        room_name=r["room_name"],
                        floor_id=r["floor_id"],
                        floor_name=r["floor_name"],
                    )
                    if r["seat_id"] is not None
                    else None
                ),
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

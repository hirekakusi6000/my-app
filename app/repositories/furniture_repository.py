import sqlite3

from app.entities.office import Furniture, SeatInfo, SeatOccupant

_COLUMNS = "id, type, label, x, y, width, height, rotation"


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

    def list_by_room(self, room_id: int, organization_id: int) -> list[Furniture]:
        rows = self.conn.execute(
            f"SELECT {_COLUMNS} FROM furniture WHERE room_id = ? AND organization_id = ?"
            " ORDER BY id",
            (room_id, organization_id),
        ).fetchall()
        return [Furniture.from_row(r) for r in rows]

    def create(self, *, organization_id: int, room_id: int, item: Furniture) -> int:
        cur = self.conn.execute(
            "INSERT INTO furniture"
            " (organization_id, room_id, type, label, x, y, width, height, rotation)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                organization_id,
                room_id,
                item.type.value,
                item.label,
                item.x,
                item.y,
                item.width,
                item.height,
                item.rotation,
            ),
        )
        return cur.lastrowid

    def update(self, *, organization_id: int, room_id: int, item: Furniture) -> None:
        self.conn.execute(
            "UPDATE furniture SET type = ?, label = ?, x = ?, y = ?, width = ?, height = ?,"
            " rotation = ? WHERE id = ? AND room_id = ? AND organization_id = ?",
            (
                item.type.value,
                item.label,
                item.x,
                item.y,
                item.width,
                item.height,
                item.rotation,
                item.id,
                room_id,
                organization_id,
            ),
        )

    def delete_many(self, ids: list[int], organization_id: int) -> None:
        self.conn.executemany(
            "DELETE FROM furniture WHERE id = ? AND organization_id = ?",
            [(i, organization_id) for i in ids],
        )

    def clear_default_seats(self, ids: list[int]) -> None:
        """座席でなくなった家具を、デフォルト座席に設定している人の設定を外す。"""
        self.conn.executemany(
            "UPDATE profiles SET default_seat_id = NULL WHERE default_seat_id = ?",
            [(i,) for i in ids],
        )

    def occupants_in_room(self, room_id: int, organization_id: int) -> list[SeatOccupant]:
        rows = self.conn.execute(
            "SELECT pr.seat_id, pr.user_id, pr.status, pr.updated_at, p.name, p.avatar_path"
            " FROM presence pr"
            " JOIN furniture f ON f.id = pr.seat_id"
            " LEFT JOIN profiles p ON p.user_id = pr.user_id"
            " WHERE f.room_id = ? AND pr.organization_id = ?",
            (room_id, organization_id),
        ).fetchall()
        return [
            SeatOccupant(
                seat_id=r["seat_id"],
                user_id=r["user_id"],
                name=r["name"],
                status=r["status"],
                avatar_path=r["avatar_path"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    def seat_info(self, seat_id: int, organization_id: int) -> SeatInfo | None:
        row = self.conn.execute(
            "SELECT f.id, f.label, r.id AS room_id, r.name AS room_name,"
            "       fl.id AS floor_id, fl.name AS floor_name"
            " FROM furniture f"
            " JOIN rooms r ON r.id = f.room_id"
            " JOIN floors fl ON fl.id = r.floor_id"
            " WHERE f.id = ? AND f.organization_id = ? AND f.type = 'chair'",
            (seat_id, organization_id),
        ).fetchone()
        if row is None:
            return None
        return SeatInfo(
            seat_id=row["id"],
            label=row["label"],
            room_id=row["room_id"],
            room_name=row["room_name"],
            floor_id=row["floor_id"],
            floor_name=row["floor_name"],
        )

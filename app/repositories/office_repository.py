"""フロアと部屋。すべて organization_id で絞り込む。"""

import sqlite3

from app.entities.office import Floor, Room

_ROOM_COLUMNS = "id, floor_id, name, width, height, sort_order"


class FloorRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def list(self, organization_id: int) -> list[Floor]:
        rows = self.conn.execute(
            "SELECT id, name, sort_order FROM floors WHERE organization_id = ?"
            " ORDER BY sort_order, id",
            (organization_id,),
        ).fetchall()
        return [Floor.from_row(r) for r in rows]

    def get(self, floor_id: int, organization_id: int) -> Floor | None:
        row = self.conn.execute(
            "SELECT id, name, sort_order FROM floors WHERE id = ? AND organization_id = ?",
            (floor_id, organization_id),
        ).fetchone()
        return Floor.from_row(row) if row else None

    def count(self, organization_id: int) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM floors WHERE organization_id = ?", (organization_id,)
        ).fetchone()[0]

    def next_sort_order(self, organization_id: int) -> int:
        return self.conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM floors WHERE organization_id = ?",
            (organization_id,),
        ).fetchone()[0]

    def create(self, organization_id: int, name: str, sort_order: int) -> Floor:
        cur = self.conn.execute(
            "INSERT INTO floors (organization_id, name, sort_order) VALUES (?, ?, ?)",
            (organization_id, name, sort_order),
        )
        return Floor(id=cur.lastrowid, name=name, sort_order=sort_order)

    def update(self, floor_id: int, organization_id: int, name: str, sort_order: int) -> None:
        self.conn.execute(
            "UPDATE floors SET name = ?, sort_order = ? WHERE id = ? AND organization_id = ?",
            (name, sort_order, floor_id, organization_id),
        )

    def delete(self, floor_id: int, organization_id: int) -> None:
        self.conn.execute(
            "DELETE FROM floors WHERE id = ? AND organization_id = ?", (floor_id, organization_id)
        )


class RoomRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def list(self, organization_id: int) -> list[Room]:
        rows = self.conn.execute(
            f"SELECT {_ROOM_COLUMNS} FROM rooms WHERE organization_id = ? ORDER BY sort_order, id",
            (organization_id,),
        ).fetchall()
        return [Room.from_row(r) for r in rows]

    def get(self, room_id: int, organization_id: int) -> Room | None:
        row = self.conn.execute(
            f"SELECT {_ROOM_COLUMNS} FROM rooms WHERE id = ? AND organization_id = ?",
            (room_id, organization_id),
        ).fetchone()
        return Room.from_row(row) if row else None

    def count_in_floor(self, floor_id: int) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM rooms WHERE floor_id = ?", (floor_id,)
        ).fetchone()[0]

    def next_sort_order(self, floor_id: int) -> int:
        return self.conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM rooms WHERE floor_id = ?", (floor_id,)
        ).fetchone()[0]

    def create(
        self,
        *,
        organization_id: int,
        floor_id: int,
        name: str,
        width: int,
        height: int,
        sort_order: int,
    ) -> Room:
        cur = self.conn.execute(
            "INSERT INTO rooms (organization_id, floor_id, name, width, height, sort_order)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (organization_id, floor_id, name, width, height, sort_order),
        )
        return Room(
            id=cur.lastrowid,
            floor_id=floor_id,
            name=name,
            width=width,
            height=height,
            sort_order=sort_order,
        )

    def update(self, room: Room, organization_id: int) -> None:
        self.conn.execute(
            "UPDATE rooms SET name = ?, width = ?, height = ?, sort_order = ?"
            " WHERE id = ? AND organization_id = ?",
            (room.name, room.width, room.height, room.sort_order, room.id, organization_id),
        )

    def delete(self, room_id: int, organization_id: int) -> None:
        self.conn.execute(
            "DELETE FROM rooms WHERE id = ? AND organization_id = ?", (room_id, organization_id)
        )

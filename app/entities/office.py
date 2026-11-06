"""フロア・部屋・家具。

座標と大きさはグリッドの単位で持つ。
- x, y: 家具が床に占める範囲（向きを反映した後の四角形）の左上
- width, height: 向きが 0 度のときの幅と奥行き
- rotation: 0 / 90 / 180 / 270。90 度か 270 度のときは、床に占める範囲の幅と奥行きが入れ替わる
"""

import sqlite3
from dataclasses import dataclass
from enum import StrEnum


class FurnitureType(StrEnum):
    DESK = "desk"
    CHAIR = "chair"  # 椅子＝座席
    WALL = "wall"
    DOOR = "door"
    OTHER = "other"


@dataclass(frozen=True)
class Room:
    id: int
    floor_id: int
    name: str
    width: int
    height: int
    sort_order: int

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Room":
        return cls(
            id=row["id"],
            floor_id=row["floor_id"],
            name=row["name"],
            width=row["width"],
            height=row["height"],
            sort_order=row["sort_order"],
        )


@dataclass(frozen=True)
class Floor:
    id: int
    name: str
    sort_order: int
    rooms: tuple[Room, ...] = ()

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Floor":
        return cls(id=row["id"], name=row["name"], sort_order=row["sort_order"])


@dataclass(frozen=True)
class Furniture:
    id: int | None  # 新しく追加する家具は保存するまで None
    type: FurnitureType
    label: str | None
    x: int
    y: int
    width: int
    height: int
    rotation: int

    @property
    def footprint(self) -> tuple[int, int]:
        """床に占める範囲の (幅, 奥行き)。"""
        if self.rotation in (90, 270):
            return self.height, self.width
        return self.width, self.height

    @property
    def is_seat(self) -> bool:
        return self.type is FurnitureType.CHAIR

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Furniture":
        return cls(
            id=row["id"],
            type=FurnitureType(row["type"]),
            label=row["label"],
            x=row["x"],
            y=row["y"],
            width=row["width"],
            height=row["height"],
            rotation=row["rotation"],
        )


@dataclass(frozen=True)
class SeatOccupant:
    seat_id: int
    user_id: int
    name: str | None
    status: str
    avatar_path: str | None


@dataclass(frozen=True)
class SeatInfo:
    """座席の場所（デフォルト座席の表示などに使う）。"""

    seat_id: int
    label: str | None
    room_id: int
    room_name: str
    floor_id: int
    floor_name: str

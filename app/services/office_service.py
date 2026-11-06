"""フロア・部屋の管理と、部屋の配置（家具）の保存。

座っている人がいる座席（家具・部屋・フロア）を削除するときは、
先にその人を「未出勤」に戻して座席を空けてから削除する。
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace

from app.core.errors import BusinessRuleError, ConflictError, NotFoundError
from app.core.time import to_iso, utc_now
from app.entities.office import Floor, Furniture, Room, SeatOccupant
from app.entities.user import User
from app.repositories.furniture_repository import FurnitureRepository
from app.repositories.office_repository import FloorRepository, RoomRepository
from app.repositories.presence_repository import PresenceRepository

MAX_FLOORS = 5
MAX_ROOMS_PER_FLOOR = 5
MAX_FURNITURE_PER_ROOM = 500


@dataclass(frozen=True)
class Layout:
    room: Room
    floor: Floor
    furniture: list[Furniture]


class OfficeService:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.floors = FloorRepository(conn)
        self.rooms = RoomRepository(conn)
        self.furniture = FurnitureRepository(conn)
        self.presence = PresenceRepository(conn)

    # ───────── フロア ─────────

    def list_floors(self, user: User) -> list[Floor]:
        """フロアの一覧（それぞれの部屋を含む）。"""
        rooms = self.rooms.list(user.organization_id)
        return [
            replace(f, rooms=tuple(r for r in rooms if r.floor_id == f.id))
            for f in self.floors.list(user.organization_id)
        ]

    def create_floor(self, master: User, name: str) -> Floor:
        org = master.organization_id
        with self.conn, _unique_name():
            if self.floors.count(org) >= MAX_FLOORS:
                raise _limit(f"フロアは{MAX_FLOORS}つまで登録できます")
            return self.floors.create(org, name, self.floors.next_sort_order(org))

    def update_floor(
        self, master: User, floor_id: int, *, name: str | None, sort_order: int | None
    ) -> Floor:
        floor = self._get_floor(master, floor_id)
        updated = replace(
            floor,
            name=name if name is not None else floor.name,
            sort_order=sort_order if sort_order is not None else floor.sort_order,
        )
        with self.conn, _unique_name():
            self.floors.update(floor_id, master.organization_id, updated.name, updated.sort_order)
        return updated

    def delete_floor(self, master: User, floor_id: int) -> None:
        self._get_floor(master, floor_id)
        org = master.organization_id
        room_ids = [r.id for r in self.rooms.list(org) if r.floor_id == floor_id]
        with self.conn:
            self.presence.release_seats_in_rooms(room_ids, org, to_iso(utc_now()))
            self.floors.delete(floor_id, org)

    # ───────── 部屋 ─────────

    def create_room(
        self, master: User, floor_id: int, *, name: str, width: int, height: int
    ) -> Room:
        self._get_floor(master, floor_id)
        with self.conn, _unique_name():
            if self.rooms.count_in_floor(floor_id) >= MAX_ROOMS_PER_FLOOR:
                raise _limit(f"部屋は1つのフロアに{MAX_ROOMS_PER_FLOOR}つまで登録できます")
            return self.rooms.create(
                organization_id=master.organization_id,
                floor_id=floor_id,
                name=name,
                width=width,
                height=height,
                sort_order=self.rooms.next_sort_order(floor_id),
            )

    def update_room(
        self,
        master: User,
        room_id: int,
        *,
        name: str | None = None,
        width: int | None = None,
        height: int | None = None,
        sort_order: int | None = None,
    ) -> Room:
        room = self._get_room(master, room_id)
        updated = replace(
            room,
            name=name if name is not None else room.name,
            width=width if width is not None else room.width,
            height=height if height is not None else room.height,
            sort_order=sort_order if sort_order is not None else room.sort_order,
        )
        furniture = self.furniture.list_by_room(room_id, master.organization_id)
        if any(not _fits(f, updated) for f in furniture):
            raise BusinessRuleError(
                "家具が部屋からはみ出してしまうため、この大きさにはできません",
                code="ROOM_TOO_SMALL",
            )
        with self.conn, _unique_name():
            self.rooms.update(updated, master.organization_id)
        return updated

    def delete_room(self, master: User, room_id: int) -> None:
        self._get_room(master, room_id)
        org = master.organization_id
        with self.conn:
            self.presence.release_seats_in_rooms([room_id], org, to_iso(utc_now()))
            self.rooms.delete(room_id, org)

    # ───────── 配置 ─────────

    def get_layout(self, user: User, room_id: int) -> Layout:
        room = self._get_room(user, room_id)
        floor = self.floors.get(room.floor_id, user.organization_id)
        assert floor is not None
        return Layout(
            room=room,
            floor=floor,
            furniture=self.furniture.list_by_room(room_id, user.organization_id),
        )

    def save_layout(self, master: User, room_id: int, items: list[Furniture]) -> Layout:
        """部屋の家具をまとめて保存する。

        id がある家具は更新、id がない家具は追加、送られてこなかった家具は削除する。
        """
        room = self._get_room(master, room_id)
        org = master.organization_id
        if len(items) > MAX_FURNITURE_PER_ROOM:
            raise _limit(f"1つの部屋に置ける家具は{MAX_FURNITURE_PER_ROOM}個までです")

        existing = {f.id: f for f in self.furniture.list_by_room(room_id, org)}
        incoming_ids = [i.id for i in items if i.id is not None]
        if len(incoming_ids) != len(set(incoming_ids)) or any(
            i not in existing for i in incoming_ids
        ):
            raise BusinessRuleError("配置のデータが正しくありません", code="INVALID_FURNITURE")
        for item in items:
            if not _fits(item, room):
                raise BusinessRuleError(
                    "部屋からはみ出している家具があります", code="FURNITURE_OUT_OF_ROOM"
                )

        removed = [fid for fid in existing if fid not in set(incoming_ids)]
        # 椅子から別の種類に変わった家具も「座席がなくなった」として扱う
        no_longer_seats = removed + [
            i.id for i in items if i.id is not None and existing[i.id].is_seat and not i.is_seat
        ]
        no_longer_seats = [fid for fid in no_longer_seats if existing[fid].is_seat]

        with self.conn:
            self.presence.release_seats(no_longer_seats, org, to_iso(utc_now()))
            self.furniture.clear_default_seats(no_longer_seats)
            self.furniture.delete_many(removed, org)
            for item in items:
                if item.id is None:
                    self.furniture.create(organization_id=org, room_id=room_id, item=item)
                else:
                    self.furniture.update(organization_id=org, room_id=room_id, item=item)
        return self.get_layout(master, room_id)

    def get_occupants(self, user: User, room_id: int) -> list[SeatOccupant]:
        self._get_room(user, room_id)
        return self.furniture.occupants_in_room(room_id, user.organization_id)

    # ───────── 内部処理 ─────────

    def _get_floor(self, user: User, floor_id: int) -> Floor:
        floor = self.floors.get(floor_id, user.organization_id)
        if floor is None:
            raise NotFoundError("フロアが見つかりません")
        return floor

    def _get_room(self, user: User, room_id: int) -> Room:
        room = self.rooms.get(room_id, user.organization_id)
        if room is None:
            raise NotFoundError("部屋が見つかりません")
        return room


def _fits(item: Furniture, room: Room) -> bool:
    w, h = item.footprint
    return item.x + w <= room.width and item.y + h <= room.height


def _limit(message: str) -> BusinessRuleError:
    return BusinessRuleError(message, code="LIMIT_EXCEEDED")


@contextmanager
def _unique_name() -> Iterator[None]:
    try:
        yield
    except sqlite3.IntegrityError as exc:
        raise ConflictError("同じ名前がすでに登録されています", code="NAME_TAKEN") from exc

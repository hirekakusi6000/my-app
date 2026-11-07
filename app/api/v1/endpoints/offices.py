"""フロア・部屋・配置。参照は全員（パスワード変更後）、変更はマスターのみ。"""

import sqlite3

from fastapi import APIRouter, Depends, status

from app.api.deps import require_active_user, require_master, require_password_changed
from app.api.v1.presenters import avatar_url
from app.db.connection import get_db
from app.entities.office import Floor, Furniture, Room
from app.entities.presence import is_stale
from app.entities.user import User
from app.schemas.office import (
    FloorCreateRequest,
    FloorResponse,
    FloorUpdateRequest,
    FurnitureItem,
    LayoutRequest,
    LayoutResponse,
    OccupantResponse,
    RoomCreateRequest,
    RoomResponse,
    RoomUpdateRequest,
)
from app.services.office_service import Layout, OfficeService

router = APIRouter(tags=["offices"])


def get_service(conn: sqlite3.Connection = Depends(get_db)) -> OfficeService:
    return OfficeService(conn)


def _room(r: Room) -> RoomResponse:
    return RoomResponse(
        id=r.id,
        floor_id=r.floor_id,
        name=r.name,
        width=r.width,
        height=r.height,
        sort_order=r.sort_order,
    )


def _floor(f: Floor) -> FloorResponse:
    return FloorResponse(
        id=f.id, name=f.name, sort_order=f.sort_order, rooms=[_room(r) for r in f.rooms]
    )


def _layout(layout: Layout) -> LayoutResponse:
    return LayoutResponse(
        room=_room(layout.room),
        floor_name=layout.floor.name,
        furniture=[
            FurnitureItem(
                id=f.id,
                type=f.type,
                label=f.label,
                x=f.x,
                y=f.y,
                width=f.width,
                height=f.height,
                rotation=f.rotation,
            )
            for f in layout.furniture
        ],
    )


# ───────── フロア ─────────


@router.get("/floors", response_model=list[FloorResponse])
def list_floors(
    user: User = Depends(require_password_changed),
    service: OfficeService = Depends(get_service),
) -> list[FloorResponse]:
    return [_floor(f) for f in service.list_floors(user)]


@router.post("/floors", response_model=FloorResponse, status_code=status.HTTP_201_CREATED)
def create_floor(
    body: FloorCreateRequest,
    master: User = Depends(require_master),
    service: OfficeService = Depends(get_service),
) -> FloorResponse:
    return _floor(service.create_floor(master, body.name))


@router.patch("/floors/{floor_id}", response_model=FloorResponse)
def update_floor(
    floor_id: int,
    body: FloorUpdateRequest,
    master: User = Depends(require_master),
    service: OfficeService = Depends(get_service),
) -> FloorResponse:
    floor = service.update_floor(master, floor_id, name=body.name, sort_order=body.sort_order)
    return _floor(next(f for f in service.list_floors(master) if f.id == floor.id))


@router.delete("/floors/{floor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_floor(
    floor_id: int,
    master: User = Depends(require_master),
    service: OfficeService = Depends(get_service),
) -> None:
    service.delete_floor(master, floor_id)


# ───────── 部屋 ─────────


@router.post(
    "/floors/{floor_id}/rooms", response_model=RoomResponse, status_code=status.HTTP_201_CREATED
)
def create_room(
    floor_id: int,
    body: RoomCreateRequest,
    master: User = Depends(require_master),
    service: OfficeService = Depends(get_service),
) -> RoomResponse:
    room = service.create_room(
        master, floor_id, name=body.name, width=body.width, height=body.height
    )
    return _room(room)


@router.patch("/rooms/{room_id}", response_model=RoomResponse)
def update_room(
    room_id: int,
    body: RoomUpdateRequest,
    master: User = Depends(require_master),
    service: OfficeService = Depends(get_service),
) -> RoomResponse:
    room = service.update_room(
        master,
        room_id,
        name=body.name,
        width=body.width,
        height=body.height,
        sort_order=body.sort_order,
    )
    return _room(room)


@router.delete("/rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(
    room_id: int,
    master: User = Depends(require_master),
    service: OfficeService = Depends(get_service),
) -> None:
    service.delete_room(master, room_id)


# ───────── 配置・座っている人 ─────────


@router.get("/rooms/{room_id}/layout", response_model=LayoutResponse)
def read_layout(
    room_id: int,
    user: User = Depends(require_password_changed),
    service: OfficeService = Depends(get_service),
) -> LayoutResponse:
    return _layout(service.get_layout(user, room_id))


@router.put("/rooms/{room_id}/layout", response_model=LayoutResponse)
def save_layout(
    room_id: int,
    body: LayoutRequest,
    master: User = Depends(require_master),
    service: OfficeService = Depends(get_service),
) -> LayoutResponse:
    items = [
        Furniture(
            id=i.id,
            type=i.type,
            label=i.label,
            x=i.x,
            y=i.y,
            width=i.width,
            height=i.height,
            rotation=i.rotation,
        )
        for i in body.furniture
    ]
    return _layout(service.save_layout(master, room_id, items))


@router.get("/rooms/{room_id}/occupancy", response_model=list[OccupantResponse])
def read_occupancy(
    room_id: int,
    user: User = Depends(require_active_user),
    service: OfficeService = Depends(get_service),
) -> list[OccupantResponse]:
    return [
        OccupantResponse(
            seat_id=o.seat_id,
            user_id=o.user_id,
            name=o.name,
            status=o.status,
            avatar_url=avatar_url(o.user_id, o.avatar_path),
            updated_at=o.updated_at,
            is_stale=is_stale(o.status, o.updated_at),
        )
        for o in service.get_occupants(user, room_id)
    ]

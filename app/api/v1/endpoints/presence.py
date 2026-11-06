import sqlite3

from fastapi import APIRouter, Depends, status

from app.api.deps import require_active_general, require_active_user, require_master
from app.api.v1.presenters import avatar_url
from app.db.connection import get_db
from app.entities.presence import PresenceEntry
from app.entities.user import User
from app.schemas.presence import PresenceRequest, PresenceResponse, SeatResponse
from app.services.presence_service import PresenceService

router = APIRouter(tags=["presence"])


def get_service(conn: sqlite3.Connection = Depends(get_db)) -> PresenceService:
    return PresenceService(conn)


def _response(e: PresenceEntry) -> PresenceResponse:
    return PresenceResponse(
        user_id=e.user_id,
        name=e.name,
        avatar_url=avatar_url(e.user_id, e.avatar_path),
        status=e.status,
        comment=e.comment,
        seat=(
            SeatResponse(
                seat_id=e.seat.seat_id,
                label=e.seat.label,
                room_id=e.seat.room_id,
                room_name=e.seat.room_name,
                floor_name=e.seat.floor_name,
            )
            if e.seat
            else None
        ),
        updated_at=e.updated_at,
    )


@router.get("/me/presence", response_model=PresenceResponse)
def read_my_presence(
    user: User = Depends(require_active_general),
    service: PresenceService = Depends(get_service),
) -> PresenceResponse:
    return _response(service.get_mine(user))


@router.put("/me/presence", response_model=PresenceResponse)
def update_my_presence(
    body: PresenceRequest,
    user: User = Depends(require_active_general),
    service: PresenceService = Depends(get_service),
) -> PresenceResponse:
    kwargs = {"comment": body.comment} if "comment" in body.model_fields_set else {}
    entry = service.update_mine(user, status=body.status, seat_id=body.seat_id, **kwargs)
    return _response(entry)


@router.get("/presence", response_model=list[PresenceResponse])
def list_presence(
    user: User = Depends(require_active_user),
    service: PresenceService = Depends(get_service),
) -> list[PresenceResponse]:
    return [_response(e) for e in service.list_all(user)]


@router.delete("/seats/{seat_id}/occupant", status_code=status.HTTP_204_NO_CONTENT)
def release_seat(
    seat_id: int,
    master: User = Depends(require_master),
    service: PresenceService = Depends(get_service),
) -> None:
    service.release_seat(master, seat_id)

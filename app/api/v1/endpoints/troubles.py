import sqlite3

from fastapi import APIRouter, Depends, status

from app.api.deps import require_active_general, require_active_user
from app.api.v1.presenters import avatar_url
from app.db.connection import get_db
from app.entities.trouble import Trouble, TroubleStatus
from app.entities.user import User
from app.schemas.trouble import TroubleCreateRequest, TroubleResponse, TroubleUpdateRequest
from app.services.trouble_service import TroubleService

router = APIRouter(prefix="/troubles", tags=["troubles"])


def get_service(conn: sqlite3.Connection = Depends(get_db)) -> TroubleService:
    return TroubleService(conn)


def _response(t: Trouble, viewer: User) -> TroubleResponse:
    return TroubleResponse(
        id=t.id,
        user_id=t.user_id,
        author_name=t.author_name,
        author_avatar_url=avatar_url(t.user_id, t.author_avatar_path),
        title=t.title,
        body=t.body,
        status=t.status,
        is_mine=t.user_id == viewer.id,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


@router.get("", response_model=list[TroubleResponse])
def list_troubles(
    status: TroubleStatus | None = None,
    user_id: int | None = None,
    viewer: User = Depends(require_active_user),
    service: TroubleService = Depends(get_service),
) -> list[TroubleResponse]:
    return [_response(t, viewer) for t in service.list(viewer, status=status, user_id=user_id)]


@router.post("", response_model=TroubleResponse, status_code=status.HTTP_201_CREATED)
def create_trouble(
    body: TroubleCreateRequest,
    author: User = Depends(require_active_general),
    service: TroubleService = Depends(get_service),
) -> TroubleResponse:
    return _response(service.create(author, title=body.title, body=body.body), author)


@router.patch("/{trouble_id}", response_model=TroubleResponse)
def update_trouble(
    trouble_id: int,
    body: TroubleUpdateRequest,
    author: User = Depends(require_active_general),
    service: TroubleService = Depends(get_service),
) -> TroubleResponse:
    trouble = service.update(
        author, trouble_id, title=body.title, body=body.body, status=body.status
    )
    return _response(trouble, author)


@router.delete("/{trouble_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trouble(
    trouble_id: int,
    user: User = Depends(require_active_user),
    service: TroubleService = Depends(get_service),
) -> None:
    service.delete(user, trouble_id)

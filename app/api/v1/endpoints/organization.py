"""自分の組織の設定（マスターのみ）。"""

import sqlite3

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import SESSION_COOKIE, get_avatar_storage, require_master
from app.db.connection import get_db
from app.entities.user import Organization, User
from app.schemas.organization import (
    OrganizationDeleteRequest,
    OrganizationResponse,
    OrganizationUpdateRequest,
)
from app.services.avatar_storage import AvatarStorage
from app.services.organization_service import OrganizationService

router = APIRouter(prefix="/organization", tags=["organization"])


def get_service(
    conn: sqlite3.Connection = Depends(get_db),
    storage: AvatarStorage = Depends(get_avatar_storage),
) -> OrganizationService:
    return OrganizationService(conn, storage)


def _response(o: Organization) -> OrganizationResponse:
    return OrganizationResponse(id=o.id, name=o.name, created_at=o.created_at)


@router.get("", response_model=OrganizationResponse)
def read_organization(
    master: User = Depends(require_master),
    service: OrganizationService = Depends(get_service),
) -> OrganizationResponse:
    return _response(service.get(master))


@router.patch("", response_model=OrganizationResponse)
def rename_organization(
    body: OrganizationUpdateRequest,
    master: User = Depends(require_master),
    service: OrganizationService = Depends(get_service),
) -> OrganizationResponse:
    return _response(service.rename(master, body.name))


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_organization(
    body: OrganizationDeleteRequest,
    response: Response,
    master: User = Depends(require_master),
    service: OrganizationService = Depends(get_service),
) -> None:
    service.delete(master, password=body.password, confirm_name=body.confirm_name)
    # 組織と一緒にセッションも消えているので、ブラウザの Cookie も消しておく
    response.delete_cookie(SESSION_COOKIE, path="/")

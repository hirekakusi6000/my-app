"""自分の組織の設定（マスターのみ）。"""

import logging
import sqlite3

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel

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
from app.services.sample_data_service import SampleDataService

audit = logging.getLogger("app.audit")

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
    audit.warning(
        "組織を削除しました organization_id=%s user_id=%s", master.organization_id, master.id
    )
    # 組織と一緒にセッションも消えているので、ブラウザの Cookie も消しておく
    response.delete_cookie(SESSION_COOKIE, path="/")


# ───────── お試し用のサンプルデータ ─────────


class SampleDataStatus(BaseModel):
    available: bool


def get_sample_service(conn: sqlite3.Connection = Depends(get_db)) -> SampleDataService:
    return SampleDataService(conn)


@router.get("/sample-data", response_model=SampleDataStatus)
def read_sample_data_status(
    master: User = Depends(require_master),
    service: SampleDataService = Depends(get_sample_service),
) -> SampleDataStatus:
    """サンプルデータを作成できる（まだフロアも従業員もない）か。"""
    return SampleDataStatus(available=service.is_available(master))


@router.post("/sample-data", status_code=status.HTTP_201_CREATED, response_model=SampleDataStatus)
def create_sample_data(
    master: User = Depends(require_master),
    service: SampleDataService = Depends(get_sample_service),
) -> SampleDataStatus:
    service.create(master)
    return SampleDataStatus(available=False)

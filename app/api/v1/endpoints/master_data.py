"""役職・職種・スキルの候補。参照は全員（初回設定中も可）、変更はマスターのみ。"""

import sqlite3

from fastapi import APIRouter, Depends, status

from app.api.deps import require_master, require_password_changed
from app.db.connection import get_db
from app.entities.master_data import SkillCategory
from app.entities.user import User
from app.schemas.master_data import (
    JobTypeRequest,
    JobTypeResponse,
    NameRequest,
    PositionResponse,
    SkillCreateRequest,
    SkillResponse,
)
from app.services.master_data_service import MasterDataService

router = APIRouter(tags=["master-data"])


def get_service(conn: sqlite3.Connection = Depends(get_db)) -> MasterDataService:
    return MasterDataService(conn)


# ───────── 役職 ─────────


@router.get("/positions", response_model=list[PositionResponse])
def list_positions(
    user: User = Depends(require_password_changed),
    service: MasterDataService = Depends(get_service),
) -> list[PositionResponse]:
    return [PositionResponse(id=p.id, name=p.name) for p in service.get_all(user).positions]


@router.post("/positions", response_model=PositionResponse, status_code=status.HTTP_201_CREATED)
def create_position(
    body: NameRequest,
    master: User = Depends(require_master),
    service: MasterDataService = Depends(get_service),
) -> PositionResponse:
    p = service.create_position(master, body.name)
    return PositionResponse(id=p.id, name=p.name)


@router.patch("/positions/{item_id}", response_model=PositionResponse)
def rename_position(
    item_id: int,
    body: NameRequest,
    master: User = Depends(require_master),
    service: MasterDataService = Depends(get_service),
) -> PositionResponse:
    p = service.rename_position(master, item_id, body.name)
    return PositionResponse(id=p.id, name=p.name)


@router.delete("/positions/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_position(
    item_id: int,
    master: User = Depends(require_master),
    service: MasterDataService = Depends(get_service),
) -> None:
    service.delete_position(master, item_id)


# ───────── 職種 ─────────


def _job_type(j) -> JobTypeResponse:
    return JobTypeResponse(id=j.id, name=j.name, is_engineer=j.is_engineer)


@router.get("/job-types", response_model=list[JobTypeResponse])
def list_job_types(
    user: User = Depends(require_password_changed),
    service: MasterDataService = Depends(get_service),
) -> list[JobTypeResponse]:
    return [_job_type(j) for j in service.get_all(user).job_types]


@router.post("/job-types", response_model=JobTypeResponse, status_code=status.HTTP_201_CREATED)
def create_job_type(
    body: JobTypeRequest,
    master: User = Depends(require_master),
    service: MasterDataService = Depends(get_service),
) -> JobTypeResponse:
    return _job_type(service.create_job_type(master, body.name, body.is_engineer))


@router.patch("/job-types/{item_id}", response_model=JobTypeResponse)
def update_job_type(
    item_id: int,
    body: JobTypeRequest,
    master: User = Depends(require_master),
    service: MasterDataService = Depends(get_service),
) -> JobTypeResponse:
    return _job_type(service.update_job_type(master, item_id, body.name, body.is_engineer))


@router.delete("/job-types/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job_type(
    item_id: int,
    master: User = Depends(require_master),
    service: MasterDataService = Depends(get_service),
) -> None:
    service.delete_job_type(master, item_id)


# ───────── スキル ─────────


def _skill(s) -> SkillResponse:
    return SkillResponse(id=s.id, category=s.category, name=s.name)


@router.get("/skills", response_model=list[SkillResponse])
def list_skills(
    category: SkillCategory | None = None,
    user: User = Depends(require_password_changed),
    service: MasterDataService = Depends(get_service),
) -> list[SkillResponse]:
    skills = service.get_all(user).skills
    return [_skill(s) for s in skills if category is None or s.category is category]


@router.post("/skills", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
def create_skill(
    body: SkillCreateRequest,
    master: User = Depends(require_master),
    service: MasterDataService = Depends(get_service),
) -> SkillResponse:
    return _skill(service.create_skill(master, body.category, body.name))


@router.patch("/skills/{item_id}", response_model=SkillResponse)
def rename_skill(
    item_id: int,
    body: NameRequest,
    master: User = Depends(require_master),
    service: MasterDataService = Depends(get_service),
) -> SkillResponse:
    return _skill(service.rename_skill(master, item_id, body.name))


@router.delete("/skills/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_skill(
    item_id: int,
    master: User = Depends(require_master),
    service: MasterDataService = Depends(get_service),
) -> None:
    service.delete_skill(master, item_id)

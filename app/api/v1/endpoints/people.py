import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.deps import require_active_user
from app.api.v1.presenters import avatar_url
from app.db.connection import get_db
from app.entities.person import PeopleQuery, Person
from app.entities.presence import PresenceStatus
from app.entities.user import User
from app.schemas.presence import SeatResponse
from app.schemas.profile import UserSkillResponse
from app.services.people_service import PeopleService

router = APIRouter(prefix="/people", tags=["people"])


class PersonResponse(BaseModel):
    user_id: int
    name: str
    avatar_url: str | None
    position: str | None
    job_type: str | None
    status: PresenceStatus
    comment: str | None
    seat: SeatResponse | None
    skills: list[UserSkillResponse]
    updated_at: str
    is_stale: bool


def get_service(conn: sqlite3.Connection = Depends(get_db)) -> PeopleService:
    return PeopleService(conn)


def _response(p: Person) -> PersonResponse:
    return PersonResponse(
        user_id=p.user_id,
        name=p.name,
        avatar_url=avatar_url(p.user_id, p.avatar_path),
        position=p.position,
        job_type=p.job_type,
        status=p.status,
        comment=p.comment,
        seat=(
            SeatResponse(
                seat_id=p.seat.seat_id,
                label=p.seat.label,
                room_id=p.seat.room_id,
                room_name=p.seat.room_name,
                floor_name=p.seat.floor_name,
            )
            if p.seat
            else None
        ),
        updated_at=p.updated_at,
        is_stale=p.is_stale,
        skills=[
            UserSkillResponse(category=s.category, name=s.name, years=s.years) for s in p.skills
        ],
    )


@router.get("", response_model=list[PersonResponse])
def search_people(
    q: Annotated[str | None, Query(max_length=50, description="名前の一部")] = None,
    skill: Annotated[
        list[str],
        Query(max_length=5, description="スキル名（複数指定するとすべてを持つ人）"),
    ] = [],  # noqa: B006 （FastAPI のクエリ指定で、呼び出しごとに新しいリストが作られる）
    min_years: Annotated[int, Query(ge=0, le=50, description="スキルの経験年数がこれ以上")] = 0,
    status: Annotated[list[PresenceStatus], Query(max_length=4)] = [],  # noqa: B006
    viewer: User = Depends(require_active_user),
    service: PeopleService = Depends(get_service),
) -> list[PersonResponse]:
    query = PeopleQuery(name=q, skills=tuple(skill), min_years=min_years, statuses=tuple(status))
    return [_response(p) for p in service.search(viewer, query)]

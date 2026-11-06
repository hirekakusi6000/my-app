from datetime import date
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field, StringConstraints

from app.entities.master_data import SkillCategory
from app.schemas.master_data import ItemName


def _blank_to_none(value: object) -> object:
    if isinstance(value, str) and not value.strip():
        return None
    return value


OptionalItemName = Annotated[ItemName | None, BeforeValidator(_blank_to_none)]
PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class ProfileRequest(BaseModel):
    name: PersonName
    birth_date: date
    position_name: OptionalItemName = None
    job_type_name: OptionalItemName = None
    default_seat_id: int | None = None


class SkillItem(BaseModel):
    category: SkillCategory
    name: ItemName
    years: int = Field(ge=0, le=50)


class SkillsRequest(BaseModel):
    skills: list[SkillItem] = Field(max_length=60)


class UserSkillResponse(BaseModel):
    category: SkillCategory
    name: str
    years: int


class MyProfileResponse(BaseModel):
    user_id: int
    name: str
    birth_date: date
    age: int
    position: str | None
    job_type: str | None
    is_engineer: bool
    default_seat_id: int | None
    avatar_url: str | None
    skills: list[UserSkillResponse]


class PresenceSummary(BaseModel):
    status: str
    comment: str | None


class ProfileViewResponse(BaseModel):
    """他の従業員から見るプロフィール（生年月日そのものは出さず、年齢だけを返す）。"""

    user_id: int
    name: str
    age: int
    position: str | None
    job_type: str | None
    is_engineer: bool
    avatar_url: str | None
    skills: list[UserSkillResponse]
    presence: PresenceSummary | None

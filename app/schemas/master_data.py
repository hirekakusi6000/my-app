from typing import Annotated

from pydantic import BaseModel, StringConstraints

from app.entities.master_data import SkillCategory

ItemName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class PositionResponse(BaseModel):
    id: int
    name: str


class JobTypeResponse(BaseModel):
    id: int
    name: str
    is_engineer: bool


class SkillResponse(BaseModel):
    id: int
    category: SkillCategory
    name: str


class NameRequest(BaseModel):
    name: ItemName


class JobTypeRequest(BaseModel):
    name: ItemName
    is_engineer: bool = False


class SkillCreateRequest(BaseModel):
    category: SkillCategory
    name: ItemName

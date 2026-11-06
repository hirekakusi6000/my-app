from typing import Annotated

from pydantic import BaseModel, Field

from app.schemas.auth import OrganizationName


class OrganizationResponse(BaseModel):
    id: int
    name: str
    created_at: str


class OrganizationUpdateRequest(BaseModel):
    name: OrganizationName


class OrganizationDeleteRequest(BaseModel):
    password: Annotated[str, Field(min_length=1, max_length=128)]
    confirm_name: Annotated[str, Field(min_length=1, max_length=100)]

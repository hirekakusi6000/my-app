from typing import Annotated

from pydantic import BaseModel, StringConstraints

from app.entities.trouble import TroubleStatus

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Body = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]


class TroubleCreateRequest(BaseModel):
    title: Title
    body: Body = ""


class TroubleUpdateRequest(BaseModel):
    title: Title | None = None
    body: Body | None = None
    status: TroubleStatus | None = None


class TroubleResponse(BaseModel):
    id: int
    user_id: int
    author_name: str | None
    author_avatar_url: str | None
    title: str
    body: str
    status: TroubleStatus
    is_mine: bool
    created_at: str
    updated_at: str

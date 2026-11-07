from typing import Annotated

from pydantic import BaseModel, BeforeValidator, StringConstraints

from app.entities.presence import PresenceStatus


def _blank_to_none(value: object) -> object:
    if isinstance(value, str):
        return value.strip() or None
    return value


Comment = Annotated[
    Annotated[str, StringConstraints(max_length=100)] | None, BeforeValidator(_blank_to_none)
]


class PresenceRequest(BaseModel):
    """comment を送らなかった場合は、今のコメントをそのまま残す。"""

    status: PresenceStatus
    seat_id: int | None = None
    comment: Comment = None


class SeatResponse(BaseModel):
    seat_id: int
    label: str | None
    room_id: int
    room_name: str
    floor_name: str


class PresenceResponse(BaseModel):
    user_id: int
    name: str | None
    avatar_url: str | None
    status: PresenceStatus
    comment: str | None
    seat: SeatResponse | None
    updated_at: str
    is_stale: bool  # 出勤中のまま、日本時間の今日になってから一度も更新していない


class ResetStaleResponse(BaseModel):
    count: int

from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field, StringConstraints

from app.entities.office import FurnitureType

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
RoomSize = Annotated[int, Field(ge=5, le=200)]


def _blank_to_none(value: object) -> object:
    if isinstance(value, str) and not value.strip():
        return None
    return value.strip() if isinstance(value, str) else value


Label = Annotated[
    Annotated[str, StringConstraints(max_length=50)] | None, BeforeValidator(_blank_to_none)
]


class FloorCreateRequest(BaseModel):
    name: Name


class FloorUpdateRequest(BaseModel):
    name: Name | None = None
    sort_order: int | None = Field(default=None, ge=0, le=1000)


class RoomCreateRequest(BaseModel):
    name: Name
    width: RoomSize = 30
    height: RoomSize = 20


class RoomUpdateRequest(BaseModel):
    name: Name | None = None
    width: RoomSize | None = None
    height: RoomSize | None = None
    sort_order: int | None = Field(default=None, ge=0, le=1000)


class RoomResponse(BaseModel):
    id: int
    floor_id: int
    name: str
    width: int
    height: int
    sort_order: int


class FloorResponse(BaseModel):
    id: int
    name: str
    sort_order: int
    rooms: list[RoomResponse]


class FurnitureItem(BaseModel):
    id: int | None = None
    type: FurnitureType
    label: Label = None
    x: int = Field(ge=0, le=200)
    y: int = Field(ge=0, le=200)
    width: int = Field(ge=1, le=200)
    height: int = Field(ge=1, le=200)
    rotation: Literal[0, 90, 180, 270] = 0


class LayoutRequest(BaseModel):
    furniture: list[FurnitureItem] = Field(max_length=500)


class LayoutResponse(BaseModel):
    room: RoomResponse
    floor_name: str
    furniture: list[FurnitureItem]


class OccupantResponse(BaseModel):
    seat_id: int
    user_id: int
    name: str | None
    status: str
    avatar_url: str | None
    has_open_trouble: bool = False

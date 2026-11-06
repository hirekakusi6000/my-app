from pydantic import BaseModel

from app.schemas.auth import Email, Password


class CreateUserRequest(BaseModel):
    email: Email
    initial_password: Password


class UpdateUserRequest(BaseModel):
    email: Email


class ResetPasswordRequest(BaseModel):
    new_password: Password


class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    name: str | None
    must_change_password: bool
    profile_completed: bool
    created_at: str


class UserListResponse(BaseModel):
    items: list[UserResponse]
    general_user_count: int
    general_user_limit: int

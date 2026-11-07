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


class ImportRowResponse(BaseModel):
    line: int
    email: str
    # 作成したときだけ、自動生成したものも含めて返す（確認だけのときは CSV に書かれた値のみ）
    initial_password: str | None
    password_provided: bool  # CSV に初期パスワードが書かれていたか（false なら自動生成）
    error: str | None


class ImportResponse(BaseModel):
    created: bool
    error: str | None
    rows: list[ImportRowResponse]

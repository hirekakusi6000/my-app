from typing import Annotated

from pydantic import AfterValidator, BaseModel, EmailStr, Field, StringConstraints


def _lower(value: str) -> str:
    return value.lower()


# メールアドレスは前後の空白を除き、小文字にそろえて扱う
Email = Annotated[EmailStr, AfterValidator(_lower)]
Password = Annotated[str, Field(min_length=8, max_length=128)]
OrganizationName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]


class SignupRequest(BaseModel):
    organization_name: OrganizationName
    email: Email
    password: Password


class LoginRequest(BaseModel):
    email: Email
    # ログイン時は長さで弾かず、照合の結果だけを返す（ルールを推測されないように）
    password: Annotated[str, Field(min_length=1, max_length=128)]


class ChangePasswordRequest(BaseModel):
    current_password: Annotated[str, Field(min_length=1, max_length=128)]
    new_password: Password


class OrganizationResponse(BaseModel):
    id: int
    name: str


class MeResponse(BaseModel):
    id: int
    email: str
    role: str
    must_change_password: bool
    profile_completed: bool
    organization: OrganizationResponse

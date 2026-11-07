import sqlite3

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.api.deps import get_avatar_storage, require_master
from app.db.connection import get_db
from app.entities.user import Role, User, UserSummary
from app.schemas.users import (
    CreateUserRequest,
    ImportResponse,
    ImportRowResponse,
    ResetPasswordRequest,
    UpdateUserRequest,
    UserListResponse,
    UserResponse,
)
from app.services.avatar_storage import AvatarStorage
from app.services.user_csv import MAX_CSV_BYTES, parse_user_csv
from app.services.user_service import MAX_GENERAL_USERS, UserService

router = APIRouter(prefix="/users", tags=["users"])


def get_user_service(
    conn: sqlite3.Connection = Depends(get_db),
    storage: AvatarStorage = Depends(get_avatar_storage),
) -> UserService:
    return UserService(conn, storage)


def _from_summary(s: UserSummary) -> UserResponse:
    return UserResponse(
        id=s.id,
        email=s.email,
        role=s.role.value,
        name=s.profile_name,
        must_change_password=s.must_change_password,
        profile_completed=s.profile_name is not None,
        created_at=s.created_at,
    )


def _from_user(u: User) -> UserResponse:
    return UserResponse(
        id=u.id,
        email=u.email,
        role=u.role.value,
        name=None,
        must_change_password=u.must_change_password,
        profile_completed=False,
        created_at=u.created_at,
    )


@router.get("", response_model=UserListResponse)
def list_users(
    master: User = Depends(require_master),
    service: UserService = Depends(get_user_service),
) -> UserListResponse:
    summaries = service.list_users(master)
    return UserListResponse(
        items=[_from_summary(s) for s in summaries],
        general_user_count=sum(1 for s in summaries if s.role is Role.GENERAL),
        general_user_limit=MAX_GENERAL_USERS,
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    body: CreateUserRequest,
    master: User = Depends(require_master),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    user = service.create_general_user(
        master, email=body.email, initial_password=body.initial_password
    )
    return _from_user(user)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    body: UpdateUserRequest,
    master: User = Depends(require_master),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    service.update_email(master, user_id, email=body.email)
    updated = next(s for s in service.list_users(master) if s.id == user_id)
    return _from_summary(updated)


@router.post("/{user_id}/password-reset", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    user_id: int,
    body: ResetPasswordRequest,
    master: User = Depends(require_master),
    service: UserService = Depends(get_user_service),
) -> None:
    service.reset_password(master, user_id, new_password=body.new_password)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    master: User = Depends(require_master),
    service: UserService = Depends(get_user_service),
) -> None:
    service.delete_user(master, user_id)


@router.post("/import", response_model=ImportResponse)
def import_users(
    file: UploadFile = File(...),
    dry_run: bool = Query(False, description="true なら内容の確認だけ行い、作成しない"),
    master: User = Depends(require_master),
    service: UserService = Depends(get_user_service),
) -> ImportResponse:
    """CSV で一般ユーザーをまとめて作成する。1行でもエラーがあれば1人も作成しない。"""
    data = file.file.read(MAX_CSV_BYTES + 1)
    rows = parse_user_csv(data)
    result = service.import_users(master, rows, dry_run=dry_run)
    return ImportResponse(
        created=result.created,
        error=result.error,
        rows=[
            ImportRowResponse(
                line=r.line,
                email=r.email,
                initial_password=r.initial_password if result.created else None,
                password_provided=source.initial_password is not None,
                error=r.error,
            )
            for r, source in zip(result.rows, rows, strict=True)
        ],
    )

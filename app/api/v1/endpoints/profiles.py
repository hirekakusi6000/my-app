import sqlite3

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import get_avatar_storage, require_active_user, require_general
from app.core.time import calculate_age, today_jst
from app.db.connection import get_db
from app.entities.profile import Profile, ProfileDetail, UserSkill
from app.entities.user import User
from app.schemas.profile import (
    MyProfileResponse,
    PresenceSummary,
    ProfileRequest,
    ProfileViewResponse,
    SkillsRequest,
    UserSkillResponse,
)
from app.services.avatar_storage import MAX_AVATAR_BYTES, AvatarStorage
from app.services.profile_service import ProfileService

router = APIRouter(tags=["profiles"])


def get_service(
    conn: sqlite3.Connection = Depends(get_db),
    storage: AvatarStorage = Depends(get_avatar_storage),
) -> ProfileService:
    return ProfileService(conn, storage)


def _avatar_url(profile: Profile) -> str | None:
    if not profile.avatar_path:
        return None
    # ファイル名が変わると URL も変わるので、画像を変えたときにブラウザの古いキャッシュが使われない
    return f"/api/v1/users/{profile.user_id}/avatar?v={profile.avatar_path[:8]}"


def _skill_list(skills: list[UserSkill]) -> list[UserSkillResponse]:
    return [UserSkillResponse(category=s.category, name=s.name, years=s.years) for s in skills]


def _skills(detail: ProfileDetail) -> list[UserSkillResponse]:
    return _skill_list(detail.skills)


def _my_profile(detail: ProfileDetail) -> MyProfileResponse:
    p = detail.profile
    return MyProfileResponse(
        user_id=p.user_id,
        name=p.name,
        birth_date=p.birth_date,
        age=calculate_age(p.birth_date, today_jst()),
        position=p.position,
        job_type=p.job_type,
        is_engineer=p.is_engineer,
        default_seat_id=p.default_seat_id,
        avatar_url=_avatar_url(p),
        skills=_skills(detail),
    )


# ───────── 自分のプロフィール（一般ユーザー、初回設定中も可） ─────────


@router.get("/me/profile", response_model=MyProfileResponse)
def read_my_profile(
    user: User = Depends(require_general),
    service: ProfileService = Depends(get_service),
) -> MyProfileResponse:
    return _my_profile(service.get_my_profile(user))


@router.put("/me/profile", response_model=MyProfileResponse)
def save_my_profile(
    body: ProfileRequest,
    user: User = Depends(require_general),
    service: ProfileService = Depends(get_service),
) -> MyProfileResponse:
    detail = service.save_profile(
        user,
        name=body.name,
        birth_date=body.birth_date,
        position_name=body.position_name,
        job_type_name=body.job_type_name,
        default_seat_id=body.default_seat_id,
    )
    return _my_profile(detail)


@router.put("/me/skills", response_model=list[UserSkillResponse])
def save_my_skills(
    body: SkillsRequest,
    user: User = Depends(require_general),
    service: ProfileService = Depends(get_service),
) -> list[UserSkillResponse]:
    skills = service.save_skills(user, [(s.category, s.name, s.years) for s in body.skills])
    return _skill_list(skills)


@router.put("/me/avatar", response_model=MyProfileResponse)
def upload_my_avatar(
    file: UploadFile = File(...),
    user: User = Depends(require_general),
    service: ProfileService = Depends(get_service),
) -> MyProfileResponse:
    # 上限＋1バイトまでだけ読む（巨大なファイルをすべてメモリに載せない）
    data = file.file.read(MAX_AVATAR_BYTES + 1)
    return _my_profile(service.set_avatar(user, data))


@router.delete("/me/avatar", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_avatar(
    user: User = Depends(require_general),
    service: ProfileService = Depends(get_service),
) -> None:
    service.delete_avatar(user)


# ───────── 他の従業員のプロフィール ─────────


@router.get("/profiles/{user_id}", response_model=ProfileViewResponse)
def read_profile(
    user_id: int,
    viewer: User = Depends(require_active_user),
    service: ProfileService = Depends(get_service),
) -> ProfileViewResponse:
    detail = service.get_profile_detail(viewer, user_id)
    p = detail.profile
    return ProfileViewResponse(
        user_id=p.user_id,
        name=p.name,
        age=calculate_age(p.birth_date, today_jst()),
        position=p.position,
        job_type=p.job_type,
        is_engineer=p.is_engineer,
        avatar_url=_avatar_url(p),
        skills=_skills(detail),
        presence=(
            PresenceSummary(status=detail.presence.status, comment=detail.presence.comment)
            if detail.presence
            else None
        ),
    )


@router.get("/users/{user_id}/avatar", response_class=FileResponse)
def read_avatar(
    user_id: int,
    viewer: User = Depends(require_active_user),
    service: ProfileService = Depends(get_service),
) -> FileResponse:
    path, media_type = service.get_avatar_file(viewer, user_id)
    return FileResponse(
        path,
        media_type=media_type,
        headers={
            "Cache-Control": "private, max-age=86400",
            "X-Content-Type-Options": "nosniff",
        },
    )

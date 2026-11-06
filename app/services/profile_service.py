"""プロフィール・技術スキル・プロフィール画像。"""

import sqlite3
from datetime import date
from pathlib import Path

from app.core.errors import BusinessRuleError, NotFoundError
from app.core.time import to_iso, today_jst, utc_now
from app.entities.master_data import SkillCategory
from app.entities.profile import ProfileDetail, UserSkill
from app.entities.user import Role, User
from app.repositories.furniture_repository import FurnitureRepository
from app.repositories.master_data_repository import (
    JobTypeRepository,
    PositionRepository,
    SkillRepository,
)
from app.repositories.presence_repository import PresenceRepository
from app.repositories.profile_repository import ProfileRepository, UserSkillRepository
from app.repositories.user_repository import UserRepository
from app.services.avatar_storage import AvatarStorage

MIN_BIRTH_DATE = date(1900, 1, 1)


class ProfileService:
    def __init__(self, conn: sqlite3.Connection, avatar_storage: AvatarStorage) -> None:
        self.conn = conn
        self.storage = avatar_storage
        self.profiles = ProfileRepository(conn)
        self.user_skills = UserSkillRepository(conn)
        self.positions = PositionRepository(conn)
        self.job_types = JobTypeRepository(conn)
        self.skills = SkillRepository(conn)
        self.furniture = FurnitureRepository(conn)
        self.presence = PresenceRepository(conn)
        self.users = UserRepository(conn)

    # ───────── 自分のプロフィール ─────────

    def get_my_profile(self, user: User) -> ProfileDetail:
        profile = self.profiles.get(user.id, user.organization_id)
        if profile is None:
            raise NotFoundError("プロフィールが未登録です", code="PROFILE_NOT_REGISTERED")
        seat = (
            self.furniture.seat_info(profile.default_seat_id, user.organization_id)
            if profile.default_seat_id
            else None
        )
        return ProfileDetail(
            profile=profile, skills=self.user_skills.list(user.id), default_seat=seat
        )

    def save_profile(
        self,
        user: User,
        *,
        name: str,
        birth_date: date,
        position_name: str | None,
        job_type_name: str | None,
        default_seat_id: int | None,
    ) -> ProfileDetail:
        if not (MIN_BIRTH_DATE <= birth_date <= today_jst()):
            raise BusinessRuleError("生年月日が正しくありません", code="INVALID_BIRTH_DATE")
        if default_seat_id is not None and not self.furniture.is_seat(
            default_seat_id, user.organization_id
        ):
            raise BusinessRuleError("選択した座席が見つかりません", code="INVALID_SEAT")

        org = user.organization_id
        with self.conn:
            # 候補にない名前は、その組織の候補に自動で追加する
            position_id = (
                self.positions.get_or_create(org, position_name) if position_name else None
            )
            job_type = self.job_types.get_or_create(org, job_type_name) if job_type_name else None
            self.profiles.upsert(
                user_id=user.id,
                name=name,
                birth_date=birth_date.isoformat(),
                position_id=position_id,
                job_type_id=job_type.id if job_type else None,
                default_seat_id=default_seat_id,
                now=to_iso(utc_now()),
            )
            # エンジニア以外の職種になった場合、技術スキルは持たない
            if job_type is None or not job_type.is_engineer:
                self.user_skills.clear(user.id)
        return self.get_my_profile(user)

    def save_skills(
        self, user: User, items: list[tuple[SkillCategory, str, int]]
    ) -> list[UserSkill]:
        profile = self.get_my_profile(user).profile
        if not profile.is_engineer:
            raise BusinessRuleError(
                "技術スキルは職種がエンジニアの場合に登録できます", code="SKILLS_NOT_ALLOWED"
            )
        keys = [(category, name.casefold()) for category, name, _ in items]
        if len(keys) != len(set(keys)):
            raise BusinessRuleError("同じスキルが重複しています", code="DUPLICATE_SKILL")

        with self.conn:
            ids = [
                (self.skills.get_or_create(user.organization_id, category, name), years)
                for category, name, years in items
            ]
            self.user_skills.replace(user.id, ids)
        return self.user_skills.list(user.id)

    # ───────── プロフィール画像 ─────────

    def set_avatar(self, user: User, data: bytes) -> ProfileDetail:
        old = self.get_my_profile(user).profile.avatar_path
        filename = self.storage.save(data)
        try:
            with self.conn:
                self.profiles.set_avatar(user.id, filename, to_iso(utc_now()))
        except Exception:
            self.storage.delete(filename)
            raise
        self.storage.delete(old)
        return self.get_my_profile(user)

    def delete_avatar(self, user: User) -> None:
        old = self.get_my_profile(user).profile.avatar_path
        with self.conn:
            self.profiles.set_avatar(user.id, None, to_iso(utc_now()))
        self.storage.delete(old)

    # ───────── 他の従業員のプロフィール ─────────

    def get_profile_detail(self, viewer: User, user_id: int) -> ProfileDetail:
        """同じ組織の一般ユーザーのプロフィール。見つからなければ 404。"""
        profile = self.profiles.get(user_id, viewer.organization_id)
        target = self.users.get(user_id, viewer.organization_id)
        if profile is None or target is None or target.role is not Role.GENERAL:
            raise NotFoundError("プロフィールが見つかりません")
        return ProfileDetail(
            profile=profile,
            skills=self.user_skills.list(user_id),
            presence=self.presence.get(user_id, viewer.organization_id),
        )

    def get_avatar_file(self, viewer: User, user_id: int) -> tuple[Path, str]:
        profile = self.profiles.get(user_id, viewer.organization_id)
        if profile is None or profile.avatar_path is None:
            raise NotFoundError("画像が登録されていません")
        path = self.storage.path(profile.avatar_path)
        if not path.exists():
            raise NotFoundError("画像が登録されていません")
        return path, self.storage.media_type(profile.avatar_path)

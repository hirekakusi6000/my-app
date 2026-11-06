import sqlite3
from dataclasses import dataclass
from datetime import date

from app.entities.master_data import SkillCategory


@dataclass(frozen=True)
class UserSkill:
    category: SkillCategory
    name: str
    years: int

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "UserSkill":
        return cls(category=SkillCategory(row["category"]), name=row["name"], years=row["years"])


@dataclass(frozen=True)
class Profile:
    user_id: int
    name: str
    birth_date: date
    position: str | None
    job_type: str | None
    is_engineer: bool
    avatar_path: str | None
    default_seat_id: int | None
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Profile":
        return cls(
            user_id=row["user_id"],
            name=row["name"],
            birth_date=date.fromisoformat(row["birth_date"]),
            position=row["position_name"],
            job_type=row["job_type_name"],
            is_engineer=bool(row["is_engineer"]),
            avatar_path=row["avatar_path"],
            default_seat_id=row["default_seat_id"],
            updated_at=row["updated_at"],
        )


@dataclass(frozen=True)
class Presence:
    status: str
    seat_id: int | None
    comment: str | None


@dataclass(frozen=True)
class ProfileDetail:
    """プロフィール＋スキル（＋他の人から見るときは在席状態）。"""

    profile: Profile
    skills: list[UserSkill]
    presence: Presence | None = None

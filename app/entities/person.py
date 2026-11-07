from dataclasses import dataclass

from app.entities.office import SeatInfo
from app.entities.presence import PresenceStatus
from app.entities.profile import UserSkill


@dataclass(frozen=True)
class Person:
    """メンバー検索の結果1人分。"""

    user_id: int
    name: str
    avatar_path: str | None
    position: str | None
    job_type: str | None
    status: PresenceStatus
    comment: str | None
    seat: SeatInfo | None
    skills: tuple[UserSkill, ...]


@dataclass(frozen=True)
class PeopleQuery:
    """メンバー検索の条件。指定しなかった条件では絞り込まない。"""

    name: str | None = None  # 名前の一部
    skills: tuple[str, ...] = ()  # すべてを持っている人（大文字・小文字は区別しない）
    min_years: int = 0  # 指定したスキルの経験年数がこれ以上
    statuses: tuple[PresenceStatus, ...] = ()  # いずれかの状態の人

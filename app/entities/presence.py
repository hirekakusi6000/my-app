from dataclasses import dataclass
from enum import StrEnum

from app.entities.office import SeatInfo


class PresenceStatus(StrEnum):
    NOT_WORKING = "not_working"  # 未出勤
    PRESENT = "present"  # 在席中（座席あり）
    AWAY = "away"  # 離席中（座席は確保したまま）
    REMOTE = "remote"  # リモート

    @property
    def has_seat(self) -> bool:
        return self in (PresenceStatus.PRESENT, PresenceStatus.AWAY)


@dataclass(frozen=True)
class PresenceEntry:
    """従業員1人の勤務状況（名前・座席の場所つき）。"""

    user_id: int
    name: str | None
    avatar_path: str | None
    status: PresenceStatus
    comment: str | None
    seat: SeatInfo | None
    updated_at: str

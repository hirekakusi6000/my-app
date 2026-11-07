from dataclasses import dataclass
from enum import StrEnum

from app.core.time import is_before_today_jst
from app.entities.office import SeatInfo


class PresenceStatus(StrEnum):
    NOT_WORKING = "not_working"  # 未出勤
    PRESENT = "present"  # 在席中（座席あり）
    AWAY = "away"  # 離席中（座席は確保したまま）
    REMOTE = "remote"  # リモート

    @property
    def has_seat(self) -> bool:
        return self in (PresenceStatus.PRESENT, PresenceStatus.AWAY)


def is_stale(status: str, updated_at: str) -> bool:
    """出勤中（在席・離席・リモート）のまま、日本時間の今日になってから一度も更新していないか。

    日付が変わっても状態はリセットしない仕様なので、退勤し忘れていそうな人を見分けるために使う。
    """
    return PresenceStatus(status) is not PresenceStatus.NOT_WORKING and is_before_today_jst(
        updated_at
    )


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

    @property
    def is_stale(self) -> bool:
        return is_stale(self.status, self.updated_at)

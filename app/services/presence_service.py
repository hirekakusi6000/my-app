"""出勤・在席の管理。

状態の変わり方:
  出社（在席中）… 座席が必要。空いている自分の組織の椅子を選ぶ（座席変更も同じ操作）
  離席中        … 出社中（在席中・離席中）の人だけがなれる。座席はそのまま確保する
  リモート      … 座席は空く
  未出勤（退勤）… 座席は空く
日付が変わっても状態は変えない（本人が変えるまで、またはマスターが座席を空けるまでそのまま）。
"""

import sqlite3
from typing import Final

from app.core.errors import BusinessRuleError, ConflictError, NotFoundError
from app.core.time import start_of_today_jst, to_iso, utc_now
from app.entities.presence import PresenceEntry, PresenceStatus
from app.entities.user import User
from app.repositories.furniture_repository import FurnitureRepository
from app.repositories.presence_repository import PresenceRepository

_KEEP: Final = object()  # コメントを変更しないことを表す目印


class PresenceService:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.presence = PresenceRepository(conn)
        self.furniture = FurnitureRepository(conn)

    def get_mine(self, user: User) -> PresenceEntry:
        entries = self.presence.list_entries(user.organization_id, user_id=user.id)
        if not entries:
            raise NotFoundError("勤務状況が見つかりません")
        return entries[0]

    def list_all(self, user: User) -> list[PresenceEntry]:
        return self.presence.list_entries(user.organization_id)

    def update_mine(
        self,
        user: User,
        *,
        status: PresenceStatus,
        seat_id: int | None = None,
        comment: str | None | object = _KEEP,
    ) -> PresenceEntry:
        org = user.organization_id
        current = self.presence.get(user.id, org)
        if current is None:
            raise NotFoundError("勤務状況が見つかりません")

        if status is PresenceStatus.PRESENT:
            if seat_id is None:
                raise BusinessRuleError("座席を選んでください", code="SEAT_REQUIRED")
            if not self.furniture.is_seat(seat_id, org):
                raise BusinessRuleError("選択した座席が見つかりません", code="INVALID_SEAT")
        elif status is PresenceStatus.AWAY:
            if not PresenceStatus(current.status).has_seat:
                raise BusinessRuleError(
                    "出社していないため、離席中にはできません", code="INVALID_TRANSITION"
                )
            seat_id = current.seat_id  # 離席中も座席はそのまま
        else:
            seat_id = None

        new_comment = current.comment if comment is _KEEP else comment
        try:
            with self.conn:
                self.presence.update(
                    user_id=user.id,
                    organization_id=org,
                    status=status,
                    seat_id=seat_id,
                    comment=new_comment,  # type: ignore[arg-type]
                    now=to_iso(utc_now()),
                )
        except sqlite3.IntegrityError as exc:
            # UNIQUE 制約により、同時に同じ座席を選んだ場合も片方だけが成功する
            raise ConflictError(
                "この座席は他の人が使用中です。別の座席を選んでください", code="SEAT_OCCUPIED"
            ) from exc
        return self.get_mine(user)

    def reset_stale(self, master: User) -> int:
        """日本時間の今日になってから更新していない出勤中の人を、まとめて「未出勤」に戻す。"""
        with self.conn:
            return self.presence.reset_stale(
                master.organization_id, before=start_of_today_jst(), now=to_iso(utc_now())
            )

    def release_seat(self, master: User, seat_id: int) -> None:
        """マスターが座席を強制的に空ける（座っていた人は未出勤に戻る）。"""
        org = master.organization_id
        if self.presence.find_user_on_seat(seat_id, org) is None:
            raise NotFoundError("この座席には誰も座っていません")
        with self.conn:
            self.presence.release_seats([seat_id], org, to_iso(utc_now()))
